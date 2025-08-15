from django.db import models
import logging
from urllib.parse import urlparse, urlunparse
import boto3
from django.conf import settings
import requests
import uuid
import time
import mimetypes
from .groq_mixin import GroqMixin
from .aws_mixin import AwsMixin
from .taggable_mixin import TaggableMixin
from .summarizable_mixin import SummarizableMixin
import boto3
import time
import uuid

logger = logging.getLogger(__name__)
transcribe_client = boto3.client('transcribe', region_name='us-east-1')

class Podcast(models.Model, GroqMixin, AwsMixin, TaggableMixin, SummarizableMixin):
    rss_feed = models.ForeignKey('RSSFeed', on_delete=models.CASCADE, related_name='podcasts', blank=True, null=True, help_text="RSS feed this podcast came from")
    raw_audio_url = models.URLField(max_length=2000, help_text="URL of the raw audio file")
    transcript = models.TextField(blank=True, null=True, help_text="Raw transcript from speech-to-text")
    script_transcript = models.TextField(blank=True, null=True, help_text="Formatted transcript with speaker identification")
    summary = models.TextField(blank=True, null=True, help_text="AI-generated summary of the episode")
    title = models.CharField(max_length=512, blank=True, null=True, help_text="Title of the podcast episode")
    tags = models.ManyToManyField('Tag', blank=True, related_name='podcasts', help_text="Tags associated with this podcast")
    release_date = models.DateTimeField(blank=True, null=True, help_text="Original release date of the podcast episode")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.raw_audio_url
    
    def clean_url(self, url):
        """
        Remove URL parameters from the given URL.
        Returns the clean URL without query parameters.
        """
        if not url:
            return url
        
        try:
            parsed = urlparse(url)
            # Reconstruct URL without query parameters
            clean_url = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                '',  # Remove query string
                ''   # Remove fragment
            ))
            return clean_url
        except Exception as e:
            logger.warning(f"Failed to clean URL {url}: {str(e)}")
            return url
    
    def upload_audio_to_s3(self, audio_url):
        """
        Upload audio file from URL to S3 and return the S3 URI.
        Returns the S3 URI or None if failed.
        """
        try:
            from botocore.exceptions import ClientError, NoCredentialsError
            
            # Get S3 configuration
            bucket_name = getattr(settings, 'AWS_S3_BUCKET', None)
            if not bucket_name:
                logger.error("AWS_S3_BUCKET not configured")
                return None
            
            # Initialize S3 client
            s3_client = boto3.client(
                's3',
                region_name=getattr(settings, 'AWS_REGION', 'us-east-1'),
                aws_access_key_id=getattr(settings, 'AWS_ACCESS_KEY_ID', None),
                aws_secret_access_key=getattr(settings, 'AWS_SECRET_ACCESS_KEY', None)
            )
            
            # Download the audio file
            logger.info(f"Downloading audio file from: {audio_url}")
            response = requests.get(audio_url, stream=True, timeout=300)
            response.raise_for_status()
            
            # Determine file extension from URL or Content-Type
            parsed_url = urlparse(audio_url)
            file_extension = None
            
            # Try to get extension from URL path
            if '.' in parsed_url.path:
                file_extension = parsed_url.path.split('.')[-1].lower()
                # Clean common query parameters that might be appended
                if '?' in file_extension:
                    file_extension = file_extension.split('?')[0]
            
            # If no extension from URL, try to determine from Content-Type
            if not file_extension:
                content_type = response.headers.get('content-type', '')
                if content_type:
                    extension = mimetypes.guess_extension(content_type)
                    if extension:
                        file_extension = extension.lstrip('.')
            
            # Default to mp3 if we can't determine the format
            if not file_extension:
                file_extension = 'mp3'
            
            # Ensure valid audio file extension
            valid_extensions = ['mp3', 'wav', 'm4a', 'flac', 'ogg', 'aac', 'mp4']
            if file_extension not in valid_extensions:
                logger.warning(f"Unknown audio file extension: {file_extension}, defaulting to mp3")
                file_extension = 'mp3'
            
            # Generate unique S3 key
            unique_id = uuid.uuid4().hex[:8]
            s3_key = f"audio/podcast-{unique_id}.{file_extension}"
            
            # Determine content type for S3 upload
            content_type = response.headers.get('content-type', f'audio/{file_extension}')
            
            # Upload to S3
            logger.info(f"Uploading audio file to S3: s3://{bucket_name}/{s3_key}")
            s3_client.upload_fileobj(
                response.raw,
                bucket_name,
                s3_key,
                ExtraArgs={
                    'ContentType': content_type,
                    'Metadata': {
                        'original_url': audio_url[:1000],  # Truncate to avoid metadata limits
                        'podcast_id': str(self.id) if self.id else 'new',
                        'upload_timestamp': str(time.time())
                    }
                }
            )
            
            # Return S3 URI
            s3_uri = f"s3://{bucket_name}/{s3_key}"
            logger.info(f"Audio file uploaded successfully to: {s3_uri}")
            return s3_uri
            
        except NoCredentialsError:
            logger.error("AWS credentials not configured for S3 upload")
            return None
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            logger.error(f"AWS S3 client error during upload ({error_code}): {str(e)}")
            return None
        except requests.exceptions.Timeout:
            logger.error(f"Timeout downloading audio file from {audio_url}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download audio file from {audio_url}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Failed to upload audio to S3: {str(e)}")
            return None

    def save(self, *args, **kwargs):
        """
        Override save to clean URL parameters from raw_audio_url.
        """
        if self.raw_audio_url:
            self.raw_audio_url = self.clean_url(self.raw_audio_url)
        super().save(*args, **kwargs)
    
    def generate_transcript(self, method='groq'):
        """
        Generate transcript using the specified method or auto-detect best available.
        
        Args:
            method (str): 'groq', 'aws', or 'auto' to choose automatically
            
        Returns:
            str: The transcript text or None if failed
        """
        logger.info(f"Generating transcript for: {self.raw_audio_url} using method: {method}")
        
        if method == 'auto':
            # Auto-select based on available configuration
            groq_key = getattr(settings, 'GROQ_API_KEY', None)
            aws_configured = all([
                getattr(settings, 'AWS_ACCESS_KEY_ID', None),
                getattr(settings, 'AWS_SECRET_ACCESS_KEY', None)
            ])
            
            if groq_key:
                method = 'groq'
                logger.info("Auto-selected Groq for transcription")
            elif aws_configured:
                method = 'aws'
                logger.info("Auto-selected AWS Transcribe for transcription")
            else:
                logger.error("No transcription service configured (GROQ_API_KEY or AWS credentials)")
                return None
        
        if method == 'groq':
            return self.get_transcript_from_groq()
        elif method == 'aws':
            return self.get_transcript_from_aws()
        else:
            logger.error(f"Unknown transcription method: {method}")
            return None

    def process_complete_workflow(self):
        """
        Complete workflow: generate transcript, apply tags, create speaker script, and generate summary.
        Returns a summary of what was accomplished.
        """
        results = {
            'transcript_generated': False,
            'tags_applied': 0,
            'script_generated': False,
            'summary_generated': False,
            'errors': []
        }
        
        try:
            # Step 1: Generate transcript if needed
            if not self.transcript:
                transcript = self.generate_transcript()
                if transcript:
                    results['transcript_generated'] = True
                    logger.info(f"Transcript generated for: {self.raw_audio_url}")
                else:
                    results['errors'].append("Failed to generate transcript")
                    return results
            
            # Step 2: Apply tags
            applied_tags = self.suggest_and_apply_tags()
            if applied_tags:
                results['tags_applied'] = len(applied_tags)
                logger.info(f"Applied {len(applied_tags)} tags to: {self.raw_audio_url}")
            else:
                results['errors'].append("Failed to apply tags")
            
            # Step 3: Generate speaker script
            script = self.generate_speaker_script()
            if script:
                results['script_generated'] = True
                logger.info(f"Speaker script generated for: {self.raw_audio_url}")
            else:
                results['errors'].append("Failed to generate speaker script")
            
            # Step 4: Generate episode summary
            summary = self.generate_summary()
            if summary:
                results['summary_generated'] = True
                logger.info(f"Episode summary generated for: {self.raw_audio_url}")
            else:
                results['errors'].append("Failed to generate episode summary")
            
            return results
            
        except Exception as e:
            logger.error(f"Error in complete workflow for {self.raw_audio_url}: {str(e)}")
            results['errors'].append(f"Workflow error: {str(e)}")
            return results
    
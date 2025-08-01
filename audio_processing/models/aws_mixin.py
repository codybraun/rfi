import boto3
from django.conf import settings
import uuid
import time
import boto3
import time
import uuid
from botocore.exceptions import ClientError, NoCredentialsError
import logging

logger = logging.getLogger(__name__)
transcribe_client = boto3.client('transcribe', region_name='us-east-1')

class AwsMixin():

    def get_transcript_from_aws(self):
        """
        Process the audio file to generate a transcript using AWS Transcribe.
        Ensures the audio file is uploaded to S3 first if needed.
        Returns the transcript text or None if failed.
        """

        s3_uri = self.upload_audio_to_s3(self.raw_audio_url)
        logger.info(f"Processing transcript with AWS Transcribe for: {self.raw_audio_url}")
        
        try:
            # First, ensure we have an S3 URI for the audio file
            if not s3_uri:
                logger.error(f"Failed to get S3 URI for audio file: {self.raw_audio_url}")
                return None
            
            # Initialize AWS Transcribe client
            transcribe_client = boto3.client(
                'transcribe',
                region_name=getattr(settings, 'AWS_REGION', 'us-east-1'),
                aws_access_key_id=getattr(settings, 'AWS_ACCESS_KEY_ID', None),
                aws_secret_access_key=getattr(settings, 'AWS_SECRET_ACCESS_KEY', None)
            )
            
            # Generate unique job name
            job_name = f"podcast-transcribe-{uuid.uuid4().hex[:8]}"
            
            # Determine audio format from S3 URI
            audio_format = 'mp3'  # default
            if s3_uri.lower().endswith('.wav'):
                audio_format = 'wav'
            elif s3_uri.lower().endswith('.m4a'):
                audio_format = 'm4a'
            elif s3_uri.lower().endswith('.flac'):
                audio_format = 'flac'
            elif s3_uri.lower().endswith('.ogg'):
                audio_format = 'ogg'
            
            # Start transcription job
            output_bucket = getattr(settings, 'AWS_TRANSCRIBE_OUTPUT_BUCKET', None)
            
            job_params = {
                'TranscriptionJobName': job_name,
                'Media': {'MediaFileUri': s3_uri},
                'MediaFormat': audio_format,
                'LanguageCode': 'en-US',
                'Settings': {
                    'ShowSpeakerLabels': True,
                    'MaxSpeakerLabels': 10,
                    'ShowAlternatives': True,
                    'MaxAlternatives': 2
                }
            }
            
            # Only add OutputBucketName if it's configured and not empty
            if output_bucket and output_bucket.strip():
                job_params['OutputBucketName'] = output_bucket.strip()
            
            response = transcribe_client.start_transcription_job(**job_params)
            
            logger.info(f"Started AWS Transcribe job: {job_name} for S3 URI: {s3_uri}")
            
            # Poll for job completion
            max_wait_time = 600
            poll_interval = 30
            elapsed_time = 0
            
            while elapsed_time < max_wait_time:
                response = transcribe_client.get_transcription_job(
                    TranscriptionJobName=job_name
                )
                
                status = response['TranscriptionJob']['TranscriptionJobStatus']
                
                if status == 'COMPLETED':
                    # Get transcript from the output location
                    transcript_uri = response['TranscriptionJob']['Transcript']['TranscriptFileUri']
                    transcript_text = self._download_aws_transcript(transcript_uri)
                    
                    if transcript_text:
                        self.transcript = transcript_text
                        self.save()
                        logger.info(f"AWS Transcribe completed for: {self.raw_audio_url}")
                        
                        # Cleanup the transcription job
                        try:
                            transcribe_client.delete_transcription_job(
                                TranscriptionJobName=job_name
                            )
                        except Exception as e:
                            logger.warning(f"Failed to cleanup transcription job {job_name}: {str(e)}")
                        
                        return transcript_text
                    else:
                        logger.error(f"Failed to download transcript from AWS for: {self.raw_audio_url}")
                        return None
                        
                elif status == 'FAILED':
                    failure_reason = response['TranscriptionJob'].get('FailureReason', 'Unknown error')
                    logger.error(f"AWS Transcribe job failed for {self.raw_audio_url}: {failure_reason}")
                    return None
                
                # Wait before polling again
                time.sleep(poll_interval)
                elapsed_time += poll_interval
                logger.info(f"AWS Transcribe job {job_name} status: {status} (elapsed: {elapsed_time}s)")
            
            # Job didn't complete within time limit
            logger.error(f"AWS Transcribe job {job_name} timed out after {max_wait_time} seconds")
            return None
            
        except NoCredentialsError:
            logger.error("AWS credentials not configured for Transcribe")
            return None
        except ClientError as e:
            logger.error(f"AWS Transcribe client error for {self.raw_audio_url}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Failed to process transcript with AWS Transcribe for {self.raw_audio_url}: {str(e)}")
            return None
    
    def _download_aws_transcript(self, transcript_uri):
        """
        Download and parse the transcript from AWS Transcribe output using boto3.
        Returns the transcript text or None if failed.
        """
        try:
            import json
            from urllib.parse import urlparse
            
            # Parse the S3 URI to get bucket and key
            parsed_uri = urlparse(transcript_uri)
            
            # Handle both s3:// and https://s3.amazonaws.com formats
            if parsed_uri.scheme == 's3':
                bucket_name = parsed_uri.netloc
                object_key = parsed_uri.path.lstrip('/')
            else:
                # Handle https://s3.amazonaws.com/bucket/key format
                path_parts = parsed_uri.path.lstrip('/').split('/', 1)
                if len(path_parts) == 2:
                    bucket_name = path_parts[0]
                    object_key = path_parts[1]
                else:
                    # Handle https://bucket.s3.amazonaws.com/key format
                    bucket_name = parsed_uri.netloc.split('.')[0]
                    object_key = parsed_uri.path.lstrip('/')
            
            logger.info(f"Downloading transcript from S3: bucket={bucket_name}, key={object_key}")
            
            # Initialize S3 client with proper credentials
            s3_client = boto3.client(
                's3',
                region_name=getattr(settings, 'AWS_REGION', 'us-east-1'),
                aws_access_key_id=getattr(settings, 'AWS_ACCESS_KEY_ID', None),
                aws_secret_access_key=getattr(settings, 'AWS_SECRET_ACCESS_KEY', None)
            )
            
            # Download the transcript file from S3
            response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
            transcript_content = response['Body'].read().decode('utf-8')
            
            # Parse the JSON transcript
            transcript_data = json.loads(transcript_content)
            
            # Extract the transcript text from AWS format
            if 'results' in transcript_data and 'transcripts' in transcript_data['results']:
                transcripts = transcript_data['results']['transcripts']
                if transcripts and len(transcripts) > 0:
                    return transcripts[0].get('transcript', '')
            
            logger.error("Invalid transcript format from AWS Transcribe")
            return None
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == 'NoSuchKey':
                logger.error(f"Transcript file not found in S3: {transcript_uri}")
            elif error_code == 'AccessDenied':
                logger.error(f"Access denied to transcript file in S3: {transcript_uri}")
                logger.error("Please ensure your AWS credentials have s3:GetObject permission for the transcribe output bucket")
            else:
                logger.error(f"AWS S3 error downloading transcript ({error_code}): {str(e)}")
            return None
        except NoCredentialsError:
            logger.error("AWS credentials not configured for S3 transcript download")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AWS transcript JSON: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error downloading AWS transcript: {str(e)}")
            return None

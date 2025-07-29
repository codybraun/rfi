from django.db import models
import logging
from urllib.parse import urlparse, urlunparse

logger = logging.getLogger(__name__)


class Podcast(models.Model):
    rss_feed = models.ForeignKey('RSSFeed', on_delete=models.CASCADE, related_name='podcasts', blank=True, null=True, help_text="RSS feed this podcast came from")
    raw_audio_url = models.URLField(max_length=2000, help_text="URL of the raw audio file")
    transcript = models.TextField(blank=True, null=True)
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
    
    def save(self, *args, **kwargs):
        """
        Override save to clean URL parameters from raw_audio_url.
        """
        if self.raw_audio_url:
            self.raw_audio_url = self.clean_url(self.raw_audio_url)
        super().save(*args, **kwargs)
    
    def process_transcript(self):
        """
        Process the audio file to generate a transcript using the Groq API.
        Returns the transcript text or None if failed.
        """
        from django.conf import settings
        import requests
        
        logger.info(f"Processing transcript for: {self.raw_audio_url}")
        
        try:
            url = "https://api.groq.com/openai/v1/audio/transcriptions"
            api_key = getattr(settings, 'GROQ_API_KEY', '')
            
            if not api_key:
                logger.error("GROQ_API_KEY not configured")
                return None
            
            headers = {"Authorization": f"Bearer {api_key}"}
            clean_url = self.clean_url(self.raw_audio_url)
            files = {
                "url": (None, clean_url),
                "model": (None, "whisper-large-v3"),
                "language": (None, "en"),
                "response_format": (None, "json"),
            }
            response = requests.post(url, headers=headers, files=files)
            response.raise_for_status()
            
            transcript = response.json().get("text", "")
            
            if transcript:
                self.transcript = transcript
                self.save()
                logger.info(f"Transcript updated for: {self.raw_audio_url}")
                return transcript
            else:
                logger.warning(f"No transcript returned for: {self.raw_audio_url}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed for {self.raw_audio_url}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Failed to process transcript for {self.raw_audio_url}: {str(e)}")
            return None

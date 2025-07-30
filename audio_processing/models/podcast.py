from django.db import models
import logging
from urllib.parse import urlparse, urlunparse

logger = logging.getLogger(__name__)


class Podcast(models.Model):
    rss_feed = models.ForeignKey('RSSFeed', on_delete=models.CASCADE, related_name='podcasts', blank=True, null=True, help_text="RSS feed this podcast came from")
    raw_audio_url = models.URLField(max_length=2000, help_text="URL of the raw audio file")
    transcript = models.TextField(blank=True, null=True)
    tags = models.ManyToManyField('Tag', blank=True, related_name='podcasts', help_text="Tags associated with this podcast")
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
    
    def _validate_transcript(self):
        """Check if transcript exists and is valid for processing."""
        if not self.transcript or not self.transcript.strip():
            logger.warning(f"No transcript available for podcast: {self.raw_audio_url}")
            return False
        return True
    
    def _get_available_tags(self):
        """Get all available tags formatted for LLM processing."""
        from .tag import Tag
        all_tags = Tag.objects.all()
        
        if not all_tags.exists():
            logger.warning("No tags available in the database")
            return None
        
        tag_list = []
        for tag in all_tags:
            tag_info = {
                "id": tag.id,
                "name": tag.name,
                "description": tag.description or tag.name
            }
            tag_list.append(tag_info)
        
        return tag_list
    
    def _call_groq_for_tag_suggestions(self, tag_list):
        """Call Groq API to get tag suggestions based on transcript."""
        from django.conf import settings
        import requests
        
        url = "https://api.groq.com/openai/v1/chat/completions"
        api_key = getattr(settings, 'GROQ_API_KEY', '')
        
        if not api_key:
            logger.error("GROQ_API_KEY not configured")
            return None
        
        # Get the prompt from prompts file
        from ..prompts import get_tag_suggestion_prompt
        prompt = get_tag_suggestion_prompt(tag_list, self.transcript[:2000])
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "llama3-8b-8192",
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3,
            "max_tokens": 100,
        }
        
        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            
            result = response.json()
            content = result['choices'][0]['message']['content'].strip()
            return content
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed for tag suggestion: {str(e)}")
            return None
    
    def _parse_and_apply_tags(self, llm_response):
        """Parse LLM response and apply valid tags to the podcast."""
        import json
        from .tag import Tag
        
        try:
            suggested_tag_ids = json.loads(llm_response)
            if not isinstance(suggested_tag_ids, list):
                logger.error(f"Expected list of tag IDs, got: {type(suggested_tag_ids)}")
                return None
            
            applied_tags = []
            for tag_id in suggested_tag_ids:
                try:
                    tag = Tag.objects.get(id=tag_id)
                    self.tags.add(tag)
                    applied_tags.append(tag_id)
                    logger.info(f"Applied tag '{tag.name}' to podcast: {self.raw_audio_url}")
                except Tag.DoesNotExist:
                    logger.warning(f"Tag with ID {tag_id} does not exist")
            
            if applied_tags:
                logger.info(f"Successfully applied {len(applied_tags)} tags to podcast: {self.raw_audio_url}")
                return applied_tags
            else:
                logger.warning(f"No valid tags were applied to podcast: {self.raw_audio_url}")
                return []
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {llm_response}")
            return None
    
    def suggest_and_apply_tags(self):
        """
        Use Groq LLM to analyze the podcast transcript and suggest relevant tags.
        Returns a list of applied tag IDs or None if failed.
        """
        # Validate transcript
        if not self._validate_transcript():
            return None
        
        # Get available tags
        tag_list = self._get_available_tags()
        if tag_list is None:
            return None
        
        logger.info(f"Analyzing transcript for tag suggestions: {self.raw_audio_url}")
        
        # Get tag suggestions from Groq
        llm_response = self._call_groq_for_tag_suggestions(tag_list)
        if llm_response is None:
            logger.error(f"Failed to get tag suggestions for podcast: {self.raw_audio_url}")
            return None
        
        # Parse and apply tags
        applied_tags = self._parse_and_apply_tags(llm_response)
        return applied_tags

    def generate_transcript(self):
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

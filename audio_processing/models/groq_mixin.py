import logging
from django.conf import settings
import requests
import re

logger = logging.getLogger(__name__)

class GroqMixin():

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
        
    
    def get_transcript_from_groq(self):
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
    
    def generate_speaker_script(self):
        """
        Use Groq LLM to convert the raw transcript into a formatted script with speaker identification.
        Returns the script transcript or None if failed.
        """
        # Validate transcript
        if not self._validate_transcript():
            return None
        
        logger.info(f"Generating speaker script for: {self.raw_audio_url}")
        
        try:
            from django.conf import settings
            import requests
            
            url = "https://api.groq.com/openai/v1/chat/completions"
            api_key = getattr(settings, 'GROQ_API_KEY', '')
            
            if not api_key:
                logger.error("GROQ_API_KEY not configured")
                return None
            
            # Get the prompt from prompts file
            from ..prompts import get_speaker_transcript_prompt
            prompt = get_speaker_transcript_prompt(self.transcript)
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "deepseek-r1-distill-llama-70b",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.3,
                "max_tokens": 8000
            }
            
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            
            result = response.json()
            script_content = result['choices'][0]['message']['content'].strip()

            script_content = re.sub(r'<think>.*?</think>', '', script_content, flags=re.DOTALL).strip()
            
            if script_content:
                self.script_transcript = script_content
                self.save()
                logger.info(f"Speaker script generated for: {self.raw_audio_url}")
                return script_content
            else:
                logger.warning(f"No script content returned for: {self.raw_audio_url}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed for script generation: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Failed to generate speaker script: {str(e)}")
            return None
import logging

logger = logging.getLogger(__name__)


class SummarizableMixin:
    """
    Mixin to provide summarization functionality using Groq LLM for content summarization.
    """
    
    def generate_summary(self):
        """
        Generate a summary of the content using Groq LLM based on the transcript.
        Returns the summary text or None if failed.
        
        Note: This method requires the model to have a 'transcript' field and 'summary' field,
        and access to Groq API (usually from GroqMixin).
        """
        # Validate transcript
        if not hasattr(self, 'transcript') or not self.transcript or not self.transcript.strip():
            logger.warning(f"No transcript available for summary generation: {getattr(self, 'raw_audio_url', str(self))}")
            return None
        
        logger.info(f"Generating summary for {self.__class__.__name__}: {getattr(self, 'raw_audio_url', str(self))}")
        
        try:
            from django.conf import settings
            import requests
            
            url = "https://api.groq.com/openai/v1/chat/completions"
            api_key = getattr(settings, 'GROQ_API_KEY', '')
            
            if not api_key:
                logger.error("GROQ_API_KEY not configured")
                return None
            
            # Get the prompt from prompts file
            from ..prompts import get_episode_summary_prompt
            prompt = get_episode_summary_prompt(self.transcript)
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "llama3-70b-8192",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.3,
                "max_tokens": 1000
            }
            
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            
            result = response.json()
            summary_content = result['choices'][0]['message']['content'].strip()
            
            # Remove <think></think> blocks that some models include
            import re
            summary_content = re.sub(r'<think>.*?</think>', '', summary_content, flags=re.DOTALL).strip()
            
            if summary_content:
                if hasattr(self, 'summary'):
                    self.summary = summary_content
                    self.save()
                    logger.info(f"Summary generated for {self.__class__.__name__}: {getattr(self, 'raw_audio_url', str(self))}")
                else:
                    logger.warning(f"Model {self.__class__.__name__} does not have a 'summary' field")
                return summary_content
            else:
                logger.warning(f"No summary content returned for {self.__class__.__name__}: {getattr(self, 'raw_audio_url', str(self))}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed for summary generation: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Failed to generate summary for {self.__class__.__name__}: {str(e)}")
            return None

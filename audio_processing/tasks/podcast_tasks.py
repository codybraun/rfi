from celery import shared_task
from audio_processing.models import Podcast
import logging

logger = logging.getLogger(__name__)


@shared_task
def add_transcript(podcast_id):
    """
    Celery task to process a podcast file and generate transcript.
    """
    logger.info(f"Processing transcript for podcast ID: {podcast_id}")
    # Get or create podcast entry
    podcast = Podcast.objects.get(pk=podcast_id)
    
    # Process transcript using model method
    transcript = podcast.generate_transcript()
    
    if transcript:
        logger.info(f"Podcast transcript updated: {podcast}")
        return {"success": True, "transcript_length": len(transcript)}
    else:
        logger.error(f"Failed to process transcript for: {podcast}")
        return {"success": False, "error": "Failed to generate transcript"}

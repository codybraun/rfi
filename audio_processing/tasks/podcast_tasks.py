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

@shared_task
def suggest_and_apply_tags(podcast_id):
    """
    Celery task to suggest and apply tags to a podcast.
    """
    logger.info(f"Suggesting tags for podcast ID: {podcast_id}")
    
    try:
        podcast = Podcast.objects.get(pk=podcast_id)
        applied_tags = podcast.suggest_and_apply_tags()
        
        if applied_tags is not None:
            logger.info(f"Applied {len(applied_tags)} tags to podcast: {podcast.raw_audio_url[:50]}...")
            return {"success": True, "applied_tags": len(applied_tags)}
        else:
            logger.error(f"No tags applied for podcast: {podcast.raw_audio_url[:50]}")
            return {"success": False, "error": "No tags applied"}
    
    except Exception as e:
        logger.error(f"Error suggesting tags for podcast ID {podcast_id}: {str(e)}")
        return {"success": False, "error": str(e)}
    
@shared_task
def process_complete_workflow(podcast_id):
    """
    Celery task to process the complete workflow for a podcast:
    1. Generate transcript
    2. Suggest and apply tags
    """
    logger.info(f"Starting complete workflow for podcast ID: {podcast_id}")
    
    podcast = Podcast.objects.get(pk=podcast_id)
    return podcast.process_complete_workflow()
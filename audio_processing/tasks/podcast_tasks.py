from celery import shared_task
from audio_processing.models import Podcast


@shared_task
def process_file(public_filename):
    """
    Celery task to process a podcast file and generate transcript.
    """
    print(f"Processing S3 file: {public_filename}")
    
    # Get or create podcast entry
    podcast, created = Podcast.objects.get_or_create(raw_audio_url=public_filename)
    
    # Process transcript using model method
    transcript = podcast.process_transcript()
    
    if transcript:
        print(f"Podcast transcript updated: {podcast}")
        return {"success": True, "transcript_length": len(transcript)}
    else:
        print(f"Failed to process transcript for: {podcast}")
        return {"success": False, "error": "Failed to generate transcript"}

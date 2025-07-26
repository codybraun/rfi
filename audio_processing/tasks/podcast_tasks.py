from celery import shared_task
import requests
from django.conf import settings
from audio_processing.models import Podcast


@shared_task
def process_file(public_filename):
    print(f"Processing S3 file: {public_filename}")
    url = "https://api.lemonfox.ai/v1/audio/transcriptions"
    api_key = settings.WHISPER_API_KEY
    headers = {"Authorization": f"Bearer {api_key}"}
    data = {
        "file": public_filename,
        "language": "english",
        "response_format": "json",
    }
    response = requests.post(url, headers=headers, data=data)
    transcript = response.json().get("text", "")
    podcast, created = Podcast.objects.get_or_create(raw_audio_url=public_filename)
    podcast.transcript = transcript
    podcast.save()
    print(f"Podcast entry updated: {podcast}")

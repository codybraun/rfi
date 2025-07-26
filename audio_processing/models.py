from django.db import models
from django.utils import timezone
import feedparser
import logging

logger = logging.getLogger(__name__)


class RSSFeed(models.Model):
    name = models.CharField(max_length=200, help_text="Friendly name for the RSS feed")
    url = models.URLField(unique=True, help_text="RSS feed URL")
    description = models.TextField(blank=True, null=True, help_text="Description of the podcast feed")
    is_active = models.BooleanField(default=True, help_text="Whether to actively process this feed")
    last_processed = models.DateTimeField(blank=True, null=True, help_text="Last time this feed was processed")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "RSS Feed"
        verbose_name_plural = "RSS Feeds"
        ordering = ['-created_at']

    def __str__(self):
        return self.name
    
    def fetch_feed(self):
        """
        Fetch and parse the RSS feed.
        Returns the parsed feed object or None if failed.
        """
        logger.info(f"Fetching RSS feed: {self.url}")
        try:
            feed = feedparser.parse(self.url)
            
            # Update feed name if we have a title and current name is generic
            if (hasattr(feed, 'feed') and hasattr(feed.feed, 'title') and 
                feed.feed.title and self.name == f'RSS Feed from {self.url}'):
                self.name = feed.feed.title
                self.save()
            
            if feed.bozo:
                logger.warning(f"Feed has parsing issues: {self.url}")
                if hasattr(feed, 'bozo_exception'):
                    logger.warning(f"Bozo exception: {feed.bozo_exception}")
            
            return feed
        except Exception as e:
            logger.error(f"Failed to fetch feed {self.url}: {str(e)}")
            return None
    
    def create_podcast_from_entry(self, entry):
        """
        Creates a podcast from an RSS entry.
        Returns the created/existing Podcast object or None if failed.
        """
        title = entry.get('title', 'No Title')
        logger.info(f"Processing podcast entry: {title}")
        
        # Extract audio URL from enclosures
        audio_url = None
        if hasattr(entry, 'enclosures') and entry.enclosures:
            for enclosure in entry.enclosures:
                if enclosure.get('type', '').startswith('audio/'):
                    audio_url = enclosure.get('href')
                    break
        
        # Fallback: check for links that might be audio files
        if not audio_url and hasattr(entry, 'links'):
            for link in entry.links:
                if link.get('type', '').startswith('audio/'):
                    audio_url = link.get('href')
                    break
        
        if not audio_url:
            logger.warning(f"No audio URL found for entry: {title}")
            return None
        
        # Check if podcast already exists
        existing_podcast = Podcast.objects.filter(raw_audio_url=audio_url).first()
        if existing_podcast:
            logger.info(f"Podcast already exists: {title}")
            return existing_podcast
        
        # Create new podcast
        try:
            podcast = Podcast.objects.create(
                raw_audio_url=audio_url,
                rss_feed=self
            )
            logger.info(f"Created podcast: {title} - {audio_url}")
            return podcast
        except Exception as e:
            logger.error(f"Failed to create podcast for entry '{title}': {str(e)}")
            return None
    
    def process_feed(self):
        """
        Process this RSS feed and create podcasts for all entries.
        Returns a summary of the processing results.
        """
        if not self.is_active:
            logger.info(f"RSS feed is inactive: {self.url}")
            return {'error': "RSS feed is marked as inactive"}
        
        feed = self.fetch_feed()
        if not feed:
            return {'error': "Failed to fetch feed"}
        
        if not hasattr(feed, 'entries') or not feed.entries:
            logger.warning(f"No entries found in feed: {self.url}")
            return {'error': "No entries found in feed"}
        
        created_count = 0
        existing_count = 0
        failed_count = 0
        
        for entry in feed.entries:
            result = self.create_podcast_from_entry(entry)
            if result is None:
                failed_count += 1
            elif result:
                # Check if this was a new creation
                if result.created_at >= timezone.now() - timezone.timedelta(seconds=1):
                    created_count += 1
                else:
                    existing_count += 1
        
        # Update last_processed timestamp
        self.last_processed = timezone.now()
        self.save()
        
        summary = {
            'total_entries': len(feed.entries),
            'created': created_count,
            'existing': existing_count,
            'failed': failed_count,
            'rss_feed_id': self.id,
            'rss_feed_name': self.name
        }
        
        logger.info(f"RSS feed processing complete: {summary}")
        return summary
    
    def get_summary(self):
        """
        Get summary information about this RSS feed and its podcasts.
        """
        podcast_count = self.podcasts.count()
        
        return {
            'id': self.id,
            'name': self.name,
            'url': self.url,
            'is_active': self.is_active,
            'last_processed': self.last_processed,
            'podcast_count': podcast_count,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }


class Podcast(models.Model):
    rss_feed = models.ForeignKey(RSSFeed, on_delete=models.CASCADE, related_name='podcasts', blank=True, null=True, help_text="RSS feed this podcast came from")
    raw_audio_url = models.URLField()
    transcript = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.raw_audio_url

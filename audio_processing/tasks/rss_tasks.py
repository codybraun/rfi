import logging
from django.utils import timezone
from ..models import Podcast, RSSFeed
from celery import shared_task

logger = logging.getLogger(__name__)


def process_podcast_rss_feed(feed_url):
    """
    Process a podcast RSS feed by URL.
    Creates or gets the RSSFeed object and processes it.
    """
    logger.info(f"Processing RSS feed: {feed_url}")
    
    # Get or create RSSFeed object
    rss_feed, created = RSSFeed.objects.get_or_create(
        url=feed_url,
        defaults={'name': f'RSS Feed from {feed_url}', 'is_active': True}
    )
    
    if created:
        logger.info(f"Created new RSSFeed object for {feed_url}")
    
    return rss_feed.process_feed()


@shared_task
def process_rss_feed_by_id(rss_feed_id):
    """
    Celery task to process an RSS feed by its database ID.
    """
    try:
        rss_feed = RSSFeed.objects.get(id=rss_feed_id)
        return rss_feed.process_feed()
    except RSSFeed.DoesNotExist:
        logger.error(f"RSS feed with ID {rss_feed_id} does not exist")
        return {'error': f"RSS feed with ID {rss_feed_id} does not exist"}


@shared_task
def process_all_active_rss_feeds():
    """
    Celery task to process all active RSS feeds.
    """
    active_feeds = RSSFeed.objects.filter(is_active=True)
    results = []
    
    for rss_feed in active_feeds:
        logger.info(f"Processing RSS feed: {rss_feed.name} ({rss_feed.url})")
        result = rss_feed.process_feed()
        results.append(result)
    
    summary = {
        'total_feeds_processed': len(results),
        'feeds': results
    }
    
    logger.info(f"Completed processing all active RSS feeds: {len(results)} feeds")
    return summary


def get_rss_feed_summary(rss_feed_id):
    """
    Get summary information about an RSS feed and its podcasts.
    """
    try:
        rss_feed = RSSFeed.objects.get(id=rss_feed_id)
        return rss_feed.get_summary()
    except RSSFeed.DoesNotExist:
        return {'error': f"RSS feed with ID {rss_feed_id} does not exist"}
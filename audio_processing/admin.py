from django.contrib import admin
from .models import RSSFeed, Podcast


@admin.register(RSSFeed)
class RSSFeedAdmin(admin.ModelAdmin):
    list_display = ('name', 'url', 'is_active', 'last_processed', 'podcast_count', 'created_at')
    list_filter = ('is_active', 'created_at', 'last_processed')
    search_fields = ('name', 'url', 'description')
    readonly_fields = ('created_at', 'updated_at', 'last_processed')
    list_editable = ('is_active',)
    
    def podcast_count(self, obj):
        return obj.podcasts.count()
    podcast_count.short_description = 'Podcast Count'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'url', 'description', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'last_processed'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_active', 'mark_inactive', 'process_feed']
    
    def mark_active(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f"{queryset.count()} RSS feeds marked as active.")
    mark_active.short_description = "Mark selected RSS feeds as active"
    
    def mark_inactive(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f"{queryset.count()} RSS feeds marked as inactive.")
    mark_inactive.short_description = "Mark selected RSS feeds as inactive"
    
    def process_feed(self, request, queryset):
        """Process selected RSS feeds."""
        for rss_feed in queryset:
            rss_feed.process_feed()
        self.message_user(request, f"Processing initiated for {queryset.count()} RSS feeds.")
    process_feed.short_description = "Process selected RSS feeds"


@admin.register(Podcast)
class PodcastAdmin(admin.ModelAdmin):
    list_display = ('truncated_url', 'rss_feed', 'has_transcript', 'created_at', 'updated_at')
    list_filter = ('rss_feed', 'created_at', 'updated_at')
    search_fields = ('raw_audio_url', 'transcript', 'rss_feed__name')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('rss_feed',)
    
    def truncated_url(self, obj):
        if len(obj.raw_audio_url) > 50:
            return obj.raw_audio_url[:47] + "..."
        return obj.raw_audio_url
    truncated_url.short_description = 'Audio URL'
    
    def has_transcript(self, obj):
        return bool(obj.transcript and obj.transcript.strip())
    has_transcript.boolean = True
    has_transcript.short_description = 'Has Transcript'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('rss_feed', 'raw_audio_url')
        }),
        ('Content', {
            'fields': ('transcript',),
            'classes': ('wide',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['clear_transcript', 'export_transcripts', 'fetch_transcript']
    
    def clear_transcript(self, request, queryset):
        queryset.update(transcript='')
        self.message_user(request, f"Cleared transcripts for {queryset.count()} podcasts.")
    clear_transcript.short_description = "Clear transcripts for selected podcasts"
    
    def export_transcripts(self, request, queryset):
        # This could be enhanced to actually export data
        count = queryset.filter(transcript__isnull=False).exclude(transcript='').count()
        self.message_user(request, f"Found {count} podcasts with transcripts to export.")
    export_transcripts.short_description = "Export transcripts for selected podcasts"
    
    def fetch_transcript(self, request, queryset):
        """Fetch transcripts for selected podcasts."""
        for podcast in queryset:
            podcast.process_transcript()
        self.message_user(request, f"Transcript processing initiated for {queryset.count()} podcasts.")
    fetch_transcript.short_description = "Fetch transcripts for selected podcasts"

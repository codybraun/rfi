from django.contrib import admin
from .models import RSSFeed, Podcast, Tag
from audio_processing.tasks.podcast_tasks import add_transcript, suggest_and_apply_tags, process_complete_workflow
from import_export.admin import ImportExportModelAdmin
from audio_processing.tasks.rss_tasks import process_rss_feed_by_id

@admin.register(RSSFeed)
class RSSFeedAdmin(ImportExportModelAdmin):
    list_display = ('name', 'url', 'is_active', 'last_processed', 'podcast_count')
    list_filter = ('is_active', 'created_at', 'last_processed', 'tags')
    search_fields = ('name', 'url', 'description')
    readonly_fields = ('created_at', 'updated_at', 'last_processed')
    list_editable = ('is_active',)
    
    def podcast_count(self, obj):
        return obj.podcasts.count()
    podcast_count.short_description = 'Podcast Count'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'url', 'description', 'is_active', 'tags')
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
            process_rss_feed_by_id.delay(rss_feed.id)
        self.message_user(request, f"Processing initiated for {queryset.count()} RSS feeds.")
    process_feed.short_description = "Process selected RSS feeds"


@admin.register(Podcast)
class PodcastAdmin(admin.ModelAdmin):
    list_display = ('title', 'truncated_url', 'rss_feed', 'has_transcript', 'has_script', 'has_summary', 'created_at', 'updated_at', 'release_date')
    list_filter = ('rss_feed', 'created_at', 'updated_at', 'tags', 'release_date')
    search_fields = ('raw_audio_url', 'transcript', 'script_transcript', 'rss_feed__name')
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
    
    def has_script(self, obj):
        return bool(obj.script_transcript and obj.script_transcript.strip())
    has_script.boolean = True
    has_script.short_description = 'Has Script'

    def has_summary(self, obj):
        return bool(obj.summary and obj.summary.strip())
    has_summary.boolean = True
    has_summary.short_description = 'Has Summary'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('rss_feed', 'raw_audio_url', 'tags', 'title', 'release_date')
        }),
        ('Content', {
            'fields': ('transcript', 'script_transcript', 'summary'),
            'classes': ('wide',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['clear_transcript', 'export_transcripts', 'fetch_transcript',
               'suggest_tags', 'generate_speaker_scripts', 'run_complete_workflow', 'add_summary']

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
            add_transcript.delay(podcast.id)
        self.message_user(request, f"Transcript processing initiated for {queryset.count()} podcasts.")
    fetch_transcript.short_description = "Fetch transcripts for selected podcasts"

    def add_summary(self, request, queryset):
        """Generate summaries for selected podcasts."""
        success_count = 0
        error_count = 0
        
        for podcast in queryset:
            try:
                summary = podcast.generate_summary()
                if summary:
                    success_count += 1
            except Exception as e:
                error_count += 1
                self.message_user(
                    request, 
                    f"Error generating summary for {podcast.raw_audio_url[:50]}...: {str(e)}", 
                    level='ERROR'
                )
        
        if success_count > 0:
            self.message_user(
                request, 
                f"Successfully generated summaries for {success_count} podcasts."
            )
        
        if error_count > 0:
            self.message_user(
                request, 
                f"{error_count} podcasts failed to generate summaries.", 
                level='ERROR'
            )
    
    def suggest_tags(self, request, queryset):
        """Use AI to suggest and apply tags to selected podcasts."""
        success_count = 0
        error_count = 0
        no_transcript_count = 0
        
        for podcast in queryset:
            if not podcast.transcript or not podcast.transcript.strip():
                no_transcript_count += 1
                continue
            try:
                applied_tags = suggest_and_apply_tags.delay(podcast.id)
            except Exception as e:
                error_count += 1
                self.message_user(
                    request, 
                    f"Error suggesting tags for {podcast.raw_audio_url[:50]}...: {str(e)}", 
                    level='ERROR'
                )
        
        if success_count > 0:
            self.message_user(
                request, 
                f"Successfully suggested tags for {success_count} podcasts."
            )
        
        if no_transcript_count > 0:
            self.message_user(
                request, 
                f"{no_transcript_count} podcasts skipped (no transcript available).", 
                level='WARNING'
            )
        
        if error_count > 0:
            self.message_user(
                request, 
                f"{error_count} podcasts failed to process.", 
                level='ERROR'
            )
    
    suggest_tags.short_description = "AI suggest and apply tags for selected podcasts"
    
    def generate_speaker_scripts(self, request, queryset):
        """Generate speaker-attributed scripts for selected podcasts."""
        success_count = 0
        error_count = 0
        no_transcript_count = 0
        already_has_script_count = 0
        
        for podcast in queryset:
            if not podcast.transcript or not podcast.transcript.strip():
                no_transcript_count += 1
                continue
            
            if podcast.script_transcript and podcast.script_transcript.strip():
                already_has_script_count += 1
                continue
                
            try:
                script = podcast.generate_speaker_script()
            except Exception as e:
                error_count += 1
                self.message_user(
                    request, 
                    f"Error generating speaker script for {podcast.raw_audio_url[:50]}...: {str(e)}", 
                    level='ERROR'
                )
        
        if success_count > 0:
            self.message_user(
                request, 
                f"Successfully generated speaker scripts for {success_count} podcasts."
            )
        
        if no_transcript_count > 0:
            self.message_user(
                request, 
                f"{no_transcript_count} podcasts skipped (no transcript available).", 
                level='WARNING'
            )
        
        if already_has_script_count > 0:
            self.message_user(
                request, 
                f"{already_has_script_count} podcasts skipped (already have speaker scripts).", 
                level='WARNING'
            )
        
        if error_count > 0:
            self.message_user(
                request, 
                f"{error_count} podcasts failed to generate speaker scripts.", 
                level='ERROR'
            )
    
    generate_speaker_scripts.short_description = "Generate speaker scripts for selected podcasts"
    
    def run_complete_workflow(self, request, queryset):
        """Run the complete workflow (transcript, tags, summary, speaker script) for selected podcasts."""
        total_processed = 0
        total_errors = []
        
        for podcast in queryset:
            try:
                process_complete_workflow.delay(podcast.id)
                total_processed += 1
            except Exception as e:
                total_errors.append(f"{podcast.raw_audio_url[:30]}...: {str(e)}")
        
        self.message_user(
            request, 
            f"Processed {total_processed} podcasts. "
        )
        
        if total_errors:
            for error in total_errors[:5]:  # Show first 5 errors
                self.message_user(request, f"Error: {error}", level='ERROR')
            
            if len(total_errors) > 5:
                self.message_user(
                    request, 
                    f"...and {len(total_errors) - 5} more errors. Check logs for details.", 
                    level='ERROR'
                )
    
    run_complete_workflow.short_description = "Run complete workflow (transcript + tags + speaker script)"


@admin.register(Tag)
class TagAdmin(ImportExportModelAdmin):
    list_display = ('name', 'slug', 'color_display', 'rss_feed_count', 'podcast_count', 'created_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('name', 'slug', 'description')
    readonly_fields = ('created_at', 'updated_at')
    prepopulated_fields = {'slug': ('name',)}
    
    def color_display(self, obj):
        """Display color as a colored box."""
        if obj.color:
            return f'<span style="background-color: {obj.color}; padding: 3px 8px; border-radius: 3px; color: white;">{obj.color}</span>'
        return '-'
    color_display.allow_tags = True
    color_display.short_description = 'Color'
    
    def rss_feed_count(self, obj):
        return obj.rss_feeds.count()
    rss_feed_count.short_description = 'RSS Feeds'
    
    def podcast_count(self, obj):
        return obj.podcasts.count()
    podcast_count.short_description = 'Podcasts'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description')
        }),
        ('Appearance', {
            'fields': ('color',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

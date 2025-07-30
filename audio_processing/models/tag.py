from django.db import models


class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True, help_text="Tag name")
    slug = models.SlugField(max_length=100, unique=True, help_text="URL-friendly tag name")
    description = models.TextField(blank=True, null=True, help_text="Optional description of the tag")
    color = models.CharField(max_length=7, blank=True, null=True, help_text="Hex color code for the tag (e.g., #FF5733)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Tag"
        verbose_name_plural = "Tags"
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """Auto-generate slug from name if not provided."""
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

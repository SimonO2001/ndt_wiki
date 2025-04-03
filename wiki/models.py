# wiki/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    custom_template = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Optional path to a custom template, e.g. 'wiki/category_production.html'"
    )

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class WikiPage(models.Model):
    NOTE = 'note'
    GUIDE = 'guide'
    PAGE_TYPE_CHOICES = [
        (NOTE, 'Note'),
        (GUIDE, 'Guide'),
    ]
    
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    content = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='pages')
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    page_type = models.CharField(max_length=10, choices=PAGE_TYPE_CHOICES, default=NOTE)
    version = models.IntegerField(default=1)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} ({self.get_page_type_display()})"


# wiki/models.py

class GuideStep(models.Model):
    """
    Represents a single step in a multi-step guide.
    """
    wiki_page = models.ForeignKey(
        WikiPage, on_delete=models.CASCADE, related_name='guide_steps'
    )
    step_order = models.PositiveIntegerField(editable=False)  # We'll auto-set this.
    step_content = models.TextField()
    file = models.FileField(upload_to='guide_steps/', blank=True, null=True)

    def save(self, *args, **kwargs):
        # If this is a new step (no primary key yet)
        if not self.pk:
            # Count existing steps for this guide, increment for the new one
            existing_steps = GuideStep.objects.filter(wiki_page=self.wiki_page).count()
            self.step_order = existing_steps + 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Step {self.step_order} for {self.wiki_page.title}"



class ResourceLink(models.Model):
    """
    Stores useful links (e.g., drivers, BIOS settings, external documentation).
    """
    page = models.ForeignKey(WikiPage, on_delete=models.CASCADE, related_name='resources')
    name = models.CharField(max_length=200)
    url = models.URLField()
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.url})"


class MediaFile(models.Model):
    """
    Stores images or videos associated with a guide.
    """
    page = models.ForeignKey(WikiPage, on_delete=models.CASCADE, related_name='media_files')
    file = models.FileField(upload_to='wiki_media/')
    description = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.file.name

from django.contrib import admin
from .models import Category, WikiPage, ResourceLink, MediaFile

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(WikiPage)
class WikiPageAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'author', 'created_at', 'updated_at', 'version')
    prepopulated_fields = {'slug': ('title',)}

@admin.register(ResourceLink)
class ResourceLinkAdmin(admin.ModelAdmin):
    list_display = ('page', 'name', 'url')

@admin.register(MediaFile)
class MediaFileAdmin(admin.ModelAdmin):
    list_display = ('page', 'file')

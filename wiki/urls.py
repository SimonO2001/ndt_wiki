# wiki/urls.py
from django.urls import path
from . import views

app_name = "wiki"

urlpatterns = [
    path("", views.home, name="home"),
    path("category/<slug:cat_slug>/", views.category_detail, name="category_detail"),
    path("page/<slug:page_slug>/", views.page_detail, name="page_detail"),

    # Create pages
    path("create/note/", views.note_create, name="note_create"),
    path("category/<slug:cat_slug>/guide_create/", views.guide_create, name="guide_create"),

    # NEW: PDF import
    path("guide/import/", views.guide_import_upload,  name="guide_import_upload"),
    path("guide/import/preview/", views.guide_import_preview, name="guide_import_preview"),

    path("search/", views.search, name="search"),
]

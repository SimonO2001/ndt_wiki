# wiki/urls.py
from django.urls import include, path
from . import views

app_name = 'wiki'

urlpatterns = [
    path('', views.home, name='home'),
    path('category/<slug:cat_slug>/', views.category_detail, name='category_detail'),
    path('page/<slug:page_slug>/', views.page_detail, name='page_detail'),


    # Separate routes for note vs. guide
    path('create/note/', views.note_create, name='note_create'),
    path('category/<slug:cat_slug>/guide_create/', views.guide_create, name='guide_create'),

    path('search/', views.search, name='search'),
]

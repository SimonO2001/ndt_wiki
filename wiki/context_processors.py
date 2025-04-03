# wiki/context_processors.py
from .models import Category

def all_categories_processor(request):
    return {'all_categories': Category.objects.all()}

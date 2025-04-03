# wiki/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required

from .models import Category, WikiPage, GuideStep
from .forms import NoteForm, GuideForm, GuideStepFormSet
from django.db.models import Q


def home(request):
    categories = Category.objects.all()
    return render(request, 'wiki/home.html', {
        'categories': categories,
    })

def category_detail(request, cat_slug):
    category = get_object_or_404(Category, slug=cat_slug)
    all_pages = category.pages.all()

    # Split into two groups
    guides = all_pages.filter(page_type=WikiPage.GUIDE).order_by('-created_at')
    notes = all_pages.filter(page_type=WikiPage.NOTE).order_by('-created_at')

    template_name = category.custom_template or 'wiki/category_detail.html'
    return render(request, template_name, {
        'category': category,
        'guides': guides,
        'notes': notes,
        'current_category': category,
    })


def page_detail(request, page_slug):
    page = get_object_or_404(WikiPage, slug=page_slug)
    guide_steps = page.guide_steps.order_by('step_order') if page.page_type == WikiPage.GUIDE else None
    
    return render(request, 'wiki/page_detail.html', {
        'page': page,
        'guide_steps': guide_steps,
        'current_category': page.category,  # <-- Pass category here
    })


@login_required
def note_create(request):
    if request.method == 'POST':
        form = NoteForm(request.POST)
        if form.is_valid():
            note_page = form.save(commit=False)
            note_page.author = request.user
            note_page.page_type = WikiPage.NOTE
            note_page.save()
            return redirect('wiki:page_detail', page_slug=note_page.slug)
    else:
        form = NoteForm()
    return render(request, 'wiki/note_create.html', {'form': form})

@login_required
def guide_create(request, cat_slug=None):
    current_category = None
    if cat_slug:
        current_category = get_object_or_404(Category, slug=cat_slug)

    if request.method == 'POST':
        form = GuideForm(request.POST, request.FILES)
        guide_formset = GuideStepFormSet(request.POST, request.FILES, queryset=GuideStep.objects.none())

        if form.is_valid() and guide_formset.is_valid():
            guide_page = form.save(commit=False)
            guide_page.author = request.user
            guide_page.page_type = WikiPage.GUIDE

            # If you want to lock the category to the current one, do:
            if current_category:
                guide_page.category = current_category

            guide_page.save()

            for step_form in guide_formset:
                if step_form.cleaned_data and not step_form.cleaned_data.get('DELETE'):
                    step = step_form.save(commit=False)
                    step.wiki_page = guide_page
                    step.save()

            return redirect('wiki:page_detail', page_slug=guide_page.slug)
    else:
        form = GuideForm()
        guide_formset = GuideStepFormSet(queryset=GuideStep.objects.none())

    return render(request, 'wiki/guide_create.html', {
        'form': form,
        'guide_formset': guide_formset,
        'current_category': current_category,
    })



def search(request):
    query = request.GET.get('q', '')
    from_cat_slug = request.GET.get('from_category', None)

    current_cat = None
    if from_cat_slug:
        # If the category might not exist, handle gracefully
        try:
            current_cat = Category.objects.get(slug=from_cat_slug)
        except Category.DoesNotExist:
            pass

    results = []
    if query:
        results = WikiPage.objects.filter(
            Q(title__icontains=query) | Q(content__icontains=query)
        )

    return render(request, 'wiki/search_results.html', {
        'query': query,
        'results': results,
        'current_category': current_cat,  # So breadcrumb can show "Home → Production → Search"
    })


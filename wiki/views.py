# wiki/views.py

from pathlib import Path
from django.forms import modelformset_factory
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


# wiki/views.py
def page_detail(request, page_slug):
    page = get_object_or_404(WikiPage, slug=page_slug)
    guide_steps = None

    if page.page_type == WikiPage.GUIDE:
        guide_steps = page.guide_steps.order_by('step_order')
        template_name = 'wiki/guide_detail.html'
    else:
        template_name = 'wiki/note_detail.html'

    return render(request, template_name, {
        'page': page,
        'guide_steps': guide_steps,
        'current_category': page.category,
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
        # Pre‑select current category if we have one
        form = GuideForm(initial={'category': current_category}) if current_category else GuideForm()
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

# keep all previous imports
import base64, fitz, uuid
from pathlib import Path
from django.core.files.base import ContentFile
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .forms import GuideForm, GuideStepForm, PDFImportForm, GuideStepFormSet
from .models import WikiPage, GuideStep
from django.utils.safestring import mark_safe

# ------------------------------------------------------------
# helper that builds a light‑weight draft from the uploaded PDF
# ------------------------------------------------------------
# wiki/views.py (up at the top)

def _pdf_to_draft(file_obj):
    import base64, fitz, io
    from pathlib import Path

    doc   = fitz.open(stream=file_obj.read(), filetype="pdf")
    title = Path(file_obj.name).stem.replace("_", " ").title()
    intro = f"Imported from **{file_obj.name}** ({doc.page_count} pages)."
    steps = []

    THUMB_W = 240
    FULL_W  = 1024

    for page in doc:
        text = page.get_text("text").strip() or f"Page {page.number+1}"

        # small thumbnail
        zoom   = THUMB_W / page.rect.width
        mat    = fitz.Matrix(zoom, zoom)
        pix    = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
        thumb_b64 = base64.b64encode(pix.tobytes("png")).decode()

        # full-res image
        zoom2  = FULL_W / page.rect.width
        mat2   = fitz.Matrix(zoom2, zoom2)
        pix2   = page.get_pixmap(matrix=mat2, colorspace=fitz.csRGB)
        full_b64  = base64.b64encode(pix2.tobytes("png")).decode()

        steps.append({
            "text": text,
            "thumb": thumb_b64,
            "full":  full_b64,
        })

    return {"title": title, "intro": intro, "steps": steps}





# =====================================================================
#  1)  UPLOAD  /wiki/guide/import/
# =====================================================================
@login_required
def guide_import_upload(request):
    if request.method == "POST":
        form = PDFImportForm(request.POST, request.FILES)
        if form.is_valid():
            draft = _pdf_to_draft(request.FILES["file"])
            request.session["import_draft"]    = draft
            cat = form.cleaned_data["category"]
            request.session["import_category"] = cat.id if cat else None
            return redirect("wiki:guide_import_preview")
    else:
        form = PDFImportForm()
    return render(request, "wiki/guide_import_upload.html", {"form": form})


# ✂ ------------------------------------------------------------------
# 2)  PREVIEW  /wiki/guide/import/preview/
# --------------------------------------------------------------------
@login_required
def guide_import_preview(request):
    draft = request.session.get("import_draft")
    if not draft:
        return redirect("wiki:guide_import_upload")

    pages = []
    for s in draft["steps"]:
        img_file = None
        img_tag  = ""
        if s["thumb"]:
            # thumbnail for preview
            img_tag = mark_safe(
              f'<img src="data:image/png;base64,{s["thumb"]}" '
              'class="img-thumbnail d-block mb-2" style="max-width:220px">'
            )
        if s["full"]:
            # full-res for saving later
            full_bytes = base64.b64decode(s["full"])
            img_name   = f"import_{uuid.uuid4().hex}.png"
            img_file   = ContentFile(full_bytes, name=img_name)

        pages.append({
            "text": s["text"],
            "file": img_file,    # full-res here
            "tag":  img_tag,     # thumb here
        })

    # ── one empty form per PDF page  ────────────────────────────────
    StepFormSet = modelformset_factory(
        GuideStep,
        form       = GuideStepForm,
        extra      = len(pages),     # ← key point!
        can_delete = True,
    )

    # ---------------------------------------------------- POST (Save guide)
    if request.method == "POST":
        guide_form = GuideForm(request.POST, request.FILES)
        formset    = StepFormSet(request.POST, request.FILES,
                                 queryset=GuideStep.objects.none())

        if guide_form.is_valid() and formset.is_valid():
            guide = guide_form.save(commit=False)
            guide.author, guide.page_type = request.user, WikiPage.GUIDE
            guide.save()

            order = 1
            for f, p in zip(formset.forms, pages):
                cd = f.cleaned_data
                if not cd or cd.get("DELETE"):
                    continue

                # pick the file: user upload wins, otherwise our preview file
                upload = cd.get("file")
                the_file = upload if upload else p["file"]

                # pick the text: user override (if any), otherwise the PDF text
                text = cd.get("step_content") or p["text"]

                step = GuideStep(
                    wiki_page  = guide,
                    step_content = text,
                    file       = the_file,
                    step_order = order,
                )
                step.save()
                order += 1

            request.session.pop("import_draft", None)  # done
            return redirect("wiki:page_detail", page_slug=guide.slug)

    # ---------------------------------------------------- GET (preview)
    else:
        guide_form = GuideForm(initial={
            "title":    draft["title"],
            "content":  draft["intro"],
            "category": request.session.get("import_category"),
        })

        # build initial list **before** constructing the form‑set

        # 1) build the initial data list
        initial_steps = [{"step_content": page["text"]} for page in pages]

        # 2) instantiate your formset with that initial list
        formset = StepFormSet(
            queryset=GuideStep.objects.none(),
            initial = initial_steps,
        )

        # 3) now actually assign both the field‐initial **and** the thumbnail HTML
        for form, page in zip(formset.forms, pages):
            form.fields['step_content'].initial = page["text"]
            form.img_preview = page["tag"]



    # render
    return render(
        request,
        "wiki/guide_import_preview.html",
        {
            "form":          guide_form,   # guide header
            "guide_formset": formset,      # steps (template expects this name)
            "draft_name":    draft["title"]
        },
    )


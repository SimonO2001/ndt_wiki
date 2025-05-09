# wiki/views.py

import io
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

import re, base64, fitz
from pathlib import Path

# how wide our thumbnails and full-res snapshots should be (px)
THUMB_W = 240
FULL_W  = 1024

def _pdf_to_draft(file_obj):
    """
    Convert PDF (or PDF-stream) to a draft dict:
      {
        "title": str,
        "intro": str,
        "steps": [
          { "text": str, "thumb": base64-png, "full": base64-png },
          …
        ]
      }

    - If doc.page_count > 1: one step per page.
    - If doc.page_count == 1 but text contains "1.", "2.", … at line-starts,
      split on those numbers into multiple steps.
    """
    data = file_obj.read()
    doc = fitz.open(stream=data, filetype="pdf")

    name = getattr(file_obj, "name", "upload.pdf")
    title = Path(name).stem.replace("_", " ").title()
    intro = f"Imported from **{name}** ({doc.page_count} pages)."

    steps = []

    if doc.page_count == 1:
        # single page: split out numbered list
        page = doc[0]
        text = page.get_text("text").strip()

        # find all leading numbers "1.", "2.", …
        headers = re.findall(r'(?m)^\s*(\d+)\.\s*', text)
        parts   = re.split  (r'(?m)^\s*\d+\.\s*', text)[1:]  # drop before "1."

        # render thumbnail once
        zoom  = THUMB_W / page.rect.width
        mat   = fitz.Matrix(zoom, zoom)
        pix   = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
        thumb = base64.b64encode(pix.tobytes("png")).decode()

        # for each sub-step, generate its full-res
        for header, body in zip(headers, parts):
            # full-res for that step
            zoom2 = FULL_W / page.rect.width
            mat2  = fitz.Matrix(zoom2, zoom2)
            pix2  = page.get_pixmap(matrix=mat2, colorspace=fitz.csRGB)
            full  = base64.b64encode(pix2.tobytes("png")).decode()

            steps.append({
                "text": body.strip(),
                "thumb": thumb,
                "full":  full,
            })

    else:
        # multi-page: one step per page
        for page in doc:
            text = page.get_text("text").strip()
            if not text:
                continue

            # thumbnail
            zoom  = THUMB_W / page.rect.width
            mat   = fitz.Matrix(zoom, zoom)
            pix   = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
            thumb = base64.b64encode(pix.tobytes("png")).decode()

            # full-res
            zoom2 = FULL_W / page.rect.width
            mat2  = fitz.Matrix(zoom2, zoom2)
            pix2  = page.get_pixmap(matrix=mat2, colorspace=fitz.csRGB)
            full  = base64.b64encode(pix2.tobytes("png")).decode()

            steps.append({
                "text": text,
                "thumb": thumb,
                "full":  full,
            })

    return {"title": title, "intro": intro, "steps": steps}


import subprocess
import tempfile
from pathlib import Path
from django.core.files.uploadedfile import InMemoryUploadedFile

def _odt_to_pdf(uploaded_odt):
    # write the uploaded .odt to a temp file
    odt_fd, odt_path = tempfile.mkstemp(suffix=".odt")
    with open(odt_path, "wb") as f:
        for chunk in uploaded_odt.chunks():
            f.write(chunk)

    # convert to PDF next to it
    pdf_path = Path(odt_path).with_suffix(".pdf")
    subprocess.run([
        "soffice", "--headless", "--convert-to", "pdf", "--outdir",
        str(pdf_path.parent), odt_path
    ], check=True)

    # read the PDF back in as a Django file-like object
    with open(pdf_path, "rb") as f:
        pdf_data = f.read()

    # clean up
    Path(odt_path).unlink()
    pdf_path.unlink()

    # wrap in a Django InMemoryUploadedFile if you need
    return io.BytesIO(pdf_data)


from pathlib import Path
import io
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import PDFImportForm, GuideForm, GuideStepFormSet
from .views import _pdf_to_draft, _odt_to_pdf

@login_required
def guide_import_upload(request):
    if request.method == "POST":
        form = PDFImportForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded = request.FILES["file"]

            # If .odt, convert it to a PDF in-memory
            if uploaded.name.lower().endswith(".odt"):
                pdf_stream = _odt_to_pdf(uploaded)
                # Give it a .name so _pdf_to_draft can infer a title
                pdf_stream.name = Path(uploaded.name).with_suffix(".pdf").name
                draft = _pdf_to_draft(pdf_stream)
            else:
                # Already a PDF; file_obj has .name by default
                draft = _pdf_to_draft(uploaded)

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


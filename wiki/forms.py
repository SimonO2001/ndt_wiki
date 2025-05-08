# wiki/forms.py
from django import forms
from django.forms import modelformset_factory
from .models import Category, WikiPage, GuideStep


# ──────────────────────────────────────────────────────────────
#  Main page‑creation forms
# ──────────────────────────────────────────────────────────────
class NoteForm(forms.ModelForm):
    class Meta:
        model = WikiPage
        fields = ["title", "content", "category"]


class GuideForm(forms.ModelForm):
    class Meta:
        model = WikiPage
        fields = ["title", "content", "category"]


# ──────────────────────────────────────────────────────────────
#  Guide‑step form + reusable form‑set
# ──────────────────────────────────────────────────────────────
class GuideStepForm(forms.ModelForm):
    """Used for both manual guide creation and PDF import preview."""
    class Meta:
        model  = GuideStep
        fields = ["step_content", "file"]      # step_order & wiki_page handled in code


# Global factory: always provides ONE blank extra form.
# If you pass a longer `initial=[…]` list, Django auto‑grows the form‑set.
GuideStepFormSet = modelformset_factory(
    GuideStep,
    form       = GuideStepForm,
    extra      = 1,        # spare blank row when creating from scratch
    can_delete = True,
)


# ──────────────────────────────────────────────────────────────
#  PDF import helper form (upload + optional category)
# ──────────────────────────────────────────────────────────────
class PDFImportForm(forms.Form):
    file     = forms.FileField(label="Select a PDF file")
    category = forms.ModelChoiceField(
        queryset     = Category.objects.all(),
        required     = False,
        empty_label  = "— choose category (optional) —",
    )

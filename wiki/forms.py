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
# wiki/forms.py
from django import forms
from django.forms.widgets import ClearableFileInput
from .models import GuideStep

class GuideStepForm(forms.ModelForm):
    file = forms.FileField(
        required=False,
        widget=ClearableFileInput,  # <-- renders the “Clear” checkbox
        label="Step image",
    )

    class Meta:
        model = GuideStep
        fields = ["step_content", "file"]


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

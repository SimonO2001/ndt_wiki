# wiki/forms.py
from django import forms
from django.forms import modelformset_factory
from .models import WikiPage, GuideStep

class NoteForm(forms.ModelForm):
    class Meta:
        model = WikiPage
        fields = ['title', 'content', 'category']

class GuideForm(forms.ModelForm):
    class Meta:
        model = WikiPage
        fields = ['title', 'content', 'category']

class GuideStepForm(forms.ModelForm):
    class Meta:
        model = GuideStep
        # Exclude step_order (it’s auto) and wiki_page (set in code)
        fields = ['step_content', 'file']  

GuideStepFormSet = modelformset_factory(
    GuideStep,
    form=GuideStepForm,
    extra=1,
    can_delete=True
)

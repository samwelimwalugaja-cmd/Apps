from django import forms
from .models import Event

class EventRegistrationForm(forms.Form):
    event_id = forms.IntegerField(widget=forms.HiddenInput)
    phone = forms.CharField(max_length=15, required=True)
    guests = forms.IntegerField(min_value=0, max_value=5, required=False)
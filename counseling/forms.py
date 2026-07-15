from django import forms
from .models import PsychiatristProfile, AvailabilitySlot, Booking
from django.utils import timezone
from datetime import timedelta

class PsychiatristProfileForm(forms.ModelForm):
    class Meta:
        model = PsychiatristProfile
        fields = [
            'full_name',
            'license_no',
            'specialization',
            'languages',
            'years_experience',
            'bio',
            'photo',
            'available_chat',
            'available_voice',
            'available_video',
            'rating',
        ]
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 3}),
        }

class AvailabilitySlotForm(forms.ModelForm):
    class Meta:
        model = AvailabilitySlot
        fields = ['start', 'end']
        widgets = {
            'start': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'end': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start')
        end = cleaned_data.get('end')
        
        if start and end:
            if end <= start:
                raise forms.ValidationError("End time must be after start time.")
            if start < timezone.now():
                raise forms.ValidationError("Cannot create slots in the past.")
            # Ensure minimum 30 minutes duration
            if (end - start) < timedelta(minutes=30):
                raise forms.ValidationError("Slot must be at least 30 minutes long.")
        
        return cleaned_data

class BookingForm(forms.ModelForm):
    def __init__(self, *args, psychiatrist=None, **kwargs):
        super().__init__(*args, **kwargs)
        if psychiatrist:
            choices = []
            if psychiatrist.available_chat:
                choices.append(('chat', 'Chat'))
            if psychiatrist.available_voice:
                choices.append(('voice', 'Voice'))
            if psychiatrist.available_video:
                choices.append(('video', 'Video'))
            self.fields['mode'].choices = choices

    class Meta:
        model = Booking
        fields = ['mode', 'allow_anonymous', 'pseudonym', 'notes']
        widgets = {
            'mode': forms.Select(attrs={'class': 'form-select'}),
            'allow_anonymous': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'pseudonym': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional display name'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Any specific concerns or topics you\'d like to discuss...'}),
        }

class FeedbackForm(forms.Form):
    rating = forms.IntegerField(
        min_value=1,
        max_value=5,
        widget=forms.HiddenInput()
    )
    comment = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Share your feedback (optional)...'})
    )

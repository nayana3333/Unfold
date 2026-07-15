from django import forms

from .models import Report


class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ['reason', 'severity', 'details']
        widgets = {
            'reason': forms.Select(attrs={'class': 'form-control'}),
            'severity': forms.Select(attrs={'class': 'form-control'}),
            'details': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe what feels unsafe or inappropriate.',
            }),
        }

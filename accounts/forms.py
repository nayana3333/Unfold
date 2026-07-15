from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Profile

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    role = forms.ChoiceField(
        choices=(
            (Profile.ROLE_PATIENT, 'Patient'),
            (Profile.ROLE_COUNSELOR, 'Counselor'),
        ),
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    password2 = forms.CharField(label="Confirm Password", widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    class Meta:
        model = User
        fields = ['username', 'email', 'role', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            profile, _ = Profile.objects.get_or_create(user=user)
            profile.role = self.cleaned_data['role']
            profile.verification_status = (
                Profile.VERIFICATION_PENDING
                if profile.role == Profile.ROLE_COUNSELOR
                else Profile.VERIFICATION_APPROVED
            )
            profile.save(update_fields=['role', 'verification_status', 'updated_at'])
            user._state.fields_cache.pop('profile', None)
        return user

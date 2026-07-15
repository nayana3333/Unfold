from django import forms
from .models import Post, Story
from django.utils import timezone

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['content', 'image', 'file', 'is_anonymous', 'pseudonym', 'allow_comments']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': "What's on your mind?"
            }),
            'is_anonymous': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'allow_comments': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'pseudonym': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Optional display name'
            })
        }

    def clean(self):
        cleaned_data = super().clean()
        content = (cleaned_data.get('content') or '').strip()
        image = cleaned_data.get('image')
        file = cleaned_data.get('file')
        carousel_images = self.files.getlist('images') if self.files else []

        if not (content or image or file or carousel_images):
            raise forms.ValidationError('Add a caption, photo, or file before publishing.')

        if image and hasattr(image, 'content_type') and not image.content_type.startswith('image/'):
            raise forms.ValidationError('Please upload a valid image file.')

        for uploaded in carousel_images:
            if hasattr(uploaded, 'content_type') and not uploaded.content_type.startswith('image/'):
                raise forms.ValidationError('Please upload only valid image files in the carousel.')

        return cleaned_data

class StoryForm(forms.ModelForm):
    class Meta:
        model = Story
        fields = ['content', 'image', 'video', 'is_anonymous', 'pseudonym']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': "Share your story..."
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
                'onchange': 'previewImage(this)'
            }),
            'video': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'video/*',
                'onchange': 'previewVideo(this)'
            }),
            'is_anonymous': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'pseudonym': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Optional display name'
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        image = cleaned_data.get('image')
        video = cleaned_data.get('video')
        content = cleaned_data.get('content')
        
        if not (image or video or content):
            raise forms.ValidationError('You must provide either text, image, or video for your story.')
        
        if image and video:
            raise forms.ValidationError('You can only upload either an image or a video, not both.')

        if not cleaned_data.get('is_anonymous'):
            cleaned_data['pseudonym'] = ''
            
        return cleaned_data

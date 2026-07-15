from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
    ROLE_PATIENT = 'patient'
    ROLE_COUNSELOR = 'counselor'
    ROLE_ADMIN = 'admin'
    ROLE_CHOICES = (
        (ROLE_PATIENT, 'Patient'),
        (ROLE_COUNSELOR, 'Counselor'),
        (ROLE_ADMIN, 'Admin'),
    )

    VERIFICATION_PENDING = 'pending'
    VERIFICATION_APPROVED = 'approved'
    VERIFICATION_REJECTED = 'rejected'
    VERIFICATION_CHOICES = (
        (VERIFICATION_PENDING, 'Pending'),
        (VERIFICATION_APPROVED, 'Approved'),
        (VERIFICATION_REJECTED, 'Rejected'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_PATIENT)
    verification_status = models.CharField(
        max_length=20,
        choices=VERIFICATION_CHOICES,
        default=VERIFICATION_PENDING,
    )
    image = models.ImageField(upload_to='profiles/', blank=True, null=True)
    bio = models.TextField(blank=True, default='Welcome to your safe space. Share, connect, and grow.')
    about = models.TextField(blank=True)
    interests = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

    @property
    def is_patient(self):
        return self.role == self.ROLE_PATIENT

    @property
    def is_counselor(self):
        return self.role == self.ROLE_COUNSELOR

    @property
    def is_platform_admin(self):
        return self.role == self.ROLE_ADMIN

    @receiver(post_save, sender=User)
    def create_user_profile(sender, instance, created, **kwargs):
        if created:
            Profile.objects.create(user=instance)

    @receiver(post_save, sender=User)
    def save_user_profile(sender, instance, **kwargs):
        if hasattr(instance, 'profile'):
            instance.profile.save()

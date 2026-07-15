from django.views.generic import ListView, CreateView, DetailView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.db.models import Q, Avg
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from .models import PsychiatristProfile, AvailabilitySlot, Booking, Feedback
from .forms import BookingForm, FeedbackForm, AvailabilitySlotForm

class CounselingListView(ListView):
    template_name = "counseling/counseling_list.html"
    context_object_name = "psychiatrists"

    def get_queryset(self):
        queryset = PsychiatristProfile.objects.filter(
            is_female=True, 
            is_verified=True
        ).select_related('user')
        
        # Filter by specialization
        specialization = self.request.GET.get('specialization', '').strip()
        if specialization:
            queryset = queryset.filter(
                Q(specialization__icontains=specialization) |
                Q(bio__icontains=specialization)
            )
        
        # Filter by rating
        min_rating = self.request.GET.get('rating', '').strip()
        if min_rating:
            try:
                min_rating_float = float(min_rating)
                queryset = queryset.filter(rating__gte=min_rating_float)
            except ValueError:
                pass
        
        # Order by rating (highest first) or created_at
        queryset = queryset.order_by('-rating', '-created_at')
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['specializations'] = PsychiatristProfile.objects.filter(
            is_verified=True
        ).values_list('specialization', flat=True).distinct()
        context['selected_specialization'] = self.request.GET.get('specialization', '')
        context['selected_rating'] = self.request.GET.get('rating', '')
        return context


class PatientDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "counseling/patient_dashboard.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['bookings'] = Booking.objects.filter(
            user=self.request.user
        ).select_related('psychiatrist', 'slot').order_by('-created_at')
        context['upcoming_bookings'] = context['bookings'].filter(
            status__in=['pending', 'confirmed'],
            slot__start__gte=timezone.now()
        )
        context['past_bookings'] = context['bookings'].filter(
            Q(status='completed') | Q(slot__start__lt=timezone.now())
        )
        context['pending_count'] = context['bookings'].filter(status='pending').count()
        context['confirmed_count'] = context['bookings'].filter(status='confirmed').count()
        context['completed_count'] = context['bookings'].filter(status='completed').count()
        return context


class PsychiatristDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "counseling/psychiatrist_dashboard.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        if not PsychiatristProfile.objects.filter(user=request.user).exists():
            return render(request, "counseling/access_required.html", {
                "title": "Counselor access required",
                "message": "This workspace is available only for verified psychiatrists and counselors.",
                "primary_label": "Go to patient dashboard",
                "primary_url": "counseling:patient_dashboard",
                "secondary_label": "Browse counseling",
                "secondary_url": "counseling:list",
            }, status=403)
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = PsychiatristProfile.objects.get(user=self.request.user)
        
        # Get upcoming slots
        context['upcoming_slots'] = AvailabilitySlot.objects.filter(
            psychiatrist=profile,
            start__gte=timezone.now()
        ).order_by('start')
        
        # Get bookings
        context['bookings'] = Booking.objects.filter(
            psychiatrist=profile
        ).select_related('user', 'slot').order_by('-created_at')
        
        # Get pending bookings
        context['pending_bookings'] = context['bookings'].filter(
            status='pending',
            slot__start__gte=timezone.now()
        )
        
        # Get today's bookings
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        context['today_bookings'] = context['bookings'].filter(
            slot__start__gte=today_start,
            slot__start__lt=today_end,
            status__in=['pending', 'confirmed']
        )
        
        context['profile'] = profile
        context['confirmed_count'] = context['bookings'].filter(status='confirmed').count()
        context['completed_count'] = context['bookings'].filter(status='completed').count()
        context['available_slot_count'] = context['upcoming_slots'].filter(is_booked=False).count()
        return context


class BookAppointmentView(LoginRequiredMixin, CreateView):
    model = Booking
    form_class = BookingForm
    template_name = "counseling/book_appointment.html"
    
    def get_psychiatrist(self):
        return get_object_or_404(
            PsychiatristProfile,
            id=self.kwargs.get('psychiatrist_id'),
            is_verified=True,
            is_female=True
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        psychiatrist = self.get_psychiatrist()
        
        # Get available slots (not booked and in the future)
        available_slots = AvailabilitySlot.objects.filter(
            psychiatrist=psychiatrist,
            is_booked=False,
            start__gte=timezone.now()
        ).order_by('start')
        
        context['psychiatrist'] = psychiatrist
        context['available_slots'] = available_slots
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['psychiatrist'] = self.get_psychiatrist()
        return kwargs
    
    def form_valid(self, form):
        psychiatrist = self.get_psychiatrist()
        slot_id = self.request.POST.get('slot_id')
        
        if not slot_id:
            form.add_error(None, "Please select an available time slot.")
            return self.form_invalid(form)
        
        with transaction.atomic():
            slot = get_object_or_404(
                AvailabilitySlot.objects.select_for_update(),
                id=slot_id,
                psychiatrist=psychiatrist,
                is_booked=False,
                start__gte=timezone.now()
            )

            booking = form.save(commit=False)
            booking.user = self.request.user
            booking.psychiatrist = psychiatrist
            booking.slot = slot
            booking.status = 'pending'
            booking.full_clean()
            booking.save()

            slot.is_booked = True
            slot.save(update_fields=['is_booked'])
        
        messages.success(self.request, f'Appointment booked successfully with {psychiatrist.full_name}!')
        return redirect('counseling:patient_dashboard')


class UpdateBookingStatusView(LoginRequiredMixin, TemplateView):
    allowed_statuses = {'confirmed', 'cancelled', 'completed'}

    def post(self, request, *args, **kwargs):
        booking = get_object_or_404(
            Booking.objects.select_related('psychiatrist', 'slot'),
            id=kwargs.get('booking_id')
        )
        new_status = kwargs.get('status')

        if new_status not in self.allowed_statuses:
            messages.error(request, "That booking action is not available.")
            return redirect('counseling:patient_dashboard')

        is_counselor = hasattr(request.user, 'psychiatrist_profile') and booking.psychiatrist.user_id == request.user.id
        is_patient = booking.user_id == request.user.id

        if new_status == 'confirmed' and not is_counselor:
            messages.error(request, "Only the assigned counselor can confirm this session.")
            return redirect('counseling:patient_dashboard')
        if new_status == 'completed' and not is_counselor:
            messages.error(request, "Only the assigned counselor can complete this session.")
            return redirect('counseling:patient_dashboard')
        if new_status == 'cancelled' and not (is_patient or is_counselor):
            messages.error(request, "You do not have access to cancel this session.")
            return redirect('counseling:patient_dashboard')

        booking.status = new_status
        booking.save(update_fields=['status'])

        if new_status == 'cancelled':
            booking.slot.is_booked = False
            booking.slot.save(update_fields=['is_booked'])

        messages.success(request, f'Booking marked as {booking.get_status_display().lower()}.')
        if is_counselor:
            return redirect('counseling:psychiatrist_dashboard')
        return redirect('counseling:patient_dashboard')


class SessionView(LoginRequiredMixin, DetailView):
    model = Booking
    template_name = "counseling/session.html"
    context_object_name = "booking"
    pk_url_kwarg = "booking_id"
    
    def get_queryset(self):
        # Users can only view their own bookings, psychiatrists can view their bookings
        user = self.request.user
        if hasattr(user, 'psychiatrist_profile'):
            return Booking.objects.filter(psychiatrist__user=user)
        return Booking.objects.filter(user=user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        booking = self.get_object()
        
        # Check if session can start (within 15 minutes before or during slot)
        slot_start = booking.slot.start
        slot_end = booking.slot.end
        now = timezone.now()
        
        context['can_start'] = (
            now >= slot_start - timedelta(minutes=15) and
            now <= slot_end and
            booking.status in ['pending', 'confirmed']
        )
        context['is_psychiatrist'] = hasattr(self.request.user, 'psychiatrist_profile')
        return context


class SubmitFeedbackView(LoginRequiredMixin, TemplateView):
    template_name = "counseling/feedback.html"
    
    def get_booking(self):
        booking_id = self.kwargs.get('booking_id')
        booking = get_object_or_404(
            Booking,
            id=booking_id,
            user=self.request.user
        )
        # Allow feedback for completed bookings or past bookings
        if booking.status not in ['completed', 'confirmed'] and booking.slot.start > timezone.now():
            from django.http import Http404
            raise Http404("Cannot submit feedback for future bookings.")
        return booking
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['booking'] = self.get_booking()
        return context
    
    def post(self, request, *args, **kwargs):
        booking = self.get_booking()
        form = FeedbackForm(request.POST)
        
        if form.is_valid():
            rating = form.cleaned_data['rating']
            comment = form.cleaned_data.get('comment', '')
            
            # Create or update feedback
            feedback, created = Feedback.objects.get_or_create(
                booking=booking,
                defaults={'rating': rating, 'comment': comment}
            )
            if not created:
                feedback.rating = rating
                feedback.comment = comment
                feedback.save()
            
            # Update psychiatrist average rating
            psychiatrist = booking.psychiatrist
            avg_rating = Feedback.objects.filter(
                booking__psychiatrist=psychiatrist
            ).aggregate(Avg('rating'))['rating__avg']
            
            if avg_rating:
                psychiatrist.rating = round(avg_rating, 2)
                psychiatrist.save()
            
            # Mark booking as completed if it was confirmed and is in the past
            if booking.status == 'confirmed' and booking.slot.start < timezone.now():
                booking.status = 'completed'
                booking.save()
            
            messages.success(request, 'Thank you for your feedback!')
            return redirect('counseling:patient_dashboard')
        
        context = self.get_context_data()
        context['form'] = form
        return self.render_to_response(context)


class BrowseDirectoryView(ListView):
    template_name = "counseling/directory.html"
    context_object_name = "psychiatrists"
    paginate_by = 12
    
    def get_queryset(self):
        queryset = PsychiatristProfile.objects.filter(
            is_female=True,
            is_verified=True
        ).select_related('user')
        
        # Filter by specialization
        specialization = self.request.GET.get('specialization', '').strip()
        if specialization:
            queryset = queryset.filter(specialization__icontains=specialization)
        
        # Filter by rating
        min_rating = self.request.GET.get('rating', '').strip()
        if min_rating:
            try:
                queryset = queryset.filter(rating__gte=float(min_rating))
            except ValueError:
                pass
        
        # Search
        search = self.request.GET.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(full_name__icontains=search) |
                Q(specialization__icontains=search) |
                Q(bio__icontains=search)
            )
        
        return queryset.order_by('-rating', '-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['specializations'] = PsychiatristProfile.objects.filter(
            is_verified=True
        ).exclude(specialization='').values_list('specialization', flat=True).distinct()
        return context

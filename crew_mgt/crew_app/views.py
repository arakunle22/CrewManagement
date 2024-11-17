# Imports
from datetime import date, timedelta
import logging

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.cache import cache_page
import time
from django.db.models import Q

from .forms import (
    CrewRegistrationForm, CrewProfileForm, DocumentUploadForm, LoginForm,
    TaskFilterForm, LeaveRequestForm
)
from .models import (
    User, CrewProfile, Document, Attendance, LeaveRequest, Task,
    Announcement, Shift, Performance, Payroll
)

# Configuration
logger = logging.getLogger(__name__)


def home(request):
    """
    Simple view to render the home page.
    """
    return render(request, 'crew/home.html')

# === Authentication and Registration Views ===

def register_view(request):
    logger.debug("=== Starting registration process ===")
    if request.method == 'POST':
        registration_form = CrewRegistrationForm(request.POST)
        profile_form = CrewProfileForm(request.POST)
        document_form = DocumentUploadForm(request.POST, request.FILES)
        
        if all([registration_form.is_valid(), profile_form.is_valid(), document_form.is_valid()]):
            try:
                # Save user, profile, and document
                user = registration_form.save(commit=False)
                user.username = user.email
                user.is_crew = True
                user.save()
                
                profile = profile_form.save(commit=False)
                profile.user = user
                profile.recruitment_status = 'pending'
                profile.save()
                
                document = document_form.save(commit=False)
                document.crew_profile = profile
                document.save()
                
                messages.success(request, 'Registration successful. Profile pending approval.')
                return redirect('login')
                
            except Exception as e:
                logger.error(f"Registration failed: {str(e)}")
                messages.error(request, 'Registration failed. Please try again.')
    else:
        registration_form = CrewRegistrationForm()
        profile_form = CrewProfileForm()
        document_form = DocumentUploadForm()

    return render(request, 'crew/register.html', {
        'registration_form': registration_form,
        'profile_form': profile_form,
        'document_form': document_form
    })


def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            
            user = authenticate(request, username=email, password=password)
            if user is not None:
                if user.is_active:
                    login(request, user)
                    messages.success(request, 'Login successful!')
                    return redirect('recruitment_status')
                else:
                    messages.error(request, 'Your account is not active.')
            else:
                messages.error(request, 'Invalid credentials.')
    else:
        form = LoginForm()
    return render(request, 'crew/login.html', {'form': form})

def crew_login_view(request):
    """Login view for approved crew members to access the crew portal directly."""
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            
            user = authenticate(request, username=email, password=password)
            if user is not None:
                profile = getattr(user, 'crew_profile', None)
                
                if profile and profile.recruitment_status == 'approved':
                    login(request, user)
                    messages.success(request, 'Login successful! Welcome to the crew portal.')
                    return redirect('crew_portal')
                else:
                    messages.error(request, 'Your recruitment status is not approved.')
            else:
                messages.error(request, 'Invalid credentials.')
    else:
        form = LoginForm()
    
    return render(request, 'crew/crew_login.html', {'form': form})


# === Dashboard Views ===

@login_required
def recruitment_status(request):
    if request.user.is_crew:
        profile = request.user.crew_profile
        documents = profile.documents.all()
        return render(request, 'crew/recruitment_status.html', {
            'profile': profile,
            'documents': documents
        })
    return redirect('admin_dashboard')


@login_required
def admin_dashboard(request):
    if request.user.is_hr:
        pending_profiles = CrewProfile.objects.filter(recruitment_status='pending')
        return render(request, 'crew/admin_dashboard.html', {
            'pending_profiles': pending_profiles
        })
    return redirect('login')


# === Portal Views ===

from django.utils import timezone
from django.shortcuts import redirect

@login_required
def crew_portal(request):
    """Main portal dashboard view with 10-minute inactivity logout."""
    profile = request.user.crew_profile
    today = date.today()

   # Set session timeout for 10 minutes of inactivity
    request.session.set_expiry(600)

    current_timestamp = int(time.time())
    last_activity = request.session.get('_last_activity')

    if last_activity is None:
        request.session['_last_activity'] = current_timestamp
    elif current_timestamp - last_activity > 600:
        return redirect('crew_login')

    request.session['_last_activity'] = current_timestamp

    # Other crew portal logic
    attendance, _ = Attendance.objects.get_or_create(
        crew=profile,
        date=today,
        defaults={'clock_in': None, 'clock_out': None}
    )

    active_tasks = Task.objects.filter(
        crew=profile, status__in=['pending', 'in_progress']
    ).order_by('deadline')[:3]

   # Fetching the upcoming shifts for the logged-in user
    upcoming_shifts = Shift.objects.filter(crew=profile).order_by('-start_time')

    
   # Fetch announcements and paginate them to show only 2 per page
    announcements = Announcement.objects.filter(
        Q(departments=profile.department) | Q(is_global=True)
    ).distinct().order_by('-created_at')[:2]
    
    # Set up paginator: 1 announcement per page
    paginator = Paginator(announcements, 2)  
    page_number = request.GET.get('page')
    page_announcements = paginator.get_page(page_number)

    context = {
    'profile': profile,
    'attendance': attendance,
    'active_tasks': active_tasks,
    'upcoming_shifts': upcoming_shifts,
    'announcements': page_announcements,
    'active_view': 'dashboard'
}

    return render(request, 'crew/portal.html', context)


@login_required
def tasks_view(request):
    profile = request.user.crew_profile
    filter_form = TaskFilterForm(request.GET)
    tasks = Task.objects.filter(crew=profile).order_by('deadline')
    
    if filter_form.is_valid() and filter_form.cleaned_data['status'] != 'all':
        tasks = tasks.filter(status=filter_form.cleaned_data['status'])
    
    return render(request, 'crew/portal/tasks.html', {
        'profile': profile,
        'tasks': tasks,
        'filter_form': filter_form,
        'active_view': 'tasks'
    })


@login_required
@require_POST
def update_task_status(request, task_id):
    task = get_object_or_404(Task, id=task_id, crew=request.user.crew_profile)
    new_status = request.POST.get('status')
    
    if new_status in dict(Task.STATUS_CHOICES):
        task.status = new_status
        task.save()
        return JsonResponse({'status': 'success'})
    
    return JsonResponse({'status': 'error'}, status=400)


@login_required
def attendance_view(request):
    """View for displaying attendance page with clock in/out functionality."""
    profile = request.user.crew_profile
    today = date.today()
    
    attendance, _ = Attendance.objects.get_or_create(
        crew=profile, date=today, defaults={'clock_in': None, 'clock_out': None}
    )
    
    recent_attendance = Attendance.objects.filter(
        crew=profile
    ).order_by('-date')[:7]
    
    context = {
        'profile': profile,
        'attendance': attendance,
        'recent_attendance': recent_attendance,
    }
    
    return render(request, 'crew/portal/attendance.html', context)


@login_required
@require_POST
def clock_in(request):
    """Handle clock-in requests."""
    profile = request.user.crew_profile
    today = date.today()
    current_time = timezone.now()

    attendance, created = Attendance.objects.get_or_create(
        crew=profile, date=today, defaults={'clock_in': current_time}
    )
    
    if not created and attendance.clock_in:
        messages.warning(request, 'You have already clocked in for today.')
        return redirect('crew_portal')
        
    attendance.clock_in = current_time
    attendance.save()
    
    messages.success(request, f'Clocked in successfully at {current_time.strftime("%H:%M")}.')
    return redirect('crew_portal')


@login_required
@require_POST
def clock_out(request):
    """Handle clock-out requests."""
    profile = request.user.crew_profile
    today = date.today()
    current_time = timezone.now()
    
    try:
        attendance = Attendance.objects.get(crew=profile, date=today)
        
        if attendance.clock_out:
            messages.warning(request, 'You have already clocked out for today.')
            return redirect('crew_portal')
            
        attendance.clock_out = current_time
        attendance.save()
        
        messages.success(request, f'Clocked out successfully at {current_time.strftime("%H:%M")}.')
        return redirect('crew_portal')
        
    except Attendance.DoesNotExist:
        messages.error(request, 'No clock-in record found for today.')
        return redirect('crew_portal')


@login_required
def leave_view(request):
    profile = request.user.crew_profile
    
    if request.method == 'POST':
        form = LeaveRequestForm(request.POST)
        if form.is_valid():
            leave_request = form.save(commit=False)
            leave_request.crew = profile
            leave_request.save()
            messages.success(request, 'Leave request submitted successfully.')
            return redirect('leave')
    else:
        form = LeaveRequestForm()
    
    recent_requests = LeaveRequest.objects.filter(
        crew=profile
    ).order_by('-created_at')[:5]
    
    return render(request, 'crew/portal/leave.html', {
        'profile': profile,
        'form': form,
        'recent_requests': recent_requests,
        'active_view': 'leave'
    })


@cache_page(60 * 15)  # Cache for 15 minutes
@login_required
def profile_view(request):
    profile = get_object_or_404(CrewProfile, user=request.user)
    
    recent_performance = Performance.objects.filter(
        crew=profile
    ).select_related('reviewed_by').order_by('-review_date').first()
    
    attendance_list = Attendance.objects.filter(crew=profile).order_by('-date')
    paginator = Paginator(attendance_list, 10)
    page = request.GET.get('page')
    recent_attendance = paginator.get_page(page)
    
    active_tasks = Task.objects.filter(
        crew=profile, status__in=['pending', 'in_progress']
    ).order_by('deadline')
    
    pending_leaves = LeaveRequest.objects.filter(
        crew=profile, status='pending'
    ).order_by('start_date')
    
    latest_payroll = Payroll.objects.filter(
        crew=profile
    ).order_by('-month').first()
    
    return render(request, 'crew/portal/profile.html', {
        'profile': profile,
        'recent_performance': recent_performance,
        'recent_attendance': recent_attendance,
        'active_tasks': active_tasks,
        'pending_leaves': pending_leaves,
        'latest_payroll': latest_payroll,
        'active_view': 'profile'
    })

@login_required
def shift_view(request):
    
    try:
        profile = request.user.crew_profile
        # Retrieve shifts associated with this CrewProfile
        upcoming_shifts = Shift.objects.filter(crew=profile).order_by('-start_time')
    except CrewProfile.DoesNotExist:
        upcoming_shifts = None  # If no profile exists, set upcoming_shifts to None

    context = {
        'upcoming_shifts': upcoming_shifts,
    }
    return render(request, 'crew/portal/shifts.html', context)
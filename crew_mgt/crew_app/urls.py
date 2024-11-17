# urls.py
from django.urls import path
from . import views
from django.views.generic import RedirectView
from django.contrib.auth.views import LogoutView

urlpatterns = [
    # Authentication URLs
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', LogoutView.as_view(next_page='home'), name='logout'),
    path('crew-login/', views.crew_login_view, name='crew_login'),
    path('accounts/login/', RedirectView.as_view(url='/crew_login/', permanent=True)),  # Redirect to new login path

    # Home and Status URLs
    path('', views.home, name='home'),
    path('recruitment-status/', views.recruitment_status, name='recruitment_status'),

    # Portal URLs - all under /portal namespace
    path('portal/', views.crew_portal, name='crew_portal'),
    path('portal/profile/', views.profile_view, name='profile'),
    path('portal/shift/', views.shift_view, name='shift'),
    path('portal/leave/', views.leave_view, name='leave'),

    # Task Management URLs
    path('portal/tasks/', views.tasks_view, name='tasks'),
    path('portal/tasks/<int:task_id>/update/', views.update_task_status, name='update_task'),

    # Attendance Management URLs
    path('portal/attendance/', views.attendance_view, name='attendance'),
    path('portal/attendance/clock-in/', views.clock_in, name='clock_in'),
    path('portal/attendance/clock-out/', views.clock_out, name='clock_out'),
]

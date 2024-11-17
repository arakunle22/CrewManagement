from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, CrewProfile, Department, Position, Document, Attendance, Shift, LeaveRequest, Task, Payroll, Performance, Announcement

# Register the custom User model with the admin site
admin.site.register(User, UserAdmin)

@admin.register(CrewProfile)
class CrewProfileAdmin(admin.ModelAdmin):
    list_display = ('crew_id', 'first_name', 'last_name', 'department', 'position', 'recruitment_status')
    list_filter = ('recruitment_status', 'department', 'position')
    search_fields = ('first_name', 'last_name', 'crew_id')
    readonly_fields = ('crew_id', 'date_joined', 'last_modified')
    actions = ['approve_profile', 'reject_profile']

    def approve_profile(self, request, queryset):
        queryset.update(recruitment_status='approved')
    approve_profile.short_description = 'Approve selected profiles'

    def reject_profile(self, request, queryset):
        queryset.update(recruitment_status='rejected')
    reject_profile.short_description = 'Reject selected profiles'

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at')
    search_fields = ('name',)

@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ('title', 'department', 'description', 'created_at')
    search_fields = ('title', 'department__name')
    list_filter = ('department',)

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'crew_profile', 'uploaded_at', 'is_verified')
    search_fields = ('title', 'crew_profile__first_name', 'crew_profile__last_name')
    list_filter = ('is_verified',)
    actions = ['verify_document']

    def verify_document(self, request, queryset):
        queryset.update(is_verified=True)
    verify_document.short_description = 'Verify selected documents'

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('crew', 'date', 'clock_in', 'clock_out', 'hours_worked')
    search_fields = ('crew__first_name', 'crew__last_name')
    list_filter = ('date',)

@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ('crew', 'start_time', 'end_time', 'description')
    list_filter = ('crew', 'start_time')
    search_fields = ('crew__user__email', 'description')

@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ('crew', 'start_date', 'end_date', 'reason', 'status')
    search_fields = ('crew__first_name', 'crew__last_name')
    list_filter = ('status', 'start_date', 'end_date')
    actions = ['approve_leave', 'reject_leave']

    def approve_leave(self, request, queryset):
        queryset.update(status='approved')
    approve_leave.short_description = 'Approve selected leave requests'

    def reject_leave(self, request, queryset):
        queryset.update(status='rejected')
    reject_leave.short_description = 'Reject selected leave requests'

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'crew', 'status', 'deadline')
    search_fields = ('title', 'crew__first_name', 'crew__last_name')
    list_filter = ('status', 'deadline')

@admin.register(Payroll)
class PayrollAdmin(admin.ModelAdmin):
    list_display = ('crew', 'month', 'basic_salary', 'overtime_pay', 'deductions', 'net_salary', 'payment_status', 'payment_date')
    search_fields = ('crew__first_name', 'crew__last_name')
    list_filter = ('month', 'payment_status')

@admin.register(Performance)
class PerformanceAdmin(admin.ModelAdmin):
    list_display = ('crew', 'review_date', 'rating', 'comments', 'reviewed_by')
    search_fields = ('crew__first_name', 'crew__last_name', 'reviewed_by__username')
    list_filter = ('review_date', 'rating')

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_global', 'created_at', 'created_by')
    search_fields = ('title', 'content', 'created_by__username')
    list_filter = ('is_global', 'created_at')
    actions = ['send_announcement']

    def send_announcement(self, request, queryset):
        for announcement in queryset:
            announcement.departments.all().crew_profile_set.send_announcement(announcement.title, announcement.content)
    send_announcement.short_description = 'Send selected announcements'
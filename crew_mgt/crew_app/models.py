from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid

class User(AbstractUser):
    email = models.EmailField(unique=True)
    is_crew = models.BooleanField(default=False)
    is_hr = models.BooleanField(default=False)

    def __str__(self):
        return self.email

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='crew_app_user_groups',
        related_query_name='crew_app_user',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='crew_app_user_permissions',
        related_query_name='crew_app_user',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

class Department(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

class Position(models.Model):
    title = models.CharField(max_length=100)
    department = models.ForeignKey(
        Department, 
        on_delete=models.PROTECT,  # Changed from CASCADE to PROTECT
        related_name='positions'
    )
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.department}"

    class Meta:
        ordering = ['title']

class CrewProfile(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='crew_profile'
    )
    crew_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20)
    date_of_birth = models.DateField()
    address = models.TextField()
    department = models.ForeignKey(
        Department, 
        on_delete=models.SET_NULL, 
        null=True,
        blank=True,
        related_name='crew_members'
    )
    position = models.ForeignKey(
        Position, 
        on_delete=models.SET_NULL, 
        null=True,
        blank=True,
        related_name='crew_members'
    )
    recruitment_status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending'
    )
    date_joined = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.crew_id} - {self.first_name} {self.last_name}"

    def save(self, *args, **kwargs):
        # Ensure position matches department
        if self.position and self.department:
            if self.position.department != self.department:
                self.position = None
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['last_name', 'first_name']

class Document(models.Model):
    crew_profile = models.ForeignKey(
        CrewProfile, 
        on_delete=models.CASCADE, 
        related_name='documents'
    )
    title = models.CharField(max_length=100)
    file = models.FileField(upload_to='crew_documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.title} - {self.crew_profile.crew_id}"

class Attendance(models.Model):
    crew = models.ForeignKey(
        CrewProfile, 
        on_delete=models.CASCADE,
        related_name='attendances'
    )
    date = models.DateField()
    clock_in = models.DateTimeField(null=True, blank=True)
    clock_out = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['crew', 'date']
        ordering = ['-date']

    def __str__(self):
        return f"{self.crew.crew_id} - {self.date}"

    def hours_worked(self):
        if self.clock_in and self.clock_out:
            return (self.clock_out - self.clock_in).total_seconds() / 3600
        return 0

class Shift(models.Model):
    crew = models.ForeignKey(
        CrewProfile, 
        on_delete=models.CASCADE,
        related_name='shifts'
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.crew.crew_id} - {self.start_time.date()}"

    def shift_duration(self):
        return (self.end_time - self.start_time).total_seconds() / 3600

    class Meta:
        ordering = ['-start_time']

class LeaveRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    crew = models.ForeignKey(
        CrewProfile, 
        on_delete=models.CASCADE,
        related_name='leave_requests'
    )
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.crew.crew_id} - {self.start_date}"

    class Meta:
        ordering = ['-created_at']

class Task(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]

    crew = models.ForeignKey(
        CrewProfile, 
        on_delete=models.CASCADE,
        related_name='tasks'
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending'
    )
    deadline = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_status_color(self):
        status_colors = {
            'pending': 'warning',
            'in_progress': 'info',
            'completed': 'success'
        }
        return status_colors.get(self.status, 'secondary')
    def __str__(self):
        return f"{self.title} - {self.crew.crew_id}"

    class Meta:
        ordering = ['deadline']

class Payroll(models.Model):
    crew = models.ForeignKey(
        CrewProfile, 
        on_delete=models.CASCADE,
        related_name='payrolls'
    )
    month = models.DateField()
    basic_salary = models.DecimalField(max_digits=10, decimal_places=2)
    overtime_pay = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    net_salary = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status = models.BooleanField(default=False)
    payment_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.crew.crew_id} - {self.month}"

    def save(self, *args, **kwargs):
        self.net_salary = self.basic_salary + self.overtime_pay - self.deductions
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-month']
        unique_together = ['crew', 'month']

class Performance(models.Model):
    RATING_CHOICES = [
        (1, 'Poor'),
        (2, 'Below Average'),
        (3, 'Average'),
        (4, 'Good'),
        (5, 'Excellent'),
    ]

    crew = models.ForeignKey(
        CrewProfile, 
        on_delete=models.CASCADE,
        related_name='performances'
    )
    review_date = models.DateField()
    rating = models.IntegerField(choices=RATING_CHOICES)
    comments = models.TextField()
    reviewed_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='reviews_given'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.crew.crew_id} - {self.review_date}"

    class Meta:
        ordering = ['-review_date']

class Announcement(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    departments = models.ManyToManyField(Department, blank=True, related_name='announcements')
    is_global = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='announcements_created'
    )
    
    def get_department_names(self):
        return ", ".join([dept.name for dept in self.departments.all()])

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']
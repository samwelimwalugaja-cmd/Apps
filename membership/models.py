from django.db import models
from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib.auth.hashers import make_password


class Member(models.Model):
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('inactive', 'Inactive'),
        ('active', 'Active'),
    ]
    
    APPROVAL_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
    ]
    
    # Authentication fields
    username = models.CharField(max_length=150, unique=True, blank=True, null=True)
    
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100)
    
    email = models.EmailField(max_length=100, unique=True)
    password = models.CharField(max_length=255)
    is_deleted = models.BooleanField(default=False)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    is_admin = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        if not self.password.startswith('pbkdf2_'):
            self.password = make_password(self.password)
        # Auto-generate username from email if not provided
        if not self.username and self.email:
            self.username = self.email.split('@')[0]
        super().save(*args, **kwargs)
    
    gender = models.CharField(max_length=10, null=True, blank=True, choices=GENDER_CHOICES)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    whyhycg = models.TextField(null=True, blank=True)
    
    
     # New fields for payment tracking
    payment_deadline = models.DateTimeField(null=True, blank=True)
    payment_step = models.IntegerField(default=1)  # 1,2,3,4
    payment_submitted = models.BooleanField(default=False)
    payment_receipt = models.FileField(upload_to='payments/', null=True, blank=True)
    payment_transaction_ref = models.CharField(max_length=100, null=True, blank=True)
    payment_status = models.CharField(max_length=20, default='pending')  # pending, approved, rejected
    payment_submitted_at = models.DateTimeField(null=True, blank=True)
    
    
    profile_picture = models.ImageField(upload_to='profile_pictures/', null=True, blank=True)
    
    approved = models.CharField(max_length=20, choices=APPROVAL_CHOICES, default='pending')
    registration_fee_status = models.CharField(max_length=20, default='pending')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='inactive')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def is_active_member(self):
        """For admin compatibility"""
        return self.approved == 'approved' and self.status == 'active'
    
    @property
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Announcement(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    file = models.FileField(upload_to='announcements/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(Member, on_delete=models.SET_NULL, null=True, blank=True)
    
     # 🔥 NEW FIELD
    expires_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        # default: announcement in expire after 5 days
        if not self.expires_at:
            self.expires_at = self.created_at + timedelta(days=5) if self.created_at else timezone.now() + timedelta(days=5)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.title


class Event(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    file = models.FileField(upload_to='events/', null=True, blank=True)
    budget = models.DecimalField(max_digits=10, decimal_places=2)
    event_date = models.DateField()
    location = models.CharField(max_length=255)
    time = models.TimeField()
    
    attendees = models.ManyToManyField(Member, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(Member, on_delete=models.SET_NULL, null=True, blank=True, related_name='events_created')
    
    def __str__(self):
        return self.title


class MembershipPayment(models.Model):
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='payments')
    month = models.CharField(max_length=7)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    approved_by = models.ForeignKey(Member, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_payments')
    receipt_file = models.FileField(upload_to='payment_receipts/', null=True, blank=True)
    
    def __str__(self):
        return f"{self.member.first_name} - {self.month}"


class Donation(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='donations')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    campaign_name = models.CharField(max_length=255)
    message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    receipt_file = models.FileField(upload_to='donation_receipts/', null=True, blank=True)
    
    def __str__(self):
        return f"{self.member.first_name} - {self.amount}"


class MembershipReport(models.Model):
    REPORT_TYPES = [
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annual', 'Annual'),
        ('special', 'Special'),
    ]
    
    report_title = models.CharField(max_length=255)
    period = models.CharField(max_length=50)  # e.g., "January 2025"
    published_year = models.IntegerField()
    total_members = models.IntegerField()
    collections = models.DecimalField(max_digits=12, decimal_places=2)
    file = models.FileField(upload_to='reports/membership/', null=True, blank=True)
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(Member, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return self.report_title


class EventReport(models.Model):
    EVENT_TYPES = [
        ('workshop', 'Workshop'),
        ('fundraising', 'Fundraising'),
        ('outreach', 'Outreach'),
        ('training', 'Training'),
        ('other', 'Other'),
    ]
    
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='reports', null=True, blank=True)
    event_name = models.CharField(max_length=255)
    event_date = models.DateField()
    event_type = models.CharField(max_length=100, choices=EVENT_TYPES)
    attendees = models.IntegerField()
    funds_raised = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    published_date = models.DateField(auto_now_add=True)
    report_file = models.FileField(upload_to='reports/events/', null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"Report: {self.event_name}"
    
    
class EventRegistration(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('CANCELLED', 'Cancelled'),
        ('ATTENDED', 'Attended'),
    ]
    
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='registrations')
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='event_registrations')
    phone = models.CharField(max_length=15)
    guests = models.IntegerField(default=0)
    registration_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    confirmation_sent = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['event', 'member']  # Mmemba hawezi kujiregister mara mbili kwenye event moja
    
    def __str__(self):
        return f"{self.member.first_name} - {self.event.title}"


class FinancialReport(models.Model):
    REPORT_TYPE_CHOICES = [
        ('income', 'Income Statement'),
        ('expenditure', 'Expenditure Report'),
        ('balance', 'Balance Sheet'),
        ('audit', 'Audit Report'),
    ]
    
    PERIOD_CHOICES = [
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annual', 'Annual'),
    ]
    
    report_title = models.CharField(max_length=255)
    type = models.CharField(max_length=50, choices=REPORT_TYPE_CHOICES)
    period = models.CharField(max_length=50, choices=PERIOD_CHOICES)
    year = models.IntegerField()
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    report_file = models.FileField(upload_to='reports/financial/', null=True, blank=True)
    created_by = models.ForeignKey(Member, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return self.report_title


class ImpactReport(models.Model):
    CATEGORY_CHOICES = [
        ('education', 'Education'),
        ('health', 'Health'),
        ('economic', 'Economic Empowerment'),
        ('environment', 'Environment'),
        ('community', 'Community Development'),
    ]
    
    report_title = models.CharField(max_length=255)
    category = models.CharField(max_length=100, choices=CATEGORY_CHOICES)
    period = models.CharField(max_length=50)
    lives_impacted = models.IntegerField()
    beneficiaries = models.IntegerField()
    report_file = models.FileField(upload_to='reports/impact/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    report_content = models.TextField(blank=True, null=True, help_text="Detailed impact report content")
    created_by = models.ForeignKey(Member, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return self.report_title
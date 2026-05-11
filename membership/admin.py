from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count
from django.utils import timezone
from .models import (
    Member, Announcement, Event, EventRegistration, 
    MembershipPayment, Donation, MembershipReport, 
    EventReport, FinancialReport, ImpactReport
)

# ============================================================
# INLINE CLASSES
# ============================================================

class EventRegistrationInline(admin.TabularInline):
    """Show registrations inside Event admin page"""
    model = EventRegistration
    extra = 0
    fields = ['member', 'phone', 'guests', 'status', 'registration_date']
    readonly_fields = ['registration_date']
    can_delete = True
    show_change_link = True
    classes = ['collapse']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('member')


class MembershipPaymentInline(admin.TabularInline):
    """Show payments inside Member admin page"""
    model = MembershipPayment
    fk_name = 'member'
    extra = 0
    fields = ['month', 'amount', 'status', 'created_at']
    readonly_fields = ['created_at']
    can_delete = True
    classes = ['collapse']


class DonationInline(admin.TabularInline):
    """Show donations inside Member admin page"""
    model = Donation
    extra = 0
    fields = ['amount', 'campaign_name', 'created_at']
    readonly_fields = ['created_at']
    can_delete = True
    classes = ['collapse']


# ============================================================
# MEMBER ADMIN
# ============================================================

@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'email', 'phone_number', 
                   'approved', 'status', 'payment_status', 'total_events_registered']
    list_filter = ['approved', 'status', 'payment_status', 'gender', 'is_admin', 'date_joined']
    search_fields = ['first_name', 'last_name', 'email', 'phone_number', 'username']
    readonly_fields = ['date_joined', 'created_at', 'updated_at']
    inlines = [MembershipPaymentInline, DonationInline]
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('first_name', 'middle_name', 'last_name', 'gender', 'phone_number', 'address')
        }),
        ('Account Information', {
            'fields': ('username', 'email', 'password', 'profile_picture')
        }),
        ('Registration & Approval', {
            'fields': ('approved', 'status', 'payment_status', 'payment_step', 
                      'payment_deadline', 'payment_submitted', 'whyhycg')
        }),
        ('Payment Tracking', {
            'fields': ('payment_receipt', 'payment_transaction_ref', 'payment_submitted_at'),
            'classes': ('collapse',)
        }),
        ('Permissions', {
            'fields': ('is_admin', 'is_staff', 'is_superuser', 'is_deleted', 'expires_at'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('date_joined', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def total_events_registered(self, obj):
        count = obj.event_registrations.count()
        return f"{count} events"
    total_events_registered.short_description = 'Events Registered'
    
    actions = ['approve_members', 'reject_members', 'export_members_csv']
    
    def approve_members(self, request, queryset):
        updated = queryset.update(approved='approved', status='active')
        self.message_user(request, f'✅ {updated} member(s) approved')
    approve_members.short_description = "Approve selected members"
    
    def reject_members(self, request, queryset):
        updated = queryset.update(approved='pending', status='inactive')
        self.message_user(request, f'❌ {updated} member(s) rejected')
    reject_members.short_description = "Reject selected members"
    
    def export_members_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID', 'First Name', 'Last Name', 'Email', 'Phone', 
                        'Gender', 'Status', 'Approved', 'Payment Status', 'Date Joined'])
        
        for member in queryset:
            writer.writerow([
                member.id, member.first_name, member.last_name, 
                member.email, member.phone_number, member.gender,
                member.status, member.approved, member.payment_status,
                member.date_joined.strftime('%Y-%m-%d') if member.date_joined else ''
            ])
        
        response = HttpResponse(output.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="members_report.csv"'
        return response
    export_members_csv.short_description = "📊 Export selected members to CSV"


# ============================================================
# ANNOUNCEMENT ADMIN - FIXED (No format_html issues)
# ============================================================

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ['title', 'created_at', 'expires_at', 'status_display', 'created_by']
    list_filter = ['created_at', 'expires_at']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at']
    
    def status_display(self, obj):
        """Display status without format_html issues"""
        if obj.expires_at and obj.expires_at > timezone.now():
            return "✓ Active"
        elif obj.expires_at and obj.expires_at <= timezone.now():
            return "✗ Expired"
        return "No expiry"
    status_display.short_description = 'Status'


# ============================================================
# EVENT ADMIN
# ============================================================

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['title', 'event_date', 'time', 'location', 'budget', 'total_attendees', 'status_count']
    list_filter = ['event_date', 'location', 'created_at']
    search_fields = ['title', 'description', 'location']
    readonly_fields = ['created_at']
    inlines = [EventRegistrationInline]
    filter_horizontal = ['attendees']
    
    fieldsets = (
        ('Event Information', {
            'fields': ('title', 'description', 'event_date', 'time', 'location')
        }),
        ('Budget & Files', {
            'fields': ('budget', 'file'),
            'classes': ('collapse',)
        }),
        ('Attendees', {
            'fields': ('attendees',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def total_attendees(self, obj):
        return obj.registrations.count()
    total_attendees.short_description = 'Registered'
    
    def status_count(self, obj):
        confirmed = obj.registrations.filter(status='CONFIRMED').count()
        pending = obj.registrations.filter(status='PENDING').count()
        return f"✓{confirmed} | ⏳{pending}"
    status_count.short_description = 'C/P'
    
    actions = ['export_events_csv']
    
    def export_events_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID', 'Title', 'Date', 'Time', 'Location', 'Budget', 'Total Registrations'])
        
        for event in queryset:
            writer.writerow([
                event.id, event.title, event.event_date, event.time, 
                event.location, event.budget, event.registrations.count()
            ])
        
        response = HttpResponse(output.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="events_report.csv"'
        return response
    export_events_csv.short_description = "📊 Export events to CSV"


# ============================================================
# EVENT REGISTRATION ADMIN
# ============================================================

@admin.register(EventRegistration)
class EventRegistrationAdmin(admin.ModelAdmin):
    list_display = ['id', 'get_event_title', 'get_event_date', 'get_member_name', 
                   'phone', 'guests', 'registration_date', 'status']
    list_filter = ['status', 'registration_date', 'event__event_date']
    search_fields = ['member__first_name', 'member__last_name', 'phone', 'event__title']
    readonly_fields = ['registration_date']
    raw_id_fields = ['event', 'member']
    
    def get_event_title(self, obj):
        return obj.event.title
    get_event_title.short_description = 'Event'
    
    def get_event_date(self, obj):
        return obj.event.event_date
    get_event_date.short_description = 'Event Date'
    
    def get_member_name(self, obj):
        return f"{obj.member.first_name} {obj.member.last_name}"
    get_member_name.short_description = 'Member'
    
    actions = ['mark_as_confirmed', 'mark_as_cancelled', 'mark_as_attended', 'export_csv']
    
    def mark_as_confirmed(self, request, queryset):
        updated = queryset.update(status='CONFIRMED')
        self.message_user(request, f'✅ {updated} registration(s) confirmed')
    mark_as_confirmed.short_description = "Mark as CONFIRMED"
    
    def mark_as_cancelled(self, request, queryset):
        updated = queryset.update(status='CANCELLED')
        self.message_user(request, f'❌ {updated} registration(s) cancelled')
    mark_as_cancelled.short_description = "Mark as CANCELLED"
    
    def mark_as_attended(self, request, queryset):
        updated = queryset.update(status='ATTENDED')
        self.message_user(request, f'✓ {updated} registration(s) marked as attended')
    mark_as_attended.short_description = "Mark as ATTENDED"
    
    def export_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID', 'Event', 'Member', 'Phone', 'Guests', 'Registration Date', 'Status'])
        
        for reg in queryset:
            writer.writerow([
                reg.id, reg.event.title, f"{reg.member.first_name} {reg.member.last_name}",
                reg.phone, reg.guests, reg.registration_date, reg.status
            ])
        
        response = HttpResponse(output.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="registrations.csv"'
        return response
    export_csv.short_description = "📊 Export to CSV"


# ============================================================
# MEMBERSHIP PAYMENT ADMIN
# ============================================================

@admin.register(MembershipPayment)
class MembershipPaymentAdmin(admin.ModelAdmin):
    list_display = ['member', 'month', 'amount', 'status', 'created_at']
    list_filter = ['status', 'month', 'created_at']
    search_fields = ['member__first_name', 'member__last_name', 'month']
    readonly_fields = ['created_at']
    
    actions = ['approve_payments', 'reject_payments']
    
    def approve_payments(self, request, queryset):
        updated = queryset.update(status='approved')
        self.message_user(request, f'✅ {updated} payment(s) approved')
    approve_payments.short_description = "Approve selected payments"
    
    def reject_payments(self, request, queryset):
        updated = queryset.update(status='rejected')
        self.message_user(request, f'❌ {updated} payment(s) rejected')
    reject_payments.short_description = "Reject selected payments"


# ============================================================
# DONATION ADMIN
# ============================================================

@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ['member', 'amount', 'campaign_name', 'created_at']
    list_filter = ['created_at', 'campaign_name']
    search_fields = ['member__first_name', 'member__last_name', 'campaign_name']
    readonly_fields = ['created_at']


# ============================================================
# MEMBERSHIP REPORT ADMIN
# ============================================================

@admin.register(MembershipReport)
class MembershipReportAdmin(admin.ModelAdmin):
    list_display = ['report_title', 'period', 'published_year', 'report_type', 'total_members', 'collections']
    list_filter = ['report_type', 'published_year', 'created_at']
    search_fields = ['report_title', 'period']
    readonly_fields = ['created_at']


# ============================================================
# EVENT REPORT ADMIN
# ============================================================

@admin.register(EventReport)
class EventReportAdmin(admin.ModelAdmin):
    list_display = ['event_name', 'event_date', 'event_type', 'attendees', 'funds_raised']
    list_filter = ['event_type', 'event_date', 'published_date']
    search_fields = ['event_name', 'notes']


# ============================================================
# FINANCIAL REPORT ADMIN
# ============================================================

@admin.register(FinancialReport)
class FinancialReportAdmin(admin.ModelAdmin):
    list_display = ['report_title', 'type', 'period', 'year', 'total_amount']
    list_filter = ['type', 'period', 'year']
    search_fields = ['report_title']
    readonly_fields = ['created_at']


# ============================================================
# IMPACT REPORT ADMIN
# ============================================================

@admin.register(ImpactReport)
class ImpactReportAdmin(admin.ModelAdmin):
    list_display = ['report_title', 'category', 'period', 'lives_impacted', 'beneficiaries']
    list_filter = ['category', 'created_at']
    search_fields = ['report_title', 'report_content']


# ============================================================
# CUSTOM ADMIN SITE HEADER
# ============================================================

admin.site.site_header = "HYCG Admin"
admin.site.site_title = "HYCG Admin Portal"
admin.site.index_title = "Welcome to HYCG Membership Administration"
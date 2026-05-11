from asyncio import events
from enum import member
from time import timezone
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.urls import reverse
from django.http import JsonResponse

from datetime import timedelta
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os



from django.shortcuts import render,redirect
from .models import Member, Announcement, Event, EventReport, MembershipPayment, Donation, MembershipReport, FinancialReport, ImpactReport, EventRegistration
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.db import models  


#================= Member Helper Function =================
def get_logged_in_member(request):
    member_id = request.session.get('member_id')
    if not member_id:
        return None
    
    try:
        return Member.objects.get(id=member_id)
    except Member.DoesNotExist:
        return None
    
#================= End of Member Helper Function =================


#================= Check Status View =================
def check_status(request):
    member_id = request.session.get('member_id')

    if not member_id:
        return JsonResponse({'status': 'not_logged_in'})

    member = Member.objects.get(id=member_id)

    return JsonResponse({
        'status': member.status,
        'approved': member.approved
    })
#================= End of Check Status View =================
    
#================= Member Registration View =================
def register(request):
    if request.method =='POST':
        first_name=request.POST.get('first_name')
        last_name=request.POST.get('last_name')
        email=request.POST.get('email')
        password=request.POST.get('password')
        gender=request.POST.get('gender')
        profile_picture=request.FILES.get('profile_picture')
        
        # 🔥 CHECK IF EMAIL IS ALREADY REGISTERED
        if Member.objects.filter(email=email).exists():
            messages.error(request, "Email already registered!")
            return redirect('membership:register')

        # 🔥 HAPA NDIPO UNAWEKA LOGIC YA KUREGISTER MEMBER
        Member.objects.create(
            first_name=first_name,
            last_name=last_name,
            email=email,
            password=make_password(password),
            gender=gender,
            profile_picture=profile_picture
        )
        # ✅ SUCCESS MESSAGE
        messages.success(request, f"🎉 Registration successful {first_name}!.")
        return redirect('membership:register')
    return render(request,'registration.html')

#================= End of Member Registration View =================

#================= Member Login View =================
def login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        # 🔥 HAPA NDIPO UNAWEKA LOGIC YA KUKI CHECK EMAIL NA PASSWORD
        try:
            member = Member.objects.get(email=email)

            if check_password(password, member.password):
                request.session['member_id'] = member.id

                # 🔥 LOGIC YAKO HALISI
                if member.approved == "pending":
                    return redirect('membership:Make Payment')

                elif member.approved == "pending" and member.status == "inactive":
                    return redirect('membership:Make Payment')

                elif member.status == "inactive" and member.approved == "approved":
                    return redirect('membership:Make Profile')

                elif member.status == "active" and member.approved == "approved":
                    return redirect('membership:dashboard')

            else:
                messages.error(request, "Incorrect password.")
                return redirect('membership:login')


        except Member.DoesNotExist:
            messages.error(request, "Email not found.")
            return redirect('membership:login')

    return render(request, 'login.html')

#================= End of Member Login View =================

#================= Forget Password Views =================
def forgetPassword(request):
    if request.method == 'POST':
        email = request.POST.get('email')

        # 🔥 CHECK IF EMAIL EXISTS
        try:
            member = Member.objects.get(email=email)

            request.session['reset_member'] = member.id

            # 🔥 HAPA NDIPO UNAWEKA LINK
            reset_link = request.build_absolute_uri(
                reverse('membership:Reset Password')
            )

            # 🔥 kisha unaituma email
            send_mail(
                subject="Reset Password",
                message=f"Click this link to reset your password: {reset_link}",
                from_email="your_email@gmail.com",
                recipient_list=[email],
                fail_silently=False
            )

            return redirect('membership:check email')

        except Member.DoesNotExist:
            messages.error(request, "Email not found")

    return render(request, 'forgot password.html')

#================= End of Forget Password Views =================

#================= Reset Password View =================
def resetPassword(request):
    member_id = request.session.get('reset_member')

    if not member_id:
        return redirect('membership:forgetPassword')

    member = Member.objects.get(id=member_id)

    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if new_password != confirm_password:
            messages.error(request, "Passwords do not match")
            return redirect('membership:Reset Password')

        member.password = make_password(new_password)
        member.save()

        messages.success(request, "Password reset successfully")
        return redirect('membership:login')

    return render(request,'reset password.html')

#================= End of Reset Password View =================

#================= Check Email View =================
def checkEmail(request):
    return render(request,'check_email.html')
#================= End of Check Email View =================


#================= Payment Page View after Registration =================
def paymentPage(request):
    member_id = request.session.get('member_id')
    
    if not member_id:
        return redirect('membership:login')
    
    member = Member.objects.get(id=member_id)
    
    # Create deadline if doesn't exist (first time visiting payment page)
    if not member.payment_deadline:
        member.payment_deadline = timezone.now() + timedelta(days=14)
        member.save()
    
    # Check if deadline has expired
    is_expired = timezone.now() > member.payment_deadline
    
    return render(request, 'payment.html', {
        'member': member,
        'is_expired': is_expired,
        'deadline': member.payment_deadline
    })

@csrf_exempt
def submit_payment(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=400)
    
    member_id = request.session.get('member_id')
    if not member_id:
        return JsonResponse({'error': 'Not logged in'}, status=401)
    
    try:
        member = Member.objects.get(id=member_id)
        
        # Check if already submitted
        if member.payment_submitted:
            return JsonResponse({'error': 'Payment already submitted'}, status=400)
        
        # Check if expired
        if timezone.now() > member.payment_deadline:
            return JsonResponse({'error': 'Payment deadline has expired'}, status=400)
        
        # Get data
        transaction_ref = request.POST.get('transaction_ref', '')
        receipt_file = request.FILES.get('receipt_file')
        
        if not receipt_file:
            return JsonResponse({'error': 'Receipt file required'}, status=400)
        
        # Save receipt
        file_extension = os.path.splitext(receipt_file.name)[1]
        file_name = f"payment_{member.id}_{timezone.now().strftime('%Y%m%d_%H%M%S')}{file_extension}"
        file_path = default_storage.save(f'payments/{file_name}', ContentFile(receipt_file.read()))
        
        # Update member
        member.payment_receipt = file_path
        member.payment_transaction_ref = transaction_ref
        member.payment_submitted = True
        member.payment_step = 4
        member.payment_submitted_at = timezone.now()
        member.payment_status = 'pending'
        member.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Payment submitted successfully',
            'step': 4
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def check_payment_status(request):
    member_id = request.session.get('member_id')
    
    if not member_id:
        return JsonResponse({'error': 'Not logged in'}, status=401)
    
    try:
        member = Member.objects.get(id=member_id)
        
        return JsonResponse({
            'submitted': member.payment_submitted,
            'step': member.payment_step,
            'status': member.payment_status,
            'approved': member.payment_status == 'approved',
            'deadline': member.payment_deadline.isoformat() if member.payment_deadline else None,
            'is_expired': timezone.now() > member.payment_deadline if member.payment_deadline else False
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
    
@csrf_exempt
def save_payment_step(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=400)
    
    member_id = request.session.get('member_id')
    if not member_id:
        return JsonResponse({'error': 'Not logged in'}, status=401)
    
    try:
        data = json.loads(request.body)
        step = data.get('step')
        
        member = Member.objects.get(id=member_id)
        member.payment_step = step
        member.save()
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

#================= End of Payment Page View after Registration =================

#================= Make Profile Views =================
def makeprofile(request):
    member_id = request.session.get('member_id')
    
    if not member_id:
        return redirect('membership:login')
    member = Member.objects.get(id=member_id)
    
    if request.method == 'POST':
        member.first_name = request.POST.get('first_name')
        member.middle_name = request.POST.get('middle_name')
        member.last_name = request.POST.get('last_name')
        member.email = request.POST.get('email')
        member.gender = request.POST.get('gender')
        member.phone_number = request.POST.get('phone_number')
        member.address = request.POST.get('address')
        member.whyhycg = request.POST.get('whyhycg')
        
        if request.FILES.get('profile_picture'):
            member.profile_picture = request.FILES.get('profile_picture')
        
        # 🔥 IMPORTANT
        member.status = "active"

        member.save()

        messages.success(request, "Profile completed successfully!")

        return redirect('membership:dashboard')
    return render(request, 'make profile.html', {'member': member})

#================= End of Make Profile Views =================


#================= Dashboard View =================
def dashboard(request):
    member = get_logged_in_member(request)
    events_list = Event.objects.all().order_by('-event_date')

    paginator = Paginator(events_list, 5)  # 5 events per page
    page_number = request.GET.get('page')
    events = paginator.get_page(page_number)
    
    total_events = Event.objects.count()
    upcoming_events = Event.objects.filter(event_date__gte=timezone.now().date()).count()
    context = {
        'events': Event.objects.all(),
        'total_events': total_events,
        'upcoming_events': upcoming_events,
    }
    
    announcements = Announcement.objects.filter(
        expires_at__gte=timezone.now()
    ).order_by('-created_at')[:3]   # 🔥 only 3

    context = {
        'announcements': announcements,
    }
    
    if not member:
        return redirect('membership:login')

    return render(request,'dashboard.html', {'member': member, 'events': events, 'total_events': total_events, 'upcoming_events': upcoming_events, 'announcements': announcements})

#================= End of Dashboard View =================


#================= View Profile Views =================
def viewProfile(request):
    member_id = request.session.get('member_id')

    if not member_id:
        return redirect('membership:login')

    member = Member.objects.get(id=member_id)

    return render(request,'viewprofile.html', {'member': member})

#================= End of View Profile Views =================


#================= Edit Profile Views =================
def editProfile(request):
    member_id = request.session.get('member_id')

    if not member_id:
        return redirect('membership:login')

    member = Member.objects.get(id=member_id)

    if request.method == 'POST':
        member.first_name = request.POST.get('first_name')
        member.middle_name = request.POST.get('middle_name')
        member.last_name = request.POST.get('last_name')
        member.email = request.POST.get('email')
        member.phone_number = request.POST.get('phone_number')
        member.nationality = request.POST.get('nationality')
        member.address = request.POST.get('address')

        if request.FILES.get('profile_picture'):
            member.profile_picture = request.FILES.get('profile_picture')

        member.save()

        messages.success(request, "Profile updated successfully!")
        return redirect('membership:viewProfile')

    return render(request, 'edit_profile.html', {'member': member})

#================= End of Edit Profile Views =================


#================= Change Password View =================
def changePassword(request):
    member_id = request.session.get('member_id')

    if not member_id:
        return redirect('membership:login')

    member = Member.objects.get(id=member_id)

    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if not check_password(current_password, member.password):
            messages.error(request, "Current password is incorrect.")
            return redirect('membership:changePassword')
        
        if new_password != confirm_password:
            messages.error(request, "New password and confirm password do not match.")
            return redirect('membership:changePassword')

        member.password = make_password(new_password)
        member.save()

        messages.success(request, "Password changed successfully!")
        return redirect('membership:dashboard')

    return render(request, 'change_password.html', {'member': member})

#================= End of Change Password View =================


#================= Delete Account View =================
def deleteAccount(request):
    member_id = request.session.get('member_id')

    if not member_id:
        return redirect('membership:login')

    member = Member.objects.get(id=member_id)

    if request.method == 'POST':
        member.delete()
        request.session.flush()
        messages.success(request, "Account deleted successfully!")
        return redirect('membership:register')

    return render(request, 'delete_account.html', {'member': member})

#================= End of Delete Account View =================



def viewAnnouncement(request):
    member_id = request.session.get('member_id')

    if not member_id:
        return redirect('membership:login')

    member = Member.objects.get(id=member_id)
    
    # Get ALL announcements (including expired) ordered by created_at (newest first)
    announcements = Announcement.objects.all().order_by('-created_at')
    
    # Add custom property to check if announcement is new (not expired)
    for announcement in announcements:
        if announcement.expires_at:
            announcement.is_new = timezone.now() <= announcement.expires_at
        else:
            announcement.is_new = True  # No expiry means always new
    
    # Count total announcements
    total_count = announcements.count()
    
    # Count active (new) announcements
    active_count = sum(1 for a in announcements if a.is_new)
    expired_count = total_count - active_count
    
    context = {
        'member': member,
        'announcements': announcements,
        'total_count': total_count,
        'active_count': active_count,
        'expired_count': expired_count,
        'now': timezone.now(),
    }
    
    return render(request, 'view_announcement.html', context)


#================= Donation Views =================
def donation(request):
    member_id = request.session.get('member_id')

    if not member_id:
        return redirect('membership:login')

    member = Member.objects.get(id=member_id)

    if request.method == 'POST':
        amount = request.POST.get('amount')
        # Process donation logic here
        messages.success(request, "Donation submitted successfully!")
        return redirect('membership:dashboard')

    return render(request, 'donation.html', {'member': member})

#================= End of Donation Views =================


#================= Make Donation Views =================
def makeDonation(request):
    member_id = request.session.get('member_id')

    if not member_id:
        return redirect('membership:login')

    member = Member.objects.get(id=member_id)

    if request.method == 'POST':
        amount = request.POST.get('amount')
        # Process donation logic here
        messages.success(request, "Donation submitted successfully!")
        return redirect('membership:dashboard')

    return render(request, 'make_donation.html', {'member': member})

#================= End of Make Donation Views =================

#================= Donation History Views =================
def donationHistory(request):
    member_id = request.session.get('member_id')

    if not member_id:
        return redirect('membership:login')

    member = Member.objects.get(id=member_id)

    # Process donation history retrieval logic here

    return render(request, 'donation_history.html', {'member': member})

#================= End of Donation History Views =================


#================= Membership Fee Payment Views =================
def membershipfeePayment(request):
    member_id = request.session.get('member_id')

    if not member_id:
        return redirect('membership:login')

    member = Member.objects.get(id=member_id)

    if request.method == 'POST':
        amount = request.POST.get('amount')
        # Process membership fee payment logic here
        messages.success(request, "Membership fee payment submitted successfully!")
        return redirect('membership:dashboard')

    return render(request, 'membershipfee_payment.html', {'member': member})
#================= End of Membership Fee Payment Views =================


#================= Payment History Views =================
def paymentHistory(request):
    member_id = request.session.get('member_id')

    if not member_id:
        return redirect('membership:login')

    member = Member.objects.get(id=member_id)

    # Process payment history retrieval logic here

    return render(request, 'payment_history.html', {'member': member})

#================= End of Payment History Views =================

#================= Financial Report Views =================
def financialReport(request):
    member_id = request.session.get('member_id')

    if not member_id:
        return redirect('membership:login')

    member = Member.objects.get(id=member_id)

    # Process financial report generation logic here

    return render(request, 'financial_report.html', {'member': member})

#================= End of Financial Report Views =================



#================= Event Management and Reporting Views =================
def event(request):
    member_id = request.session.get('member_id')

    if not member_id:
        return redirect('membership:login')

    member = Member.objects.get(id=member_id)

    if request.method == 'POST':
        event_name = request.POST.get('event_name')
        # Process event registration logic here
        messages.success(request, "Event registration submitted successfully!")
        return redirect('membership:dashboard')

    return render(request, 'event.html', {'member': member})

#================= End of Event Management and Reporting Views =================


#================= Report Views =================
def report(request):
    member_id = request.session.get('member_id')

    if not member_id:
        return redirect('membership:login')

    member = Member.objects.get(id=member_id)

    # Process report generation logic here

    return render(request, 'report.html', {'member': member})

#================= End of Report Views =================


#================= Membership Report Views =================
def membershipReport(request):
    member_id = request.session.get('member_id')

    if not member_id:
        return redirect('membership:login')

    member = Member.objects.get(id=member_id)

    # Process report generation logic here

    return render(request, 'membership_report.html', {'member': member})

#================= End of Membership Report Views =================


#================= Upcoming Event Views =================
def upcomingEvent(request):
    member_id = request.session.get('member_id')
    
    if not member_id:
        return redirect('membership:login')
    
    member = Member.objects.get(id=member_id)
    now = timezone.now()  # Sasa hivi kwa timezone yako (Tanzania)
    
    # ============================================================
    # 🔥 FIX: Onyesha events ambazo:
    # 1. Date ni kubwa kuliko LEO, AU
    # 2. Date ni LEO lakini TIME bado haijafika
    # ============================================================
    upcoming_events = Event.objects.filter(
        Q(event_date__gt=now.date()) |  # Events za baadaye
        Q(event_date=now.date(), time__gt=now.time())  # Events za leo ambazo TIME bado haijafika
    ).order_by('event_date', 'time')
    
    # Angalia kama member amesajiliwa kwenye kila event
    for event in upcoming_events:
        event.already_registered = EventRegistration.objects.filter(
            event=event, 
            member=member,
            status='CONFIRMED'
        ).exists()
        
        event.has_cancelled = EventRegistration.objects.filter(
            event=event,
            member=member,
            status='CANCELLED'
        ).exists()
        
        # Count confirmed registrations only
        event.confirmed_count = EventRegistration.objects.filter(
            event=event,
            status='CONFIRMED'
        ).count()
    
    # Handle registration logic (POST)
    if request.method == 'POST':
        event_id = request.POST.get('event_id')
        phone = request.POST.get('phone')
        guests = request.POST.get('guests', 0)
        
        if event_id:
            try:
                event = Event.objects.get(id=event_id)
                
                # Check if user has cancelled registration
                cancelled_reg = EventRegistration.objects.filter(
                    event=event,
                    member=member,
                    status='CANCELLED'
                ).first()
                
                if cancelled_reg:
                    # Reactivate cancelled registration
                    cancelled_reg.status = 'CONFIRMED'
                    cancelled_reg.phone = phone
                    cancelled_reg.guests = int(guests) if guests else 0
                    cancelled_reg.save()
                    messages.success(request, f"Successfully re-registered for {event.title}!")
                    
                else:
                    # Check if user already has CONFIRMED registration
                    existing_confirmed = EventRegistration.objects.filter(
                        event=event,
                        member=member,
                        status='CONFIRMED'
                    ).exists()
                    
                    if existing_confirmed:
                        messages.warning(request, f"You are already registered for {event.title}!")
                    else:
                        # Create new registration
                        EventRegistration.objects.create(
                            event=event,
                            member=member,
                            phone=phone,
                            guests=int(guests) if guests else 0,
                            status='CONFIRMED'
                        )
                        messages.success(request, f"Successfully registered for {event.title}!")
                    
            except Event.DoesNotExist:
                messages.error(request, "Event not found!")
        
        return redirect('membership:upcoming event')
    
    context = {
        'member': member,
        'upcoming_events': upcoming_events,
        'now': now,
    }
    return render(request, 'upcoming_event.html', context)

#================= End of Upcoming Event Views =================






#================= My Events Views =================

def myEvents(request):
    member_id = request.session.get('member_id')
    
    if not member_id:
        return redirect('membership:login')
    
    member = Member.objects.get(id=member_id)
    today = timezone.now().date()
    
    # ============================================================
    # GET ALL REGISTRATIONS (zote pamoja)
    # ============================================================
    all_registrations = EventRegistration.objects.filter(
        member=member
    ).exclude(status='CANCELLED').select_related('event').order_by('-event__event_date', '-registration_date')
    
    # ============================================================
    # FILTERS
    # ============================================================
    search_query = request.GET.get('search')
    status_filter = request.GET.get('status')
    event_type_filter = request.GET.get('event_type')
    year_filter = request.GET.get('year')
    
    if search_query:
        all_registrations = all_registrations.filter(
            Q(event__title__icontains=search_query) |
            Q(event__location__icontains=search_query)
        )
    
    if status_filter:
        all_registrations = all_registrations.filter(status=status_filter)
    
    if event_type_filter == 'upcoming':
        all_registrations = all_registrations.filter(event__event_date__gte=today)
    elif event_type_filter == 'past':
        all_registrations = all_registrations.filter(event__event_date__lt=today)
    
    if year_filter:
        all_registrations = all_registrations.filter(event__event_date__year=year_filter)
    
    # ============================================================
    # STATISTICS
    # ============================================================
    total_registrations = all_registrations.count()
    upcoming_count = all_registrations.filter(event__event_date__gte=today).count()
    past_count = all_registrations.filter(event__event_date__lt=today).count()
    
    total_guests = all_registrations.aggregate(total=Sum('guests'))['total'] or 0
    
    # Available years for filter
    available_years = all_registrations.dates('event__event_date', 'year').values_list('event__event_date__year', flat=True).distinct()
    
    # ============================================================
    # PAGINATION (10 per page)
    # ============================================================
    paginator = Paginator(all_registrations, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # ============================================================
    # CONTEXT
    # ============================================================
    context = {
        'member': member,
        'page_obj': page_obj,
        'today': today,
        'total_registrations': total_registrations,
        'upcoming_count': upcoming_count,
        'past_count': past_count,
        'total_guests': total_guests,
        'search_query': search_query,
        'status_filter': status_filter,
        'event_type_filter': event_type_filter,
        'year_filter': year_filter,
        'available_years': available_years,
    }
    
    return render(request, 'my_events.html', context)


# ============================================================
# DOWNLOAD CERTIFICATE VIEW
# ============================================================
def download_certificate(request, registration_id):
    member_id = request.session.get('member_id')
    
    if not member_id:
        return redirect('membership:login')
    
    from django.http import HttpResponse
    import mimetypes
    
    try:
        registration = EventRegistration.objects.get(id=registration_id, member_id=member_id)
        
        if registration.event.file:
            file_path = registration.event.file.path
            with open(file_path, 'rb') as f:
                response = HttpResponse(f.read(), content_type=mimetypes.guess_type(file_path)[0])
                response['Content-Disposition'] = f'attachment; filename="{registration.event.title}_certificate.pdf"'
                return response
        else:
            messages.error(request, "Certificate not available for this event")
            return redirect('membership:my events')
            
    except EventRegistration.DoesNotExist:
        messages.error(request, "Registration not found")
        return redirect('membership:my events')
    
    

# ============================================================
# EDIT REGISTRATION VIEW
# ============================================================

def edit_registration(request):
    member_id = request.session.get('member_id')
    
    if not member_id:
        return redirect('membership:login')
    
    if request.method == 'POST':
        registration_id = request.POST.get('registration_id')
        phone = request.POST.get('phone')
        guests = request.POST.get('guests')
        
        try:
            registration = EventRegistration.objects.get(id=registration_id, member_id=member_id)
            
            if registration.event.event_date >= timezone.now().date():
                registration.phone = phone
                registration.guests = int(guests) if guests else 0
                registration.save()
                messages.success(request, f"Registration for {registration.event.title} updated successfully!")
            else:
                messages.error(request, "Cannot edit past events!")
                
        except EventRegistration.DoesNotExist:
            messages.error(request, "Registration not found!")
    
    return redirect('membership:my events')



#================= Event Cancellation Views =================
def cancel_registration(request):
    member_id = request.session.get('member_id')
    
    if not member_id:
        return redirect('membership:login')
    
    if request.method == 'POST':
        registration_id = request.POST.get('registration_id')
        
        try:
            registration = EventRegistration.objects.get(id=registration_id, member_id=member_id)
            
            if registration.event.event_date >= timezone.now().date():
                registration.status = 'CANCELLED'
                registration.save()
                messages.success(request, f"Registration for {registration.event.title} has been cancelled.")
            else:
                messages.error(request, "Cannot cancel past events!")
                
        except EventRegistration.DoesNotExist:
            messages.error(request, "Registration not found!")
    
    return redirect('membership:my events')
#================= END of Event Cancellation Views ========================



#================= Past Event Views =================
def pastEvent(request):
    member_id = request.session.get('member_id')

    if not member_id:
        return redirect('membership:login')

    member = Member.objects.get(id=member_id)

    # Process report generation logic here

    return render(request, 'past_event.html', {'member': member})

#================= End of Past Event Views =================



#================= Event Report Views =================
def eventReport(request):
    member_id = request.session.get('member_id')

    if not member_id:
        return redirect('membership:login')

    member = Member.objects.get(id=member_id)

    # Process report generation logic here

    return render(request, 'event_report.html', {'member': member})

#================= End of Event Report Views =================


#================= Impact Report Views =================
def impactReport(request):
    member_id = request.session.get('member_id')

    if not member_id:
        return redirect('membership:login')

    member = Member.objects.get(id=member_id)

    # Process report generation logic here

    return render(request, 'impact_report.html', {'member': member})

#================= End of Impact Report Views =================

def delete_expired_members():
    expired = Member.objects.filter(
        expires_at__lt=timezone.now(),
        registration_fee_status='pending'
    )
    expired.delete()

#================= Logout View =================
def logout(request):
    request.session.flush()
    messages.success(request, f" You have been logged out successfully !.")
    return redirect('membership:login')
#================= End of Logout View =================



def send_registration_confirmation(registration):
    """Tuma confirmation kwa user"""
    # Hii ni template tu - unahitaji API yako ya SMS au email
    message = f"""
    Hello {registration.member.first_name},
    
    You have successfully registered for {registration.event.title}!
    Date: {registration.event.event_date}
    Time: {registration.event.time}
    Location: {registration.event.location}
    Guests: {registration.guests}
    
    Registration ID: #{registration.id}
    
    Thank you for registering!
    """
    # Tuma SMS au email hapa
    print(message)  # Kwa development, anza na hii
    
    
def event_details_json(request, event_id):
    try:
        event = Event.objects.get(id=event_id)
        data = {
            'title': event.title,
            'event_date': event.event_date.strftime('%d %B %Y'),
            'time': event.time.strftime('%I:%M %p'),
            'location': event.location,
            'description': event.description,
            'created_by': event.created_by.first_name if event.created_by else 'Admin',
        }
        return JsonResponse(data)
    except Event.DoesNotExist:
        return JsonResponse({'error': 'Event not found'}, status=404)
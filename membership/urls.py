from django.urls import path
from . import views

app_name='membership'

urlpatterns = [
    
    #================= Authentication and User Management =================
    path('register/', views.register, name='register'),
    path('login/',views.login, name='login'),
    
    path('forgetPassword',views.forgetPassword, name='Forget Password'),
    path('reset-password/',views.resetPassword, name='Reset Password'),
    path('changePassword',views.changePassword, name='change Password'),
    path('deleteAccount',views.deleteAccount, name='delete Account'),
    path('logout',views.logout, name='logout'),
    #================= End of Authentication and User Management =================
    
    #================= Profile Management =================
    path('checkEmail',views.checkEmail, name='check email'),
    path('makeProfile',views.makeprofile, name='Make Profile'),
    path('dashboard',views.dashboard, name='dashboard'),
    path('viewProfile',views.viewProfile, name='view Profile'),
    path('editProfile/',views.editProfile, name='edit Profile'),
    #================= End of Profile Management =================
    
    path('all-announcements/',views.viewAnnouncement, name='all-announcements'),
    path('announcement/<int:announcement_id>/', views.viewAnnouncement, name='view-announcement'),
    
    #================= Donation and Financial Management =================
    path('makePayment',views.paymentPage, name='Make Payment'),
    path('submit-payment/', views.submit_payment, name='submit_payment'),
    path('check-payment-status/', views.check_payment_status, name='check_payment_status'),
    path('save-payment-step/', views.save_payment_step, name='save_payment_step'),
    
    path('donation',views.donation, name='donation'),
    path('makeDonation',views.makeDonation,name="make donation"),
    path('donationHistory',views.donationHistory, name='donation history'),
    path('membershipfeePayment',views.membershipfeePayment, name='membership fee payment'),\
    path('paymentHistory',views.paymentHistory, name='payment history'),
    #================= End of Donation and Financial Management =================
    
    #================= Event Management and Reporting =================
    path('membershipReport',views.membershipReport, name='membership report'),
    path('financialReport',views.financialReport, name='financial report'),
    path('impactReport',views.impactReport, name='impact report'),
    path('event/',views.event, name='event'),
    path('report/',views.report, name='report'),
    path('upcomingEvent',views.upcomingEvent,name="upcoming event"),
    
    path('cancel-registration/', views.cancel_registration, name='cancel_registration'),
    path('edit-registration/', views.edit_registration, name='edit_registration'),
    
    path('download-certificate/<int:registration_id>/', views.download_certificate, name='download_certificate'),
    
    
    path('myEvents',views.myEvents,name="my events"),
    path('pastEvent',views.pastEvent,name="past event"),
    path('eventReport',views.eventReport,name="event report"),
    #================= End of Event Management and Reporting =================
    
    
    
    
    path('check-status/', views.check_status, name='check_status')
]

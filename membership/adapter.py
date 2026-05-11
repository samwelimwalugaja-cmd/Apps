from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from .models import Member

class MySocialAccountAdapter(DefaultSocialAccountAdapter):

    def save_user(self, request, sociallogin, form=None):
        # ❌ HATUTUNGI Django User kabisa kwa members
        email = sociallogin.account.extra_data.get('email')
        first_name = sociallogin.account.extra_data.get('given_name', '')
        last_name = sociallogin.account.extra_data.get('family_name', '')

        # ✔ create MEMBER ONLY
        Member.objects.get_or_create(
            email=email,
            defaults={
                "first_name": first_name,
                "last_name": last_name,
            }
        )

        # ❌ return dummy user (but NOT used for system access)
        return None
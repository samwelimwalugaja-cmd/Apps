from .models import Member

def member_context(request):
    member = None

    member_id = request.session.get('member_id')
    if member_id:
        try:
            member = Member.objects.get(id=member_id)
        except Member.DoesNotExist:
            member = None

    return {
        'member': member
    }
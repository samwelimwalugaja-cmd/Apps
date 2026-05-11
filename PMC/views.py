from django.shortcuts import render

# home
def home(request):
    name='samwel'
    return render(request,'home.html',{'jina':name})

from django.shortcuts import render
from .models import Jersey

def jersey_list(request):

    all_jerseys = Jersey.objects.all()
    
    
    return render(request, 'jerseys/home.html', {'jerseys': all_jerseys})
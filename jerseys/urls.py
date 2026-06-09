from django.urls import path
from . import views

urlpatterns = [
    
    path('', views.jersey_list, name='jersey_list'),
]
from django.urls import path
from . import views

urlpatterns = [
    path('', views.jersey_list, name='jersey_list'),
    
    path('jersey/<int:pk>/', views.jersey_detail, name='jersey_detail'),
    path('add-to-cart/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.cart_detail, name='cart_detail'),
]
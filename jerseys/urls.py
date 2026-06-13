from django.urls import path
from . import views

urlpatterns = [
    # --- PRODUCT & NAVIGATION PATHS ---
    path('', views.jersey_list, name='jersey_list'),
    path('jersey/<int:pk>/', views.jersey_detail, name='jersey_detail'),
    
    # --- CART SYSTEM PATHS (AJAX & PAGES) ---
    path('add-to-cart/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.cart_detail, name='cart_detail'),
    path('update-cart-item/', views.update_cart_item, name='update_cart_item'),
    path('remove-from-cart/', views.remove_from_cart, name='remove_from_cart'),
    
    # --- CHECKOUT & PAYMENT INTEGRATION PATHS ---
    path('checkout/', views.checkout_view, name='checkout'),
    path('payment-gateway/<int:order_id>/', views.payment_gateway_view, name='payment_gateway'),
    path('order-success/<int:order_id>/', views.order_success_view, name='order_success'),
    
    # --- AUTHENTICATION PATHS ---
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
]
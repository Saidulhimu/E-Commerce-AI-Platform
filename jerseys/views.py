from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User
from django.db.models import Q 
from django.http import JsonResponse
from .models import Jersey, Review, Cart, CartItem 
import json 

# --- AUTHENTICATION VIEWS ---

def register_view(request):
    """Handle user registration with custom fields"""
    if request.method == 'POST':
        u_name = request.POST.get('username')
        e_mail = request.POST.get('email')
        pass_word = request.POST.get('password')
        conf_pass = request.POST.get('confirm_password')

        if pass_word != conf_pass:
            messages.error(request, "Passwords do not match!")
            return render(request, 'auth/register.html')

        if User.objects.filter(username=u_name).exists():
            messages.error(request, "Username already exists!")
            return render(request, 'auth/register.html')
            
        user = User.objects.create_user(username=u_name, email=e_mail, password=pass_word)
        user.save()
        
        # Automatically log in the user after successful registration
        login(request, user)
        messages.success(request, "Registration successful! Welcome to KitZone.")
        return redirect('jersey_list')

    return render(request, 'auth/register.html')


def login_view(request):
    """Handle user authentication and session creation"""
    if request.method == 'POST':
        u_name = request.POST.get('username')
        pass_word = request.POST.get('password')
        
        user = authenticate(username=u_name, password=pass_word)
        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back, {u_name}!")
            return redirect('jersey_list')
        else:
            messages.error(request, "Invalid username or password.")
            
    return render(request, 'auth/login.html')


def logout_view(request):
    """Clear user session and log out"""
    logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect('jersey_list')


# --- PRODUCT VIEWS ---

def jersey_list(request):
    """Display jerseys with optional category filtering and search functionality"""
    category_filter = request.GET.get('category')
    search_query = request.GET.get('search') 
    jerseys = Jersey.objects.all()
    
    if category_filter:
        category_filter = category_filter.strip()
        jerseys = jerseys.filter(category__iexact=category_filter)
        
    if search_query:
        search_query = search_query.strip()
        jerseys = jerseys.filter(
            Q(title__icontains=search_query) | 
            Q(team_name__icontains=search_query)
        )
        
    # গ্লোবাল নেভবার কার্ট কাউন্টার সিঙ্ক করার জন্য লজিক
    cart_session = _cart_id(request)
    total_items = 0
    try:
        cart = Cart.objects.get(cart_id=cart_session)
        total_items = sum(item.quantity for item in CartItem.objects.filter(cart=cart))
    except Cart.DoesNotExist:
        pass
        
    context = {
        'jerseys': jerseys,
        'selected_category': category_filter, 
        'search_query': search_query,  
        'total_items': total_items,
    }
    return render(request, 'jerseys/home.html', context)


def jersey_detail(request, pk):
    """Display single jersey details and handle dynamic review submissions"""
    jersey = get_object_or_404(Jersey, pk=pk)
    
    if request.method == 'POST':
        customer_name = request.POST.get('customer_name')
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')
        
        if customer_name and rating and comment:
            Review.objects.create(
                jersey=jersey,
                customer_name=customer_name,
                rating=int(rating),
                comment=comment
            )
            return redirect('jersey_detail', pk=jersey.pk)

    reviews = jersey.reviews.all().order_by('-created_at')
    avg_rating = sum(r.rating for r in reviews) / reviews.count() if reviews.exists() else 0

    # ডিটেইলস পেজেও নেভবার কাউন্টার সিঙ্ক রাখার ব্যবস্থা
    cart_session = _cart_id(request)
    total_items = 0
    try:
        cart = Cart.objects.get(cart_id=cart_session)
        total_items = sum(item.quantity for item in CartItem.objects.filter(cart=cart))
    except Cart.DoesNotExist:
        pass

    context = {
        'jersey': jersey,
        'reviews': reviews,
        'avg_rating': round(avg_rating, 1),
        'total_items': total_items,
    }
    return render(request, 'jerseys/jersey_detail.html', context)


# --- CART SYSTEM HELPERS & VIEWS ---

def _cart_id(request):
    """Get or create a permanent unique session key for guest/user carts"""
    if not request.session.session_key:
        request.session.create()
    
    if 'cart_initialized' not in request.session:
        request.session['cart_initialized'] = True
        request.session.modified = True
        
    return request.session.session_key


def add_to_cart(request):
    """AJAX handler to add items/quantities to the cart database permanently"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            jersey_id = data.get('jersey_id')
            selected_size = data.get('size')
            quantity = int(data.get('quantity', 1))
            
            if selected_size == 'Stock Out' or not selected_size:
                return JsonResponse({'status': 'error', 'message': 'Invalid size or out of stock'}, status=400)
                
            jersey = Jersey.objects.get(id=jersey_id)
            cart, created = Cart.objects.get_or_create(cart_id=_cart_id(request))
            
            cart_item, item_created = CartItem.objects.get_or_create(
                cart=cart,
                jersey=jersey,
                size=selected_size,
                defaults={'quantity': quantity}
            )
            
            if not item_created:
                cart_item.quantity += quantity
                cart_item.save()
                
            total_cart_items = sum(item.quantity for item in CartItem.objects.filter(cart=cart))
            
            return JsonResponse({
                'status': 'success',
                'message': f'{jersey.title} added to cart!',
                'total_items': total_cart_items
            })
            
        except Jersey.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Jersey not found'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
            
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)


def cart_detail(request):
    """Render the shopping cart page with dynamic tiered delivery fees"""
    cart_session = _cart_id(request)
    try:
        cart = Cart.objects.get(cart_id=cart_session)
        cart_items = CartItem.objects.filter(cart=cart)
        
        for item in cart_items:
            item.sub_total = item.jersey.price * item.quantity
            
        total_price = sum(item.jersey.price * item.quantity for item in cart_items)
    except Cart.DoesNotExist:
        cart_items = []
        total_price = 0
        
    total_items = sum(item.quantity for item in cart_items) if cart_items else 0
    
    # ডাইনামিক ডেলিভারি ফি লজিক (প্রতি আইটেমে ৩০ টাকা, সর্বোচ্চ ১৫০ টাকা লক)
    if total_items > 0:
        delivery_fee = min(total_items * 30, 150)
    else:
        delivery_fee = 0
        
    grand_total = total_price + delivery_fee
        
    context = {
        'cart_items': cart_items,
        'total_price': total_price,
        'total_items': total_items,
        'delivery_fee': delivery_fee,
        'grand_total': grand_total,
    }
    return render(request, 'jerseys/cart.html', context)


def update_cart_item(request):
    """AJAX handler to increase/decrease quantity and return computed grand totals"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            item_id = data.get('item_id')
            action = data.get('action')
            
            cart_item = CartItem.objects.get(id=item_id)
            cart = cart_item.cart
            
            if action == 'increase':
                cart_item.quantity += 1
            elif action == 'decrease' and cart_item.quantity > 1:
                cart_item.quantity -= 1
                    
            cart_item.save()
            
            item_subtotal = cart_item.jersey.price * cart_item.quantity
            all_items = CartItem.objects.filter(cart=cart)
            
            total_price = sum(item.jersey.price * item.quantity for item in all_items)
            total_items = sum(item.quantity for item in all_items)
            
            # AJAX রেসপন্সের জন্যও ডাইনামিক ডেলিভারি হিসাব
            delivery_fee = min(total_items * 30, 150) if total_items > 0 else 0
            grand_total = total_price + delivery_fee
            
            return JsonResponse({
                'status': 'success',
                'quantity': cart_item.quantity,
                'item_subtotal': item_subtotal,
                'total_price': total_price,
                'total_items': total_items,
                'delivery_fee': delivery_fee,
                'grand_total': grand_total
            })
        except CartItem.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Item not found'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
            
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)


def remove_from_cart(request):
    """AJAX handler to completely remove an item from the cart database"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            item_id = data.get('item_id')
            
            cart_item = CartItem.objects.get(id=item_id)
            cart = cart_item.cart
            cart_item.delete()
            
            all_items = CartItem.objects.filter(cart=cart)
            total_price = sum(item.jersey.price * item.quantity for item in all_items)
            total_items = sum(item.quantity for item in all_items)
            
            # ডিলিট করার পর নতুন ডেলিভারি ও গ্র্যান্ড টোটাল
            delivery_fee = min(total_items * 30, 150) if total_items > 0 else 0
            grand_total = total_price + delivery_fee
            
            return JsonResponse({
                'status': 'success',
                'total_price': total_price,
                'total_items': total_items,
                'delivery_fee': delivery_fee,
                'grand_total': grand_total,
                'message': 'Item removed from cart'
            })
        except CartItem.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Item not found'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
            
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)
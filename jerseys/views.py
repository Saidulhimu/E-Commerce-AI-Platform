from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User
from django.db.models import Q 
from django.http import JsonResponse
from django.db import transaction
from django.contrib.auth.decorators import login_required  # নতুন ইমপোর্ট
from django.urls import reverse  # ডায়নামিক URL-এর জন্য নতুন ইমপোর্ট
from .models import Jersey, Review, Cart, CartItem, Order, OrderItem, JerseySize
import json 
import uuid

# --- AUTHENTICATION VIEWS ---
def register_view(request):
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
        login(request, user)
        messages.success(request, "Registration successful! Welcome to KitZone.")
        return redirect('jersey_list')
    return render(request, 'auth/register.html')


def login_view(request):
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
    logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect('jersey_list')


# --- PRODUCT VIEWS (UPDATED WITH DYNAMIC SEARCH & FILTERS) ---
def jersey_list(request):
    """ডাইনামিক সার্চ, মাল্টিপল কালেকশন ফিল্টারিং এবং প্রাইজ রেঞ্জ সার্চ কন্ট্রোলার"""
    jerseys = Jersey.objects.all()
    
    # ইনপুট প্যারামিটার রিসিভ করা
    search_query = request.GET.get('search', '').strip()
    category_filter = request.GET.get('category', '').strip()
    version_filter = request.GET.get('version', '').strip()
    min_price = request.GET.get('min_price', '').strip()
    max_price = request.GET.get('max_price', '').strip()

    # ১. কিওয়ার্ড সার্চ (টাইটেল এবং টিম নেম এর ওপর)
    if search_query:
        jerseys = jerseys.filter(
            Q(title__icontains=search_query) | 
            Q(team_name__icontains=search_query)
        )
        
    # ২. ক্যাটাগরি ফিল্টার
    if category_filter:
        jerseys = jerseys.filter(category__iexact=category_filter)
        
    # ৩. জার্সি সংস্করণ ফিল্টার (Player / Fan Edition)
    if version_filter:
        jerseys = jerseys.filter(version__icontains=version_filter)
        
    # ৪. প্রাইজ রেঞ্জ ফিল্টার
    if min_price:
        jerseys = jerseys.filter(price__gte=int(min_price))
    if max_price:
        jerseys = jerseys.filter(price__lte=int(max_price))
        
    # গ্লোবাল নেভবার কার্ট কাউন্টার সিঙ্ক
    cart_session = _cart_id(request)
    total_items = 0
    try:
        cart = Cart.objects.get(cart_id=cart_session)
        total_items = sum(item.quantity for item in CartItem.objects.filter(cart=cart))
    except Cart.DoesNotExist:
        pass
        
    context = {
        'jerseys': jerseys,
        'search_query': search_query,
        'selected_category': category_filter,
        'selected_version': version_filter,
        'min_price': min_price,
        'max_price': max_price,
        'total_items': total_items,
    }
    return render(request, 'jerseys/home.html', context)


def jersey_detail(request, pk):
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
    if not request.session.session_key:
        request.session.create()
    if 'cart_initialized' not in request.session:
        request.session['cart_initialized'] = True
        request.session.modified = True
    return request.session.session_key


def add_to_cart(request):
    if request.method == 'POST':
        # ১. ইউজার লগইন করা না থাকলে AJAX ফ্রন্টএন্ডে রিডাইরেক্ট রেসপন্স পাঠানো
        if not request.user.is_authenticated:
            return JsonResponse({
                'status': 'not_logged_in',
                'message': 'Please log in to add items to your cart.',
                'redirect_url': reverse('login')  # লগইন পেজের ডাইনামিক URL
            }, status=401)

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


@login_required  # লগইন ছাড়া সরাসরি কার্ট পেজ দেখতে পারবে না
def cart_detail(request):
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
    delivery_fee = min(total_items * 30, 150) if total_items > 0 else 0
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
    if request.method == 'POST':
        if not request.user.is_authenticated:
            return JsonResponse({'status': 'error', 'message': 'Authentication required'}, status=401)

        try:
            data = json.loads(request.body)
            item_id = data.get('item_id')
            action = data.get('action')
            
            # ইউজার কার্ট ভেরিফিকেশন আরও সিকিউর করা হয়েছে
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
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)


def remove_from_cart(request):
    if request.method == 'POST':
        if not request.user.is_authenticated:
            return JsonResponse({'status': 'error', 'message': 'Authentication required'}, status=401)

        try:
            data = json.loads(request.body)
            item_id = data.get('item_id')
            cart_item = CartItem.objects.get(id=item_id)
            cart = cart_item.cart
            cart_item.delete()
            
            all_items = CartItem.objects.filter(cart=cart)
            total_price = sum(item.jersey.price * item.quantity for item in all_items)
            total_items = sum(item.quantity for item in all_items)
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
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)


# --- CHECKOUT, ATOMIC STOCK CONTROL & PAYMENT GATEWAY INTEGRATION ---
@login_required  # লগইন ছাড়া চেকাউট পেজে আসা সম্পূর্ণ লকড
def checkout_view(request):
    cart_session = _cart_id(request)
    try:
        cart = Cart.objects.get(cart_id=cart_session)
        cart_items = CartItem.objects.filter(cart=cart, is_active=True)
    except Cart.DoesNotExist:
        messages.error(request, "Your cart is empty!")
        return redirect('jersey_list')

    if not cart_items.exists():
        messages.error(request, "Your cart is empty!")
        return redirect('jersey_list')

    total_price = sum(item.jersey.price * item.quantity for item in cart_items)
    total_items = sum(item.quantity for item in cart_items)
    delivery_fee = min(total_items * 30, 150) if total_items > 0 else 0
    grand_total = total_price + delivery_fee

    if request.method == 'POST':
        # যেহেতু ইউজার অলরেডি লগইনড, তাই সরাসরি তার রিয়েল প্রোফাইল নাম সেট করা হচ্ছে
        full_name = request.user.get_full_name() if request.user.get_full_name() else request.user.username

        email = request.POST.get('email')
        phone_number = request.POST.get('phone_number')
        address = request.POST.get('address')
        city = request.POST.get('city')
        payment_method = request.POST.get('payment_method')

        try:
            with transaction.atomic():
                # ১. রিয়েল-টাইম অ্যাটমিক স্টক চেকিং
                for item in cart_items:
                    jersey_size = JerseySize.objects.select_for_update().get(jersey=item.jersey, size=item.size)
                    if jersey_size.stock < item.quantity:
                        raise ValueError(f"Not enough stock for {item.jersey.title} ({item.size}). Available: {jersey_size.stock}")

                # ২. অর্ডার রেকর্ড ইনিশিয়ালাইজেশন
                order = Order.objects.create(
                    user=request.user,  # গেস্ট কন্ডিশন রিমুভড
                    full_name=full_name,
                    email=email,
                    phone_number=phone_number,
                    address=address,
                    city=city,
                    postal_code="N/A",  
                    total_price=total_price,
                    delivery_fee=delivery_fee,
                    grand_total=grand_total,
                    payment_method=payment_method,
                    status='Pending'
                )

                # ৩. অর্ডার আইটেম প্রিপারেশন এবং ডাইনামিক স্টক হ্রাস (Reduction)
                for item in cart_items:
                    OrderItem.objects.create(
                        order=order, jersey=item.jersey, size=item.size,
                        quantity=item.quantity, price=item.jersey.price
                    )
                    jersey_size = JerseySize.objects.get(jersey=item.jersey, size=item.size)
                    jersey_size.stock -= item.quantity
                    jersey_size.save()

                # ৪. পেমেন্ট গেটওয়ে রাউটিং লজিক
                if payment_method == 'Bkash':
                    return redirect('payment_gateway', order_id=order.id)
                else:
                    cart_items.delete()
                    messages.success(request, "Order placed successfully with Cash on Delivery!")
                    return redirect('order_success', order_id=order.id)

        except ValueError as e:
            messages.error(request, str(e))
            return redirect('checkout')

    context = {
        'cart_items': cart_items,
        'total_price': total_price,
        'delivery_fee': delivery_fee,
        'grand_total': grand_total,
        'total_items': total_items,
    }
    return render(request, 'jerseys/checkout.html', context)


def payment_gateway_view(request, order_id):
    """বিকাশ/অনলাইন পেমেন্ট গেটওয়ের স্যান্ডবক্স সিমুলেশন ভিউ"""
    order = get_object_or_404(Order, id=order_id)
    if request.method == 'POST':
        order.status = 'Paid'
        order.transaction_id = "TRX-" + uuid.uuid4().hex[:10].upper()
        order.save()

        cart_session = _cart_id(request)
        CartItem.objects.filter(cart__cart_id=cart_session).delete()

        messages.success(request, f"Payment successful via bKash! TxnID: {order.transaction_id}")
        return redirect('order_success', order_id=order.id)
        
    return render(request, 'jerseys/payment_sandbox.html', {'order': order})


def order_success_view(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'jerseys/order_success.html', {'order': order})
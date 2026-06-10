from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q  
# 🟢 নিচে Cart এবং CartItem ইমপোর্ট করা হলো
from .models import Jersey, Review, Cart, CartItem 
from django.http import JsonResponse
import json # 🟢 json টা ফাইলের ওপরে নিয়ে আসলাম (স্ট্যান্ডার্ড প্র্যাকটিস)

# 1. Product list view with Category Filter & Search Engine
def jersey_list(request):
    category_filter = request.GET.get('category')
    search_query = request.GET.get('search') 
    
    jerseys = Jersey.objects.all()
    
    # Category filtering logic
    if category_filter:
        jerseys = jerseys.filter(category=category_filter)
        
    # Search engine logic 
    if search_query:
        jerseys = jerseys.filter(
            Q(title__icontains=search_query) | 
            Q(team_name__icontains=search_query)
        )
        
    context = {
        'jerseys': jerseys,
        'selected_category': category_filter, 
        'search_query': search_query,  
    }
    return render(request, 'jerseys/home.html', context)


# 2. Product detail view with dynamic review system
def jersey_detail(request, pk):
    # Fetch the specific jersey by id (primary key)
    jersey = get_object_or_404(Jersey, pk=pk)
    
    # Handle customer review submission via POST request
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

    # Get all reviews for this specific jersey
    reviews = jersey.reviews.all().order_by('-created_at')
    
    # Calculate average rating dynamically
    avg_rating = 0
    if reviews.exists():
        avg_rating = sum(r.rating for r in reviews) / reviews.count()

    context = {
        'jersey': jersey,
        'reviews': reviews,
        'avg_rating': round(avg_rating, 1),
    }
    return render(request, 'jerseys/jersey_detail.html', context)


# 3. Session helper function for Cart
def _cart_id(request):
    cart = request.session.session_key
    if not cart:
        request.session.create()
        cart = request.session.session_key
    return cart


# 4. Add to Cart Logic (AJAX Request)
def add_to_cart(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        jersey_id = data.get('jersey_id')
        selected_size = data.get('size')
        
        if selected_size == 'Stock Out' or not selected_size:
            return JsonResponse({'status': 'error', 'message': 'Invalid size or out of stock'}, status=400)
            
        try:
            jersey = Jersey.objects.get(id=jersey_id)
            
            # 🟢 Get or Create Cart
            cart, created = Cart.objects.get_or_create(cart_id=_cart_id(request))
            
            # 🟢 Get or Create Cart Item
            cart_item, item_created = CartItem.objects.get_or_create(
                cart=cart,
                jersey=jersey,
                size=selected_size
            )
            
            if not item_created:
                cart_item.quantity += 1
                cart_item.save()
                
            # Calculate total items in cart
            total_cart_items = sum(item.quantity for item in cart.items.all())
            
            return JsonResponse({
                'status': 'success',
                'message': f'{jersey.title} added to cart!',
                'total_items': total_cart_items
            })
            
        except Jersey.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Jersey not found'}, status=404)
            
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)


# Cart Details View
def cart_detail(request):
    cart_session = _cart_id(request)
    try:
        # ইউজারের কার্ট এবং কার্টের ভেতরের সব আইটেম খুঁজে বের করা
        cart = Cart.objects.get(cart_id=cart_session)
        cart_items = CartItem.objects.filter(cart=cart)
        
        # সব আইটেমের মোট দাম হিসাব করা
        total_price = sum(item.jersey.price * item.quantity for item in cart_items)
    except Cart.DoesNotExist:
        # যদি কার্টে কিছু না থাকে
        cart_items = []
        total_price = 0
        
    context = {
        'cart_items': cart_items,
        'total_price': total_price,
    }
    return render(request, 'jerseys/cart.html', context)
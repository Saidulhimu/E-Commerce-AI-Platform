from .models import Cart, CartItem
from .views import _cart_id

def global_cart_counter(request):
    """সব পেজের নেভবারে কার্টের সঠিক সংখ্যা দেখানোর প্রসেসর"""
    cart_session = _cart_id(request)
    total_items = 0
    try:
        cart = Cart.objects.get(cart_id=cart_session)
        total_items = sum(item.quantity for item in CartItem.objects.filter(cart=cart))
    except Cart.DoesNotExist:
        pass
        
    return {'total_items': total_items}
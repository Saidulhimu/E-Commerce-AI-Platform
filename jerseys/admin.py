from django.contrib import admin
from .models import Jersey, JerseySize, Review, Cart, CartItem  # 🟢 Cart এবং CartItem ইমপোর্ট করলাম


class JerseySizeInline(admin.TabularInline):
    model = JerseySize
    extra = 3 


@admin.register(Jersey)
class JerseyAdmin(admin.ModelAdmin):
    list_display = ('title', 'team_name', 'category', 'price', 'is_trending', 'total_stock')
    list_filter = ('category', 'is_trending', 'team_name')
    search_fields = ('title', 'team_name')
    inlines = [JerseySizeInline]


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ('jersey', 'size', 'quantity', 'total_price')  # অ্যাডমিন থেকে যেন এডিট করে নষ্ট না হয়


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('cart_id', 'created_at')
    search_fields = ('cart_id',)
    inlines = [CartItemInline]


admin.site.register(JerseySize)
admin.site.register(Review)
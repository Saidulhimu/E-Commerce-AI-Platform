from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class Jersey(models.Model):
    # Define category choices for the jersey
    CATEGORY_CHOICES = [
        ('home', 'Home Kit'),
        ('away', 'Away Kit'),
        ('training', 'Training Kit'),
    ]

    title = models.CharField(max_length=200)
    team_name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.IntegerField()
    image_url = models.URLField(max_length=500, blank=True, null=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='home')
    version = models.CharField(max_length=50, default='Player Edition')
    is_trending = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.team_name} - {self.title} ({self.get_category_display()})"

    
    @property
    def total_stock(self):
        return sum(item.stock for item in self.sizes.all())


class JerseySize(models.Model):
    
    jersey = models.ForeignKey(Jersey, on_delete=models.CASCADE, related_name='sizes')
    size = models.CharField(max_length=10, choices=[('M', 'M'), ('L', 'L'), ('XL', 'XL'), ('XXL', 'XXL')])
    stock = models.IntegerField(default=0)

    class Meta:
        # not double entry for same jersey and size
        unique_together = ('jersey', 'size')

    def __str__(self):
        return f"{self.jersey.title} - Size: {self.size} (Stock: {self.stock})"


class Review(models.Model):
    jersey = models.ForeignKey(Jersey, on_delete=models.CASCADE, related_name='reviews')
    customer_name = models.CharField(max_length=100)
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review by {self.customer_name} - {self.rating} ⭐"
    

class Cart(models.Model):
   
    cart_id = models.CharField(max_length=250, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cart {self.cart_id}"

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    jersey = models.ForeignKey(Jersey, on_delete=models.CASCADE)
    size = models.CharField(max_length=10)
    quantity = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    def total_price(self):
        return self.jersey.price * self.quantity

    def __str__(self):
        return f"{self.jersey.title} ({self.size}) x {self.quantity}"
    

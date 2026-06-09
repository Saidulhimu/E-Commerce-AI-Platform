from django.db import models

class Jersey(models.Model):
    # Basic Info
    title = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField()
    
    # Specific Info
    team_name = models.CharField(max_length=100)
    jersey_type = models.CharField(max_length=50) # Home, Away, Third Kit
    version = models.CharField(max_length=50)     # Fan Edition, Player Edition
    
    # size ans custom option
    size = models.CharField(max_length=10)        # S, M, L, XL, XXL
    has_custom_name = models.BooleanField(default=False) # নাম-নাম্বার প্রিন্ট করার সুবিধা
  
  
    image_url = models.URLField(max_length=500, blank=True, null=True)  
    # Tracking and time
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.team_name} - {self.title}"
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Category(models.Model):
    name = models.CharField(max_length=100)
    def __str__(self):
        return self.name

class Product(models.Model):
    # Asegúrate de que esta línea esté idéntica:
    #category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products', null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    seller = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    brand = models.CharField(max_length=100)
    part_number = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=12, decimal_places=2)
    stock = models.IntegerField(default=1)
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):

        return f"{self.brand} - {self.title}"


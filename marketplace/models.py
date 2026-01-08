from django.db import models
from django.contrib.auth.models import User
from cloudinary.models import CloudinaryField

class Category(models.Model):
    name = models.CharField(max_length=100)
    
    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

class IndustrialProduct(models.Model):
    title = models.CharField(max_length=200)
    brand = models.CharField(max_length=100)
    part_number = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=12, decimal_places=2)
    stock = models.IntegerField(default=1)
    # Usamos Cloudinary para persistencia en Render
    image = CloudinaryField('image', null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    seller = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True) # auto_now llena el campo solo

    def __str__(self):
        return f"{self.title} - {self.brand}"

class Sale(models.Model):
    product = models.ForeignKey(IndustrialProduct, on_delete=models.SET_NULL, null=True, verbose_name="Producto")
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Comprador")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Monto Pagado")
    mp_payment_id = models.CharField(max_digits=100, verbose_name="ID Pago Mercado Pago")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Venta")

    def __str__(self):
        return f"Venta {self.id} - {self.product.title if self.product else 'Producto Eliminado'}"

    class Meta:
        verbose_name = "Venta"
        verbose_name = "Ventas"
    

 




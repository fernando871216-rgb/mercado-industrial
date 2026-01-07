from django.db import models
from django.conf import settings
from cloudinary.models import CloudinaryField

class IndustrialProduct(models.Model):

# Modelo de Categorías
class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nombre de la Categoría")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Categories"

# Modelo de Producto con el nuevo nombre para resetear la base de datos
class IndustrialProduct(models.Model):
    title = models.CharField(max_length=200, verbose_name="Título del Producto")
    brand = models.CharField(max_length=100, verbose_name="Marca")
    part_number = models.CharField(max_length=100, verbose_name="Número de Parte")
    description = models.TextField(verbose_name="Descripción")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Precio")
    stock = models.IntegerField(default=1, verbose_name="Existencias")
    image = models.ImageField(upload_to='products/', null=True, blank=True, verbose_name="Imagen del Producto")
    
    # Relaciones
    category = models.ForeignKey(
        Category, 
        on_delete=models.CASCADE, 
        related_name='products',
        verbose_name="Categoría"
    )
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        verbose_name="Vendedor"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    image = CloudinaryField('image', null=True, blank=True)

    def __str__(self):
        return f"{self.title} - {self.brand}"
    

 

from django.contrib import admin
from .models import Category, IndustrialProduct
from .models import Sale

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'buyer', 'amount', 'created_at', 'mp_payment_id')
    list_filter = ('created_at',)
    search_fields = ('mp_payment_id', 'buyer__username', 'product__title')

# Registro de Categorías
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)

# Registro del nuevo modelo IndustrialProduct
@admin.register(IndustrialProduct)
class IndustrialProductAdmin(admin.ModelAdmin):
    # Mostramos los campos principales en la lista del administrador
    list_display = ('title', 'brand', 'price', 'stock', 'category','seller')
    # Permitimos filtrar por categoría y marca
    list_filter = ('category', 'brand')
    # Añadimos un buscador por título y número de parte
    search_fields = ('title', 'brand', 'description')



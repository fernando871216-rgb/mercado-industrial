from django.contrib import admin
from .models import Category, Profile, IndustrialProduct, Sale

# 1. Registro de Ventas
@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'buyer', 'seller', 'price', 'created_at')
    list_filter = ('created_at', 'seller')
    search_fields = ('product__title', 'buyer__username', 'seller__username')

# 2. Registro de Productos Industriales (Configuración Unificada)
@admin.register(IndustrialProduct)
class IndustrialProductAdmin(admin.ModelAdmin):
    # Mostramos los campos clave, incluyendo el Número de Parte
    list_display = ('title', 'brand', 'part_number', 'price', 'stock', 'category', 'seller')
    # Filtros laterales útiles
    list_filter = ('category', 'brand', 'created_at')
    # Buscador potente para el administrador
    search_fields = ('title', 'brand', 'part_number', 'description')

# 3. Registro de Categorías
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

# 4. Registro de Perfiles de Usuario
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number')
    search_fields = ('user__username', 'phone_number')

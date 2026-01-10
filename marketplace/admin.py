from django.contrib import admin
from .models import Category, IndustrialProduct, Profile, Sale

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')

@admin.register(IndustrialProduct)
class IndustrialProductAdmin(admin.ModelAdmin):
    # 'user' es el vendedor en tu modelo
    list_display = ('id', 'title', 'brand', 'price', 'stock', 'category', 'user')
    list_filter = ('category', 'brand')
    search_fields = ('title', 'brand', 'part_number')

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'banco', 'clabe', 'beneficiario')
    search_fields = ('user__username', 'clabe', 'phone')

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    # HE FUSIONADO LAS COLUMNAS AQUÍ:
    # Ahora verás quién compró, si ya RECIBIÓ y si ya le PAGASTE al vendedor
    list_display = (
        'id', 
        'product', 
        'buyer', 
        'price', 
        'status', 
        'recibido_por_comprador', 
        'pagado_a_vendedor', 
        'created_at'
    )
    
    # Filtros laterales para encontrar rápido lo pendiente
    list_filter = ('status', 'recibido_por_comprador', 'pagado_a_vendedor', 'created_at')
    
    # Buscador por nombre de producto o comprador
    search_fields = ('product__title', 'buyer__username')

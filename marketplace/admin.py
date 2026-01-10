from django.contrib import admin
from .models import Category, IndustrialProduct, Profile, Sale

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')

@admin.register(IndustrialProduct)
class IndustrialProductAdmin(admin.ModelAdmin):
    # Cambiamos 'seller' por 'user', que es como se llama en tu modelo
    list_display = ('id', 'title', 'brand', 'price', 'stock', 'category', 'user')
    list_filter = ('category', 'brand')
    search_fields = ('title', 'brand', 'part_number')

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    # Cambiamos 'phone_number' por 'phone', que es como se llama en tu modelo
    list_display = ('user', 'phone', 'banco', 'clabe', 'beneficiario')
    search_fields = ('user__username', 'clabe', 'phone')

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    # En Sale no existe 'seller' directamente, se accede a través del producto
    list_display = ('id', 'product', 'buyer', 'price', 'status', 'pagado_a_vendedor', 'created_at')
    list_filter = ('status', 'pagado_a_vendedor', 'created_at')
    search_fields = ('product__title', 'buyer__username')


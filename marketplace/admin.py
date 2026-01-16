from django.contrib import admin
from .models import Category, IndustrialProduct, Profile, Sale

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')

@admin.register(IndustrialProduct)
class IndustrialProductAdmin(admin.ModelAdmin):
    # Columnas que verás en la lista principal
    list_display = ('title', 'price', 'brand', 'peso', 'cp_origen', 'stock')
    
    # Filtros laterales para encontrar productos rápido
    list_filter = ('brand', 'category')
    
    # Buscador por nombre y marca
    search_fields = ('title', 'brand', 'description')

    # Organización de los campos dentro del formulario de edición
    fieldsets = (
        ('Información General', {
            'fields': ('title', 'description', 'price', 'brand', 'category', 'image', 'stock')
        }),
        ('Logística y Envío (SoloEnvíos)', {
            'fields': (
                'cp_origen', 
                ('largo', 'ancho', 'alto'), 
                'peso'
            ),
            'description': 'Configura las dimensiones reales del paquete para que el cotizador funcione correctamente.',
        }),
    )

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'banco', 'clabe', 'beneficiario', 'get_address')
    search_fields = ('user__username', 'clabe', 'phone', 'address')
    def get_address(self, obj):
        return obj.address
    
    # Nombre de la columna en el panel
    get_address.short_description = 'Dirección Completa'
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
    readonly_fields = ('created_at',)
    search_fields = ('product__title', 'buyer__username')




from django.contrib import admin
from .models import Category, IndustrialProduct, Profile, Sale
from django.utils.html import format_html

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')

@admin.register(IndustrialProduct)
class IndustrialProductAdmin(admin.ModelAdmin):
    # 1. Agregamos 'mostrar_imagen' y 'tiene_pdf' a la lista
    list_display = ('mostrar_imagen', 'title', 'price', 'brand', 'peso', 'cp_origen', 'stock', 'user', 'tiene_pdf')
    
    # 2. Filtros laterales corregidos
    list_filter = ('brand', 'category', 'user', 'created_at')
    
    # 3. Buscador (agregué el usuario por si quieres buscar productos de alguien específico)
    search_fields = ('title', 'brand', 'description', 'user__username')

    # Organización de los campos dentro del formulario de edición
    fieldsets = (
        ('Información General', {
            'fields': ('title', 'description', 'price', 'brand', 'category', 'image', 'stock', 'user', 'ficha_tecnica')
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

    # --- FUNCIONES EXTRA ---

    # Función para ver la miniatura de la foto en la lista
    def mostrar_imagen(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width: 45px; height: 45px; border-radius: 8px; object-fit: cover;" />', obj.image.url)
        return "No foto"
    mostrar_imagen.short_description = 'Imagen'

    # Función para ver si tiene el PDF de la ficha técnica
    def tiene_pdf(self, obj):
        if obj.ficha_tecnica:
            return format_html('<span style="color: #27ae60; font-weight: bold;">✔ PDF</span>')
        return format_html('<span style="color: #e74c3c;">✘</span>')
    tiene_pdf.short_description = 'Ficha'

    # Para que si creas un producto tú desde el admin, sepa quién eres
    def save_model(self, request, obj, form, change):
        if not obj.user:
            obj.user = request.user
        super().save_model(request, obj, form, change)

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'banco', 'clabe', 'beneficiario', 'get_address')
    search_fields = ('user__username', 'clabe', 'phone', 'address', 'beneficiario', 'banco')
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








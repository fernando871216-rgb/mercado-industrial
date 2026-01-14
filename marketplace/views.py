import requests
import urllib3
import json
import mercadopago
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages

# Modelos y Formularios
from .models import IndustrialProduct, Category, Sale
from .forms import ProductForm 

# Configuración de Seguridad y SDK
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
SDK = mercadopago.SDK("APP_USR-2885162849289081-010612-228b3049d19e3b756b95f319ee9d0011-40588817")

# ==========================================
# 1. PÁGINAS PRINCIPALES (Sincronizadas con URLs)
# ==========================================

def home(request):
    products = IndustrialProduct.objects.all().order_by('-created_at')
    categories = Category.objects.all()
    return render(request, 'marketplace/home.html', {'products': products, 'categories': categories})

def detalle_producto(request, product_id):
    product = get_object_or_404(IndustrialProduct, id=product_id)
    # Generar preferencia de Mercado Pago
    preference_data = {
        "items": [{
            "id": str(product.id),
            "title": product.title,
            "quantity": 1,
            "unit_price": float(product.price),
            "currency_id": "MXN"
        }],
        "back_urls": {
            "success": request.build_absolute_uri('/pago-exitoso/'),
            "failure": request.build_absolute_uri('/pago-fallido/')
        },
        "auto_return": "approved",
        "external_reference": str(product.id),
    }
    preference_result = SDK.preference().create(preference_data)
    preference_id = preference_result["response"]["id"]
    
    return render(request, 'marketplace/product_detail.html', {
        'product': product, 
        'preference_id': preference_id
    })

def category_detail(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    products = IndustrialProduct.objects.filter(category=category)
    return render(request, 'marketplace/home.html', {'products': products, 'category': category})

# ==========================================
# 2. CUENTA Y PERFIL
# ==========================================

def registro(request):
    return render(request, 'marketplace/registro.html')

@login_required
def editar_perfil(request):
    return render(request, 'marketplace/editar_perfil.html')

# ==========================================
# 3. INVENTARIO DEL VENDEDOR
# ==========================================

@login_required
def mi_inventario(request):
    products = IndustrialProduct.objects.filter(user=request.user)
    return render(request, 'marketplace/mi_inventario.html', {'products': products})

@login_required
def subir_producto(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.user = request.user
            product.save()
            return redirect('mi_inventario')
    else:
        form = ProductForm()
    return render(request, 'marketplace/subir_producto.html', {'form': form})

@login_required
def editar_producto(request, pk):
    producto = get_object_or_404(IndustrialProduct, pk=pk, user=request.user)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=producto)
        if form.is_valid():
            form.save()
            return redirect('mi_inventario')
    else:
        form = ProductForm(instance=producto)
    return render(request, 'marketplace/editar_producto.html', {'form': form, 'producto': producto})

@login_required
def borrar_producto(request, pk):
    producto = get_object_or_404(IndustrialProduct, pk=pk, user=request.user)
    if request.method == 'POST':
        producto.delete()
    return redirect('mi_inventario')

# ==========================================
# 4. COMPRAS Y VENTAS
# ==========================================

@login_required
def mis_compras(request):
    compras = Sale.objects.filter(buyer=request.user).order_by('-created_at')
    return render(request, 'marketplace/mis_compras.html', {'compras': compras})

@login_required
def mis_ventas(request):
    ventas = Sale.objects.filter(product__user=request.user).order_by('-created_at')
    return render(request, 'marketplace/mis_ventas.html', {'ventas': ventas})

@login_required
def cambiar_estado_venta(request, venta_id):
    venta = get_object_or_404(Sale, id=venta_id, product__user=request.user)
    if venta.status == 'pendiente':
        venta.status = 'completado'
        venta.save()
    return redirect('mis_ventas')

@login_required
def cancelar_venta(request, venta_id):
    venta = get_object_or_404(Sale, id=venta_id)
    if venta.product.user == request.user or request.user.is_staff:
        producto = venta.product
        producto.stock += 1
        producto.save()
        venta.status = 'cancelado'
        venta.save()
        messages.success(request, "Venta cancelada.")
    return redirect('mis_ventas')

@login_required
def confirmar_recepcion(request, venta_id):
    if request.method == 'POST':
        venta = get_object_or_404(Sale, id=venta_id)
        if venta.buyer == request.user:
            venta.recibido_por_comprador = True
            venta.status = 'entregado'
            venta.save()
            messages.success(request, "¡Recepción confirmada!")
    return redirect('mis_compras')

@login_required
def actualizar_guia(request, venta_id):
    if request.method == 'POST':
        venta = get_object_or_404(Sale, id=venta_id)
        if venta.product.user == request.user:
            venta.shipping_company = request.POST.get('shipping_company

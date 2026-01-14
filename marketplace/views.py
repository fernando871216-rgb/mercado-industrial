from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import IndustrialProduct, Category, Sale, Profile
from .forms import RegistroForm, ProductForm, ProfileForm # Asegúrate de tener estos formularios en forms.py
import requests
import mercadopago
from decimal import Decimal

# --- CONFIGURACIÓN ---
SDK = mercadopago.SDK("TU_ACCESS_TOKEN_PRODUCCION") # Reemplaza con tu token real

# --- VISTAS PRINCIPALES ---
def home(request):
    products = IndustrialProduct.objects.all().order_by('-created_at')
    categories = Category.objects.all()
    return render(request, 'marketplace/home.html', {'products': products, 'categories': categories})

def detalle_producto(request, product_id):
    product = get_object_or_404(IndustrialProduct, id=product_id)
    # Preferencia inicial (sin envío)
    preference_data = {
        "items": [{
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

# --- SOLOENVÍOS ---
def cotizar_soloenvios(request):
    cp_origen = request.GET.get('cp_origen')
    cp_destino = request.GET.get('cp_destino')
    peso = request.GET.get('peso', 1)
    largo = request.GET.get('largo', 10)
    ancho = request.GET.get('ancho', 10)
    alto = request.GET.get('alto', 10)

    url = "https://soloenvios.com/api/v1/rates"
    headers = {
        "Authorization": "Bearer TU_TOKEN_SOLOENVIO", # Tu token de SoloEnvíos
        "Content-Type": "application/json"
    }
    
    payload = {
        "origin_zip_code": str(cp_origen),
        "destination_zip_code": str(cp_destino),
        "package": {
            "weight": float(peso),
            "width": int(ancho),
            "height": int(alto),
            "length": int(largo)
        }
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        data = response.json()
        tarifas_finales = []
        
        for t in data:
            precio_base = float(t['price'])
            # Tu comisión del 8%
            precio_con_comision = round(precio_base * 1.08, 2)
            tarifas_finales.append({
                'paqueteria': t['service_name'],
                'precio_final': precio_con_comision,
                'tiempo': t['delivery_days']
            })
        return JsonResponse({'tarifas': tarifas_finales})
    except Exception as e:
        return JsonResponse({'error': str(e), 'tarifas': []})

def actualizar_preferencia_pago(request):
    product_id = request.GET.get('id')
    costo_envio = float(request.GET.get('envio', 0))
    product = get_object_or_404(IndustrialProduct, id=product_id)
    
    total = float(product.price) + costo_envio
    
    preference_data = {
        "items": [{
            "title": f"{product.title} + Envío",
            "quantity": 1,
            "unit_price": total,
            "currency_id": "MXN"
        }],
        "back_urls": {
            "success": request.build_absolute_uri('/pago-exitoso/'),
            "failure": request.build_absolute_uri('/pago-fallido/')
        }
    }
    res = SDK.preference().create(preference_data)
    return JsonResponse({'preference_id': res["response"]["id"], 'total_nuevo': total})

# --- GESTIÓN DE USUARIOS Y PRODUCTOS (Faltantes para el Build) ---
def registro(request):
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = RegistroForm()
    return render(request, 'marketplace/registro.html', {'form': form})

@login_required
def editar_perfil(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('home')
    else:
        form = ProfileForm(instance=profile)
    return render(request, 'marketplace/editar_perfil.html', {'form': form})

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

# (Aquí agregarías editar_producto, borrar_producto, mis_ventas, etc. siguiendo el mismo patrón)

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
    return render(request, 'marketplace/editar_producto.html', {'form': form})

@login_required
def borrar_producto(request, pk):
    producto = get_object_or_404(IndustrialProduct, pk=pk, user=request.user)
    if request.method == 'POST':
        producto.delete()
    return redirect('mi_inventario')

@login_required
def mis_compras(request):
    compras = Sale.objects.filter(buyer=request.user).order_by('-created_at')
    return render(request, 'marketplace/mis_compras.html', {'compras': compras})

@login_required
def mis_ventas(request):
    ventas = Sale.objects.filter(product__user=request.user).order_by('-created_at')
    return render(request, 'marketplace/mis_ventas.html', {'ventas': ventas})

def pago_exitoso(request):
    return render(request, 'marketplace/pago_exitoso.html')

def pago_fallido(request):
    return render(request, 'marketplace/pago_fallido.html')

@login_required
def actualizar_guia(request, venta_id):
    venta = get_object_or_404(Sale, id=venta_id, product__user=request.user)
    if request.method == 'POST':
        venta.tracking_number = request.POST.get('tracking_number')
        venta.shipping_company = request.POST.get('shipping_company')
        venta.status = 'enviado'
        venta.save()
    return redirect('mis_ventas')

@login_required
def cancelar_venta(request, venta_id):
    venta = get_object_or_404(Sale, id=venta_id, product__user=request.user)
    venta.status = 'cancelado'
    venta.save()
    return redirect('mis_ventas')

# Estas son funciones adicionales para tu panel de control
@login_required
def panel_administrador(request):
    if not request.user.is_staff:
        return redirect('home')
    ventas = Sale.objects.all().order_by('-created_at')
    return render(request, 'marketplace/panel_admin.html', {'ventas': ventas})

@login_required
def marcar_como_pagado(request, venta_id):
    if not request.user.is_staff:
        return redirect('home')
    venta = get_object_or_404(Sale, id=venta_id)
    venta.pagado_a_vendedor = True
    venta.save()
    return redirect('panel_administrador')

@login_required
def confirmar_recepcion(request, venta_id):
    venta = get_object_or_404(Sale, id=venta_id, buyer=request.user)
    venta.recibido_por_comprador = True
    venta.status = 'entregado'
    venta.save()
    return redirect('mis_compras')

def mercadopago_webhook(request):
    # Por ahora solo para evitar error 404, retorna ok
    return JsonResponse({'status': 'ok'}, status=200)

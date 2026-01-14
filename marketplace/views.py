import os
import mercadopago
import json
import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.db.models import Q, Sum
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
from django.contrib import messages

from .models import IndustrialProduct, Category, Sale, Profile
from .forms import RegistroForm, ProductoForm, UserUpdateForm, ProfileUpdateForm

# --- 1. ACTUALIZAR PREFERENCIA (MERCADO PAGO) ---
def actualizar_preferencia_pago(request):
    """ Esta función refresca el botón de pago cuando se elige un flete """
    if request.method == 'GET':
        producto_id = request.GET.get('id')
        precio_envio = float(request.GET.get('envio', 0))
        
        producto = get_object_or_404(IndustrialProduct, id=producto_id)
        total = float(producto.price) + precio_envio

        # Usa tu token real aquí también
        sdk = mercadopago.SDK("APP_USR-2885162849289081-010612-228b3049d19e3b756b95f319ee9d0011-40588817")

        preference_data = {
            "items": [
                {
                    "title": f"{producto.title} + Envío",
                    "quantity": 1,
                    "unit_price": total,
                    "currency_id": "MXN",
                }
            ],
            "external_reference": str(producto.id),
            "back_urls": {
                "success": request.build_absolute_uri(reverse('pago_exitoso')),
                "failure": request.build_absolute_uri(reverse('pago_fallido')),
            },
            "auto_return": "approved",
        }

        preference_response = sdk.preference().create(preference_data)
        nuevo_id = preference_response["response"]["id"]

        return JsonResponse({'preference_id': nuevo_id, 'total_nuevo': total})

# --- 2. COTIZAR (SOLO ENVÍOS) ---
def cotizar_soloenvios(request):
    """ Conecta con SoloEnvíos y añade 8% de comisión """
    cp_origen = request.GET.get('cp_origen')
    cp_destino = request.GET.get('cp_destino')
    peso = request.GET.get('peso', 1)
    largo = request.GET.get('largo', 10)
    ancho = request.GET.get('ancho', 10)
    alto = request.GET.get('alto', 10)

    # URL y Token de SoloEnvíos
    url = "https://soloenvios.com/api/v1/rates" 
    token = "-mUChsOjBGG5dJMchXbLLQBdPxQJldm4wx3kLPoWWDs" # Tu Token
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "origin_zip_code": cp_origen,
        "destination_zip_code": cp_destino,
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
        # SoloEnvíos devuelve los resultados en la llave 'rates'
        for rate in data.get('rates', []):
            precio_original = float(rate['total_price'])
            # APLICAMOS TU GANANCIA DEL 8%
            precio_con_comision = round(precio_original * 1.08, 2)
            
            tarifas_finales.append({
                'paqueteria': rate['provider'],
                'tiempo': rate['delivery_days'],
                'precio_final': precio_con_comision
            })

        return JsonResponse({'tarifas': tarifas_finales})

    except Exception as e:
        return JsonResponse({'error': str(e), 'tarifas': []})

# --- 3. DETALLE DEL PRODUCTO ---
def detalle_producto(request, product_id):
    product = get_object_or_404(IndustrialProduct, id=product_id)
    preference_id = None
    
    mp_token = "APP_USR-2885162849289081-010612-228b3049d19e3b756b95f319ee9d0011-40588817" 
    
    try:
        sdk = mercadopago.SDK(mp_token)
        preference_data = {
            "items": [
                {
                    "title": product.title,
                    "quantity": 1,
                    "unit_price": float(product.price),
                    "currency_id": "MXN"
                }
            ],
            "external_reference": str(product.id),
            "back_urls": {
                "success": request.build_absolute_uri(reverse('pago_exitoso')),
                "failure": request.build_absolute_uri(reverse('pago_fallido')),
            },
            "auto_return": "approved",
        }
        preference_response = sdk.preference().create(preference_data)
        preference_id = preference_response["response"].get("id")
    except Exception as e:
        print(f"Error MP: {e}")

    return render(request, 'marketplace/product_detail.html', {
        'product': product,
        'preference_id': preference_id
    })

# --- RESTO DE TUS VISTAS (HOME, LOGIN, ETC) ---

def home(request):
    query = request.GET.get('q')
    if query:
        products = IndustrialProduct.objects.filter(
            Q(title__icontains=query) | Q(brand__icontains=query) | Q(part_number__icontains=query)
        ).distinct()
    else:
        products = IndustrialProduct.objects.all().order_by('-created_at')
    return render(request, 'marketplace/home.html', {'products': products, 'query': query})

@login_required
def mis_compras(request):
    compras = Sale.objects.filter(buyer=request.user).order_by('-created_at')
    return render(request, 'marketplace/mis_compras.html', {'compras': compras})

@login_required
def mis_ventas(request):
    ventas = Sale.objects.filter(product__user=request.user).order_by('-created_at')
    return render(request, 'marketplace/mis_ventas.html', {'ventas': ventas})

@login_required
def subir_producto(request):
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES)
        if form.is_valid():
            producto = form.save(commit=False)
            producto.user = request.user
            producto.save()
            return redirect('mi_inventario')
    else:
        form = ProductoForm()
    return render(request, 'marketplace/subir_producto.html', {'form': form})

@login_required
def editar_producto(request, pk):
    producto = get_object_or_404(IndustrialProduct, pk=pk, user=request.user)
    if request.method == "POST":
        form = ProductoForm(request.POST, request.FILES, instance=producto)
        if form.is_valid():
            form.save()
            return redirect('mi_inventario')
    else:
        form = ProductoForm(instance=producto)
    return render(request, 'marketplace/subir_producto.html', {'form': form, 'edit': True})

@login_required
def borrar_producto(request, pk):
    producto = get_object_or_404(IndustrialProduct, pk=pk, user=request.user)
    producto.delete()
    return redirect('mi_inventario')

@login_required
def mi_inventario(request):
    if request.user.is_staff:
        productos = IndustrialProduct.objects.all().order_by('-created_at')
    else:
        productos = IndustrialProduct.objects

def category_detail(request, category_id):
    """ Muestra los productos filtrados por una categoría específica """
    category = get_object_or_404(Category, id=category_id)
    products = IndustrialProduct.objects.filter(category=category).order_by('-created_at')
    return render(request, 'marketplace/home.html', {
        'products': products, 
        'category': category
    })

# --- FUNCIÓN DE REGISTRO ---
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

# --- FUNCIÓN DE CAMBIAR ESTADO DE VENTA ---
def cambiar_estado_venta(request, venta_id):
    venta = get_object_or_404(Sale, id=venta_id, product__user=request.user)
    venta.status = 'completado' if venta.status == 'pendiente' else 'pendiente'
    venta.save()
    return redirect('mis_ventas')

# --- FUNCIÓN DE PROCESAR PAGO (BÁSICO) ---
def procesar_pago(request, product_id):
    if request.method == 'POST':
        producto = get_object_or_404(IndustrialProduct, id=product_id)
        if producto.stock > 0:
            Sale.objects.create(
                product=producto,
                buyer=request.user,
                price=producto.price,
                status='pendiente'
            )
            producto.stock -= 1
            producto.save()
            return redirect('pago_exitoso')
    return redirect('detalle_producto', product_id=product_id)

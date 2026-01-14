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
import base64

# IMPORTANTE: Usando tus nombres exactos de forms.py
from .models import IndustrialProduct, Category, Sale, Profile
from .forms import ProductForm, RegistroForm, ProfileForm, UserUpdateForm

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
SDK = mercadopago.SDK("APP_USR-2885162849289081-010612-228b3049d19e3b756b95f319ee9d0011-40588817")

# ==========================================
# 1. PERFIL (Corregido con tus 2 formularios)
# ==========================================
@login_required
def editar_perfil(request):
    # Obtenemos o creamos el perfil del usuario
    profile, created = Profile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        # Usamos tus clases: UserUpdateForm y ProfileForm
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileForm(request.POST, instance=profile)
        
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, "¡Tu perfil ha sido actualizado!")
            return redirect('editar_perfil')
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileForm(instance=profile)

    return render(request, 'marketplace/editar_perfil.html', {
        'u_form': u_form,
        'p_form': p_form
    })

# ==========================================
# 2. SOLOENVÍOS (Corregido con tus campos: peso, largo, etc.)
# ==========================================
def cotizar_soloenvios(request):
    # 1. Preparar datos de la URL
    cp_origen = request.GET.get('cp_origen', '').strip()
    cp_destino = request.GET.get('cp_destino', '').strip()
    
    # Credenciales de tu aplicación
    client_id = "puouHyooEp4uBo0Nnov46lUFOf-memYBLGRYhdB1eRA"
    client_secret = "vzVupeT2PMAktJp5SbXlyivRf8ajqqRD0015Pxhz-Ps"
    
    try:
        # --- PASO 1: OBTENER EL TOKEN ---
        auth_url = 'https://app.soloenvios.com/api/v1/oauth/token'
        
        # Según tu manual: application/x-www-form-urlencoded
        # En requests, esto se hace pasando un diccionario al parámetro 'data'
        auth_payload = {
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob'
        }
        
        headers_auth = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }

        auth_res = requests.post(auth_url, data=auth_payload, headers=headers_auth, verify=False, timeout=10)
        
        if auth_res.status_code != 200:
            # Si falla, imprimimos el error exacto del manual
            print(f"ERROR AUTH SOLOENVIOS: {auth_res.text}")
            return JsonResponse({
                'tarifas': [], 
                'error': 'Error de Autenticación',
                'detalle': auth_res.json().get('error_description', 'Credenciales inválidas')
            })
            
        token_data = auth_res.json()
        token = token_data.get('access_token')

        # --- PASO 2: COTIZACIÓN ---
        # Usaremos el endpoint de quotations que vimos en tu consola de pruebas
        rates_url = "https://app.soloenvios.com/api/v1/quotations"
        
        headers_rates = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Construcción del paquete según el estándar de SoloEnvíos
        payload_rates = {
            "origin_zip_code": cp_origen,
            "destination_zip_code": cp_destino,
            "packages": [
                {
                    "weight": float(request.GET.get('peso') or 1),
                    "width": int(float(request.GET.get('ancho') or 20)),
                    "height": int(float(request.GET.get('alto') or 20)),
                    "length": int(float(request.GET.get('largo') or 20)),
                    "description": "Caja de cartón"
                }
            ]
        }
        
        res = requests.post(rates_url, json=payload_rates, headers=headers_rates, verify=False)
        
        if res.status_code == 200:
            data = res.json()
            # El endpoint de quotations devuelve una lista o un objeto con 'rates'
            rates_list = data.get('rates', data) if isinstance(data, dict) else data
            
            tarifas = []
            for t in rates_list:
                # Extraemos el costo total
                precio = t.get('total_price') or t.get('price') or t.get('cost')
                if precio:
                    tarifas.append({
                        'paqueteria': t.get('service_name') or t.get('carrier_name') or 'Envío',
                        'precio_final': round(float(precio) * 1.08, 2), # 8% margen
                        'tiempo': t.get('delivery_days') or 'N/A'
                    })
            return JsonResponse({'tarifas': tarifas})
        
        return JsonResponse({
            'tarifas': [], 
            'error': f'Error en Cotización: {res.status_code}', 
            'detalle': res.text
        })

    except Exception as e:
        return JsonResponse({'tarifas': [], 'error': str(e)})

# ==========================================
# 3. GESTIÓN DE PRODUCTOS
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
# 4. RESTO DE FUNCIONES (Sincronizadas con URLs)
# ==========================================
def home(request):
    products = IndustrialProduct.objects.all().order_by('-created_at')
    categories = Category.objects.all()
    return render(request, 'marketplace/home.html', {'products': products, 'categories': categories})

def detalle_producto(request, product_id):
    product = get_object_or_404(IndustrialProduct, id=product_id)
    pref_data = {
        "items": [{"id": str(product.id), "title": product.title, "quantity": 1, "unit_price": float(product.price), "currency_id": "MXN"}],
        "external_reference": str(product.id),
    }
    pref = SDK.preference().create(pref_data)
    return render(request, 'marketplace/product_detail.html', {'product': product, 'preference_id': pref["response"]["id"]})

def category_detail(request, category_id):
    cat = get_object_or_404(Category, id=category_id)
    return render(request, 'marketplace/home.html', {'products': IndustrialProduct.objects.filter(category=cat), 'category': cat})

def registro(request):
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = RegistroForm()
    return render(request, 'marketplace/registro.html', {'form': form})

@login_required
def mis_ventas(request):
    ventas = Sale.objects.filter(product__user=request.user).order_by('-created_at')
    return render(request, 'marketplace/mis_ventas.html', {'ventas': ventas})

@login_required
def mis_compras(request):
    compras = Sale.objects.filter(buyer=request.user).order_by('-created_at')
    return render(request, 'marketplace/mis_compras.html', {'compras': compras})

@login_required
def cambiar_estado_venta(request, venta_id):
    v = get_object_or_404(Sale, id=venta_id, product__user=request.user)
    if v.status == 'pendiente': v.status = 'completado'; v.save()
    return redirect('mis_ventas')

@login_required
def cancelar_venta(request, venta_id):
    v = get_object_or_404(Sale, id=venta_id); v.status = 'cancelado'; v.save()
    return redirect('mis_ventas')

@login_required
def confirmar_recepcion(request, venta_id):
    v = get_object_or_404(Sale, id=venta_id, buyer=request.user)
    v.status = 'entregado'; v.save()
    return redirect('mis_compras')

@login_required
def actualizar_guia(request, venta_id):
    if request.method == 'POST':
        v = get_object_or_404(Sale, id=venta_id, product__user=request.user)
        v.shipping_company = request.POST.get('shipping_company')
        v.tracking_number = request.POST.get('tracking_number')
        v.status = 'enviado'; v.save()
    return redirect('mis_ventas')

def procesar_pago(request, product_id):
    return redirect('detalle_producto', product_id=product_id)

def actualizar_pago(request):
    pid = request.GET.get('id')
    envio = float(request.GET.get('envio', 0))
    prod = get_object_or_404(IndustrialProduct, id=pid)
    total = float(prod.price) + envio
    pref = SDK.preference().create({"items": [{"title": prod.title, "quantity": 1, "unit_price": total, "currency_id": "MXN"}]})
    return JsonResponse({'preference_id': pref["response"]["id"], 'total_nuevo': f"{total:,.2f}"})

@login_required
def crear_intencion_compra(request, product_id):
    p = get_object_or_404(IndustrialProduct, id=product_id)
    Sale.objects.create(product=p, buyer=request.user, price=p.price, status='pendiente')
    return redirect('mis_compras')

@staff_member_required
def panel_administrador(request):
    ventas = Sale.objects.all().order_by('-created_at')
    return render(request, 'marketplace/panel_admin.html', {'ventas': ventas})

@staff_member_required
def marcar_como_pagado(request, venta_id):
    v = get_object_or_404(Sale, id=venta_id); v.pagado_a_vendedor = True; v.save()
    return redirect('panel_administrador')

def pago_exitoso(request): return render(request, 'marketplace/pago_exitoso.html')
def pago_fallido(request): return render(request, 'marketplace/pago_fallido.html')
def mercadopago_webhook(request): return JsonResponse({'status': 'ok'})

















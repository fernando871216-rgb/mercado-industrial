from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import JsonResponse
from decimal import Decimal
import requests
import mercadopago

# Importa tus modelos y formularios
# IMPORTANTE: Asegúrate de que en models.py el modelo se llame Sale o Venta
from .models import IndustrialProduct, Category, Sale, Profile
from .forms import RegistroForm, ProductForm, ProfileForm

# --- CONFIGURACIÓN ---
SDK = mercadopago.SDK("APP_USR-2885162849289081-010612-228b3049d19e3b756b95f319ee9d0011-40588817")

# --- VISTAS PRINCIPALES ---
def home(request):
    products = IndustrialProduct.objects.all().order_by('-created_at')
    categories = Category.objects.all()
    return render(request, 'marketplace/home.html', {'products': products, 'categories': categories})

def detalle_producto(request, product_id):
    product = get_object_or_404(IndustrialProduct, id=product_id)
    return render(request, 'marketplace/product_detail.html', {'product': product})

# Esta es la función que te pide el error de Render
def procesar_pago(request, product_id):
    product = get_object_or_404(IndustrialProduct, id=product_id)
    # Lógica básica para generar la preferencia de Mercado Pago
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
    # Redirigimos al checkout de Mercado Pago
    return redirect(preference_result["response"]["init_point"])

def category_detail(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    products = IndustrialProduct.objects.filter(category=category)
    return render(request, 'marketplace/home.html', {'products': products, 'category': category})

# --- SOLOENVÍOS ---
def cotizar_soloenvios(request):
    cp_origen = request.GET.get('cp_origen')
    cp_destino = request.GET.get('cp_destino')
    peso = request.GET.get('peso', 1)
    
    url = "https://soloenvios.com/api/v1/rates"
    headers = {
        "Authorization": "-mUChsOjBGG5dJMchXbLLQBdPxQJldm4wx3kLPoWWDs",
        "Content-Type": "application/json"
    }
    payload = {
        "origin_zip_code": str(cp_origen),
        "destination_zip_code": str(cp_destino),
        "package": {"weight": float(peso), "width": 10, "height": 10, "length": 10}
    }
    try:
        response = requests.post(url, json=payload, headers=headers)
        data = response.json()
        tarifas_finales = []
        for t in data:
            precio_con_comision = round(float(t['price']) * 1.08, 2)
            tarifas_finales.append({
                'paqueteria': t['service_name'],
                'precio_final': precio_con_comision,
                'tiempo': t['delivery_days']
            })
        return JsonResponse({'tarifas': tarifas_finales})
    except:
        return JsonResponse({'tarifas': []})

def actualizar_preferencia_pago(request):
    product_id = request.GET.get('id')
    costo_envio = float(request.GET.get('envio', 0))
    product = get_object_or_404(IndustrialProduct, id=product_id)
    total = float(product.price) + costo_envio
    
    preference_data = {
        "items": [{"title": f"{product.title} + Envío", "quantity": 1, "unit_price": total, "currency_id": "MXN"}]
    }
    res = SDK.preference().create(preference_data)
    return JsonResponse({'preference_id': res["response"]["id"], 'total_nuevo': total})

# --- GESTIÓN DE USUARIOS Y PRODUCTOS ---
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

# --- FLUJO DE VENTAS ---
@login_required
def mis_compras(request):
    compras = Sale.objects.filter(buyer=request.user).order_by('-created_at')
    return render(request, 'marketplace/mis_compras.html', {'compras': compras})

@login_required
def mis_ventas(request):
    ventas = Sale.objects.filter(product__user=request.user).order_by('-created_at')
    return render(request, 'marketplace/mis_ventas.html', {'ventas': ventas})

@login_required
def actualizar_guia(request, venta_id):
    if request.method == 'POST':
        venta = get_object_or_404(Sale, id=venta_id)
        if venta.product.user == request.user:
            venta.shipping_company = request.POST.get('shipping_company')
            venta.tracking_number = request.POST.get('tracking_number')
            venta.status = 'enviado'
            venta.save()
            messages.success(request, "Guía registrada correctamente.")
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
        if venta.status != 'cancelado':
            producto = venta.product
            producto.stock += 1
            producto.save()
            venta.status = 'cancelado'
            venta.save()
            messages.success(request, "Venta cancelada.")
    return redirect('mis_ventas')

# --- PANEL ADMIN ---
@staff_member_required
def panel_administrador(request):
    ventas = Sale.objects.all().order_by('-created_at')
    # Sumar la comisión de todas las ventas que no estén canceladas
    tus_ganancias = sum(v.get_platform_commission() for v in ventas if v.status != 'cancelado')
    return render(request, 'marketplace/panel_admin.html', {
        'ventas': ventas, 
        'tus_ganancias': tus_ganancias
    })

@staff_member_required
def marcar_como_pagado(request, venta_id):
    venta = get_object_or_404(Sale, id=venta_id)
    venta.pagado_a_vendedor = True
    venta.save()
    return redirect('panel_administrador')

# --- OTROS ---
def pago_exitoso(request):
    return render(request, 'marketplace/pago_exitoso.html')

def pago_fallido(request):
    return render(request, 'marketplace/pago_fallido.html')

def mercadopago_webhook(request):
    return JsonResponse({'status': 'ok'}, status=200)


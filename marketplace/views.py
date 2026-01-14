from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import JsonResponse
from decimal import Decimal
import requests
import mercadopago
import json
from .models import IndustrialProduct, Category, Sale, Profile
from .forms import RegistroForm, ProductForm, ProfileForm, UserUpdateForm

# --- CONFIGURACIÓN ---
SDK = mercadopago.SDK("APP_USR-2885162849289081-010612-228b3049d19e3b756b95f319ee9d0011-40588817")

# --- VISTAS PRINCIPALES ---
def home(request):
    products = IndustrialProduct.objects.all().order_by('-created_at')
    categories = Category.objects.all()
    return render(request, 'marketplace/home.html', {'products': products, 'categories': categories})

def detalle_producto(request, product_id):
    product = get_object_or_404(IndustrialProduct, id=product_id)
    
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

# --- MERCADO PAGO Y LOGÍSTICA ---

# Esta función es necesaria porque tu urls.py la menciona
def procesar_pago(request, product_id):
    # Por ahora redirigimos al detalle para evitar errores
    return redirect('product_detail', product_id=product_id)

def actualizar_pago(request):
    product_id = request.GET.get('id')
    costo_envio = float(request.GET.get('envio', 0))
    product = get_object_or_404(IndustrialProduct, id=product_id)
    total = float(product.price) + costo_envio
    
    preference_data = {
        "items": [{
            "id": str(product.id),
            "title": f"{product.title} + Envío",
            "quantity": 1, 
            "unit_price": total, 
            "currency_id": "MXN"
        }],
        "external_reference": str(product.id),
    }
    res = SDK.preference().create(preference_data)
    return JsonResponse({
        'preference_id': res["response"]["id"], 
        'total_nuevo': f"{total:,.2f}"
    })

# --- SOLOENVÍOS ---
def cotizar_soloenvios(request):
    # Obtenemos los CPs y aseguramos que sean strings limpios
    cp_origen = request.GET.get('cp_origen', '').strip()
    cp_destino = request.GET.get('cp_destino', '').strip()
    
    # Si no hay CPs, no intentamos cotizar
    if not cp_origen or not cp_destino:
        return JsonResponse({'tarifas': [], 'error': 'Faltan códigos postales'})

    # Forzamos dimensiones mínimas si vienen vacías o en 0
    # Las APIs de envío suelen fallar si el peso es 0
    peso = float(request.GET.get('peso') or 1)
    largo = float(request.GET.get('largo') or 10)
    ancho = float(request.GET.get('ancho') or 10)
    alto = float(request.GET.get('alto') or 10)
    
    url = "https://soloenvios.com/api/v1/rates"
    headers = {
        "Authorization": "Bearer -mUChsOjBGG5dJMchXbLLQBdPxQJldm4wx3kLPoWWDs", # Añadí 'Bearer ' que es el estándar
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    # Estructura exacta que pide SoloEnvíos
    payload = {
        "origin_zip_code": cp_origen,
        "destination_zip_code": cp_destino,
        "package": {
            "weight": peso,
            "width": ancho,
            "height": alto,
            "length": largo
        }
    }
    
    try:
        # Imprimimos en la consola de Render para que puedas ver si hay error
        print(f"Cotizando: De {cp_origen} a {cp_destino} con peso {peso}")
        
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        # Si la respuesta es 200 (OK)
        if response.status_code == 200:
            data = response.json()
            tarifas_finales = []
            
            # SoloEnvíos a veces devuelve una lista, a veces un objeto con 'rates'
            # Esta lógica cubre ambos casos
            rates = data if isinstance(data, list) else data.get('rates', [])
            
            for t in rates:
                # Calculamos tu comisión del 8%
                precio_original = float(t.get('price', 0))
                if precio_original > 0:
                    precio_con_comision = round(precio_original * 1.08, 2)
                    tarifas_finales.append({
                        'paqueteria': t.get('service_name', 'Servicio Estándar'),
                        'precio_final': precio_con_comision,
                        'tiempo': t.get('delivery_days', 'N/D')
                    })
            return JsonResponse({'tarifas': tarifas_finales})
        else:
            print(f"Error API SoloEnvíos: {response.status_code} - {response.text}")
            return JsonResponse({'tarifas': [], 'error': 'No se encontraron rutas disponibles'})
            
    except Exception as e:
        print(f"Excepción en cotizador: {str(e)}")
        return JsonResponse({'tarifas': [], 'error': 'Error de conexión'})

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
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileForm(request.POST, instance=profile)
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            return redirect('editar_perfil')
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileForm(instance=profile)
    return render(request, 'marketplace/editar_perfil.html', {'u_form': u_form, 'p_form': p_form})

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
    tus_ganancias = sum(
        (v.get_platform_commission() for v in ventas if v.status == 'pagado' or v.status == 'enviado'), 
        Decimal('0.00')
    )
    return render(request, 'marketplace/panel_admin.html', {'ventas': ventas, 'tus_ganancias': tus_ganancias})

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
    payment_id = request.GET.get('data.id') or request.GET.get('id')
    topic = request.GET.get('type') or request.GET.get('topic')

    if topic == 'payment' and payment_id:
        url = f"https://api.mercadopago.com/v1/payments/{payment_id}"
        headers = {"Authorization": f"Bearer {SDK.access_token}"}
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            payment_info = response.json()
            if payment_info['status'] == 'approved':
                product_id = payment_info['external_reference']
                product = get_object_or_404(IndustrialProduct, id=product_id)
                
                sale, created = Sale.objects.get_or_create(
                    product=product,
                    status='pendiente',
                    defaults={'price': product.price}
                )
                sale.status = 'pagado'
                sale.save()
    return JsonResponse({'status': 'ok'}, status=200)

@login_required
def crear_intencion_compra(request, product_id):
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
        messages.success(request, "Intención de compra registrada. El stock ha sido apartado.")
    return redirect('mis_compras')


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
    
    # GENERAR PREFERENCIA INICIAL PARA QUE EL BOTÓN APAREZCA AL CARGAR
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
        "external_reference": str(product.id), # Importante para saber qué se vendió
    }
    
    preference_result = SDK.preference().create(preference_data)
    preference_id = preference_result["response"]["id"]
    
    return render(request, 'marketplace/product_detail.html', {
        'product': product,
        'preference_id': preference_id  # <--- Esto es lo que hacía falta para el HTML
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
        "Authorization": "-mUChsOjBGG5dJMchXbLLQBdPxQJldm4wx3kLPoWWDs",
        "Content-Type": "application/json"
    }
    payload = {
        "origin_zip_code": str(cp_origen),
        "destination_zip_code": str(cp_destino),
        "package": {
            "weight": float(peso), 
            "width": float(ancho), 
            "height": float(alto), 
            "length": float(largo)
        }
    }
    try:
        response = requests.post(url, json=payload, headers=headers)
        data = response.json()
        tarifas_finales = []
        for t in data:
            # Tu comisión del 8%
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
        'total_nuevo': f"{total:,.2f}" # Formateado con comas
    })

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
    # Intentamos obtener el perfil, si no existe lo creamos para evitar errores
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

    return render(request, 'marketplace/editar_perfil.html', {
        'u_form': u_form,
        'p_form': p_form
    })

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

# VISTA PARA EDITAR (Asegura que pase el objeto 'producto')
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
    
    # Es vital que aquí diga 'producto': producto
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
    # Usamos "Sale" porque así se llama en tu models.py
    # Buscamos productos que pertenecen al usuario logueado
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
    
    # Calculamos ganancias sumando comisiones de ventas que NO estén pendientes ni canceladas
    # Solo sumamos lo que ya es un ingreso real o pagado
    tus_ganancias = sum(
        (v.get_platform_commission() for v in ventas if v.status == 'pagado' or v.status == 'enviado'), 
        Decimal('0.00')
    )
    
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
    payment_id = request.GET.get('data.id') or request.GET.get('id')
    topic = request.GET.get('type') or request.GET.get('topic')

    if topic == 'payment' and payment_id:
        url = f"https://api.mercadopago.com/v1/payments/{payment_id}"
        headers = {"Authorization": f"Bearer {SDK.access_token}"}
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            payment_info = response.json()
            if payment_info['status'] == 'approved':
                # Obtenemos el ID del producto que guardamos en external_reference
                product_id = payment_info['external_reference']
                product = IndustrialProduct.objects.get(id=product_id)
                
                # Buscamos si ya existe la venta pendiente para marcarla como pagada
                # O creamos una nueva si no existía
                sale, created = Sale.objects.get_or_create(
                    product=product,
                    status='pendiente',
                    defaults={'price': product.price}
                )
                sale.status = 'pagado'
                sale.save()
                
    return JsonResponse({'status': 'ok'}, status=200)



# VISTA DE COMPRA (Aquí es donde descontamos el stock)
@login_required
def crear_intencion_compra(request, product_id):
    producto = get_object_or_404(IndustrialProduct, id=product_id)
    
    # Verificamos si hay stock antes de hacer nada
    if producto.stock > 0:
        # Creamos el registro en el modelo Sale (Venta)
        Sale.objects.create(
            product=producto,
            buyer=request.user,
            price=producto.price,
            status='pendiente'
        )
        
        # DESCONTAMOS EL STOCK
        producto.stock -= 1
        producto.save()
        
    return redirect('mis_compras')







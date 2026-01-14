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

# IMPORTANTE: Asegúrate que estos modelos y formularios existan en tu proyecto
from .models import IndustrialProduct, Category, Sale
from .forms import ProductForm 

# Desactivar advertencias de seguridad para Render
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# CONFIGURACIÓN DE MERCADO PAGO
SDK = mercadopago.SDK("APP_USR-2885162849289081-010612-228b3049d19e3b756b95f319ee9d0011-40588817")

# ==========================================
# 1. API DE SOLOENVÍOS (Logística)
# ==========================================
def cotizar_soloenvios(request):
    cp_origen = request.GET.get('cp_origen', '').strip()
    cp_destino = request.GET.get('cp_destino', '').strip()
    
    if not cp_origen or not cp_destino:
        return JsonResponse({'tarifas': [], 'error': 'Faltan datos'})

    client_id = "-mUChsOjBGG5dJMchXbLLQBdPxQJldm4wx3kLPoWWDs"
    client_secret = "MweefVUPz-_8ECmutghmvda-YTOOB7W6zFiXwJD8yw"
    
    auth_url = "https://app.soloenvios.com/api/v1/oauth/token"
    auth_payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials",
        "redirect_uri": "urn:ietf:wg:oauth:2.0:oob"
    }
    
    try:
        auth_res = requests.post(auth_url, json=auth_payload, verify=False, timeout=15)
        if auth_res.status_code == 200:
            access_token = auth_res.json().get('access_token')
            rates_url = "https://app.soloenvios.com/api/v1/rates"
            headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
            
            paquete = {
                "origin_zip_code": str(cp_origen),
                "destination_zip_code": str(cp_destino),
                "package": {
                    "weight": float(request.GET.get('peso') or 1),
                    "width": float(request.GET.get('ancho') or 20),
                    "height": float(request.GET.get('alto') or 20),
                    "length": float(request.GET.get('largo') or 20)
                }
            }
            
            response = requests.post(rates_url, json=paquete, headers=headers, verify=False, timeout=15)
            if response.status_code == 200:
                data = response.json()
                rates = data if isinstance(data, list) else data.get('rates', [])
                tarifas_finales = []
                for t in rates:
                    precio = float(t.get('price') or t.get('cost') or 0)
                    if precio > 0:
                        tarifas_finales.append({
                            'paqueteria': t.get('service_name') or t.get('provider') or 'Envío',
                            'precio_final': round(precio * 1.08, 2), # Tu 8% de comisión
                            'tiempo': t.get('delivery_days') or '3-5 días'
                        })
                return JsonResponse({'tarifas': tarifas_finales})
            return JsonResponse({'tarifas': [], 'error': 'Sin cobertura'})
        return JsonResponse({'tarifas': [], 'error': 'Error de autenticación'})
    except Exception as e:
        return JsonResponse({'tarifas': [], 'error': str(e)})

# ==========================================
# 2. VISTAS PÚBLICAS Y NAVEGACIÓN
# ==========================================
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

def registro(request):
    return render(request, 'marketplace/registro.html')

# ==========================================
# 3. GESTIÓN DE INVENTARIO (VENDEDOR)
# ==========================================
@login_required
def editar_perfil(request):
    return render(request, 'marketplace/editar_perfil.html')

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
# 4. FLUJO DE VENTAS Y PAGOS
# ==========================================
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

# ==========================================
# 5. PANEL ADMIN Y WEBHOOKS
# ==========================================
@staff_member_required
def panel_administrador(request):
    ventas = Sale.objects.all().order_by('-created_at')
    tus_ganancias = sum(
        (v.get_platform_commission() for v in ventas if v.status in ['pagado', 'enviado']), 
        Decimal('0.00')
    )
    return render(request, 'marketplace/panel_admin.html', {'ventas': ventas, 'tus_ganancias': tus_ganancias})

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

def pago_exitoso(request): return render(request, 'marketplace/pago_exitoso.html')
def pago_fallido(request): return render(request, 'marketplace/pago_fallido.html')

# Funciones extra requeridas por tus URLs
def lista_productos(request):
    productos = IndustrialProduct.objects.all()
    return render(request, 'marketplace/lista_productos.html', {'productos': productos})

def procesar_pago(request, product_id):
    return redirect('product_detail', product_id=product_id)

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
import uuid
import os
import time
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
# IMPORTANTE: Solo importamos lo que existe en tu models.py
from .models import IndustrialProduct, Category, Sale, Profile
from .forms import ProductForm, RegistroForm, ProfileForm, UserUpdateForm
from django.contrib.auth.models import User

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
SDK = mercadopago.SDK("APP_USR-2885162849289081-010612-228b3049d19e3b756b95f319ee9d0011-40588817")

# ==========================================
# 1. PERFIL (Corregido con tus 2 formularios)
# ==========================================
@login_required
def editar_perfil(request):
    # Intentamos obtener el perfil del usuario, si no existe lo creamos
    profile, created = Profile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileForm(request.POST, instance=profile)
        
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, "¡Tu perfil y datos bancarios han sido actualizados!")
            return redirect('editar_perfil')
        else:
            messages.error(request, "Por favor corrige los errores abajo.")
    else:
        # Aquí es donde estaba el error: este 'else' debe estar alineado con el primer 'if'
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileForm(instance=profile)

    return render(request, 'marketplace/editar_perfil.html', {
        'u_form': u_form,
        'p_form': p_form
    })

# ==========================================
# 2. SOLOENVÍOS (Corregido con tus campos: peso, largo, etc.)
# ==========================================
def obtener_token_soloenvios():
    url = "https://app.soloenvios.com/api/v1/oauth/token"
    client_id = os.environ.get('SOLOENVIOS_CLIENT_ID', '').strip()
    client_secret = os.environ.get('SOLOENVIOS_CLIENT_SECRET', '').strip()

    if not client_id or not client_secret:
        return "ERROR_LLAVES_VACIAS"

    # Hemos quitado el "scope" para que use los que tu cuenta tiene por defecto
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials"
    }
    
    headers = {
        "Content-Type": "application/json", 
        "Accept": "application/json"
    }
    
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=20, verify=False)
        
        if res.status_code == 200:
            return res.json().get('access_token')
        else:
            # Si vuelve a fallar, nos dirá por qué
            return f"ERROR_API_{res.status_code}_{res.text}"
    except Exception as e:
        return f"ERROR_CONEXION_{str(e)}"

def cotizar_soloenvios(request):
    # 1. Obtenemos el ID del producto que viene del HTML
    product_id = request.GET.get('product_id')
    
    try:
        # Buscamos en IndustrialProduct que es el modelo que usas
        producto = get_object_or_404(IndustrialProduct, id=product_id)
        cp_origen = str(producto.cp_origen).strip().zfill(5)
        peso_db = producto.peso
        largo_db = producto.largo
        ancho_db = producto.ancho
        alto_db = producto.alto
    except Exception as e:
        print(f"Error cargando producto: {e}")
        cp_origen = "72460"
        peso_db, largo_db, ancho_db, alto_db = 1, 20, 20, 20

    # 2. Datos que vienen del formulario (por si el usuario los ajusta)
    cp_destino = str(request.GET.get('cp_destino', '')).strip().zfill(5)
    
    token = obtener_token_soloenvios()
    if "ERROR" in str(token):
        return JsonResponse({'tarifas': [], 'error': f'Fallo de Token: {token}'})

    try:
        def limpiar_valor(val, default_val):
            try:
                num = int(float(val))
                return num if num > 0 else default_val
            except:
                return default_val

        # Priorizamos lo que venga del request, si no, lo de la DB
        peso = limpiar_valor(request.GET.get('peso'), peso_db)
        largo = limpiar_valor(request.GET.get('largo'), largo_db)
        ancho = limpiar_valor(request.GET.get('ancho'), ancho_db)
        alto = limpiar_valor(request.GET.get('alto'), alto_db)

        url = "https://app.soloenvios.com/api/v1/quotations"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        payload = {
            "quotation": {
                "address_from": {
                    "country_code": "MX", "postal_code": cp_origen,
                    "area_level1": "Origen", "area_level2": "Municipio", "area_level3": "Colonia"
                },
                "address_to": {
                    "country_code": "MX", "postal_code": cp_destino,
                    "area_level1": "Destino", "area_level2": "Ciudad", "area_level3": "Colonia"
                },
                "parcels": [{
                    "length": largo, "width": ancho, "height": alto, "weight": peso,
                    "package_protected": False, "declared_value": 100
                }]
            }
        }
        
        res = requests.post(url, json=payload, headers=headers, timeout=25, verify=False)
        
        if res.status_code in [200, 201]:
            cotizacion_id = res.json().get('id')
            time.sleep(2.5) # Espera para que las paqueterías respondan
            
            res_final = requests.get(f"{url}/{cotizacion_id}", headers=headers, verify=False)
            data = res_final.json()
            
            tarifas = []
            for t in data.get('rates', []):
                if t.get('total') and float(t.get('total')) > 0:
                    tarifas.append({
                        'paqueteria': f"{t.get('provider_display_name')} ({t.get('provider_service_name')})",
                        'precio_final': round(float(t.get('total')) * 1.08, 2),
                        'tiempo': f"{t.get('days')} días" if t.get('days') else "N/A"
                    })
            return JsonResponse({'tarifas': tarifas})
        
        return JsonResponse({'tarifas': [], 'error': f'API Error: {res.text}'})

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
            # ESTA LÍNEA ES LA QUE FALTA PARA EL ANUNCIO:
            messages.success(request, f"¡El producto '{producto.title}' fue actualizado con éxito!")
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
    query = request.GET.get('q') # Captura lo que escribieron en la barra de búsqueda
    if query:
        # Filtra por Título O por Número de Parte ignorando mayúsculas/minúsculas
        products = IndustrialProduct.objects.filter(
            Q(title__icontains=query) | Q(part_number__icontains=query)
        )
    else:
        products = IndustrialProduct.objects.all()
    
    return render(request, 'marketplace/home.html', {'products': products})

def detalle_producto(request, product_id):
    product = get_object_or_404(IndustrialProduct, id=product_id)
    # Generamos la preferencia inicial del producto
    pref_data = {
        "items": [{
            "id": str(product.id), 
            "title": product.title, 
            "quantity": 1, 
            "unit_price": float(product.price), 
            "currency_id": "MXN"
        }],
        "external_reference": str(product.id),
    }
    pref = SDK.preference().create(pref_data)
    
    return render(request, 'marketplace/product_detail.html', {
        'product': product, 
        'preference_id': pref["response"]["id"],
        'public_key': "APP_USR-bab958ea-ede4-49f7-b072-1fd682f9e1b9" # Asegúrate de que esta sea tu llave pública real
    })
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
    # Traemos las ventas de los productos que pertenecen al usuario actual
    ventas = Sale.objects.filter(product__user=request.user).order_by('-created_at')
    
    if request.method == 'POST':
        venta_id = request.POST.get('venta_id')
        guia = request.POST.get('tracking_number')
        paqueteria = request.POST.get('shipping_company')
        
        venta = get_object_or_404(Sale, id=venta_id, product__user=request.user)
        venta.tracking_number = guia
        venta.shipping_company = paqueteria
        venta.status = 'enviado' # Cambiamos el estado automáticamente
        venta.save()
        messages.success(request, f"Guía de envío actualizada para {venta.product.title}")
        return redirect('mis_ventas')
    
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
    if request.method == 'POST':
        # Buscamos la venta asegurándonos que el que confirma es el comprador
        venta = get_object_or_404(Sale, id=venta_id, buyer=request.user)
        
        # Actualizamos los estados
        venta.recibido_por_comprador = True
        venta.status = 'entregado'
        venta.save()
        
        messages.success(request, "¡Gracias! Hemos registrado que recibiste tu producto.")
        return redirect('mis_compras')
    
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
    try:
        pid = request.GET.get('id')
        # Este 'envio' ya viene con el 8% aplicado desde cotizar_soloenvios
        envio_con_comision_logistica = float(request.GET.get('envio', 0))
        prod = get_object_or_404(IndustrialProduct, id=pid)
        
        precio_producto = float(prod.price)
        
        # 1. Tu comisión sobre el PRODUCTO (5% de INITRE)
        comision_initre = precio_producto * 0.05
        
        # 2. Subtotal antes de Mercado Pago
        subtotal = precio_producto + comision_initre + envio_con_comision_logistica
        
        # 3. Comisión Mercado Pago (3.49% + $4 + IVA)
        porcentaje_mp = subtotal * 0.0349
        fijo_mp = 4.0
        iva_mp = (porcentaje_mp + fjo_mp) * 0.16
        total_comision_mp = porcentaje_mp + fijo_mp + iva_mp
        
        # --- TOTAL FINAL QUE COBRA EL BOTÓN ---
        total_final = subtotal + total_comision_mp

        # CORRECCIÓN AQUÍ: 
        # Usamos 'prod.id' (que es tu variable arriba) en lugar de 'producto.id'
        # Usamos str() para asegurar que el ID del usuario se envíe bien
        user_id = request.user.id if request.user.is_authenticated else 0
        ext_ref = f"{prod.id}-{user_id}"

        preference_data = {
            "items": [
                {
                    "title": f"{prod.title}",
                    "description": "Equipo industrial + Envío certificado + Gestión de plataforma",
                    "quantity": 1,
                    "unit_price": round(total_final, 2),
                    "currency_id": "MXN"
                }
            ],
            "external_reference": ext_ref,
            "back_urls": {
                "success": f"https://mercado-industrial.onrender.com/pago-exitoso/{producto.id}/",
                "failure": "https://mercado-industrial.onrender.com/pago-fallido/",
                "pending": f"https://mercado-industrial.onrender.com/pago-exitoso/{producto.id}/"
            },
            "auto_return": "approved", # Esto obliga a Mercado Pago a volver a tu web
            "notification_url": "https://mercado-industrial.onrender.com/webhook/mercadopago/",
        }

        pref_response = SDK.preference().create(preference_data)
        
        return JsonResponse({
            'preference_id': pref_response["response"]["id"], 
            'total_nuevo': f"{total_final:,.2f}"
        })
        
    except Exception as e:
        print(f"Error en actualizar_pago: {e}") # Para que puedas verlo en los logs de Render
        return JsonResponse({'error': str(e)}, status=400)
        
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
    if request.method == 'POST':
        # Buscamos la venta por el ID que viene en la URL
        venta = get_object_or_404(Sale, id=venta_id)
        venta.pagado_a_vendedor = True
        venta.save()
        messages.success(request, f"Venta {venta.id} liquidada con éxito.")
    
    # Después de pagar, regresamos al panel
    return redirect('panel_administrador')

def pago_exitoso(request):
    product_id = request.GET.get('id')
    # Obtenemos el estado que manda Mercado Pago
    status = request.GET.get('status') 
    
    producto = get_object_or_404(IndustrialProduct, id=product_id)
    
    # Solo si el pago fue aprobado mostramos el contacto
    mostrar_contacto = False
    if status == 'approved':
        mostrar_contacto = True
        
    return render(request, 'marketplace/pago_exitoso.html', {
        'producto': producto,
        'mostrar_contacto': mostrar_contacto
    })
def pago_fallido(request): return render(request, 'marketplace/pago_fallido.html')
    
@csrf_exempt
def mercadopago_webhook(request):
    # Mercado Pago puede enviar el ID por parámetros GET o en el cuerpo JSON
    payment_id = request.GET.get('id') or request.GET.get('data.id')
    topic = request.GET.get('topic') or request.GET.get('type')

    # Si es una notificación de pago
    if (topic == 'payment' or topic == 'opened_preference') and payment_id:
        # TU TOKEN (Verifica que sea el "Production Access Token")
        token = "APP_USR-2885162849289081-010612-228b3049d19e3b756b95f319ee9d0011-40588817"
        url = f"https://api.mercadopago.com/v1/payments/{payment_id}"
        headers = {'Authorization': f'Bearer {token}'}
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                status = data.get('status')
                ref_data = data.get('external_reference')
                
                print(f"--- WEBHOOK DATA: Status={status}, ExternalRef={ref_data} ---")

                if status == 'approved' and ref_data:
                    # Separamos ID Producto e ID Comprador
                    # Usamos split('-') pero nos aseguramos de que sean solo números
                    parts = str(ref_data).split('-')
                    if len(parts) >= 2:
                        product_id = parts[0]
                        buyer_id = parts[1]
                        
                        producto = IndustrialProduct.objects.get(id=product_id)
                        comprador = User.objects.get(id=buyer_id)
                        
                        # Creamos la venta
                        venta, created = Sale.objects.get_or_create(
                            product=producto,
                            buyer=comprador,
                            status='approved',
                            defaults={'price': producto.price}
                        )
                        
                        if created:
                            print(f"VENTA EXITOSA: Producto {product_id} comprado por {buyer_id}")
                            # Bajamos el stock
                            if producto.stock > 0:
                                producto.stock -= 1
                                producto.save()
                        else:
                            print("AVISO: Esta venta ya había sido registrada anteriormente.")
            else:
                print(f"ERROR MP API: Status {response.status_code} - {response.text}")

        except Exception as e:
            print(f"CRITICAL ERROR IN WEBHOOK: {e}")
            
    return HttpResponse(status=200)












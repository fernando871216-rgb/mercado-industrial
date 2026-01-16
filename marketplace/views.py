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
from django.core.mail import send_mail
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
SDK = mercadopago.SDK("APP_USR-2885162849289081-010612-228b3049d19e3b756b95f319ee9d0011-40588817")

def generar_preferencia_pago(request, producto_id):
    producto = get_object_or_404(IndustrialProduct, id=producto_id)
    
    # 1. Recibimos el costo base del flete (ejemplo: 172.11)
    try:
        flete_bruto = float(request.GET.get('envio', 0))
    except (TypeError, ValueError):
        flete_bruto = 0

    # 2. CALCULAMOS TUS COMISIONES
    # Tu 8% sobre el flete
    ganancia_flete_initre = flete_bruto * 0.08
    flete_final_con_comision = flete_bruto + ganancia_flete_initre

    # Tu 5% sobre el precio del producto
    precio_base = float(producto.price)
    comision_prod = precio_base * 0.05
    
    # 3. UNIFICAMOS TODO (Subtotal)
    total_unificado = precio_base + comision_prod + flete_final_con_comision
    
    # 4. Sumamos comisión de Mercado Pago (aprox 4.5% para cubrir el costo del gateway)
    # Así el cliente paga la comisión y tú recibes tus ganancias íntegras
    total_pagar_final = round(total_unificado / (1 - 0.045), 2)

    # 5. CONFIGURACIÓN DE MERCADO PAGO
    sdk = mercadopago.SDK("APP_USR-2885162849289081-010612-228b3049d19e3b756b95f319ee9d0011-40588817") # Asegúrate de usar tu Access Token real

    preference_data = {
        "items": [
            {
                "title": f"{producto.title} (Incluye gestión y flete)",
                "quantity": 1,
                "unit_price": total_pagar_final,
                "currency_id": "MXN",
            }
        ],
        "back_urls": {
            "success": request.build_absolute_uri(f'/pago-exitoso/{product.id}/'),
            "failure": request.build_absolute_uri('/pago-fallido/'),
            "pending": request.build_absolute_uri('/pago-pendiente/'),
        },
        "auto_return": "approved",
        "binary_mode": True, # Para que sea aprobado o rechazado de inmediato
    }

    preference_response = sdk.preference().create(preference_data)
    preference = preference_response["response"]

    # 6. RESPUESTA AL JAVASCRIPT
    return JsonResponse({
        'preference_id': preference["id"],
        'total_final': f"{total_pagar_final:,.2f}" # Formateado con comas para el HTML
    })
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
    # Aquí definimos 'product'
    product = get_object_or_404(IndustrialProduct, id=product_id)
    
    # ID del usuario para el external_reference
    user_id = request.user.id if request.user.is_authenticated else 0
    
    pref_data = {
        "items": [{
            "id": str(product.id), 
            "title": product.title, 
            "quantity": 1, 
            "unit_price": float(product.price), 
            "currency_id": "MXN"
        }],
        # CORRECCIÓN: Usamos product.id (antes decía producto.id)
        "external_reference": f"{product.id}-{user_id}",
    }
    
    try:
        pref = SDK.preference().create(pref_data)
        preference_id = pref["response"]["id"]
    except Exception as e:
        print(f"Error Mercado Pago: {e}")
        preference_id = None

    return render(request, 'marketplace/product_detail.html', {
        'product': product, 
        'preference_id': preference_id,
        'public_key': "APP_USR-bab958ea-ede4-49f7-b072-1fd682f9e1b9"
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

def procesar_pago(request, producto_id):
    producto = get_object_or_404(IndustrialProduct, id=producto_id)
    return render(request, 'marketplace/pago.html', {'producto': producto})

        
@login_required
def crear_intencion_compra(request, product_id):
    p = get_object_or_404(IndustrialProduct, id=product_id)
    Sale.objects.create(product=p, buyer=request.user, price=p.price, status='pendiente')
    return redirect('mis_compras')

@login_required
def panel_administrador(request):
    # Verificamos que sea staff o superusuario
    if not request.user.is_staff:
        return redirect('home')

    # 1. Traemos las ventas (SOLO los campos que existen)
    # Usamos .only() para obligar a Django a ignorar campos que den error
    ventas = Sale.objects.select_related('product', 'buyer').all().order_by('-created_at')

    # 2. Cálculos para las gráficas/estadísticas
    total_ventas_count = ventas.count()
    ingresos_totales = sum(v.price for v in ventas)
    
    # 3. Datos para los últimos productos (opcional)
    productos_recientes = IndustrialProduct.objects.all().order_by('-created_at')[:5]

    context = {
        'ventas': ventas,
        'total_ventas_count': total_ventas_count,
        'ingresos_totales': ingresos_totales,
        'productos_recientes': productos_recientes,
    }
    
    return render(request, 'marketplace/panel_admin.html', context)

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

def pago_exitoso(request, producto_id):
    producto = get_object_or_404(IndustrialProduct, id=producto_id)
    return render(request, 'marketplace/pago_exitoso.html', {'producto': producto})
    
    # Mercado Pago manda el estado en la URL como ?status=approved
    status_mp = request.GET.get('collection_status') or request.GET.get('status')
    
    # 1. Primero revisamos si el status que viene en la URL es aprobado
    # 2. Por si acaso, también revisamos si ya existe una venta registrada en nuestra base de datos
    venta_confirmada = Sale.objects.filter(product=producto, buyer=request.user, status='approved').exists()
    
    mostrar_contacto = False
    if status_mp == 'approved' or venta_confirmada:
        mostrar_contacto = True
        
    return render(request, 'marketplace/pago_exitoso.html', {
        'producto': producto,
        'mostrar_contacto': mostrar_contacto
    })


def pago_fallido(request): return render(request, 'marketplace/pago_fallido.html')
    
@csrf_exempt
def mercadopago_webhook(request):
    payment_id = request.GET.get('id') or request.GET.get('data.id')
    access_token = "APP_USR-2885162849289081-010612-228b3049d19e3b756b95f319ee9d0011-40588817"

    if payment_id:
        url = f"https://api.mercadopago.com/v1/payments/{payment_id}"
        headers = {'Authorization': f'Bearer {access_token.strip()}'}
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                
                if data.get('status') == 'approved':
                    ref_data = str(data.get('external_reference', ''))
                    parts = ref_data.strip().split('-')
                    
                    if len(parts) >= 2:
                        producto_id = parts[0]
                        comprador_id = parts[1]
                        
                        producto = IndustrialProduct.objects.get(id=producto_id)
                        comprador = User.objects.get(id=comprador_id)
                        monto = Decimal(str(data.get('transaction_amount')))
                        
                        # BLOQUEO DE DUPLICADOS: Evita crear 2 ventas en el mismo minuto
                        hace_un_minuto = timezone.now() - timedelta(seconds=60)
                        venta_reciente = Sale.objects.filter(
                            product=producto, 
                            buyer=comprador, 
                            created_at__gte=hace_un_minuto
                        ).exists()

                        if not venta_reciente:
                            Sale.objects.create(
                                product=producto,
                                buyer=comprador,
                                price=monto,
                                status='approved'
                            )
                            # Descontamos stock
                            if producto.stock > 0:
                                producto.stock -= 1
                                producto.save()
                            print(f"VENTA EXITOSA: Producto {producto_id} para usuario {comprador_id}")
                        else:
                            print("AVISO: Notificación duplicada detectada, no se crea otra venta.")
            
        except Exception as e:
            print(f"Error en webhook: {e}")

    return HttpResponse(status=200)

# 4. Pantalla de Éxito
def pago_exitoso(request, producto_id):
    producto = get_object_or_404(IndustrialProduct, id=producto_id)
    return render(request, 'marketplace/pago_exitoso.html', {'producto': producto})





























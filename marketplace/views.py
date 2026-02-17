import requests
import urllib3
import json
import mercadopago
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse, FileResponse, Http404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
import os
import time
from django.db.models import Q, Sum
from django.views.decorators.csrf import csrf_exempt
from .models import IndustrialProduct, Category, Sale, Profile
from .forms import ProductForm, RegistroForm, ProfileForm, UserUpdateForm
from django.contrib.auth.models import User
from django.core.mail import send_mail
from .utils import enviar_notificacion_venta
from django.conf import settings
from django.contrib.staticfiles import finders
import socket


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# CONFIGURACIÓN GLOBAL
MP_ACCESS_TOKEN = "APP_USR-2885162849289081-010612-228b3049d19e3b756b95f319ee9d0011-40588817"
SDK = mercadopago.SDK(MP_ACCESS_TOKEN)

# --- UTILIDADES ---
def descargar_apk(request):
    ruta = finders.find('app_initre.apk') or os.path.join(settings.BASE_DIR, 'static', 'app_initre.apk')
    if os.path.exists(ruta): return FileResponse(open(ruta, 'rb'), content_type='application/vnd.android.package-archive')
    raise Http404

def descargar_ficha(request, product_id):
    p = get_object_or_404(IndustrialProduct, id=product_id)
    if not p.ficha_tecnica: raise Http404
    return FileResponse(p.ficha_tecnica.open(), content_type='application/pdf')

# --- MERCADO PAGO Y WEBHOOK ---
@login_required
def generar_preferencia_pago(request, producto_id):
    producto = get_object_or_404(IndustrialProduct, id=producto_id)
    try:
        flete = float(request.GET.get('envio', 0))
        cp = request.GET.get('cp') or '00000'
    except: flete, cp = 0, '00000'
    flete_final = round(flete * 1.08, 2)
    total = round(float(producto.price) + flete_final, 2)
    pref_data = {
        "items": [{"title": producto.title, "quantity": 1, "unit_price": total, "currency_id": "MXN"}],
        "external_reference": f"{producto.id}-{request.user.id}-{flete_final}-{cp}",
        "back_urls": {"success": request.build_absolute_uri(f'/pago-exitoso/{producto.id}/?envio={flete_final}&cp={cp}'),
                      "failure": request.build_absolute_uri('/pago-fallido/'), "pending": request.build_absolute_uri('/pago-pendiente/')},
        "auto_return": "approved", "binary_mode": True,
    }
    return JsonResponse({'preference_id': SDK.preference().create(pref_data)["response"]["id"], 'total_final': f"{total:,.2f}"})

@csrf_exempt
def mercadopago_webhook(request):
    payment_id = request.GET.get('id') or request.GET.get('data.id')
    if payment_id:
        headers = {'Authorization': f'Bearer {MP_ACCESS_TOKEN}'}
        res = requests.get(f"https://api.mercadopago.com/v1/payments/{payment_id}", headers=headers)
        if res.status_code == 200:
            data = res.json()
            if data.get('status') == 'approved':
                parts = str(data.get('external_reference', '')).split('-')
                if len(parts) >= 2:
                    flete = Decimal(parts[2]) if len(parts) > 2 else Decimal('0')
                    cp = parts[3] if len(parts) > 3 else "00000"
                    try:
                        prod = IndustrialProduct.objects.get(id=parts[0])
                        user = User.objects.get(id=parts[1])
                        ganancia = (Decimal(str(prod.price)) * Decimal('0.05') + flete * Decimal('0.074')).quantize(Decimal('0.01'))
                        venta, created = Sale.objects.update_or_create(
                            payment_id=payment_id,
                            defaults={'product':prod, 'buyer':user, 'price':Decimal(str(data.get('transaction_amount'))),
                                     'shipping_cost':flete, 'shipping_cp':cp, 'status':'approved', 'ganancia_neta':ganancia}
                        )
                        if created:
                            prod.stock -= 1; prod.save()
                            try: enviar_notificacion_venta(venta)
                            except: pass
                    except: pass
    return HttpResponse(status=200)

# --- VISTAS DE USUARIO ---
def home(request):
    q = request.GET.get('q')
    products = IndustrialProduct.objects.filter(Q(title__icontains=q)|Q(part_number__icontains=q)|Q(brand__icontains=q)) if q else IndustrialProduct.objects.all()
    
    # Verificamos perfil incompleto si está logueado
    perfil_incompleto = False
    if request.user.is_authenticated:
        p = request.user.profile
        if not p.phone or not p.clabe or not p.address:
            perfil_incompleto = True
            
    return render(request, 'marketplace/home.html', {
        'products': products, 
        'perfil_incompleto': perfil_incompleto
    })

def detalle_producto(request, product_id):
    p = get_object_or_404(IndustrialProduct, id=product_id)
    u_id = request.user.id if request.user.is_authenticated else 0
    pref_data = {"items": [{"title": p.title, "quantity": 1, "unit_price": float(p.price), "currency_id": "MXN"}],
                 "external_reference": f"{p.id}-{u_id}-0-00000"}
    pref_id = SDK.preference().create(pref_data)["response"]["id"]
    return render(request, 'marketplace/product_detail.html', {'product': p, 'preference_id': pref_id, 'public_key': "APP_USR-bab958ea-ede4-49f7-b072-1fd682f9e1b9"})

# --- INVENTARIO ---
@login_required
def mi_inventario(request): return render(request, 'marketplace/mi_inventario.html', {'products': IndustrialProduct.objects.filter(user=request.user)})

@login_required
def subir_producto(request):
    form = ProductForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        p = form.save(commit=False); p.user = request.user; p.save()
        return redirect('mi_inventario')
    return render(request, 'marketplace/subir_producto.html', {'form': form})

@login_required
def editar_producto(request, pk):
    p = get_object_or_404(IndustrialProduct, pk=pk, user=request.user)
    form = ProductForm(request.POST or None, request.FILES or None, instance=p)
    if form.is_valid(): form.save(); return redirect('mi_inventario')
    return render(request, 'marketplace/editar_producto.html', {'form': form, 'producto': p})

@login_required
def borrar_producto(request, pk):
    get_object_or_404(IndustrialProduct, pk=pk, user=request.user).delete()
    return redirect('mi_inventario')

# --- COMPRAS Y VENTAS ---
@login_required
def mis_ventas(request):
    # Traemos las ventas del vendedor actual
    ventas = Sale.objects.filter(product__user=request.user).order_by('-created_at')
    
    for v in ventas:
        # Usamos el método del modelo que ya tiene los "seguros" contra valores nulos
        # Esto asegura que v.monto_limpio_vendedor SIEMPRE tenga un valor
        v.monto_limpio_vendedor = v.get_net_amount()
        
    return render(request, 'marketplace/mis_ventas.html', {'ventas': ventas})

@login_required
def mis_compras(request):
    compras = Sale.objects.filter(buyer=request.user).order_by('-created_at')
    return render(request, 'marketplace/mis_compras.html', {'compras': compras})

@login_required
def pago_exitoso(request, producto_id):
    producto = get_object_or_404(IndustrialProduct, id=producto_id)
    return render(request, 'marketplace/pago_exitoso.html', {'producto': producto, 'mostrar_contacto': True})

def pago_fallido(request): return render(request, 'marketplace/pago_fallido.html')

# --- ESTADOS DE VENTA ---
@login_required
def cambiar_estado_venta(request, venta_id):
    v = get_object_or_404(Sale, id=venta_id, product__user=request.user)
    if v.status == 'approved': v.status = 'completado'; v.save()
    return redirect('mis_ventas')

@login_required
def cancelar_venta(request, venta_id):
    v = get_object_or_404(Sale, id=venta_id, product__user=request.user)
    v.status = 'cancelado'; v.save()
    return redirect('mis_ventas')

@login_required
def confirmar_recepcion(request, venta_id):
    v = get_object_or_404(Sale, id=venta_id, buyer=request.user)
    
    # Marcamos ambos campos para que el botón desaparezca en el HTML
    v.status = 'entregado'
    v.recibido_por_comprador = True 
    v.save()
    
    # Enviamos correo al vendedor avisando que ya se entregó
    try:
        subject = f"📦 ¡Equipo entregado!: {v.product.title}"
        message = (
            f"Hola {v.product.user.username},\n\n"
            f"El comprador ha confirmado la recepción del equipo: {v.product.title}.\n\n"
            f"Tu pago de ${v.get_net_amount()} ha entrado en proceso de liquidación. "
            f"El administrador lo transferirá a tu CLABE registrada a la brevedad.\n\n"
            f"¡Gracias por confiar en INITRE!"
        )
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [v.product.user.email])
    except:
        pass # Para que la página no falle si el correo tiene problemas
        
    return redirect('mis_compras')

@login_required
def crear_intencion_compra(request, product_id):
    p = get_object_or_404(IndustrialProduct, id=product_id)
    Sale.objects.create(product=p, buyer=request.user, price=p.price, status='pendiente')
    return redirect('mis_compras')

@login_required
def actualizar_guia(request, venta_id):
    v = get_object_or_404(Sale, id=venta_id, product__user=request.user)
    if request.method == 'POST':
        v.shipping_company, v.tracking_number, v.status = request.POST.get('shipping_company'), request.POST.get('tracking_number'), 'enviado'
        v.save()
        try: send_mail("🚀 Pedido enviado", f"Tu equipo va en camino. Guía: {v.tracking_number}", settings.DEFAULT_FROM_EMAIL, [v.buyer.email])
        except: pass
    return redirect('mis_ventas')

# --- PANEL ADMINISTRADOR (Faltaba sincronizar con URLs) ---
@login_required
def panel_administrador(request):
    if not request.user.is_staff: return redirect('home')
    ventas = Sale.objects.all().order_by('-created_at')
    ingresos = Sale.objects.filter(status__in=['approved','enviado','entregado']).aggregate(total=Sum('ganancia_neta'))['total'] or 0
    return render(request, 'marketplace/panel_admin.html', {'ventas': ventas, 'ingresos_totales': ingresos})

@login_required
def marcar_como_pagado(request, venta_id):
    if request.user.is_staff:
        # 1. Buscamos la venta
        v = get_object_or_404(Sale, id=venta_id)
        
        # 2. Marcamos como pagado en la base de datos
        v.pagado_a_vendedor = True
        v.save()
        
        # 3. ENVIAMOS EL EMAIL DE NOTIFICACIÓN AL VENDEDOR
        try:
            monto_neto = v.get_net_amount()
            subject = f"💰 ¡Pago enviado!: {v.product.title}"
            
            # Mensaje detallado para el vendedor
            message = (
                f"Hola {v.product.user.username},\n\n"
                f"Te informamos que el administrador de INITRE ha marcado tu venta como LIQUIDADA.\n\n"
                f"DETALLES DEL DEPÓSITO:\n"
                f"--------------------------\n"
                f"Equipo: {v.product.title}\n"
                f"Monto Neto transferido: ${monto_neto} MXN\n"
                f"Cuenta destino: CLABE registrada en tu perfil.\n"
                f"--------------------------\n\n"
                f"El tiempo en que se refleja el saldo depende de tu institución bancaria.\n\n"
                f"¡Gracias por vender en Mercado Industrial INITRE!"
            )
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [v.product.user.email],
                fail_silently=False,
            )
        except Exception as e:
            # Si el correo falla, imprimimos el error en los logs pero no bloqueamos la página
            print(f"Error enviando correo de liquidación: {e}")
            
    return redirect('panel_administrador')

# --- OTROS ---
def registro(request):
    form = RegistroForm(request.POST or None)
    if form.is_valid(): form.save(); return redirect('login')
    return render(request, 'marketplace/registro.html', {'form': form})

@login_required
def editar_perfil(request):
    prof, _ = Profile.objects.get_or_create(user=request.user)
    u, p = UserUpdateForm(request.POST or None, instance=request.user), ProfileForm(request.POST or None, instance=prof)
    if u.is_valid() and p.is_valid(): u.save(); p.save(); return redirect('editar_perfil')
    return render(request, 'marketplace/editar_perfil.html', {'u_form': u, 'p_form': p})

        
def obtener_token_soloenvios():
    client_id = os.getenv('SOLOENVIOS_CLIENT_ID')
    client_secret = os.getenv('SOLOENVIOS_CLIENT_SECRET')
    
    url = "https://app.soloenvios.com/api/v1/oauth/token"
    
    # Según la documentación, a veces prefieren los datos así para OAuth
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials"
    }
    
    try:
        # Intentamos primero con data= (form-encoded) que es el estándar de OAuth2
        res = requests.post(url, data=payload, timeout=15)
        
        # Si no funciona con data, intentamos con json
        if res.status_code != 200:
            res = requests.post(url, json=payload, timeout=15)
            
        if res.status_code == 200:
            return res.json().get('access_token')
            
        # IMPORTANTE: Esto imprimirá el error real en tu log de Render
        print(f"FALLO AUTENTICACION: {res.status_code} - {res.text}")
        return None
    except Exception as e:
        print(f"ERROR EXCEPCION: {str(e)}")
        return None

def cotizar_soloenvios(request):
    product_id = request.GET.get('product_id')
    cp_destino = str(request.GET.get('cp_destino', '')).strip().zfill(5)
    
    token = obtener_token_soloenvios()
    if not token:
        return JsonResponse({'tarifas': [], 'error': 'Error de autenticación'})

    try:
        producto = get_object_or_404(IndustrialProduct, id=product_id)
        
        url_cot = "https://app.soloenvios.com/api/v1/quotations"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        payload = {
            "address_from": {
                "country_code": "MX", 
                "postal_code": str(producto.cp_origen).zfill(5)
            },
            "address_to": {
                "country_code": "MX", 
                "postal_code": cp_destino
            },
            "parcels": [{
                "length": int(producto.largo or 20),
                "width": int(producto.ancho or 20),
                "height": int(producto.alto or 20),
                "weight": int(producto.peso or 1)
            }]
        }
        
        res = requests.post(url_cot, json=payload, headers=headers, timeout=20)
        
        if res.status_code in [200, 201]:
            data = res.json()
            tarifas = []
            # Procesamos las tarifas que vienen de SoloEnvíos
            for t in data.get('rates', []):
                monto = t.get('total')
                if monto:
                    tarifas.append({
                        'paqueteria': f"{t.get('provider_display_name')} ({t.get('provider_service_name')})",
                        'precio_final': round(float(monto) * 1.08, 2),
                        'tiempo': f"{t.get('days')} días" if t.get('days') else "N/A"
                    })
            return JsonResponse({'tarifas': sorted(tarifas, key=lambda x: x['precio_final'])})
        
        return JsonResponse({'tarifas': [], 'error': f'API Error: {res.status_code}'})

    except Exception as e:
        return JsonResponse({'tarifas': [], 'error': 'Error de conexión'})
    
def category_detail(request, category_id):
    cat = get_object_or_404(Category, id=category_id)
    return render(request, 'marketplace/home.html', {'products': IndustrialProduct.objects.filter(category=cat), 'category': cat})
    
def como_funciona(request): return render(request, 'marketplace/como_funciona.html')
def privacidad(request): return render(request, 'marketplace/privacidad.html')
def procesar_pago(request, producto_id): return render(request, 'marketplace/pago.html', {'producto': get_object_or_404(IndustrialProduct, id=producto_id)})































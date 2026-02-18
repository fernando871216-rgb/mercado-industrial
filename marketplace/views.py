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
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# CONFIGURACIÓN GLOBAL
MP_ACCESS_TOKEN = os.environ.get("MP_ACCESS_TOKEN", "TOKEN_NO_CONFIGURADO")
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
        flete_recibido = float(request.GET.get('envio', 0))
        cp = request.GET.get('cp_destino') or '00000'
    except (TypeError, ValueError):
        flete_recibido, cp = 0, '00000'

    total_con_flete = round(float(producto.price) + flete_recibido, 2)
    titulo = f"{producto.title} (Envío a CP {cp})" if flete_recibido > 0 else producto.title

    pref_data = {
        "items": [{
            "id": str(producto.id),
            "title": titulo,
            "quantity": 1,
            "unit_price": total_con_flete,
            "currency_id": "MXN"
        }],
        "external_reference": f"PROD:{producto.id}-USER:{request.user.id}-FLETE:{flete_recibido}-CP:{cp}",
        "back_urls": {
            "success": request.build_absolute_uri(f'/pago-exitoso/{producto.id}/'),
            "failure": request.build_absolute_uri('/pago-fallido/'),
            "pending": request.build_absolute_uri('/pago-pendiente/'),
        },
        "auto_return": "approved", # Obliga a volver al sitio
        "binary_mode": True,       # Evita pagos "pendientes", o es éxito o es falla
        "notification_url": request.build_absolute_uri('/webhook/mercadopago/'),
    }
    
    res_mp = SDK.preference().create(pref_data)
    return JsonResponse({
        'preference_id': res_mp["response"]["id"], 
        'total_final': f"{total_con_flete:,.2f}"
    })


@csrf_exempt
def mercadopago_webhook(request):
    payment_id = request.GET.get('id') or request.GET.get('data.id')
    if payment_id:
        headers = {'Authorization': f'Bearer {MP_ACCESS_TOKEN}'}
        res = requests.get(f"https://api.mercadopago.com/v1/payments/{payment_id}", headers=headers)
        
        if res.status_code == 200:
            data = res.json()
            if data.get('status') == 'approved':
                ext_ref = str(data.get('external_reference', ''))
                parts = ext_ref.split('-')
                
                # Diccionario para extraer datos limpios (PROD, USER, FLETE, CP)
                ref_data = {}
                for part in parts:
                    if ':' in part:
                        key, value = part.split(':', 1)
                        ref_data[key.upper()] = value

                try:
                    # Extraer y limpiar valores
                    p_id = ref_data.get('PROD')
                    u_id = ref_data.get('USER')
                    flete_str = ref_data.get('FLETE', '0')
                    cp = ref_data.get('CP', '00000')

                    # Conversión segura a Decimal
                    try:
                        flete = Decimal(flete_str)
                    except:
                        flete = Decimal('0')

                    if p_id and u_id:
                        prod = IndustrialProduct.objects.get(id=p_id)
                        user = User.objects.get(id=u_id)
                        
                        # Cálculo de ganancia
                        precio_prod = Decimal(str(prod.price))
                        ganancia = (precio_prod * Decimal('0.05') + flete * Decimal('0.074')).quantize(Decimal('0.01'))
                        
                        total_pagado = Decimal(str(data.get('transaction_amount', '0')))

                        venta, created = Sale.objects.update_or_create(
                            payment_id=payment_id,
                            defaults={
                                'product': prod, 
                                'buyer': user, 
                                'price': total_pagado,
                                'shipping_cost': flete, 
                                'shipping_cp': cp, 
                                'status': 'approved', 
                                'ganancia_neta': ganancia
                            }
                        )
                        
                        if created:
                            # Descontar stock solo si es nueva la venta en nuestra DB
                            if prod.stock > 0:
                                prod.stock -= 1
                                prod.save()
                            
                            try: 
                                enviar_notificacion_venta(venta)
                            except: 
                                pass
                                
                except Exception as e:
                    # Log del error para depuración si algo más falla
                    print(f"Error procesando webhook: {e}")
                    pass

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
@login_required
def detalle_producto(request, product_id):
    p = get_object_or_404(IndustrialProduct, id=product_id)
    u = request.user
    
    # 1. Validación usando los nombres de tu Models.py: phone, address, clabe
    try:
        # Usamos la relación OneToOne (user.profile)
        perfil = u.profile
        # Verificamos que los campos tengan contenido
        tiene_datos = all([
            perfil.phone,    
            perfil.address,
            u.first_name,
            u.last_name
            
        ])
        perfil_incompleto = not tiene_datos
    except Exception as e:
        # Si el usuario no tiene perfil creado aún, marcar como incompleto
        print(f"Error validando perfil: {e}")
        perfil_incompleto = True

    # 2. Generar la preferencia de Mercado Pago
    pref_data = {
        "items": [{"title": p.title, "quantity": 1, "unit_price": float(p.price), "currency_id": "MXN"}],
        "external_reference": f"PROD:{p.id}-USER:{u.id}-FLETE:0-CP:00000",
        "binary_mode": True,
    }
    
    try:
        pref_id = SDK.preference().create(pref_data)["response"]["id"]
    except:
        pref_id = None

    context = {
        'product': p,
        'preference_id': pref_id,
        'public_key': "APP_USR-bab958ea-ede4-49f7-b072-1fd682f9e1b9",
        'perfil_incompleto': perfil_incompleto
    }
    return render(request, 'marketplace/product_detail.html', context)
    
# --- INVENTARIO ---
@login_required
def mi_inventario(request): return render(request, 'marketplace/mi_inventario.html', {'products': IndustrialProduct.objects.filter(user=request.user)})

@login_required
def subir_producto(request):
    # Verificamos si tiene la CLABE para poder pagarle sus futuras ventas
    try:
        perfil = request.user.profile
        if not perfil.clabe:
            messages.warning(
                request, 
                "Nota: No has configurado tu CLABE interbancaria. "
                "Podrás subir productos, pero la necesitarás para recibir tus pagos."
            )
    except Exception:
        pass

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            p = form.save(commit=False)
            p.user = request.user
            p.save()
            messages.success(request, "Producto publicado con éxito.")
            return redirect('mi_inventario')
    else:
        form = ProductForm()
        
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
    
    # Capturamos el ID de pago que envía Mercado Pago en la URL por si quieres mostrarlo
    payment_id = request.GET.get('payment_id') or request.GET.get('collection_id')
    
    contexto = {
        'producto': producto, 
        'mostrar_contacto': True,
        'payment_id': payment_id  # Esto llenará el campo "Transacción" en tu HTML
    }
    
    return render(request, 'marketplace/pago_exitoso.html', contexto)


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
# En views.py
def actualizar_guia(request, venta_id):
    if request.method == 'POST':
        venta = get_object_or_404(Sale, id=venta_id, product__user=request.user)
        guia = request.POST.get('tracking_number')
        paqueteria = request.POST.get('shipping_company')
        
        venta.tracking_number = guia
        venta.shipping_company = paqueteria
        venta.status = 'shipped' # Cambiamos el estatus a enviado
        venta.save()
        
        # --- ESTO ES LO QUE FALTA: DISPARAR EL CORREO ---
        try:
            enviar_correo_guia(venta)
            print(f"DEBUG: Correo de guía para venta {venta.id} enviado.")
        except Exception as e:
            print(f"DEBUG: Error enviando correo de guía: {e}")
            
        return redirect('mis_ventas')

def enviar_correo_guia(venta):
    asunto = f"¡Tu pedido de {venta.product.title} va en camino!"
    email_comprador = venta.buyer.email
    
    contexto = {
        'comprador': venta.buyer.first_name or venta.buyer.username,
        'producto': venta.product.title,
        'guia': venta.tracking_number,
        'paqueteria': venta.shipping_company,
    }
    
    html_content = render_to_string('emails/guia_enviada.html', contexto)
    
    msg = EmailMultiAlternatives(asunto, f"Tu guía es: {venta.tracking_number}", 'EMAIL_HOST_USER', [email_comprador])
    msg.attach_alternative(html_content, "text/html")
    msg.send()
    
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
    if not token or "ERROR" in str(token):
        return JsonResponse({'tarifas': [], 'error': 'Error de autenticación'})

    try:
        producto = get_object_or_404(IndustrialProduct, id=product_id)
        url_cot = "https://app.soloenvios.com/api/v1/quotations"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "quotation": {
                "address_from": {
                    "country_code": "MX",
                    "postal_code": str(producto.cp_origen).strip().zfill(5),
                    "area_level1": "Puebla",
                    "area_level2": "Puebla",
                    "area_level3": "Centro"
                },
                "address_to": {
                    "country_code": "MX",
                    "postal_code": cp_destino,
                    "area_level1": "Ciudad de Mexico", 
                    "area_level2": "Cuauhtemoc",
                    "area_level3": "Juarez"
                },
                "parcels": [{
                    "length": int(float(producto.largo or 20)),
                    "width": int(float(producto.ancho or 20)),
                    "height": int(float(producto.alto or 20)),
                    "weight": int(float(producto.peso or 1)),
                    "quantity": 1,
                    "mass_unit": "kg",
                    "distance_unit": "cm"
                }]
            }
        }

        for intento in range(3):
            res = requests.post(url_cot, json=payload, headers=headers, timeout=30)
            data = res.json() if res.status_code in [200, 201] else {}
            rates = data.get('rates', [])
            
            if rates:
                tarifas = []
                for t in rates:
                    monto = t.get('total')
                    if monto:
                        # --- NUEVA LÓGICA DE DETALLE ---
                        # Detectamos si es recolección a domicilio o entrega en sucursal
                        tiene_recoleccion = t.get('pick_up', False)
                        tipo_entrega = t.get('delivery_type', 'home_delivery') # home_delivery o station_delivery
                        
                        txt_recoleccion = "Recolección incluida" if tiene_recoleccion else "Dejar en sucursal"
                        txt_entrega = "Entrega a domicilio" if tipo_entrega == 'home_delivery' else "Recoger en sucursal (Ocurre)"
                        
                        tarifas.append({
                            'paqueteria': f"{t.get('provider_display_name')} ({t.get('provider_service_name')})",
                            'precio_final': round(float(monto) * 1.08, 2),
                            'tiempo': f"{t.get('days')} días" if t.get('days') else "N/A",
                            # Enviamos el detalle combinado para el frontend
                            'detalle_servicio': f"{txt_recoleccion} | {txt_entrega}"
                        })
                return JsonResponse({'tarifas': sorted(tarifas, key=lambda x: x['precio_final'])})
            
            if intento < 2:
                time.sleep(1.5 + intento)
                if intento == 0:
                    headers["Authorization"] = f"Bearer {obtener_token_soloenvios()}"

        return JsonResponse({'tarifas': [], 'error': 'No hay cobertura o la paquetería está tardando en responder.'})

    except Exception as e:
        return JsonResponse({'tarifas': [], 'error': f'Error de sistema: {str(e)}'})
    
def category_detail(request, category_id):
    cat = get_object_or_404(Category, id=category_id)
    return render(request, 'marketplace/home.html', {'products': IndustrialProduct.objects.filter(category=cat), 'category': cat})
    
def como_funciona(request): return render(request, 'marketplace/como_funciona.html')
def privacidad(request): return render(request, 'marketplace/privacidad.html')
def procesar_pago(request, producto_id): return render(request, 'marketplace/pago.html', {'producto': get_object_or_404(IndustrialProduct, id=producto_id)})































































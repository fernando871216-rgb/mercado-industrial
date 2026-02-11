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
from .models import Sale
import time
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from .models import IndustrialProduct, Category, Sale, Profile
from .forms import ProductForm, RegistroForm, ProfileForm, UserUpdateForm
from django.contrib.auth.models import User
from django.core.mail import send_mail
from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum
from .utils import enviar_notificacion_venta
from django.http import FileResponse
from django.conf import settings
from django.contrib.staticfiles import finders
from django.http import FileResponse, Http404

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
SDK = mercadopago.SDK("APP_USR-2885162849289081-010612-228b3049d19e3b756b95f319ee9d0011-40588817")

def descargar_apk(request):
    # Buscamos el archivo en las carpetas estáticas configuradas
    # Solo ponemos el nombre del archivo si está en la raíz de static
    nombre_archivo = 'app_initre.apk'
    ruta_apk = finders.find(nombre_archivo)

    if not ruta_apk:
        # Si no lo encuentra con finders, intentamos ruta manual relativa
        # Ajusta esto si tu archivo está dentro de una subcarpeta como static/app/
        from django.conf import settings
        ruta_apk = os.path.join(settings.BASE_DIR, 'static', nombre_archivo)

    if os.path.exists(ruta_apk):
        response = FileResponse(open(ruta_apk, 'rb'), content_type='application/vnd.android.package-archive')
        response['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'
        return response
    else:
        # Si después de todo no existe, lanzamos un 404 controlado en lugar de un Error 500
        raise Http404("El archivo APK no se encuentra en el servidor. Verifica que fue subido a la carpeta static.")

@login_required
def generar_preferencia_pago(request, producto_id):
    producto = get_object_or_404(IndustrialProduct, id=producto_id)
    
    try:
        flete_bruto = float(request.GET.get('envio', 0))
        cp_destino = request.GET.get('cp_destino') or request.GET.get('cp') or '00000'
    except (TypeError, ValueError):
        flete_bruto = 0
        cp_destino = '00000'

    flete_final_con_comision = flete_bruto * 1.08
    precio_base = float(producto.price)
    total_pagar_final = round(precio_base + flete_final_con_comision, 2)

    sdk = mercadopago.SDK("APP_USR-2885162849289081-010612-228b3049d19e3b756b95f319ee9d0011-40588817")

    preference_data = {
        "items": [
            {
                "title": f"{producto.title} (Incluye flete a CP {cp_destino})",
                "quantity": 1,
                "unit_price": total_pagar_final,
                "currency_id": "MXN",
            }
        ],
        # Guardamos: ID Producto - ID Comprador - Monto Flete - CP Destino
        "external_reference": f"{producto.id}-{request.user.id}-{flete_final_con_comision}-{cp_destino}",
        
        "back_urls": {
            # Agregamos &cp={cp_destino} al final de la URL de éxito
            "success": request.build_absolute_uri(f'/pago-exitoso/{producto.id}/?envio={flete_final_con_comision}&cp={cp_destino}'),
            "failure": request.build_absolute_uri('/pago-fallido/'),
            "pending": request.build_absolute_uri('/pago-pendiente/'),
        },
        "auto_return": "approved",
        "binary_mode": True,
    }

    preference_response = sdk.preference().create(preference_data)
    preference = preference_response["response"]

    return JsonResponse({
        'preference_id': preference["id"],
        'total_final': f"{total_pagar_final:,.2f}"
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
    product_id = request.GET.get('product_id')
    
    try:
        producto = get_object_or_404(IndustrialProduct, id=product_id)
        cp_origen = str(producto.cp_origen).strip().zfill(5)
        # Convertimos a float desde el inicio para evitar errores de JSON
        peso_db = float(producto.peso or 1)
        largo_db = float(producto.largo or 20)
        ancho_db = float(producto.ancho or 20)
        alto_db = float(producto.alto or 20)
    except Exception as e:
        print(f"Error cargando producto: {e}")
        cp_origen = "72460"
        peso_db, largo_db, ancho_db, alto_db = 1.0, 20.0, 20.0, 20.0

    cp_destino = str(request.GET.get('cp_destino', '')).strip().zfill(5)
    
    token = obtener_token_soloenvios()
    if "ERROR" in str(token):
        return JsonResponse({'tarifas': [], 'error': f'Fallo de Token: {token}'})

    try:
        def limpiar_valor_float(val, default_val):
            try:
                if val is None or val == '': return float(default_val)
                num = float(val)
                return num if num > 0 else float(default_val)
            except:
                return float(default_val)

        # Aseguramos que todos sean float antes de entrar al JSON
        peso = limpiar_valor_float(request.GET.get('peso'), peso_db)
        largo = limpiar_valor_float(request.GET.get('largo'), largo_db)
        ancho = limpiar_valor_float(request.GET.get('ancho'), ancho_db)
        alto = limpiar_valor_float(request.GET.get('alto'), alto_db)

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
                    "length": largo, 
                    "width": ancho, 
                    "height": alto, 
                    "weight": peso,
                    "package_protected": False, 
                    "declared_value": 100
                }]
            }
        }
        
        # Enviamos la petición
        res = requests.post(url, json=payload, headers=headers, timeout=25, verify=False)
        
        if res.status_code in [200, 201]:
            data_id = res.json().get('id')
            time.sleep(2.5) # Pausa para que SoloEnvíos recoja las tarifas de las paqueterías
            
            res_final = requests.get(f"{url}/{data_id}", headers=headers, verify=False)
            data = res_final.json()
            
            tarifas = []
            for t in data.get('rates', []):
                monto_api = t.get('total')
                if monto_api and float(monto_api) > 0:
                    tarifas.append({
                        'paqueteria': f"{t.get('provider_display_name')} ({t.get('provider_service_name')})",
                        'precio_final': round(float(monto_api) * 1.08, 2), # Tu 8% de gestión
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
            Q(title__icontains=query) | Q(part_number__icontains=query)| 
            Q(brand__icontains=query)
    
        )
    else:
        products = IndustrialProduct.objects.all()
    if request.user.is_authenticated:
        profile = getattr(request.user, 'profile', None)
        if profile:
            # Verificamos si faltan campos clave
            if not profile.phone or not profile.address:
                messages.warning(request, "⚠️ Tu perfil está incompleto. Agrega tu teléfono y dirección para poder comprar o vender.")
    return render(request, 'marketplace/home.html', {'products': products})

def detalle_producto(request, product_id):
    product = get_object_or_404(IndustrialProduct, id=product_id)
    
    # --- VALIDACIÓN DE PERFIL INCOMPLETO ---
    perfil_incompleto = False
    if request.user.is_authenticated:
        profile = getattr(request.user, 'profile', None)
        if profile:
            # Si le falta teléfono O dirección, marcamos como incompleto
            if not profile.phone or not profile.address:
                perfil_incompleto = True
                messages.warning(request, "⚠️ Completa tu teléfono y dirección en tu perfil para poder comprar.")
    # ---------------------------------------

    user_id = request.user.id if request.user.is_authenticated else 0
    
    pref_data = {
        "items": [{
            "id": str(product.id), 
            "title": product.title, 
            "quantity": 1, 
            "unit_price": float(product.price), 
            "currency_id": "MXN"
        }],
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
        'public_key': "APP_USR-bab958ea-ede4-49f7-b072-1fd682f9e1b9",
        'perfil_incompleto': perfil_incompleto  # Enviamos la variable al HTML
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
    for v in ventas:
        precio_prod = Decimal(str(v.price)) - Decimal(str(v.shipping_cost))
        comision_initre = precio_prod * Decimal('0.05')
        
        # Comisión MP (3.49% + $4 + IVA)
        com_porc_prod = precio_prod * Decimal('0.0349')
        com_fija = Decimal('4.00')
        iva_prod = (com_porc_prod + com_fija) * Decimal('0.16')
        mp_solo_producto = com_porc_prod + com_fija + iva_prod
        v.monto_limpio_vendedor = precio_prod - comision_initre - mp_solo_producto
    
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
        print(f"DEBUG: Intentando enviar correo para la venta {venta_id}") # Verás esto en los logs de Render
        v = get_object_or_404(Sale, id=venta_id, product__user=request.user)
        
        v.shipping_company = request.POST.get('shipping_company')
        v.tracking_number = request.POST.get('tracking_number')
        v.status = 'enviado'
        v.save()

        subject = f"🚀 ¡Tu pedido de {v.product.title} va en camino!"
        message = (
            f"Hola {v.buyer.username},\n\n"
            f"El vendedor ha actualizado la información de envío.\n\n"
            f"Paquetería: {v.shipping_company}\n"
            f"Guía: {v.tracking_number}\n\n"
            f"¡Gracias por usar INITRE!"
        )
        
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [v.buyer.email],
                fail_silently=False,
            )
            print("DEBUG: Correo enviado exitosamente")
            messages.success(request, "Información actualizada y cliente notificado.")
        except Exception as e:
            print(f"DEBUG ERROR: {e}")
            messages.error(request, f"Error al enviar correo: {e}")
            
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
    if not request.user.is_staff:
        return redirect('home')

    estados_validos = ['approved', 'enviado', 'entregado']
    
    # 1. Ventas para estadísticas (cuadros superiores)
    ventas_stats = Sale.objects.filter(status__in=estados_validos)
    total_ventas_count = ventas_stats.count()
    
    # 2. Ganancias totales (INITRE) acumuladas en base de datos
    resultado_ganancia = ventas_stats.aggregate(total=Sum('ganancia_neta'))
    ingresos_totales = resultado_ganancia['total'] or 0

    # 3. Traemos todas las ventas para la tabla
    ventas_todas = Sale.objects.select_related('product__user__profile', 'buyer').all().order_by('-created_at')

    # NOTA: Ya no necesitamos el bucle "for venta in ventas_todas" aquí
    # porque los cálculos ahora los hace el modelo dinámicamente cuando el HTML los pide.

    productos_recientes = IndustrialProduct.objects.all().order_by('-created_at')[:5]

    context = {
        'ventas': ventas_todas,
        'total_ventas_count': total_ventas_count,
        'ingresos_totales': ingresos_totales,
        'productos_recientes': productos_recientes,
        'ventas_pendientes_pago': Sale.objects.filter(pagado_a_vendedor=False, status__in=estados_validos).count(),
    }
    
    return render(request, 'marketplace/panel_admin.html', context)

@login_required
def marcar_como_pagado(request, venta_id):
    if not request.user.is_staff:
        return redirect('home')

    if request.method == "POST":
        venta = get_object_or_404(Sale, id=venta_id)
        venta.pagado_a_vendedor = True
        venta.save()

        # --- LÓGICA DE PRECISIÓN CORREGIDA ---
        # 1. Calculamos el precio real del producto restando el flete del total pagado
        # Esto asegura que si el flete fue de $300, el cálculo sea sobre los $1000 restantes.
        total_pagado_mp = Decimal(str(venta.price))
        costo_envio = Decimal(str(venta.shipping_cost))
        precio_producto_neto = total_pagado_mp - costo_envio
        
        # 2. Tu Comisión de Plataforma (5% sobre el neto del producto)
        comision_initre = precio_producto_neto * Decimal('0.05')
        
        # 3. Comisión Mercado Pago sobre el PRODUCTO (3.49% + $4 + IVA)
        com_porc_prod = precio_producto_neto * Decimal('0.0349')
        com_fija = Decimal('4.00')
        iva_mp_prod = (com_porc_prod + com_fija) * Decimal('0.16')
        total_mp_producto = com_porc_prod + com_fija + iva_mp_prod
        
        # 4. MONTO FINAL PROMETIDO AL VENDEDOR ($1000 - $50 - $45.12 = $904.88)
        monto_vendedor_final = precio_producto_neto - comision_initre - total_mp_producto

        try:
            subject = f"✅ ¡Pago enviado! Tu venta en INITRE: {venta.product.title}"
            message = (
                f"Hola {venta.product.user.username},\n\n"
                f"Te informamos que hemos realizado la transferencia por tu venta '{venta.product.title}'.\n\n"
                f"DETALLE DE LA LIQUIDACIÓN (Solo Producto):\n"
                f"------------------------------------------\n"
                f"Precio de venta:           ${precio_producto_neto:.2f}\n"
                f"Comisión Pasarela (MP):   -${total_mp_producto:.2f}\n"
                f"Comisión Plataforma (5%): -${comision_initre:.2f}\n"
                f"------------------------------------------\n"
                f"TOTAL TRANSFERIDO:         ${monto_vendedor_final:.2f}\n\n"
                f"Nota: Los costos de procesamiento del envío fueron cubiertos por el comprador.\n\n"
                f"La transferencia se envió a la CLABE registrada en tu perfil.\n"
                f"¡Gracias por vender en INITRE!"
            )
            
            send_mail(
                subject,
                message,
                'tu-correo-de-soporte@initre.com', 
                [venta.product.user.email],
                fail_silently=False,
            )
            messages.success(request, f"Venta {venta.payment_id} liquidada con éxito por ${monto_vendedor_final:.2f}")
        except Exception as e:
            messages.warning(request, f"Pago marcado, pero el correo falló: {e}")

    return redirect('panel_administrador')
    
@login_required
def pago_exitoso(request, producto_id):
    producto = get_object_or_404(IndustrialProduct, id=producto_id)
    status_mp = request.GET.get('collection_status') or request.GET.get('status')
    payment_id = request.GET.get('payment_id') or request.GET.get('collection_id')
    cp_url = request.GET.get('cp', '00000') # Recibimos el CP de la URL

    if status_mp == 'approved':
        try:
            flete_con_comision = Decimal(str(request.GET.get('envio', 0)))
        except:
            flete_con_comision = Decimal('0.00')

        tiene_envio = flete_con_comision > 0
        precio_base = Decimal(str(producto.price))

        # Cálculos de ganancia...
        ganancia_prod = precio_base * Decimal('0.05')
        ganancia_flete = flete_con_comision * Decimal('0.074')
        total_ganancia_neta = (ganancia_prod + ganancia_flete).quantize(Decimal('0.01'))

        # GUARDADO EN BASE DE DATOS
        venta, created = Sale.objects.update_or_create(
            payment_id=payment_id,
            defaults={
                'product': producto,
                'buyer': request.user,
                'price': precio_base + flete_con_comision,
                'shipping_cost': flete_con_comision,
                'shipping_cp': cp_url, # <--- SE GUARDA EL CP AQUÍ
                'is_delivery': tiene_envio,
                'ganancia_neta': total_ganancia_neta,
                'status': 'approved',
            }
        )
        
        if created:
            # Solo descontamos stock y enviamos correo la PRIMERA vez que se registra el pago
            if producto.stock > 0:
                producto.stock -= 1
                producto.save()
            
            enviar_notificacion_venta(venta)
            print(f"VENTA REGISTRADA: ID {payment_id} - Ganancia: {total_ganancia_neta}")

        mostrar_contacto = True
    else:
        # Si el pago no fue aprobado ahora, verificamos si ya existe uno aprobado antes
        mostrar_contacto = Sale.objects.filter(payment_id=payment_id, status='approved').exists()

    return render(request, 'marketplace/pago_exitoso.html', {
        'producto': producto,
        'mostrar_contacto': mostrar_contacto,
        'payment_id': payment_id
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
                    # Ahora dividimos la cadena: [producto_id, comprador_id, flete]
                    parts = ref_data.strip().split('-')
                    
                    if len(parts) >= 2:
                        producto_id = parts[0]
                        comprador_id = parts[1]
                        flete_pagado = Decimal(parts[2])
                        cp_destino = parts[3]
                        
                        producto = IndustrialProduct.objects.get(id=producto_id)
                        comprador = User.objects.get(id=comprador_id)
                        monto_total_cobrado = Decimal(str(data.get('transaction_amount')))
                        
                        # Calculamos la ganancia neta igual que en pago_exitoso
                        # (5% del producto + 7.4% del flete)
                        precio_base = Decimal(str(producto.price))
                        ganancia_prod = precio_base * Decimal('0.05')
                        ganancia_flete = flete_pagado * Decimal('0.074')
                        total_ganancia_neta = (ganancia_prod + ganancia_flete).quantize(Decimal('0.01'))

                        # Guardamos o actualizamos la venta
                        venta, created = Sale.objects.update_or_create(
                            payment_id=payment_id,
                            defaults={
                                'product': producto,
                                'buyer': comprador,
                                'price': monto_total_cobrado,
                                'shipping_cost': flete_pagado,
                                'shipping_cp': cp_destino,
                                'is_delivery': flete_pagado > 0,
                                'ganancia_neta': total_ganancia_neta,
                                'status': 'approved'
                            }
                        )

                        if created:
                            if producto.stock > 0:
                                producto.stock -= 1
                                producto.save()
                            
                            enviar_notificacion_venta(venta)
                            print(f"WEBHOOK: Venta exitosa con flete ${flete_pagado}")
                            
        except Exception as e:
            print(f"Error crítico en el webhook: {e}")

    return HttpResponse(status=200)

# marketplace/views.py

def como_funciona(request):
    return render(request, 'marketplace/como_funciona.html') # O el nombre de tu template









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
from django.conf import settings
from django.contrib.staticfiles import finders
from django.http import FileResponse, Http404

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
SDK = mercadopago.SDK("APP_USR-2885162849289081-010612-228b3049d19e3b756b95f319ee9d0011-40588817")

def descargar_apk(request):
    nombre_archivo = 'app_initre.apk'
    ruta_apk = finders.find(nombre_archivo)
    if not ruta_apk:
        ruta_apk = os.path.join(settings.BASE_DIR, 'static', nombre_archivo)

    if os.path.exists(ruta_apk):
        response = FileResponse(open(ruta_apk, 'rb'), content_type='application/vnd.android.package-archive')
        response['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'
        return response
    else:
        raise Http404("Archivo APK no encontrado.")

@login_required
def generar_preferencia_pago(request, producto_id):
    producto = get_object_or_404(IndustrialProduct, id=producto_id)
    
    # Captura segura de flete y CP
    try:
        flete_bruto = float(request.GET.get('envio', 0))
        cp_destino = request.GET.get('cp_destino') or request.GET.get('cp') or '00000'
    except (TypeError, ValueError):
        flete_bruto = 0
        cp_destino = '00000'

    flete_final_con_comision = round(flete_bruto * 1.08, 2)
    precio_base = float(producto.price)
    total_pagar_final = round(precio_base + flete_final_con_comision, 2)

    sdk = mercadopago.SDK("APP_USR-2885162849289081-010612-228b3049d19e3b756b95f319ee9d0011-40588817")

    preference_data = {
        "items": [
            {
                "title": f"{producto.title} (Envío a CP {cp_destino})" if flete_final_con_comision > 0 else producto.title,
                "quantity": 1,
                "unit_price": total_pagar_final,
                "currency_id": "MXN",
            }
        ],
        # GARANTIZAMOS SIEMPRE 4 ELEMENTOS PARA EL WEBHOOK
        "external_reference": f"{producto.id}-{request.user.id}-{flete_final_con_comision}-{cp_destino}",
        
        "back_urls": {
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

@login_required
def editar_perfil(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileForm(request.POST, instance=profile)
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, "¡Perfil actualizado!")
            return redirect('editar_perfil')
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileForm(instance=profile)
    return render(request, 'marketplace/editar_perfil.html', {'u_form': u_form, 'p_form': p_form})

def obtener_token_soloenvios():
    url = "https://app.soloenvios.com/api/v1/oauth/token"
    client_id = os.environ.get('SOLOENVIOS_CLIENT_ID', '').strip()
    client_secret = os.environ.get('SOLOENVIOS_CLIENT_SECRET', '').strip()
    if not client_id or not client_secret: return "ERROR_LLAVES_VACIAS"
    payload = {"client_id": client_id, "client_secret": client_secret, "grant_type": "client_credentials"}
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=20, verify=False)
        return res.json().get('access_token') if res.status_code == 200 else f"ERROR_{res.status_code}"
    except Exception as e: return str(e)

def cotizar_soloenvios(request):
    product_id = request.GET.get('product_id')
    try:
        producto = get_object_or_404(IndustrialProduct, id=product_id)
        cp_origen = str(producto.cp_origen).strip().zfill(5)
        peso_db, largo_db, ancho_db, alto_db = float(producto.peso or 1), float(producto.largo or 20), float(producto.ancho or 20), float(producto.alto or 20)
    except: return JsonResponse({'tarifas': []})

    cp_destino = str(request.GET.get('cp_destino', '')).strip().zfill(5)
    token = obtener_token_soloenvios()
    if "ERROR" in str(token): return JsonResponse({'tarifas': []})

    try:
        url = "https://app.soloenvios.com/api/v1/quotations"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        payload = {
            "quotation": {
                "address_from": {"country_code": "MX", "postal_code": cp_origen},
                "address_to": {"country_code": "MX", "postal_code": cp_destino},
                "parcels": [{"length": largo_db, "width": ancho_db, "height": alto_db, "weight": peso_db}]
            }
        }
        res = requests.post(url, json=payload, headers=headers, timeout=25, verify=False)
        if res.status_code in [200, 201]:
            data_id = res.json().get('id')
            time.sleep(2.5)
            res_final = requests.get(f"{url}/{data_id}", headers=headers, verify=False)
            tarifas = []
            for t in res_final.json().get('rates', []):
                monto = t.get('total')
                if monto: tarifas.append({'paqueteria': f"{t.get('provider_display_name')}", 'precio_final': round(float(monto) * 1.08, 2), 'tiempo': f"{t.get('days')} días"})
            return JsonResponse({'tarifas': tarifas})
    except: pass
    return JsonResponse({'tarifas': []})

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
    else: form = ProductForm()
    return render(request, 'marketplace/subir_producto.html', {'form': form})

@login_required
def editar_producto(request, pk):
    producto = get_object_or_404(IndustrialProduct, pk=pk, user=request.user)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=producto)
        if form.is_valid():
            form.save()
            messages.success(request, f"¡Producto actualizado!")
            return redirect('mi_inventario')
    else: form = ProductForm(instance=producto)
    return render(request, 'marketplace/editar_producto.html', {'form': form, 'producto': producto})

@login_required
def borrar_producto(request, pk):
    producto = get_object_or_404(IndustrialProduct, pk=pk, user=request.user)
    if request.method == 'POST': producto.delete()
    return redirect('mi_inventario')

def home(request):
    query = request.GET.get('q')
    products = IndustrialProduct.objects.filter(Q(title__icontains=query) | Q(part_number__icontains=query) | Q(brand__icontains=query)) if query else IndustrialProduct.objects.all()
    if request.user.is_authenticated:
        profile = getattr(request.user, 'profile', None)
        if profile and (not profile.phone or not profile.address):
            messages.warning(request, "⚠️ Perfil incompleto.")
    return render(request, 'marketplace/home.html', {'products': products})

def detalle_producto(request, product_id):
    product = get_object_or_404(IndustrialProduct, id=product_id)
    perfil_incompleto = False
    if request.user.is_authenticated:
        profile = getattr(request.user, 'profile', None)
        if profile and (not profile.phone or not profile.address): perfil_incompleto = True
    
    user_id = request.user.id if request.user.is_authenticated else 0
    
    # CORRECCIÓN AQUÍ: Agregamos flete y CP por defecto para evitar errores de Webhook
    pref_data = {
        "items": [{"title": product.title, "quantity": 1, "unit_price": float(product.price), "currency_id": "MXN"}],
        "external_reference": f"{product.id}-{user_id}-0-00000",
    }
    try:
        pref = SDK.preference().create(pref_data)
        preference_id = pref["response"]["id"]
    except: preference_id = None

    return render(request, 'marketplace/product_detail.html', {
        'product': product, 'preference_id': preference_id, 
        'public_key': "APP_USR-bab958ea-ede4-49f7-b072-1fd682f9e1b9", 'perfil_incompleto': perfil_incompleto
    })

def category_detail(request, category_id):
    cat = get_object_or_404(Category, id=category_id)
    return render(request, 'marketplace/home.html', {'products': IndustrialProduct.objects.filter(category=cat), 'category': cat})

def registro(request):
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid(): form.save(); return redirect('login')
    else: form = RegistroForm()
    return render(request, 'marketplace/registro.html', {'form': form})

@login_required
def mis_ventas(request):
    ventas = Sale.objects.filter(product__user=request.user).order_by('-created_at')
    for v in ventas:
        precio_prod = Decimal(str(v.price)) - Decimal(str(v.shipping_cost))
        comision_initre = precio_prod * Decimal('0.05')
        com_porc_prod = precio_prod * Decimal('0.0349')
        mp_solo_producto = com_porc_prod + Decimal('4.00') + ((com_porc_prod + Decimal('4.00')) * Decimal('0.16'))
        v.monto_limpio_vendedor = precio_prod - comision_initre - mp_solo_producto
    return render(request, 'marketplace/mis_ventas.html', {'ventas': ventas})

@login_required
def mis_compras(request):
    compras = Sale.objects.filter(buyer=request.user).order_by('-created_at')
    return render(request, 'marketplace/mis_compras.html', {'compras': compras})

@login_required
def confirmar_recepcion(request, venta_id):
    if request.method == 'POST':
        venta = get_object_or_404(Sale, id=venta_id, buyer=request.user)
        venta.recibido_por_comprador = True
        venta.status = 'entregado'
        venta.save()
        messages.success(request, "¡Gracias por confirmar!")
    return redirect('mis_compras')

@login_required
def actualizar_guia(request, venta_id):
    if request.method == 'POST':
        v = get_object_or_404(Sale, id=venta_id, product__user=request.user)
        v.shipping_company = request.POST.get('shipping_company')
        v.tracking_number = request.POST.get('tracking_number')
        v.status = 'enviado'
        v.save()
        try:
            send_mail(f"🚀 Pedido en camino", f"Guía: {v.tracking_number}", settings.DEFAULT_FROM_EMAIL, [v.buyer.email])
        except: pass
    return redirect('mis_ventas')

@login_required
def panel_administrador(request):
    if not request.user.is_staff: return redirect('home')
    estados_validos = ['approved', 'enviado', 'entregado']
    ventas_todas = Sale.objects.select_related('product__user__profile', 'buyer__profile').all().order_by('-created_at')
    resultado_ganancia = Sale.objects.filter(status__in=estados_validos).aggregate(total=Sum('ganancia_neta'))
    context = {
        'ventas': ventas_todas, 'total_ventas_count': Sale.objects.filter(status__in=estados_validos).count(),
        'ingresos_totales': resultado_ganancia['total'] or 0, 'productos_recientes': IndustrialProduct.objects.all().order_by('-created_at')[:5],
        'ventas_pendientes_pago': Sale.objects.filter(pagado_a_vendedor=False, status__in=estados_validos).count(),
    }
    return render(request, 'marketplace/panel_admin.html', context)

@login_required
def pago_exitoso(request, producto_id):
    producto = get_object_or_404(IndustrialProduct, id=producto_id)
    status_mp = request.GET.get('collection_status') or request.GET.get('status')
    payment_id = request.GET.get('payment_id') or request.GET.get('collection_id')
    cp_url = request.GET.get('cp', '00000')

    if status_mp == 'approved':
        try: flete_con_comision = Decimal(str(request.GET.get('envio', 0)))
        except: flete_con_comision = Decimal('0.00')
        precio_base = Decimal(str(producto.price))
        ganancia_neta = (precio_base * Decimal('0.05') + flete_con_comision * Decimal('0.074')).quantize(Decimal('0.01'))

        venta, created = Sale.objects.update_or_create(
            payment_id=payment_id,
            defaults={
                'product': producto, 'buyer': request.user, 'price': precio_base + flete_con_comision,
                'shipping_cost': flete_con_comision, 'shipping_cp': cp_url, 'is_delivery': flete_con_comision > 0,
                'ganancia_neta': ganancia_neta, 'status': 'approved',
            }
        )
        if created:
            if producto.stock > 0: producto.stock -= 1; producto.save()
            enviar_notificacion_venta(venta)
        mostrar_contacto = True
    else: mostrar_contacto = Sale.objects.filter(payment_id=payment_id, status='approved').exists()

    return render(request, 'marketplace/pago_exitoso.html', {'producto': producto, 'mostrar_contacto': mostrar_contacto, 'payment_id': payment_id})

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
                        # ASIGNACIÓN SEGURA (Pone ceros si no hay posición 2 o 3)
                        flete_pagado = Decimal(parts[2]) if len(parts) > 2 else Decimal('0.00')
                        cp_destino = parts[3] if len(parts) > 3 else "00000"
                        
                        try:
                            producto = IndustrialProduct.objects.get(id=producto_id)
                            comprador = User.objects.get(id=comprador_id)
                            monto_total = Decimal(str(data.get('transaction_amount', '0')))
                            ganancia_neta = (Decimal(str(producto.price)) * Decimal('0.05') + flete_pagado * Decimal('0.074')).quantize(Decimal('0.01'))

                            venta, created = Sale.objects.update_or_create(
                                payment_id=payment_id,
                                defaults={
                                    'product': producto, 'buyer': comprador, 'price': monto_total,
                                    'shipping_cost': flete_pagado, 'shipping_cp': cp_destino,
                                    'is_delivery': flete_pagado > 0, 'ganancia_neta': ganancia_neta, 'status': 'approved'
                                }
                            )
                            if created:
                                if producto.stock > 0: producto.stock -= 1; producto.save()
                                try: enviar_notificacion_venta(venta)
                                except: pass
                        except: pass
        except: pass
    return HttpResponse(status=200)

def como_funciona(request): return render(request, 'marketplace/como_funciona.html')
def privacidad(request): return render(request, 'marketplace/privacidad.html')

def descargar_ficha(request, product_id):
    try:
        product = IndustrialProduct.objects.get(id=product_id)
        if not product.ficha_tecnica: raise Http404
        file_handle = product.ficha_tecnica.open()
        response = FileResponse(file_handle, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{product.title}_Ficha_Tecnica.pdf"'
        return response
    except: raise Http404

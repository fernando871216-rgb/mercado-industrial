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
    return render(request, 'marketplace/home.html', {'products': products})

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
    ventas = Sale.objects.filter(product__user=request.user).order_by('-created_at')
    for v in ventas:
        # CÁLCULO PARA LA INTERFAZ (Soluciona el problema de la imagen que enviaste)
        precio_prod = Decimal(str(v.price)) - Decimal(str(v.shipping_cost))
        comision_initre = precio_prod * Decimal('0.05')
        com_mp = (precio_prod * Decimal('0.0349')) + Decimal('4.00')
        iva_mp = com_mp * Decimal('0.16')
        v.monto_limpio_vendedor = (precio_prod - comision_initre - (com_mp + iva_mp)).quantize(Decimal('0.01'))
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
    v.status = 'entregado'; v.save(); return redirect('mis_compras')

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
        v = get_object_or_404(Sale, id=venta_id); v.pagado_a_vendedor = True; v.save()
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

def cotizar_soloenvios(request): return JsonResponse({'tarifas': []})
def category_detail(request, category_id):
    cat = get_object_or_404(Category, id=category_id)
    return render(request, 'marketplace/home.html', {'products': IndustrialProduct.objects.filter(category=cat), 'category': cat})
def como_funciona(request): return render(request, 'marketplace/como_funciona.html')
def privacidad(request): return render(request, 'marketplace/privacidad.html')
def procesar_pago(request, producto_id): return render(request, 'marketplace/pago.html', {'producto': get_object_or_404(IndustrialProduct, id=producto_id)})

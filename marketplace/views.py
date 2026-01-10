import os
import mercadopago
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.db.models import Q
from django.core.mail import send_mail
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
import json
from .models import IndustrialProduct, Sale

# Importa tus modelos y formularios
from .models import IndustrialProduct, Category, Sale, Profile
from .forms import RegistroForm, ProductoForm, UserUpdateForm, ProfileUpdateForm

def home(request):
    query = request.GET.get('q')
    if query:
        products = IndustrialProduct.objects.filter(
            Q(title__icontains=query) | Q(brand__icontains=query) | Q(part_number__icontains=query)
        ).distinct()
    else:
        products = IndustrialProduct.objects.all().order_by('-created_at')
    return render(request, 'marketplace/home.html', {'products': products, 'query': query})

def detalle_producto(request, product_id):
    product = get_object_or_404(IndustrialProduct, id=product_id)
    preference_id = None
    
    # --- CONFIGURACIÓN DE MERCADO PAGO ---
    token = "APP_USR-2885162849289081-010612-228b3049d19e3b756b95f319ee9d0011-40588817" 
    
    try:
        sdk = mercadopago.SDK(token)
        preference_data = {
            "items": [
                {
                    "title": product.title,
                    "quantity": 1,
                    "unit_price": float(product.price),
                    "currency_id": "MXN"
                }
            ],
            "external_reference": str(product.id),
            "back_urls": {
                "success": request.build_absolute_uri(reverse('pago_exitoso')),
                "failure": request.build_absolute_uri(reverse('pago_fallido')),
            },
            "auto_return": "approved",
        }
        preference_response = sdk.preference().create(preference_data)
        preference_id = preference_response["response"].get("id")
    except Exception as e:
        print(f"Error MP: {e}")

    return render(request, 'marketplace/product_detail.html', {
        'product': product,
        'preference_id': preference_id
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
def cambiar_estado_venta(request, venta_id):
    venta = get_object_or_404(Sale, id=venta_id, product__user=request.user)
    venta.status = 'completado' if venta.status == 'pendiente' else 'pendiente'
    venta.save()
    return redirect('mis_ventas')

@login_required
def procesar_pago(request, product_id):
    if request.method == 'POST':
        producto = get_object_or_404(IndustrialProduct, id=product_id)
        
        # Evitamos comprar si no hay stock
        if producto.stock > 0:
            Sale.objects.create(
                product=producto,
                buyer=request.user,
                price=producto.price,
                status='pendiente'
            )
            producto.stock -= 1
            producto.save()
            return redirect('pago_exitoso')
        
    return redirect('detalle_producto', product_id=product_id)

@login_required
def subir_producto(request):
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES)
        if form.is_valid():
            producto = form.save(commit=False)
            producto.user = request.user
            producto.save()
            return redirect('mi_inventario')
    else:
        form = ProductoForm()
    return render(request, 'marketplace/subir_producto.html', {'form': form})

@login_required
def editar_producto(request, pk):
    producto = get_object_or_404(IndustrialProduct, pk=pk, user=request.user)
    if request.method == "POST":
        form = ProductoForm(request.POST, request.FILES, instance=producto)
        if form.is_valid():
            form.save()
            return redirect('mi_inventario')
    else:
        form = ProductoForm(instance=producto)
    return render(request, 'marketplace/subir_producto.html', {'form': form, 'edit': True})

@login_required
def borrar_producto(request, pk):
    producto = get_object_or_404(IndustrialProduct, pk=pk, user=request.user)
    producto.delete()
    return redirect('mi_inventario')

@login_required
def editar_perfil(request):
    Profile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, instance=request.user.profile)
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            return redirect('home')
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=request.user.profile)
    return render(request, 'marketplace/editar_perfil.html', {'u_form': u_form, 'p_form': p_form})

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

def category_detail(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    products = IndustrialProduct.objects.filter(category=category).order_by('-created_at')
    return render(request, 'marketplace/home.html', {'products': products, 'category': category})

def pago_fallido(request):
    return render(request, 'marketplace/pago_fallido.html')

@login_required
def pago_exitoso(request):
    # Intentamos obtener el ID del producto desde la URL que envía Mercado Pago
    product_id = request.GET.get('external_reference')
    producto_obj = None
    venta_creada = False

    if product_id:
        producto_obj = get_object_or_404(IndustrialProduct, id=product_id)
        
        # Verificamos si ya existe una venta registrada para este pago (para no duplicar)
        # Si no existe, la creamos y descontamos stock
        if producto_obj.stock > 0:
            Sale.objects.create(
                product=producto_obj,
                buyer=request.user,
                price=producto_obj.price,
                status='completado' # Al ser pago real, entra como completado
            )
            producto_obj.stock -= 1
            producto_obj.save()
            venta_creada = True

    return render(request, 'marketplace/pago_exitoso.html', {
        'producto': producto_obj,
        'venta_creada': venta_creada
    })

@staff_member_required
def panel_administrador(request):
    ventas = Sale.objects.all().order_by('-created_at')
    resumen = ventas.aggregate(Sum('price'))
    total_ventas = resumen['price__sum'] or 0
    tus_ganancias = float(total_ventas) * 0.05
    return render(request, 'marketplace/panel_admin.html', {
        'ventas': ventas,
        'total_ventas': total_ventas,
        'tus_ganancias': tus_ganancias,
    })

@login_required
def mi_inventario(request):
    # Si eres el administrador principal, te mostramos TODOS los productos para que puedas gestionarlos
    if request.user.is_staff:
        productos = IndustrialProduct.objects.all().order_by('-created_at')
    else:
        # Si eres un vendedor normal, solo ves los tuyos
        productos = IndustrialProduct.objects.filter(user=request.user).order_by('-created_at')
    
    return render(request, 'marketplace/mi_inventario.html', {
        'products': productos
    })

@staff_member_required
def marcar_como_pagado(request, venta_id):
    venta = get_object_or_404(Sale, id=venta_id)
    venta.pagado_a_vendedor = not venta.pagado_a_vendedor 
    venta.save()
    # Cambiado de 'panel_admin' a 'panel_administrador' para que coincida con la función
    return redirect('panel_administrador')

@login_required
def cancelar_venta(request, venta_id):
    # Buscamos la venta. Solo el vendedor del producto o un admin pueden cancelarla.
    venta = get_object_or_404(Sale, id=venta_id)
    
    # Verificamos permisos: Solo el dueño del producto (vendedor) o admin
    if request.user == venta.product.user or request.user.is_staff:
        if venta.status != 'cancelado':
            # 1. Devolvemos el stock al producto
            producto = venta.product
            producto.stock += 1
            producto.save()
            
            # 2. Marcamos la venta como cancelada
            venta.status = 'cancelado'
            venta.save()
            
    return redirect('mis_ventas')

@csrf_exempt
def mercadopago_webhook(request):
    if request.method == 'POST':
        payment_id = request.GET.get('id')
        
        if not payment_id:
            try:
                data = json.loads(request.body)
                payment_id = data.get('data', {}).get('id') or data.get('id')
            except:
                pass

        if payment_id:
            # --- ENVÍO DE CORREO DE AVISO ---
            try:
                asunto = f"✅ ¡Nueva Notificación de Pago! ID: {payment_id}"
                mensaje = (
                    f"Hola administrador,\n\n"
                    f"Se ha recibido una notificación de pago desde Mercado Pago.\n"
                    f"ID del Pago: {payment_id}\n\n"
                    f"Por favor, revisa tu panel de Mercado Pago y el Panel de Ventas "
                    f"de Mercado Industrial para confirmar los detalles del equipo.\n\n"
                    f"Saludos,\nTu Sistema Mercado Industrial"
                )
                
                send_mail(
                    asunto,
                    mensaje,
                    settings.DEFAULT_FROM_EMAIL, # Tu correo de salida
                    [settings.ADMIN_EMAIL],      # Tu correo personal (donde recibes)
                    fail_silently=False,
                )
            except Exception as e:
                print(f"Error enviando correo: {e}")

            return HttpResponse(status=200)
        
        return HttpResponse(status=200)
    return HttpResponse(status=200)









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
    # CORRECCIÓN: Filtramos por el dueño del producto (product__user)
    ventas = Sale.objects.filter(product__user=request.user).order_by('-created_at')
    return render(request, 'marketplace/mis_ventas.html', {'ventas': ventas})

@login_required
def cambiar_estado_venta(request, venta_id):
    # CORRECCIÓN: Cambiamos 'seller' por 'product__user'
    venta = get_object_or_404(Sale, id=venta_id, product__user=request.user)
    venta.status = 'completado' if venta.status == 'pendiente' else 'pendiente'
    venta.save()
    return redirect('mis_ventas')

@login_required
def procesar_pago(request, product_id):
    producto = get_object_or_404(IndustrialProduct, id=product_id)
    
    if producto.stock > 0:
        # CORRECCIÓN: El modelo Sale no tiene campo 'seller' directo, se saca del producto
        Sale.objects.create(
            product=producto, 
            buyer=request.user, 
            price=producto.price, 
            status='pendiente'
        )
        
        producto.stock -= 1
        producto.save()

        # NOTIFICACIÓN POR EMAIL
        try:
            asunto = f"¡Nueva venta! - {producto.title}"
            mensaje = (
                f"Hola {producto.user.username},\n\n"
                f"Has recibido una nueva venta en MarketIndustrial.\n\n"
                f"Producto: {producto.title}\n"
                f"Comprador: {request.user.username}\n"
                f"Quedan {producto.stock} unidades.\n\n"
                f"Ponte en contacto para la entrega."
            )
            send_mail(
                asunto,
                mensaje,
                'tu-correo@gmail.com',
                [producto.user.email],
                fail_silently=True,
            )
        except Exception as e:
            print(f"Error al enviar correo: {e}")

def category_detail(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    products = IndustrialProduct.objects.filter(category=category).order_by('-created_at')
    return render(request, 'marketplace/home.html', {
        'products': products, 
        'category': category
    })


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
    # Asegúrate de pegar tu ACCESS TOKEN real aquí abajo
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
    ventas = Sale.objects.filter(seller=request.user).order_by("-created_at")
    return render(request, 'marketplace/mis_ventas.html', {'ventas': ventas})

@login_required
def cambiar_estado_venta(request, venta_id):
    venta = get_object_or_404(Sale, id=venta_id, seller=request.user)
    venta.status = 'completado' if venta.status == 'pendiente' else 'pendiente'
    venta.save()
    return redirect('mis_ventas')

@login_required
def procesar_pago(request, product_id):
    # 1. Buscamos el producto
    producto = get_object_or_404(IndustrialProduct, id=product_id)
    
    # 2. VALIDACIÓN DE STOCK: Verificar si hay existencias
    if producto.stock > 0:
        # 3. Crear el registro de la venta
        Sale.objects.create(
            product=producto, 
            buyer=request.user, 
            seller=producto.seller,
            price=producto.price, 
            status='pendiente'
        )
        
        # 4. BAJAR EL STOCK: Restamos 1 a la cantidad disponible
        producto.stock -= 1
        producto.save()

        # 5. NOTIFICACIÓN POR EMAIL AL VENDEDOR
        try:
            asunto = f"¡Nueva venta! - {producto.title}"
            mensaje = (
                f"Hola {producto.seller.username},\n\n"
                f"Has recibido una nueva venta en MarketIndustrial.\n\n"
                f"Producto: {producto.title}\n"
                f"Comprador: {request.user.username}\n"
                f"Quedan {producto.stock} unidades en tu inventario.\n\n"
                f"Ponte en contacto con el comprador para la entrega."
            )
            send_mail(
                asunto,
                mensaje,
                'tu-correo@gmail.com', # Configurado en settings.py
                [producto.seller.email],
                fail_silently=True,
            )
        except Exception as e:
            print(f"Error al enviar correo: {e}")

        return redirect('mis_compras')
    
    else:
        # Si no hay stock, podrías redirigir con un mensaje de error
        return render(request, 'marketplace/pago_fallido.html', {
            'error_message': 'Lo sentimos, este producto se acaba de agotar.'
        })

# --- AQUÍ ESTABA EL ERROR CORREGIDO: order_by en lugar de order_at ---
@login_required
def mi_inventario(request):
    productos = IndustrialProduct.objects.filter(seller=request.user).order_by('-created_at')
    return render(request, 'marketplace/mi_inventario.html', {'productos': productos})

@login_required
def subir_producto(request):
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES)
        if form.is_valid():
            producto = form.save(commit=False)
            producto.seller = request.user
            producto.save()
            return redirect('mi_inventario')
    else:
        form = ProductoForm()
    return render(request, 'marketplace/subir_producto.html', {'form': form})

@login_required
def editar_producto(request, pk):
    producto = get_object_or_404(IndustrialProduct, pk=pk, seller=request.user)
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
    producto = get_object_or_404(IndustrialProduct, pk=pk, seller=request.user)
    producto.delete()
    return redirect('mi_inventario')

@login_required
def editar_perfil(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, instance=request.user.profile)
        if u_form.is_valid() and p_form.is_valid():
            u_form.save(); p_form.save()
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
    return render(request, 'marketplace/pago_exitoso.html')


@staff_member_required # Solo tú puedes entrar
def panel_administrador(request):
    ventas = Sale.objects.all().order_by('-created_at')
    
    # Calculamos el total de dinero que ha pasado por la plataforma
    total_ventas = ventas.aggregate(Sum('price'))['price__sum'] or 0
    
    # Tu ganancia bruta (5% de todo)
    tus_ganancias = float(total_ventas) * 0.05
    
    return render(request, 'marketplace/panel_admin.html', {
        'ventas': ventas,
        'total_ventas': total_ventas,
        'tus_ganancias': tus_ganancias,
    })





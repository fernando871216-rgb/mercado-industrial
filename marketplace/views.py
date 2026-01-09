import os
import mercadopago
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.core.mail import send_mail
from django.db.models import Q

# Importa tus modelos y formularios
from .models import IndustrialProduct, Category, Sale, Profile
from .forms import RegistroForm, ProductoForm, UserUpdateForm, ProfileUpdateForm

# --- 1. VISTA DE INICIO (HOME) ---
def home(request):
    query = request.GET.get('q')
    if query:
        products = IndustrialProduct.objects.filter(
            Q(title__icontains=query) | 
            Q(brand__icontains=query) | 
            Q(part_number__icontains=query)
        ).distinct()
    else:
        products = IndustrialProduct.objects.all().order_by('-created_at')
        
    return render(request, 'marketplace/home.html', {'products': products, 'query': query})

# --- 2. DETALLE DE CATEGORÍA (LA QUE FALTABA) ---
def category_detail(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    products = IndustrialProduct.objects.filter(category=category).order_by('-created_at')
    return render(request, 'marketplace/home.html', {'products': products, 'category': category})

# --- 3. PROCESAR PAGO (INTENCIÓN DE COMPRA) ---
@login_required
def procesar_pago(request, product_id):
    producto = get_object_or_404(IndustrialProduct, id=product_id)
    
    nueva_venta = Sale.objects.create(
        product=producto,
        buyer=request.user,
        seller=producto.seller,
        price=producto.price,
        status='pendiente'
    )

    # ENVÍO DE EMAIL AL VENDEDOR
    asunto = f"¡Venta Registrada! Equipo: {producto.title}"
    mensaje = f"""
    Hola {producto.seller.username},
    
    El usuario {request.user.username} ha marcado tu equipo "{producto.title}" como comprado.
    
    Por favor, revisa tu panel de 'Mis Ventas' para contactar al cliente.
    """
    
    try:
        send_mail(
            asunto,
            mensaje,
            'fernando871216@gmail.com',
            [producto.seller.email],
            fail_silently=False,
        )
    except Exception as e:
        print(f"Error enviando correo: {e}")

    return redirect('mis_compras')

# --- 4. GESTIÓN DE VENTAS Y COMPRAS ---
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
    if venta.status == 'pendiente':
        venta.status = 'completado'
    else:
        venta.status = 'pendiente'
    venta.save()
    return redirect('mis_ventas')

# --- 5. PERFIL Y PRODUCTOS ---
@login_required
def editar_perfil(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
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

    return render(request, 'marketplace/editar_perfil.html', {
        'u_form': u_form,
        'p_form': p_form
    })

def detalle_producto(request, product_id):
    product = get_object_or_404(IndustrialProduct, id=product_id)
    return render(request, 'marketplace/product_detail.html', {'product': product})

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
            return redirect('home')
    else:
        form = ProductoForm()
    return render(request, 'marketplace/subir_producto.html', {'form': form})

# --- 6. REGISTRO Y OTROS ---
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

def pago_fallido(request):
    return render(request, 'marketplace/pago_fallido.html')

@login_required
def pago_exitoso(request):
    return render(request, 'marketplace/pago_exitoso.html')

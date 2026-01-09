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

# --- 1. PROCESAR PAGO (BOTÓN DIRECTO / REGISTRO MANUAL) ---
@login_required
def procesar_pago(request, product_id):
    # Corregido: Usamos IndustrialProduct y la función correcta get_object_or_404
    producto = get_object_or_404(IndustrialProduct, id=product_id)
    
    # Crear el registro de la venta
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
    
    DATOS DEL COMPRADOR:
    - Usuario: {request.user.username}
    - Email: {request.user.email}
    
    Por favor, revisa tu panel de 'Mis Ventas' para contactar al cliente.
    """
    
    try:
        send_mail(
            asunto,
            mensaje,
            'fernando871216@gmail.com', # Tu correo configurado en settings.py
            [producto.seller.email],
            fail_silently=False,
        )
    except Exception as e:
        print(f"Error enviando correo: {e}")

    return redirect('mis_compras')

# --- 2. VISTA DE INICIO (HOME) ---
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

# --- 3. EDITAR PERFIL ---
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

# --- 4. DETALLE DEL PRODUCTO (MERCADO PAGO) ---
def detalle_producto(request, product_id):
    product = get_object_or_404(IndustrialProduct, id=product_id)
    preference_id = None
    public_key = os.environ.get('MP_PUBLIC_KEY')
    access_token = os.environ.get('MP_ACCESS_TOKEN')

    if request.user.is_authenticated and product.stock > 0:
        try:
            sdk = mercadopago.SDK(access_token)
            preference_data = {
                "items": [{
                    "title": product.title,
                    "quantity": 1,
                    "unit_price": float(product.price),
                    "currency_id": "MXN"
                }],
                "external_reference": str(product.id),
                "back_urls": {
                    "success": request.build_absolute_uri(reverse('pago_exitoso')),
                    "failure": request.build_absolute_uri(reverse('pago_fallido')),
                    "pending": request.build_absolute_uri(reverse('home')),
                },
                "auto_return": "approved",
            }
            preference_response = sdk.preference().create(preference_data)
            if "response" in preference_response:
                preference_id = preference_response["response"]["id"]
        except Exception as e:
            print(f"Error Mercado Pago: {e}")

    return render(request, 'marketplace/product_detail.html', {
        'product': product,
        'preference_id': preference_id,
        'public_key': public_key
    })

# --- 5. GESTIÓN DE VENTAS Y COMPRAS ---
@login_required
def mis_compras(request):
    compras = Sale.objects.filter(buyer=request.user).order_by('-created_at')
    return render(request, 'marketplace/mis_compras.html', {'compras': compras})

@login_required
def mis_ventas(request):
    ventas = Sale.objects.filter(seller=request.user).order_by("-created_at")
    return render(request, 'marketplace/mis_ventas.html', {'ventas': ventas})

# --- 6. CAMBIAR ESTADO DE VENTA ---
@login_required
def cambiar_estado_venta(request, venta_id):
    venta = get_object_or_404(Sale, id=venta_id, seller=request.user)
    if venta.status == 'pendiente':
        venta.status = 'completado'
    else:
        venta.status = 'pendiente'
    venta.save()
    return redirect('mis_ventas')

# --- 7. RETORNO DE PAGO EXITOSO (MERCADO PAGO) ---
@login_required
def pago_exitoso(request):
    producto_id = request.GET.get('external_reference')
    
    if producto_id:
        try:
            producto = IndustrialProduct.objects.get(id=producto_id)
            if producto.stock > 0:
                producto.stock -= 1
                producto.save()
                
                # Crear venta desde Mercado Pago
                Sale.objects.create(
                    product=producto,
                    buyer=request.user,
                    seller=producto.seller,
                    price=producto.price,
                    status='completado' # Al ser pago real, nace completada
                )

                # Notificación
                send_mail(
                    '¡Pago Confirmado!',
                    f'El usuario {request.user.username} pagó ${producto.price} por {producto.title}.',
                    'fernando871216@gmail.com',
                    [producto.seller.email],
                    fail_silently=True,
                )
        except IndustrialProduct.DoesNotExist:
            pass
            
    return render(request, 'marketplace/pago_exitoso.html')

# --- 8. INVENTARIO Y CRUD ---
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

@login_required
def editar_producto(request, pk):
    producto = get_object_or_404(IndustrialProduct, pk=pk, seller=request.user)
    if request.method == "POST":
        form = ProductoForm(request.POST, request.FILES, instance=producto)
        if form.is_valid():
            form.save()
            return redirect('product_detail', product_id=producto.id)
    else:
        form = ProductoForm(instance=producto)
    return render(request, 'marketplace/subir_producto.html', {'form': form, 'edit': True})

@login_required
def borrar_producto(request, pk):
    producto = get_object_or_404(IndustrialProduct, pk=pk, seller=request.user)
    producto.delete()
    return redirect('mi_inventario')

# --- 9. AUTH Y OTROS ---
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

def category_detail(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    products = IndustrialProduct.objects.filter(category=category)
    return render(request, 'marketplace/home.html', {'products': products, 'category': category})

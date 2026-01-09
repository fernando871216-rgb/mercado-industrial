import os
import mercadopago
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from .models import IndustrialProduct, Category
from .forms import RegistroForm, ProductoForm
from django.urls import reverse
from .models import Sale 
from django.core.mail import send_mail
from django.db.models import Q
from django.shortcuts import redirect, get_object_ some_list_or_object
from .models import IndustrialProduct, Sale

@login_required
def procesar_pago(request, product_id):
    if request.method == 'POST':
        producto = get_object_or_404(IndustrialProduct, id=product_id)
        
        # 1. Crear el registro de venta
        Sale.objects.create(
            product=producto,
            buyer=request.user,
            seller=producto.seller,
            price=producto.price
        )
        
        # 2. Restar stock (opcional si manejas inventario)
        if producto.stock > 0:
            producto.stock -= 1
            producto.save()
            
        # 3. Redirigir a una página de éxito (ej: Mis Compras)
        return redirect('mis_compras')
    
    return redirect('home')
    
# 1. VISTA DE INICIO (HOME)
def home(request):
    query = request.GET.get('q')
    
    if query:
        # Buscamos coincidencias en Título, Marca o Número de Parte
        products = IndustrialProduct.objects.filter(
            Q(title__icontains=query) | 
            Q(brand__icontains=query) | 
            Q(part_number__icontains=query)
        ).distinct()
    else:
        products = IndustrialProduct.objects.all().order_by('-created_at')
        
    return render(request, 'marketplace/home.html', {'products': products, 'query': query})

@login_required
def editar_perfil(request):
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, instance=request.user.profile)
        
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            return redirect('home') # O a una página de "Perfil actualizado"
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=request.user.profile)

    return render(request, 'marketplace/editar_perfil.html', {
        'u_form': u_form,
        'p_form': p_form
    })
    
# 2. DETALLE DEL PRODUCTO (Aquí se genera el pago)
def detalle_producto(request, product_id):
    product = get_object_or_404(IndustrialProduct, id=product_id)
    preference_id = None
    public_key = os.environ.get('MP_PUBLIC_KEY')
    access_token = os.environ.get('MP_ACCESS_TOKEN')

    # Solo creamos la preferencia si el usuario está logueado y hay stock
    if request.user.is_authenticated and product.stock > 0:
        try:
            sdk = mercadopago.SDK(access_token)
            preference_data = {
                "items": [
                    {
                        "title": product.title,
                        "quantity": 1,
                        "unit_price": float(product.price),
                        "currency_id": "MXN"
                    }
                ],
                # INDISPENSABLE para que el stock baje en pago_exitoso
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

@login_required
def mis_compras(request):
    # Obtenemos todas las ventas donde el comprador es el usuario logueado
    compras = Sale.objects.filter(buyer=request.user).order_by('-created_at')
    return render(request, 'marketplace/mis_compras.html', {'compras': compras})

@login_required
def mis_ventas(request):
    # Filtramos las ventas donde el vendedor del producto es el usuario actual
    ventas = Sale.objects.filter(product__seller=request.user).order_by('-created_at')
    return render(request, 'marketplace/mis_ventas.html', {'ventas': ventas})

# 3. PÁGINA DE ÉXITO (Baja de Stock)
def pago_exitoso(request):
    producto_id = request.GET.get('external_reference')
    payment_id = request.GET.get('collection_id') 
    
    if producto_id:
        try:
            producto = IndustrialProduct.objects.get(id=producto_id)
            if producto.stock > 0:
                # 1. Restar stock
                producto.stock -= 1
                producto.save()
                
                # 2. CREAR REGISTRO DE VENTA
                Sale.objects.create(
                    product=producto,
                    buyer=request.user,
                    amount=producto.price,
                    mp_payment_id=payment_id
                )

                # 3. ENVIAR CORREO (Debe estar indentado dentro del IF)
                send_mail(
                    '¡Vendiste un producto!',
                    f'Hola {producto.seller.username}, el usuario {request.user.username} ha comprado {producto.title}. Ponte en contacto en: {request.user.email}',
                    'fernando871216@gmail.com',  # Cambia esto por tu correo de settings.py
                    [producto.seller.email],
                    fail_silently=False,
                )
                # 3. CORREO PARA EL COMPRADOR (A su cuenta personal)
                send_mail(
                    'Confirmación de tu compra en Mercado Industrial',
                    f'Hola {request.user.username},\n\nTu pago por "{producto.title}" ha sido confirmado.\n\nDatos del vendedor para coordinar entrega:\n- Vendedor: {producto.seller.username}\n- Email: {producto.seller.email}',
                    'tu-correo-de-settings@gmail.com', # Este es el remitente
                    [request.user.email], # ESTO ENVÍA EL CORREO AL CLIENTE
                    fail_silently=False,
                )
        except IndustrialProduct.DoesNotExist:
            pass
            
    return render(request, 'marketplace/pago_exitoso.html')

# 4. PÁGINA DE FALLO
def pago_fallido(request):
    return render(request, 'marketplace/pago_fallido.html')

# 5. MI INVENTARIO
@login_required
def mi_inventario(request):
    productos = IndustrialProduct.objects.filter(seller=request.user).order_by('-created_at')
    return render(request, 'marketplace/mi_inventario.html', {'productos': productos})

# 6. SUBIR PRODUCTO
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

# 7. EDITAR PRODUCTO
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

# 8. BORRAR PRODUCTO
@login_required
def borrar_producto(request, pk):
    producto = get_object_or_404(IndustrialProduct, pk=pk, seller=request.user)
    producto.delete()
    return redirect('mi_inventario')

# 9. REGISTRO
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

# 10. CATEGORÍAS
def category_detail(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    products = IndustrialProduct.objects.filter(category=category)
    return render(request, 'marketplace/inicio.html', {'products': products, 'category': category})













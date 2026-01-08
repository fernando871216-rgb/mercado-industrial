import os
import mercadopago
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from .models import IndustrialProduct, Category
from .forms import RegistroForm, ProductoForm
from django.urls import reverse

# 1. VISTA DE INICIO (HOME)
def home(request):
    # Cambié 'home.html' por 'inicio.html' porque es el nombre que usamos en los pasos anteriores
    products = IndustrialProduct.objects.all().order_by('-created_at')
    return render(request, 'marketplace/home.html', {'products': products})

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

# 3. PÁGINA DE ÉXITO (Baja de Stock)
def pago_exitoso(request):
    # Recuperamos el ID que enviamos en 'external_reference'
    producto_id = request.GET.get('external_reference')
    
    if producto_id:
        try:
            producto = IndustrialProduct.objects.get(id=producto_id)
            if producto.stock > 0:
                producto.stock -= 1
                producto.save()
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



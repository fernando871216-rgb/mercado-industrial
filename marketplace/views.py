from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib import messages
from .models import IndustrialProduct, Category
from .forms import ProductForm
from django.shortcuts import render, get_object_or_404
import mercadopago
import os
from django.conf import settings

def detalle_producto(request, product_id):
    product = get_object_or_404(IndustrialProduct, id=product_id)
    
    # Configurar Mercado Pago
    sdk = mercadopago.SDK(os.environ.get('MP_ACCESS_TOKEN'))

    # Crear la preferencia de pago
    preference_data = {
        "items": [
            {
                "title": product.title,
                "quantity": 1,
                "unit_price": float(product.price),
                "currency_id": "MXN"  # Cambia a tu moneda local
            }
        ],
        "back_urls": {
            "success": request.build_absolute_uri('/'),
            "failure": request.build_absolute_uri('/'),
            "pending": request.build_absolute_uri('/'),
        },
        "auto_return": "approved",
    }

    preference_response = sdk.preference().create(preference_data)
    preference_id = preference_response["response"]["id"]

    return render(request, 'marketplace/product_detail.html', {
        'product': product,
        'preference_id': preference_id,
        'public_key': os.environ.get('MP_PUBLIC_KEY')
    })

def crear_pago(request, product_id):
    product = get_object_or_404(IndustrialProduct, id=product_id)
    
    # Configura tus credenciales (Usa variables de entorno en Render)
    sdk = mercadopago.SDK("TU_ACCESS_TOKEN_AQUÍ")

    # Crea el ítem del producto
    preference_data = {
        "items": [
            {
                "title": product.title,
                "quantity": 1,
                "unit_price": float(product.price),
                "currency_id": "MXN" # O tu moneda local
            }
        ],
        "back_urls": {
            "success": request.build_absolute_uri('/'),
            "failure": request.build_absolute_uri('/'),
            "pending": request.build_absolute_uri('/'),
        },
        "auto_return": "approved",
    }

    preference_response = sdk.preference().create(preference_data)
    preference = preference_response["response"]
    
    # Pasamos el ID de la preferencia al template
    return render(request, 'marketplace/pago.html', {
        'preference_id': preference['id'],
        'product': product
    })

# 1. HOME
def home(request):
    products = IndustrialProduct.objects.all().order_by('-id')
    categories = Category.objects.all()
    return render(request, 'marketplace/home.html', {'products': products, 'categories': categories})

# 2. DETALLE
def product_detail(request, pk):
    product = get_object_or_404(IndustrialProduct, pk=pk)
    return render(request, 'marketplace/product_detail.html', {'product': product})

# 3. REGISTRO
def registro(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'marketplace/registro.html', {'form': form})

# 4. SUBIR
@login_required
def subir_producto(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            producto = form.save(commit=False)
            producto.seller = request.user
            producto.save()
            return redirect('home')
    else:
        form = ProductForm()
    return render(request, 'marketplace/subir_producto.html', {'form': form})

# 5. EDITAR
@login_required
def editar_producto(request, pk):
    producto = get_object_or_404(IndustrialProduct, pk=pk)
    if producto.seller != request.user:
        return redirect('home')
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=producto)
        if form.is_valid():
            form.save()
            return redirect('product_detail', pk=producto.pk)
    else:
        form = ProductForm(instance=producto)
    return render(request, 'marketplace/subir_producto.html', {'form': form, 'editando': True})

# 6. BORRAR
@login_required
def borrar_producto(request, pk):
    producto = get_object_or_404(IndustrialProduct, pk=pk)
    if producto.seller == request.user:
        producto.delete()
        messages.success(request, "Producto eliminado.")
    return redirect('home')

# 7. FILTRO CATEGORÍA
def category_detail(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    products = IndustrialProduct.objects.filter(category=category)

    return render(request, 'marketplace/home.html', {'products': products, 'selected_category': category})
    
def pago_exitoso(request):
    return render(request, 'marketplace/pago_exitoso.html')


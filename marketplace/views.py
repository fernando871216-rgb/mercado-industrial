import os
import mercadopago
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from .models import IndustrialProduct, Category
from .forms import RegistroForm, ProductoForm

# 1. VISTA DE INICIO (HOME)
def home(request):
    products = IndustrialProduct.objects.all().order_by('-created_at')
    return render(request, 'marketplace/home.html', {'products': products})

# 2. DETALLE DEL PRODUCTO + MERCADO PAGO
def detalle_producto(request, product_id):
    product = get_object_or_404(IndustrialProduct, id=product_id)
    
    # Configurar SDK de Mercado Pago con tu Token de Render
    sdk = mercadopago.SDK(os.environ.get('MP_ACCESS_TOKEN'))

    # Crear preferencia de pago
    preference_data = {
        "items": [
            {
                "title": product.title,
                "quantity": 1,
                "unit_price": float(product.price),
                "currency_id": "MXN"  # Cambia a tu moneda si es necesario
            }
        ],
        "back_urls": {
            "success": request.build_absolute_uri('/pago-exitoso/'),
            "failure": request.build_absolute_uri('/'),
            "pending": request.build_absolute_uri('/'),
        },
        "auto_return": "approved",
    }

    preference_response = sdk.preference().create(preference_data)
    preference_id = preference_response["response"]["id"]
    print(f"Public Key: {os.environ.get('MP_PUBLIC_KEY')}")

    return render(request, 'marketplace/product_detail.html', {
        'product': product,
        'preference_id': preference_id,
        'public_key': os.environ.get('MP_PUBLIC_KEY')
    })

# 3. PÁGINA DE ÉXITO TRAS EL PAGO
def pago_exitoso(request):
    return render(request, 'marketplace/pago_exitoso.html')

# 4. SUBIR PRODUCTO (Requiere estar logueado)
@login_required
def subir_producto(request):
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES)
        if form.is_valid():
            producto = form.save(commit=False)
            producto.seller = request.user
            producto.save() # Aquí se sube la imagen a Cloudinary automáticamente
            return redirect('home')
    else:
        form = ProductoForm()
    return render(request, 'marketplace/subir_producto.html', {'form': form})

# 5. REGISTRO DE NUEVOS USUARIOS
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

# 6. FILTRO POR CATEGORÍA
def category_detail(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    products = IndustrialProduct.objects.filter(category=category)
    return render(request, 'marketplace/home.html', {'products': products, 'category': category})

# 7. EDITAR Y BORRAR (Opcionales para gestión)
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
    return redirect('home')


import os
import mercadopago
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from .models import IndustrialProduct, Category
from .forms import RegistroForm, ProductoForm
from django.shortcuts import get_object_or_404, render

# 1. VISTA DE INICIO (HOME)
def home(request):
    products = IndustrialProduct.objects.all().order_by('-created_at')
    return render(request, 'marketplace/home.html', {'products': products})

def detalle_producto(request, product_id):
    product = get_object_or_404(IndustrialProduct, id=product_id)
    
    # 1. Obtener llaves de las variables de entorno de Render
    access_token = os.environ.get('MP_ACCESS_TOKEN')
    public_key = os.environ.get('MP_PUBLIC_KEY')

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
            "back_urls": {
                "success": request.build_absolute_uri('/pago-exitoso/'),
                "failure": request.build_absolute_uri('/'),
                "pending": request.build_absolute_uri('/'),
            },
            "auto_return": "approved",
        }

        preference_response = sdk.preference().create(preference_data)
        
        # Verificamos si la respuesta fue exitosa antes de pedir el ID
        if "response" in preference_response:
            preference_id = preference_response["response"]["id"]
        else:
            preference_id = None
            print("Error en Mercado Pago:", preference_response)

    except Exception as e:
        print(f"Error de conexión: {e}")
        preference_id = None

    return render(request, 'marketplace/product_detail.html', {
        'product': product,
        'preference_id': preference_id,
        'public_key': public_key
    })

# 3. PÁGINA DE ÉXITO TRAS EL PAGO
def pago_exitoso(request):
    # Obtenemos el ID del producto que mandamos en la URL (external_reference)
    # Si no lo pasaste en la preferencia, podemos intentar obtenerlo de los parámetros
    producto_id = request.GET.get('external_reference')
    
    if producto_id:
        producto = get_object_or_404(IndustrialProduct, id=producto_id)
        if producto.stock > 0:
            producto.stock -= 1  # Restamos uno al inventario
            producto.save()
            
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

def detalle_producto(request, product_id):
    product = get_object_or_404(IndustrialProduct, id=product_id)
    preference_id = None
    public_key = os.environ.get('MP_PUBLIC_KEY')

    # SOLO creamos la preferencia si el usuario ha iniciado sesión
    if request.user.is_authenticated:
        try:
            sdk = mercadopago.SDK(os.environ.get('MP_ACCESS_TOKEN'))
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
                    "success": request.build_absolute_uri('/pago-exitoso/'),
                    "failure": request.build_absolute_uri('/'),
                },
                "auto_return": "approved",
            }
            preference_response = sdk.preference().create(preference_data)
            preference_id = preference_response["response"]["id"]
        except Exception as e:
            print(f"Error MP: {e}")

    return render(request, 'marketplace/product_detail.html', {
        'product': product,
        'preference_id': preference_id,
        'public_key': public_key
    })

@login_required
def borrar_producto(request, pk):
    producto = get_object_or_404(IndustrialProduct, pk=pk, seller=request.user)
    producto.delete()
    return redirect('home')

@login_required
def mi_inventario(request):
    # Filtramos los productos donde el vendedor es el usuario actual
    productos = IndustrialProduct.objects.filter(seller=request.user).order_by('-created_at')
    return render(request, 'marketplace/mi_inventario.html', {'productos': productos})




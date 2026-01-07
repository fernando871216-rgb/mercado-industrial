from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib import messages
from .models import Product, Category
from .forms import ProductForm
import mercadopago

def home(request):
    categorias = Category.objects.all()
    categoria_id = request.GET.get('categoria')
    
    if categoria_id:
        productos = Product.objects.filter(category_id=categoria_id)
    else:
        productos = Product.objects.all()

    # Configuración de Mercado Pago
    sdk = mercadopago.SDK("APP_USR-8745749455028291-010612-0bf761bcaa29732f502581cc416ff981-3116392416")
    
    for p in productos:
        comision = float(p.price) * 0.10
        preference_data = {
            "items": [{"title": p.title, "quantity": 1, "unit_price": float(p.price)}],
            "marketplace_fee": comision,
            "back_urls": {
                "success": "https://mercado-industrial.onrender.com/",
                "failure": "https://mercado-industrial.onrender.com/",
                "pending": "https://mercado-industrial.onrender.com/",
            },
            "auto_return": "approved",
        }
        preference_response = sdk.preference().create(preference_data)
        response = preference_response["response"]
        p.pago_url = response.get("init_point", "#")

    return render(request, 'marketplace/index.html', {
        'productos': productos, 
        'categorias': categorias
    })

def registro(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save() # Guardamos y obtenemos el usuario
            username = form.cleaned_data.get('username')
            messages.success(request, f'Cuenta creada para {username}. Ya puedes iniciar sesión.')
            return redirect('login')
        else:
            # Si el formulario no es válido (ej. contraseña corta), 
            # avisamos al usuario
            messages.error(request, "Hubo un error en el registro. Revisa los datos.")
    else:
        form = UserCreationForm()
    return render(request, 'marketplace/registro.html', {'form': form})


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

@login_required
def borrar_producto(request, product_id):
    producto = get_object_or_404(Product, id=product_id)
    if request.user == producto.seller or request.user.is_superuser:
        producto.delete()
    return redirect('home')
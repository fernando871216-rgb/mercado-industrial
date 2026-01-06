from django.shortcuts import render
import mercadopago

from django.shortcuts import get_object_ some_object, redirect
from django.contrib.auth.decorators import login_required
from .models import Product

@login_required
def borrar_producto(request, product_id):
    # Buscamos el producto por su ID
    producto = get_object_or_404(Product, id=product_id)
    
    # Verificamos si el que intenta borrar es el dueño o es un superusuario (tú)
    if request.user == producto.seller or request.user.is_superuser:
        producto.delete()
    
    return redirect('home')

def home(request):
    # 1. Configurar Mercado Pago con tu Token
    sdk = mercadopago.SDK("APP_USR-8745749455028291-010612-0bf761bcaa29732f502581cc416ff981-3116392416")
    
    # 2. Traer los productos
    from .models import Product
    productos = Product.objects.all()
    
    # 3. Preparar los productos con su link de pago
    for p in productos:
        # Calculamos tu comisión (ej. 10%)
        comision = float(p.price) * 0.10
        
        preference_data = {
            "items": [
                {
                    "title": p.title,
                    "quantity": 1,
                    "unit_price": float(p.price),
                }
            ],
            # ESTA ES LA MAGIA: Mercado Pago te separa esta parte a ti
            "marketplace_fee": comision,
            "back_urls": {
                # CAMBIA ESTO por tu link de Render:
                "success": "https://mercado-industrial.onrender.com/", 
                "failure": "https://mercado-industrial.onrender.com/",
                "pending": "https://mercado-industrial.onrender.com/",
            },
            "auto_return": "approved",
        }
        
        preference_response = sdk.preference().create(preference_data)
        response = preference_response["response"]
        
        # Esto nos imprimirá el error real en la terminal negra si algo falla
        if "init_point" not in response:
            print("ERROR DE MERCADO PAGO:", response)
            p.pago_url = "#"
        else:
            p.pago_url = response["init_point"]

    return render(request, 'marketplace/index.html', {'productos': productos})

from .forms import ProductForm
from django.shortcuts import redirect



def subir_producto(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            # Guardamos el producto y le asignamos el usuario actual
            producto = form.save(commit=False)
            producto.seller = request.user
            producto.save()
            return redirect('home')
    else:
        form = ProductForm()
    return render(request, 'marketplace/subir_producto.html', {'form': form})

from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login

def registro(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user) # Inicia sesión automáticamente tras registrarse
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'marketplace/registro.html', {'form': form})
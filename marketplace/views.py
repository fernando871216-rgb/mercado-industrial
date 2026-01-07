from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import IndustrialProduct, Category
from .forms import ProductForm
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
    
# Vista de la página principal: Muestra todos los productos y categorías
def home(request):
    # Obtenemos todos los productos de la nueva tabla
    products = IndustrialProduct.objects.all().order_by('-id')
    # Obtenemos todas las categorías para el menú lateral o filtros
    categories = Category.objects.all()
    
    context = {
        'products': products,
        'categories': categories,
    }
    return render(request, 'marketplace/home.html', context)

# Vista de detalle: Muestra la información completa de un solo equipo
def product_detail(request, pk):
    # Buscamos el producto por su ID (Primary Key)
    product = get_object_or_404(IndustrialProduct, pk=pk)
    return render(request, 'marketplace/product_detail.html', {'product': product})

# Vista para filtrar por categoría (Opcional, muy útil para mercados)
def category_detail(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    products = IndustrialProduct.objects.filter(category=category).order_by('-id')
    categories = Category.objects.all()
    
    context = {
        'category': category,
        'products': products,
        'categories': categories,
    }
    return render(request, 'marketplace/home.html', context)

@login_required
def subir_producto(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES) # request.FILES es vital para la imagen
        if form.is_valid():
            producto = form.save(commit=False)
            producto.seller = request.user # Asignamos al usuario actual como vendedor
            producto.save()
            return redirect('home')
    else:
        form = ProductForm()
    
    return render(request, 'marketplace/subir_producto.html', {'form': form})




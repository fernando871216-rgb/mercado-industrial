from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import IndustrialProduct, Category

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

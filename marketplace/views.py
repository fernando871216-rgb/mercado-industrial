from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib import messages
from .models import IndustrialProduct, Category
from .forms import ProductForm

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




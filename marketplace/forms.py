from django import forms
from .models import Product

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['title', 'brand', 'part_number', 'description', 'price', 'stock', 'image']
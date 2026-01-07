from django import forms
from .models import IndustrialProduct

class ProductForm(forms.ModelForm):
    class Meta:
        model = IndustrialProduct
        # Excluimos 'seller' porque lo asignaremos automáticamente al usuario que inició sesión
        fields = ['title', 'brand', 'part_number', 'description', 'price', 'stock', 'image', 'category']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

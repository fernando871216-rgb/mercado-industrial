from django import forms
from .models import IndustrialProduct

class ProductForm(forms.ModelForm):
    class Meta:
        model = IndustrialProduct
        # Definimos los campos que el usuario verá en la web
        fields = ['title', 'brand', 'part_number', 'description', 'price', 'stock', 'image', 'category']
        # Personalizamos los widgets para que se vean mejor
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Describe las especificaciones técnicas...'}),
            'title': forms.TextInput(attrs={'placeholder': 'Ej. PLC Allen Bradley 1756'}),
        }

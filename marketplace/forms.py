from django import forms
from django.contrib.auth.models import User
from .models import IndustrialProduct, Category, Profile
import re

# --- FORMULARIOS DE PERFIL ---
class UserUpdateForm(forms.ModelForm):
    first_name = forms.CharField(label="Nombre(s)", required=True)
    last_name = forms.CharField(label="Apellidos", required=True)
    email = forms.EmailField(label="Correo Electrónico", required=True)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
        labels = {
            'username': 'Nombre de Usuario',
        }
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

class ProfileUpdateForm(forms.ModelForm):
    # CORRECCIÓN: Cambiamos phone_number por phone para que coincida con el MODELO
    phone = forms.CharField(label="Número de WhatsApp", required=True)

    class Meta:
        model = Profile
        # CORRECCIÓN: Aquí también debe ser phone
        fields = ['phone', 'address', 'clabe', 'banco', 'beneficiario'] 
        widgets = {
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 5512345678'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Dirección completa'}),
            'phone': forms.TextInput(attrs={'placeholder': '10 dígitos sin espacios'}),
            'clabe': forms.TextInput(attrs={'placeholder': '18 dígitos de tu tarjeta/cuenta'}),
            'banco': forms.TextInput(attrs={'placeholder': 'Ej: BBVA, Santander...'}),
            'beneficiario': forms.TextInput(attrs={'placeholder': 'Nombre del titular de la cuenta'}),
            'address': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Calle, número, colonia y CP'})
        }

    # Validación corregida para el nombre del campo 'phone'
    def clean_phone(self):
        phone_data = self.cleaned_data.get('phone')
        # Quita espacios o guiones
        phone_data = re.sub(r'\D', '', phone_data) 
        if len(phone_data) != 10:
            raise forms.ValidationError("El número de celular debe tener exactamente 10 dígitos.")
        return phone_data

# --- 1. FORMULARIO DE REGISTRO ---
class RegistroForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Contraseña'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirmar Contraseña'}))

    class Meta:
        model = User
        fields = ['username', 'email', 'password']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de usuario'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Correo electrónico'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Este correo ya está registrado. Intenta con otro.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password != confirm_password:
            raise forms.ValidationError("Las contraseñas no coinciden")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user

# --- 2. FORMULARIO DE PRODUCTOS ---
class ProductoForm(forms.ModelForm):
    class Meta:
        model = IndustrialProduct
        fields = ['title', 'brand', 'part_number', 'description', 'price', 'stock', 'category', 'image']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'brand': forms.TextInput(attrs={'class': 'form-control'}),
            'part_number': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
        }


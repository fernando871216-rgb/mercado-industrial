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
    # Definimos el campo phone explícitamente para asegurar la validación
    phone = forms.CharField(label="Número de WhatsApp", required=False)

    class Meta:
        model = Profile
        # IMPORTANTE: Estos nombres deben coincidir EXACTAMENTE con tu modelo
        fields = ['phone', 'address', 'clabe', 'banco', 'beneficiario']
        
        widgets = {
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '10 dígitos'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'clabe': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '18 dígitos'}),
            'banco': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del banco'}),
            'beneficiario': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del beneficiario'}),
        }

    def clean_phone(self):
        phone_data = self.cleaned_data.get('phone')
        if phone_data:
            phone_data = re.sub(r'\D', '', phone_data)
            if len(phone_data) != 10:
                raise forms.ValidationError("El número debe tener 10 dígitos.")
        return phone_data

    def clean_clabe(self):
        clabe_data = self.cleaned_data.get('clabe')
        if clabe_data:
            clabe_data = re.sub(r'\D', '', clabe_data)
            if len(clabe_data) != 18:
                raise forms.ValidationError("La CLABE debe tener 18 dígitos.")
        return clabe_data
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




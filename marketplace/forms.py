from django import forms
from django.contrib.auth.models import User
from .models import IndustrialProduct, Category, Profile
import re

# --- 1. FORMULARIO DE PERFIL (Antes ProfileUpdateForm) ---
class ProfileForm(forms.ModelForm):
    phone = forms.CharField(required=False)
    clabe = forms.CharField(required=False)
    banco = forms.CharField(required=False)
    beneficiario = forms.CharField(required=False)
    address = forms.CharField(required=False, widget=forms.Textarea)

    class Meta:
        model = Profile
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

# --- 2. FORMULARIO DE REGISTRO ---
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
            raise forms.ValidationError("Este correo ya está registrado.")
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

# --- 3. FORMULARIO DE PRODUCTOS (Corregido: ProductForm con campos de envío) ---
class ProductForm(forms.ModelForm):
    class Meta:
        model = IndustrialProduct
        fields = [
            'title', 'brand', 'part_number', 'description', 'price', 'ficha_tecnica', 
            'stock', 'category', 'image','image2', 'image3', 'peso', 'largo', 'ancho', 'alto', 'cp_origen'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'brand': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'peso': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'KG'}),
            'largo': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'CM'}),
            'ancho': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'CM'}),
            'alto': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'CM'}),
            'cp_origen': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '5 dígitos'}),
        }

# --- 4. FORMULARIO PARA EDITAR DATOS BÁSICOS DEL USUARIO ---
class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }




from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from cloudinary.models import CloudinaryField
from decimal import Decimal

# --- MODELO DE CATEGORÍA ---
class Category(models.Model):
    name = models.CharField(max_length=100)
    
    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

# --- MODELO DE PRODUCTO INDUSTRIAL ---
class IndustrialProduct(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    brand = models.CharField(max_length=100, blank=True, null=True)
    part_number = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=12, decimal_places=2)
    stock = models.IntegerField(default=1)
    image = CloudinaryField('image', blank=True, null=True)
    image2 = CloudinaryField('image', blank=True, null=True)
    image3 = CloudinaryField('image', blank=True, null=True)
    ficha_tecnica = CloudinaryField('raw', folder='fichas_tecnicas/')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    peso = models.DecimalField(max_digits=6, decimal_places=2, default=5.0, help_text="Peso estimado en Kg")
    largo = models.IntegerField(default=30, help_text="Largo en cm")
    ancho = models.IntegerField(default=30, help_text="Ancho en cm")
    alto = models.IntegerField(default=30, help_text="Alto en cm")
    cp_origen = models.CharField(max_length=5, default="00000", help_text="Código Postal donde está el equipo")
    

    def __str__(self):
        return self.title

# --- MODELO DE PERFIL DE USUARIO ---
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    clabe = models.CharField(max_length=18, null=True, blank=True)
    banco = models.CharField(max_length=50, null=True, blank=True)
    beneficiario = models.CharField(max_length=100, null=True, blank=True)
    
    def __str__(self):
        return f"Perfil de {self.user.username}"

# --- MODELO DE VENTA (SALE) ---
class Sale(models.Model):
    product = models.ForeignKey(IndustrialProduct, on_delete=models.CASCADE)
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='compras')
    #metodo_entrega = models.CharField(max_length=20, default='recoleccion')
    price = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='pendiente')
    pagado_a_vendedor = models.BooleanField(default=False)
    payment_id = models.CharField(max_length=100, blank=True, null=True)
    ganancia_neta = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    recibido_por_comprador = models.BooleanField(default=False)
    tracking_number = models.CharField(max_length=100, blank=True, null=True, verbose_name="Número de Guía")
    shipping_company = models.CharField(max_length=50, blank=True, null=True, verbose_name="Paquetería")

    def __str__(self):
        return f"Venta de {self.product.title}"

    # --- FÓRMULAS FINANCIERAS PARA EL PANEL ---

    def get_gateway_cost(self):
        """Calcula costo de Mercado Pago: 3.49% + $4.00 + IVA del costo"""
        comision_porcentaje = self.price * Decimal('0.0349')
        fijo = Decimal('4.00')
        iva = (comision_porcentaje + fijo) * Decimal('0.16')
        total = comision_porcentaje + fijo + iva
        return total.quantize(Decimal('0.01'))

    def get_platform_commission(self):
        """Calcula la comisión de INITRE (5%)"""
        return (self.price * Decimal('0.05')).quantize(Decimal('0.01'))

    def get_net_amount(self):
        """Calcula el monto final que recibe el vendedor"""
        return (self.price - self.get_gateway_cost() - self.get_platform_commission()).quantize(Decimal('0.01'))

# --- SEÑALES (SIGNALS) ---
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    try:
        instance.profile.save()
    except Profile.DoesNotExist:
        Profile.objects.create(user=instance)















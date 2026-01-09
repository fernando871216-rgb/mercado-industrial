from django.db import models
from django.contrib.auth.models import User
# ESTAS LÍNEAS FALTABAN (Son las que causaban el error de compilación):
from django.db.models.signals import post_save
from django.dispatch import receiver

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
    description = models.TextField()
    price = models.DecimalField(max_digits=12, decimal_places=2)
    image = models.ImageField(upload_to='products/')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

# --- MODELO DE PERFIL DE USUARIO ---
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)

    def __str__(self):
        return f"Perfil de {self.user.username}"

# --- MODELO DE VENTA (SALE) ---
class Sale(models.Model):
    product = models.ForeignKey(IndustrialProduct, on_delete=models.CASCADE)
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='compras')
    price = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='pendiente')
    # Campo que agregamos para tu control de pagos:
    pagado_a_vendedor = models.BooleanField(default=False)

    def __str__(self):
        return f"Venta de {self.product.title}"

# --- SEÑALES (SIGNALS) ---
# Esto crea el perfil automáticamente cuando un usuario se registra
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    # Usamos try/except para evitar errores si el perfil no existe
    try:
        instance.profile.save()
    except Profile.DoesNotExist:
        Profile.objects.create(user=instance)

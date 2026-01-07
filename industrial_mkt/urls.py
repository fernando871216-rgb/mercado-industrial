from django.contrib import admin
from django.urls import path
from marketplace import views  # <--- ESTA LÍNEA ES LA QUE FALTA
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('vender/', views.subir_producto, name='vender'),
    path('registro/', views.registro, name='registro'),
    path('borrar/<int:product_id>/', views.borrar_producto, name='borrar_producto'),
]

# Esto es para que se vean las fotos que subes
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
from marketplace.views import home, subir_producto # Añade subir_producto

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('vender/', subir_producto, name='vender'), # Nueva ruta
]

from marketplace.views import home, subir_producto, registro # Importa registro

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('vender/', views.subir_producto, name='vender'), # El 'name' es vital,
    path('registro/', registro, name='registro'), # Nueva ruta
]

from marketplace.views import home, subir_producto, registro, borrar_producto # Añade borrar_producto

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('vender/', subir_producto, name='vender'),
    path('registro/', registro, name='registro'),
    # Nueva ruta que recibe el ID del producto a borrar
    path('borrar/<int:product_id>/', borrar_producto, name='borrar_producto'),
]
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Ruta para el panel de administración
    path('admin/', admin.site.urls),
    
    # Redirige todo el tráfico de la web a la app marketplace
    path('', include('marketplace.urls')), 
]

# Configuración para servir archivos multimedia (imágenes de productos)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    # En Render (producción), esto ayuda a que las imágenes se sirvan si usas WhiteNoise
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

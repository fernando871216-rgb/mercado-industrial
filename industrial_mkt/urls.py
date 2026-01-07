from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views # Importa las vistas de autenticación

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('marketplace.urls')),
    # Agrega esta línea para el logout:
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
]


# Configuración para servir archivos multimedia (imágenes de productos)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    # En Render (producción), esto ayuda a que las imágenes se sirvan si usas WhiteNoise
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


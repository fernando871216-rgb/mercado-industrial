from . import views
from django.contrib import admin
from django.urls import path, include # Importante agregar 'include'
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.home, name='home'),
    path('producto/<int:pk>/', views.product_detail, name='product_detail'),
    path('subir/', views.subir_producto, name='subir_producto'),
    path('editar/<int:pk>/', views.editar_producto, name='editar_producto'),
    path('borrar/<int:pk>/', views.borrar_producto, name='borrar_producto'),
    path('registro/', views.registro, name='registro'),
    path('categoria/<int:category_id>/', views.category_detail, name='category_detail'),
]

# Esto es para que las imágenes de los productos se vean en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
    # Gestión de Productos
    path('subir/', views.subir_producto, name='subir_producto'),
    path('editar/<int:pk>/', views.editar_producto, name='editar_producto'),
    path('borrar/<int:pk>/', views.borrar_producto, name='borrar_producto'),
    
    # Usuarios
    path('registro/', views.registro, name='registro'),
    path('categoria/<int:category_id>/', views.category_detail, name='category_detail'),
]


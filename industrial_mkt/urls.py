from django.urls import path
from . import views

urlpatterns = [
    # Inicio y Detalles
    path('', views.home, name='home'),
    path('producto/<int:pk>/', views.product_detail, name='product_detail'),
    
    # Gestión de Productos
    path('subir/', views.subir_producto, name='subir_producto'),
    path('editar/<int:pk>/', views.editar_producto, name='editar_producto'),
    path('borrar/<int:pk>/', views.borrar_producto, name='borrar_producto'),
    
    # Usuarios
    path('registro/', views.registro, name='registro'),
    path('categoria/<int:category_id>/', views.category_detail, name='category_detail'),
]

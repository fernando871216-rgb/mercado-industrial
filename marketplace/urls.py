from django.urls import path
from . import views

urlpatterns = [
    # Página principal
    path('', views.home, name='home'),
    
    # Detalle de producto
    path('producto/<int:pk>/', views.product_detail, name='product_detail'),
    path('producto/<int:product_id>/', views.detalle_producto, name='product_detail'),
    
    # Gestión de productos (requieren login)
    path('subir/', views.subir_producto, name='subir_producto'),
    path('editar/<int:pk>/', views.editar_producto, name='editar_producto'),
    path('borrar/<int:pk>/', views.borrar_producto, name='borrar_producto'),
    path('pago-exitoso/', views.pago_exitoso, name='pago_exitoso')
    
    # Usuarios y Filtros
    path('registro/', views.registro, name='registro'),
    path('categoria/<int:category_id>/', views.category_detail, name='category_detail'),

]


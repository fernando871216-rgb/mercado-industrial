from django.contrib import admin
from django.urls import path
from marketplace import views 

urlpatterns = [
    # Administración
    path('admin/', admin.site.urls),
    
    # Navegación Principal
    path('', views.home, name='home'),
    path('registro/', views.registro, name='registro'),
    
    # Detalle y Pagos (Mercado Pago)
    path('producto/<int:product_id>/', views.detalle_producto, name='product_detail'),
    path('pago-exitoso/', views.pago_exitoso, name='pago_exitoso'),
    
    # Gestión de productos
    path('subir/', views.subir_producto, name='subir_producto'),
    path('editar/<int:pk>/', views.editar_producto, name='editar_producto'),
    path('borrar/<int:pk>/', views.borrar_producto, name='borrar_producto'),
    
    # Filtros
    path('categoria/<int:category_id>/', views.category_detail, name='category_detail'),
]

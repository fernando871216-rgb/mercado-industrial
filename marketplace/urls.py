from django.urls import path
from django.contrib.auth import views as auth_views # Importamos las vistas de Django
from . import views

urlpatterns = [
    # Navegación y Usuarios
    path('', views.home, name='home'),
    path('registro/', views.registro, name='registro'),
    
    # LOGIN Y LOGOUT (Agregamos estas dos)
    path('login/', auth_views.LoginView.as_view(template_name='marketplace/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path('perfil/editar/', views.editar_perfil, name='editar_perfil'),
    
    # Detalle de Producto y Mercado Pago
    path('producto/<int:product_id>/', views.detalle_producto, name='product_detail'),
    path('pago-exitoso/', views.pago_exitoso, name='pago_exitoso'),
    path('pago-fallido/', views.pago_fallido, name='pago_fallido'),
    
    # Gestión de Productos
    path('subir/', views.subir_producto, name='subir_producto'),
    path('editar/<int:pk>/', views.editar_producto, name='editar_producto'),
    path('borrar/<int:pk>/', views.borrar_producto, name='borrar_producto'),
    path('mi-inventario/', views.mi_inventario, name='mi_inventario'),
    path('mis-compras/', views.mis_compras, name='mis_compras'),
    path('mis-ventas/', views.mis_ventas, name='mis_ventas'),
    
    # Filtros
    path('categoria/<int:category_id>/', views.category_detail, name='category_detail'),
]







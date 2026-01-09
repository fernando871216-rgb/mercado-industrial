from django.urls import path
from . import views

urlpatterns = [
    # Inicio y Detalles
    path('', views.home, name='home'),
    path('producto/<int:product_id>/', views.detalle_producto, name='product_detail'),
    path('categoria/<int:category_id>/', views.category_detail, name='category_detail'),

    # Perfil de Usuario
    path('registro/', views.registro, name='registro'),
    path('perfil/editar/', views.editar_perfil, name='editar_perfil'),

    # Inventario (CRUD)
    path('inventario/', views.mi_inventario, name='mi_inventario'),
    path('inventario/subir/', views.subir_producto, name='subir_producto'),
    path('inventario/editar/<int:pk>/', views.editar_producto, name='editar_producto'),
    path('inventario/borrar/<int:pk>/', views.borrar_producto, name='borrar_producto'),

    # Compras y Ventas
    path('compras/', views.mis_compras, name='mis_compras'),
    path('ventas/', views.mis_ventas, name='mis_ventas'),
    
    # Procesamiento de Pagos e Intenciones
    path('procesar-pago/<int:product_id>/', views.procesar_pago, name='procesar_pago'),
    path('pago-exitoso/', views.pago_exitoso, name='pago_exitoso'),
    path('pago-fallido/', views.pago_fallido, name='pago_fallido'),

    # Gestión de Estados (Aquí estaba el error corregido)
    path('venta/cambiar-estado/<int:venta_id>/', views.cambiar_estado_venta, name='cambiar_estado_venta'),
]

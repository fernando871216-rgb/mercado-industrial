from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from django.views.generic import TemplateView

urlpatterns = [
    path('', views.home, name='home'),
    path('producto/<int:product_id>/', views.detalle_producto, name='product_detail'),
    path('categoria/<int:category_id>/', views.category_detail, name='category_detail'),
    
    # SOLOENVÍOS
    path('cotizar-soloenvios/', views.cotizar_soloenvios, name='cotizar_soloenvios'),
    
    # MERCADO PAGO (Actualizado)
    # Cambiamos 'procesar_pago' por 'actualizar_pago' porque ese es el nombre en tu views.py
    path('actualizar-pago/', views.actualizar_pago, name='actualizar_pago'),
    path('mercadopago-webhook/', views.mercadopago_webhook, name='mercadopago_webhook'),
    
    # USUARIOS Y PRODUCTOS
    path('registro/', views.registro, name='registro'),
    path('perfil/editar/', views.editar_perfil, name='editar_perfil'),
    path('mi-inventario/', views.mi_inventario, name='mi_inventario'),
    path('subir-producto/', views.subir_producto, name='subir_producto'),
    path('producto/<int:pk>/editar/', views.editar_producto, name='editar_producto'),
    path('producto/<int:pk>/borrar/', views.borrar_producto, name='borrar_producto'),
    
    # VENTAS Y COMPRAS
    path('mis-compras/', views.mis_compras, name='mis_compras'),
    path('mis-ventas/', views.mis_ventas, name='mis_ventas'),
    path('venta/<int:venta_id>/actualizar-guia/', views.actualizar_guia, name='actualizar_guia'),
    path('venta/<int:venta_id>/confirmar/', views.confirmar_recepcion, name='confirmar_recepcion'),
    path('venta/<int:venta_id>/cancelar/', views.cancelar_venta, name='cancelar_venta'),
    
    # INTENCIÓN DE COMPRA (La que descuenta stock)
    path('producto/<int:product_id>/intencion/', views.crear_intencion_compra, name='crear_intencion_compra'),
    
    # RESULTADOS PAGO
    path('pago-exitoso/', views.pago_exitoso, name='pago_exitoso'),
    path('pago-fallido/', views.pago_fallido, name='pago_fallido'),
]




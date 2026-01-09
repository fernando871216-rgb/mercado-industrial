from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    # --- PÁGINAS PRINCIPALES ---
    path('', views.home, name='home'),
    path('producto/<int:product_id>/', views.detalle_producto, name='detalle_producto'),
    path('categoria/<int:category_id>/', views.category_detail, name='category_detail'),
    
    # --- CUENTA Y PERFIL ---
    path('registro/', views.registro, name='registro'),
    path('login/', auth_views.LoginView.as_view(template_name='marketplace/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path('perfil/editar/', views.editar_perfil, name='editar_perfil'),
    
    # --- INVENTARIO DEL VENDEDOR ---
    path('mis-productos/', views.mi_inventario, name='mi_inventario'),
    path('subir-producto/', views.subir_producto, name='subir_producto'),
    path('editar-producto/<int:pk>/', views.editar_producto, name='editar_producto'),
    path('borrar-producto/<int:pk>/', views.borrar_producto, name='borrar_producto'),
    
    # --- COMPRAS Y VENTAS ---
    path('mis-compras/', views.mis_compras, name='mis_compras'),
    path('mis-ventas/', views.mis_ventas, name='mis_ventas'),
    path('venta/estado/<int:venta_id>/', views.cambiar_estado_venta, name='cambiar_estado_venta'),
    path('procesar-pago/<int:product_id>/', views.procesar_pago, name='procesar_pago'),
    
    # --- RESULTADOS DE PAGO ---
    path('pago-exitoso/', views.pago_exitoso, name='pago_exitoso'),
    path('pago-fallido/', views.pago_fallido, name='pago_fallido'),
    
    # --- PANEL ADMINISTRATIVO (TU PANEL) ---
    path('panel-control/', views.panel_administrador, name='panel_admin'),
    path('marcar-pagado/<int:venta_id>/', views.marcar_como_pagado, name='marcar_como_pagado'),
]

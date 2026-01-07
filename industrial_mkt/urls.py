from django.contrib import admin
from django.urls import path
from marketplace import views 
from django.contrib.auth import views as auth_views # Importante para login/logout
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('vender/', views.subir_producto, name='vender'),
    path('registro/', views.registro, name='registro'),
    path('borrar/<int:product_id>/', views.borrar_producto, name='borrar_producto'),
    
    # Estas líneas definen las "direcciones" que le faltan a tu mapa
    path('login/', auth_views.LoginView.as_view(template_name='marketplace/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
from django.contrib import admin
from django.urls import path
from marketplace.views import home # Importamos tu vista

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'), # Página de inicio
]

from marketplace.views import home, subir_producto # Añade subir_producto

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('vender/', subir_producto, name='vender'), # Nueva ruta
]

from marketplace.views import home, subir_producto, registro # Importa registro

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('vender/', subir_producto, name='vender'),
    path('registro/', registro, name='registro'), # Nueva ruta
]

from marketplace.views import home, subir_producto, registro, borrar_producto # Añade borrar_producto

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('vender/', subir_producto, name='vender'),
    path('registro/', registro, name='registro'),
    # Nueva ruta que recibe el ID del producto a borrar
    path('borrar/<int:product_id>/', borrar_producto, name='borrar_producto'),
]
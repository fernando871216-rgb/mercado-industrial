from django.contrib import admin
from django.urls import path
from marketplace.views import home # Importamos tu vista

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'), # Página de inicio
]
from django.urls import path

from . import views

app_name = 'carrito'

urlpatterns = [
    path('', views.detalle, name='detalle'),
    path('agregar/<int:producto_id>/', views.agregar, name='agregar'),
    path('actualizar/<int:producto_id>/', views.actualizar, name='actualizar'),
    path('eliminar/<int:producto_id>/', views.eliminar, name='eliminar'),
    path('cupon/aplicar/', views.aplicar_cupon, name='aplicar_cupon'),
    path('cupon/quitar/', views.quitar_cupon, name='quitar_cupon'),
]

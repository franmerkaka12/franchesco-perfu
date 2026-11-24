from django.urls import path

from . import views

app_name = 'pedidos'

urlpatterns = [
    path('', views.mis_pedidos, name='mis_pedidos'),
    path('finalizar-compra/', views.checkout, name='checkout'),
    path('<int:pk>/', views.detalle, name='detalle'),
    path('<int:pk>/confirmado/', views.confirmacion, name='confirmacion'),
]

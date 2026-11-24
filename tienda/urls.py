from django.urls import path

from . import views

app_name = 'tienda'

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('productos/', views.catalogo, name='catalogo'),
    path('producto/<slug:slug>/', views.detalle, name='detalle'),
]

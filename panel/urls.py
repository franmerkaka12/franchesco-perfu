from django.urls import path

from . import views

app_name = 'panel'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),

    path('productos/', views.productos, name='productos'),
    path('productos/nuevo/', views.producto_crear, name='producto_crear'),
    path('productos/<int:pk>/editar/', views.producto_editar, name='producto_editar'),
    path('productos/<int:pk>/eliminar/', views.producto_eliminar, name='producto_eliminar'),
    path('marcas/ocultar/', views.marca_ocultar, name='marca_ocultar'),

    path('stock/', views.stock, name='stock'),
    path('stock/<int:pk>/', views.stock_actualizar, name='stock_actualizar'),

    path('categorias/', views.categorias, name='categorias'),
    path('categorias/nueva/', views.categoria_crear, name='categoria_crear'),
    path('categorias/<int:pk>/editar/', views.categoria_editar, name='categoria_editar'),
    path('categorias/<int:pk>/eliminar/', views.categoria_eliminar, name='categoria_eliminar'),

    path('pedidos/', views.pedidos, name='pedidos'),
    path('pedidos/<int:pk>/', views.pedido_detalle, name='pedido_detalle'),

    path('usuarios/', views.usuarios, name='usuarios'),
    path('usuarios/<int:pk>/', views.usuario_editar, name='usuario_editar'),

    path('promociones/', views.promociones, name='promociones'),
    path('promociones/nueva/', views.promocion_crear, name='promocion_crear'),
    path('promociones/<int:pk>/editar/', views.promocion_editar, name='promocion_editar'),
    path('promociones/<int:pk>/alternar/', views.promocion_alternar, name='promocion_alternar'),
    path('cupones/nuevo/', views.cupon_crear, name='cupon_crear'),
    path('cupones/<int:pk>/editar/', views.cupon_editar, name='cupon_editar'),
    path('cupones/<int:pk>/alternar/', views.cupon_alternar, name='cupon_alternar'),
]

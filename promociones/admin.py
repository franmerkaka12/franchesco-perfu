from django.contrib import admin

from .models import Cupon, Promocion


@admin.register(Promocion)
class PromocionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'porcentaje_descuento', 'fecha_inicio', 'fecha_fin', 'activa')
    filter_horizontal = ('productos',)


@admin.register(Cupon)
class CuponAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'tipo', 'valor', 'fecha_vencimiento', 'usos', 'usos_maximos', 'activo')

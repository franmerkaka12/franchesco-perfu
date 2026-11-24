from django.contrib import admin

from .models import DetallePedido, Pago, Pedido


class DetalleInline(admin.TabularInline):
    model = DetallePedido
    extra = 0
    readonly_fields = ('producto', 'nombre_producto', 'marca', 'cantidad', 'precio_unitario', 'subtotal')


class PagoInline(admin.StackedInline):
    model = Pago
    extra = 0


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'usuario', 'fecha', 'estado', 'total')
    list_filter = ('estado', 'fecha')
    search_fields = ('usuario__email', 'apellido')
    inlines = [DetalleInline, PagoInline]

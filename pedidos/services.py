"""Lógica de negocio del proceso de compra (CU-17 a CU-22).

Todas las operaciones se ejecutan dentro de una transacción para mantener la
integridad entre pedidos y stock (RNF-05).
"""
from django.db import transaction
from django.db.models import F

from promociones.models import Cupon
from tienda.models import Producto

from .models import DetallePedido, Pago, Pedido


class CompraError(Exception):
    """Error de negocio al confirmar la compra. `errores` es una lista de mensajes."""

    def __init__(self, errores):
        self.errores = errores if isinstance(errores, list) else [errores]
        super().__init__('; '.join(self.errores))


CAMPOS_ENTREGA = ('nombre', 'apellido', 'telefono', 'direccion', 'ciudad', 'codigo_postal', 'notas')


@transaction.atomic
def crear_pedido(usuario, carrito, datos):
    lineas = list(carrito)
    if not lineas:
        raise CompraError('Tu carrito está vacío.')

    # CU-18: verificar disponibilidad bloqueando las filas de producto
    ids = [l.producto.pk for l in lineas]
    productos = {p.pk: p for p in Producto.objects.select_for_update().filter(pk__in=ids, activo=True)}
    errores = []
    for linea in lineas:
        actual = productos.get(linea.producto.pk)
        disponible = actual.stock if actual else 0
        if linea.cantidad > disponible:
            errores.append(
                f'{linea.producto.marca} {linea.producto.nombre}: pediste {linea.cantidad} '
                f'y hay {disponible} disponible(s).'
            )
    if errores:
        raise CompraError(errores)

    # CU-20 / CU-36: calcular importe final y revalidar el cupón
    subtotal = carrito.subtotal
    cupon = carrito.cupon
    descuento = 0
    if cupon:
        cupon = Cupon.objects.select_for_update().get(pk=cupon.pk)
        if error := cupon.validar(subtotal):
            raise CompraError(error)
        descuento = cupon.calcular_descuento(subtotal)

    # CU-21: registrar pedido
    pedido = Pedido.objects.create(
        usuario=usuario,
        email=usuario.email,
        subtotal=subtotal,
        descuento=descuento,
        total=subtotal - descuento,
        cupon=cupon,
        **{c: datos.get(c, '') for c in CAMPOS_ENTREGA},
    )
    for linea in lineas:
        DetallePedido.objects.create(
            pedido=pedido,
            producto=productos[linea.producto.pk],
            nombre_producto=f'{linea.producto.nombre} {linea.producto.volumen_ml} ml',
            marca=linea.producto.marca,
            cantidad=linea.cantidad,
            precio_unitario=linea.precio_unitario,
        )
        # CU-22: actualizar stock
        Producto.objects.filter(pk=linea.producto.pk).update(stock=F('stock') - linea.cantidad)

    if cupon:
        Cupon.objects.filter(pk=cupon.pk).update(usos=F('usos') + 1)

    # CU-19: registrar el medio de pago seleccionado
    Pago.objects.create(pedido=pedido, metodo=datos['metodo_pago'], monto=pedido.total)
    return pedido


@transaction.atomic
def cambiar_estado(pedido, nuevo_estado):
    """Cambia el estado de un pedido. Al cancelar se devuelve el stock y el uso del cupón."""
    pedido = Pedido.objects.select_for_update().get(pk=pedido.pk)
    if pedido.estado == Pedido.Estado.CANCELADO:
        raise CompraError('El pedido ya está cancelado y no puede modificarse.')
    if nuevo_estado == pedido.estado:
        return pedido

    if nuevo_estado == Pedido.Estado.CANCELADO:
        for detalle in pedido.detalles.select_related('producto'):
            if detalle.producto_id:
                Producto.objects.filter(pk=detalle.producto_id).update(stock=F('stock') + detalle.cantidad)
        if pedido.cupon_id:
            Cupon.objects.filter(pk=pedido.cupon_id, usos__gt=0).update(usos=F('usos') - 1)
        Pago.objects.filter(pedido=pedido).update(estado=Pago.Estado.ANULADO)
    elif nuevo_estado != Pedido.Estado.PENDIENTE:
        Pago.objects.filter(pedido=pedido).update(estado=Pago.Estado.APROBADO)

    pedido.estado = nuevo_estado
    pedido.save(update_fields=['estado'])
    return pedido

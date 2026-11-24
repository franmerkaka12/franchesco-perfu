"""Carrito de compras guardado en la sesión.

Permite que visitantes y clientes agreguen productos (CU-12 a CU-16). Al iniciar
sesión el contenido del carrito se conserva, por lo que el visitante no pierde
su selección al registrarse para comprar.
"""
from dataclasses import dataclass
from decimal import Decimal

from tienda.models import Producto


@dataclass
class LineaCarrito:
    producto: Producto
    cantidad: int

    @property
    def precio_unitario(self):
        return self.producto.precio_final

    @property
    def subtotal(self):
        return self.precio_unitario * self.cantidad

    @property
    def stock_insuficiente(self):
        return self.cantidad > self.producto.stock


class Carrito:
    SESSION_KEY = 'carrito'
    CUPON_KEY = 'cupon_id'

    def __init__(self, request):
        self.session = request.session
        datos = self.session.get(self.SESSION_KEY)
        if not isinstance(datos, dict):
            datos = self.session[self.SESSION_KEY] = {}
        self.items = datos
        self._lineas = None
        self._cupon = None

    # --- Operaciones ---
    def _guardar(self):
        self.session.modified = True
        self._lineas = None
        self._cupon = None

    def cantidad_de(self, producto_id):
        return self.items.get(str(producto_id), 0)

    def agregar(self, producto, cantidad=1, reemplazar=False):
        """CU-12 / CU-13. Devuelve (ok, mensaje)."""
        if not producto.disponible:
            self.quitar(producto.pk)
            return False, f'{producto.nombre} no tiene stock disponible.'
        cantidad = max(int(cantidad), 0)
        nueva = cantidad if reemplazar else self.cantidad_de(producto.pk) + cantidad
        if nueva <= 0:
            self.quitar(producto.pk)
            return True, f'{producto.nombre} se quitó del carrito.'
        if nueva > producto.stock:
            self.items[str(producto.pk)] = producto.stock
            self._guardar()
            return False, f'Solo hay {producto.stock} unidad(es) disponibles de {producto.nombre}.'
        self.items[str(producto.pk)] = nueva
        self._guardar()
        if reemplazar:
            return True, 'Cantidad actualizada.'
        return True, f'{producto.marca} {producto.nombre} se agregó al carrito.'

    def quitar(self, producto_id):
        """CU-14."""
        self.items.pop(str(producto_id), None)
        self._guardar()

    def limpiar(self):
        self.items.clear()
        self.session.pop(self.CUPON_KEY, None)
        self._guardar()

    # --- Consulta (CU-15 / CU-16) ---
    def lineas(self):
        if self._lineas is None:
            ids = [int(k) for k in self.items if str(k).isdigit()]
            productos = {p.pk: p for p in Producto.objects.activos().con_promos().filter(pk__in=ids)}
            lineas = []
            for clave in list(self.items):
                producto = productos.get(int(clave)) if str(clave).isdigit() else None
                if producto is None:  # el producto ya no existe o fue despublicado
                    self.items.pop(clave)
                    self.session.modified = True
                    continue
                lineas.append(LineaCarrito(producto, int(self.items[clave])))
            self._lineas = lineas
        return self._lineas

    def __iter__(self):
        return iter(self.lineas())

    def __len__(self):
        return sum(int(c) for c in self.items.values())

    @property
    def vacio(self):
        return len(self) == 0

    @property
    def subtotal(self):
        return sum((l.subtotal for l in self.lineas()), Decimal('0'))

    @property
    def subtotal_sin_promos(self):
        return sum((l.producto.precio * l.cantidad for l in self.lineas()), Decimal('0'))

    @property
    def ahorro_promociones(self):
        return self.subtotal_sin_promos - self.subtotal

    @property
    def hay_problemas_de_stock(self):
        return any(l.stock_insuficiente for l in self.lineas())

    # --- Cupones (CU-35) ---
    def aplicar_cupon(self, cupon):
        self.session[self.CUPON_KEY] = cupon.pk
        self._guardar()

    def quitar_cupon(self):
        self.session.pop(self.CUPON_KEY, None)
        self._guardar()

    @property
    def cupon(self):
        if self._cupon is None:
            cupon_id = self.session.get(self.CUPON_KEY)
            if not cupon_id:
                return None
            from promociones.models import Cupon
            cupon = Cupon.objects.filter(pk=cupon_id).first()
            if cupon is None or cupon.validar(self.subtotal):
                # El cupón dejó de ser válido (vencido, sin usos o compra mínima no alcanzada)
                self.session.pop(self.CUPON_KEY, None)
                return None
            self._cupon = cupon
        return self._cupon

    @property
    def descuento_cupon(self):
        return self.cupon.calcular_descuento(self.subtotal) if self.cupon else Decimal('0')

    @property
    def total(self):
        """CU-20: importe final."""
        return self.subtotal - self.descuento_cupon

"""Carga datos de demostración: usuarios, categorías, productos, promociones,
cupones y algunos pedidos de ejemplo.

Uso:  python manage.py cargar_datos
"""
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from cuentas.models import Usuario
from pedidos.models import DetallePedido, Pago, Pedido
from promociones.models import Cupon, Promocion
from tienda.models import Categoria, Producto

CATEGORIAS = [
    ('Perfumes', 'Fragancias de mujer, hombre y unisex.', 1),
    ('Sets de regalo', 'Estuches y kits ideales para regalar.', 2),
    ('Cuidado corporal', 'Body mists, cremas y splash.', 3),
]

# marca, nombre, tipo, ml, genero, precio, stock, categoria, destacado, nuevo, notas, descripcion
PRODUCTOS = [
    ('Carolina Herrera', 'Good Girl', 'EDP', 80, 'F', 189000, 14, 'Perfumes', True, False,
     'Almendra, Café, Jazmín, Haba tonka, Cacao',
     'Una fragancia audaz y sofisticada, contenida en su icónico frasco stiletto. El contraste entre la luz y la oscuridad de la mujer moderna.'),
    ('Lancôme', 'La Vie Est Belle', 'EDP', 100, 'F', 215000, 9, 'Perfumes', True, False,
     'Iris, Pachulí, Praliné, Vainilla',
     'Una declaración universal a la belleza de la vida. Un gourmand floral con un acorde de iris luminoso.'),
    ('Dior', "J'adore", 'EDP', 100, 'F', 268000, 6, 'Perfumes', True, True,
     'Ylang-ylang, Rosa damascena, Jazmín sambac',
     'Un bouquet floral excepcional, femenino y luminoso. Un clásico atemporal.'),
    ('Rabanne', 'Lady Million', 'EDP', 80, 'F', 172000, 3, 'Perfumes', False, False,
     'Neroli, Frambuesa, Jazmín, Miel, Pachulí',
     'Brillante, chispeante y seductor. Una fragancia floral amaderada para mujeres con actitud.'),
    ('Givenchy', "L'Interdit", 'EDP', 80, 'F', 198500, 11, 'Perfumes', False, True,
     'Flor de azahar, Jazmín, Tuberosa, Vetiver, Pachulí',
     'Un floral blanco con un acorde oscuro. La audacia de romper las reglas.'),
    ('Calvin Klein', 'CK IN2U Woman', 'EDT', 150, 'F', 98000, 20, 'Perfumes', False, False,
     'Pomelo, Bergamota, Orquídea, Vainilla',
     'Fresca, vibrante y moderna. Para quienes viven conectados.'),
    ('Yves Saint Laurent', 'Libre', 'EDP', 90, 'F', 239000, 0, 'Perfumes', False, True,
     'Lavanda, Flor de azahar, Vainilla de Madagascar, Almizcle',
     'La fragancia de la libertad. Un floral lavanda audaz y sensual.'),
    ('Dior', 'Sauvage', 'EDT', 100, 'M', 245000, 15, 'Perfumes', True, False,
     'Bergamota de Calabria, Pimienta, Ambroxan',
     'Un acto de creación inspirado en los grandes espacios abiertos. Radicalmente fresco.'),
    ('Jean Paul Gaultier', 'Le Male Elixir', 'PARFUM', 125, 'M', 262000, 7, 'Perfumes', True, True,
     'Lavanda, Menta, Vainilla, Benjuí, Haba tonka',
     'La versión más intensa del clásico marinero. Ámbar, cálido y adictivo.'),
    ('Rabanne', 'One Million', 'EDT', 100, 'M', 179000, 18, 'Perfumes', True, False,
     'Pomelo, Menta, Canela, Cuero, Ámbar',
     'Una fragancia especiada y cuero que se volvió un ícono de la seducción.'),
    ('Hugo Boss', 'Boss Bottled', 'EDT', 100, 'M', 142000, 4, 'Perfumes', False, False,
     'Manzana, Canela, Clavo, Sándalo, Vetiver',
     'La fragancia del hombre exitoso. Amaderada, especiada y elegante.'),
    ('Versace', 'Eros', 'EDT', 100, 'M', 168000, 12, 'Perfumes', False, False,
     'Menta, Manzana verde, Haba tonka, Vainilla',
     'Inspirada en la mitología griega: fresca, intensa y apasionada.'),
    ('Azzaro', 'The Most Wanted', 'EDP', 100, 'M', 175000, 9, 'Perfumes', False, True,
     'Cardamomo, Toffee, Madera ambarada',
     'Una fragancia ambarada y especiada con una adictiva nota de toffee.'),
    ('Carolina Herrera', '212 VIP Men', 'EDT', 100, 'M', 158000, 10, 'Perfumes', False, False,
     'Lima, Pimienta, Vodka, Ginger, Cuero',
     'La fiesta más exclusiva de Nueva York convertida en fragancia.'),
    ('Calvin Klein', 'CK One', 'EDT', 200, 'U', 89000, 25, 'Perfumes', True, False,
     'Bergamota, Té verde, Papaya, Almizcle',
     'La primera fragancia compartida. Limpia, fresca y atemporal.'),
    ('Maison Margiela', 'Replica Jazz Club', 'EDT', 100, 'U', 295000, 5, 'Perfumes', False, True,
     'Pimienta rosa, Ron, Tabaco, Vainilla',
     'El recuerdo de una noche en un club de jazz de Brooklyn.'),
    ('Jo Malone', 'Wood Sage & Sea Salt', 'EDC', 100, 'U', 285000, 6, 'Perfumes', False, False,
     'Ambreta, Sal marina, Salvia',
     'Escapá a la costa británica: viento, espuma de mar y madera.'),
    ('Lancôme', 'Set La Vie Est Belle', 'SET', 50, 'F', 199000, 5, 'Sets de regalo', False, True,
     'Iris, Pachulí, Praliné',
     'Estuche con perfume de 50 ml + loción corporal de 50 ml + mini talla.'),
    ('Versace', 'Set Eros', 'SET', 100, 'M', 189000, 4, 'Sets de regalo', False, False,
     'Menta, Manzana verde, Vainilla',
     'Estuche con perfume de 100 ml + gel de ducha + mini talla de 10 ml.'),
    ('Victoria\'s Secret', 'Bare Vanilla Body Mist', 'CORPORAL', 250, 'F', 45000, 30, 'Cuidado corporal', False, False,
     'Vainilla batida, Cachemira',
     'Bruma corporal suave y envolvente para usar todos los días.'),
]


class Command(BaseCommand):
    help = 'Carga datos de demostración para la tienda Franchesco.'

    @transaction.atomic
    def handle(self, *args, **options):
        hoy = timezone.localdate()

        # --- Usuarios ---
        admin, creado = Usuario.objects.get_or_create(
            email='admin@franchesco.com',
            defaults={'first_name': 'Admin', 'last_name': 'Franchesco', 'rol': Usuario.Rol.ADMIN, 'is_superuser': True},
        )
        if creado:
            admin.set_password('Admin1234!')
            admin.save()

        cliente, creado = Usuario.objects.get_or_create(
            email='cliente@franchesco.com',
            defaults={'first_name': 'Sofía', 'last_name': 'Gómez', 'telefono': '351 555-1234',
                      'direccion': 'Av. Colón 1234', 'ciudad': 'Córdoba', 'codigo_postal': '5000'},
        )
        if creado:
            cliente.set_password('Cliente1234!')
            cliente.save()

        # --- Categorías ---
        cats = {}
        for nombre, desc, orden in CATEGORIAS:
            cats[nombre], _ = Categoria.objects.get_or_create(nombre=nombre, defaults={'descripcion': desc, 'orden': orden})

        # --- Productos ---
        productos = []
        for (marca, nombre, tipo, ml, genero, precio, stock, cat, dest, nuevo, notas, desc) in PRODUCTOS:
            p, _ = Producto.objects.get_or_create(
                marca=marca, nombre=nombre, volumen_ml=ml,
                defaults=dict(tipo=tipo, genero=genero, precio=Decimal(precio), stock=stock,
                              categoria=cats[cat], destacado=dest, es_nuevo=nuevo, notas=notas, descripcion=desc),
            )
            productos.append(p)
        por_nombre = {p.nombre: p for p in productos}

        # --- Promociones ---
        cyber, _ = Promocion.objects.get_or_create(
            nombre='Cyber Franchesco',
            defaults={'porcentaje_descuento': Decimal('30'), 'fecha_inicio': hoy - timedelta(days=2),
                      'fecha_fin': hoy + timedelta(days=30), 'descripcion': 'Hasta 30% OFF en fragancias seleccionadas.'},
        )
        cyber.productos.add(*[por_nombre[n] for n in ('Good Girl', 'Sauvage', 'One Million', 'CK One', 'CK IN2U Woman', "L'Interdit")])

        hombre, _ = Promocion.objects.get_or_create(
            nombre='Semana del Hombre',
            defaults={'porcentaje_descuento': Decimal('20'), 'fecha_inicio': hoy,
                      'fecha_fin': hoy + timedelta(days=15)},
        )
        hombre.productos.add(*[por_nombre[n] for n in ('Boss Bottled', 'Eros', 'The Most Wanted')])

        # --- Cupones ---
        Cupon.objects.get_or_create(codigo='BIENVENIDA10', defaults={
            'descripcion': '10% OFF en tu primera compra', 'tipo': Cupon.Tipo.PORCENTAJE,
            'valor': Decimal('10'), 'fecha_vencimiento': hoy + timedelta(days=365)})
        Cupon.objects.get_or_create(codigo='FRAN5000', defaults={
            'descripcion': '$5.000 OFF en compras desde $100.000', 'tipo': Cupon.Tipo.MONTO,
            'valor': Decimal('5000'), 'monto_minimo': Decimal('100000'),
            'fecha_vencimiento': hoy + timedelta(days=60), 'usos_maximos': 100})
        Cupon.objects.get_or_create(codigo='VERANO2025', defaults={
            'descripcion': 'Cupón vencido (para probar la validación)', 'tipo': Cupon.Tipo.PORCENTAJE,
            'valor': Decimal('15'), 'fecha_vencimiento': hoy - timedelta(days=30)})

        # --- Pedidos de ejemplo (para que el panel tenga información) ---
        if not Pedido.objects.exists():
            ejemplos = [
                (6, Pedido.Estado.ENTREGADO, Pago.Metodo.CREDITO, [('Sauvage', 1), ('CK One', 2)]),
                (4, Pedido.Estado.ENVIADO, Pago.Metodo.MERCADOPAGO, [('Good Girl', 1)]),
                (2, Pedido.Estado.PAGADO, Pago.Metodo.DEBITO, [('One Million', 1), ('Eros', 1)]),
                (1, Pedido.Estado.PREPARANDO, Pago.Metodo.CREDITO, [('Sauvage', 2)]),
                (0, Pedido.Estado.PENDIENTE, Pago.Metodo.TRANSFERENCIA, [("J'adore", 1)]),
            ]
            for dias, estado, metodo, items in ejemplos:
                subtotal = sum(por_nombre[n].precio * c for n, c in items)
                pedido = Pedido.objects.create(
                    usuario=cliente, estado=estado, nombre=cliente.first_name, apellido=cliente.last_name,
                    email=cliente.email, telefono=cliente.telefono, direccion=cliente.direccion,
                    ciudad=cliente.ciudad, codigo_postal=cliente.codigo_postal,
                    subtotal=subtotal, total=subtotal,
                )
                for n, c in items:
                    p = por_nombre[n]
                    DetallePedido.objects.create(pedido=pedido, producto=p, nombre_producto=p.nombre,
                                                 marca=p.marca, cantidad=c, precio_unitario=p.precio)
                Pago.objects.create(pedido=pedido, metodo=metodo, monto=subtotal,
                                    estado=Pago.Estado.PENDIENTE if estado == Pedido.Estado.PENDIENTE else Pago.Estado.APROBADO)
                Pedido.objects.filter(pk=pedido.pk).update(fecha=timezone.now() - timedelta(days=dias, hours=dias * 3))

        self.stdout.write(self.style.SUCCESS('Datos de demostración cargados.'))
        self.stdout.write('  Administrador: admin@franchesco.com / Admin1234!')
        self.stdout.write('  Cliente demo:  cliente@franchesco.com / Cliente1234!')
        self.stdout.write('  Cupones: BIENVENIDA10, FRAN5000 (VERANO2025 está vencido)')

from django.conf import settings
from django.db import models
from django.urls import reverse


class Pedido(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente de pago'
        PAGADO = 'pagado', 'Pagado'
        PREPARANDO = 'preparando', 'En preparación'
        ENVIADO = 'enviado', 'Enviado'
        ENTREGADO = 'entregado', 'Entregado'
        CANCELADO = 'cancelado', 'Cancelado'

    COLORES = {
        'pendiente': 'warning', 'pagado': 'info', 'preparando': 'primary',
        'enviado': 'secondary', 'entregado': 'success', 'cancelado': 'danger',
    }

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='pedidos')
    fecha = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=15, choices=Estado.choices, default=Estado.PENDIENTE)

    # Datos de entrega (copiados al momento de la compra)
    nombre = models.CharField(max_length=80)
    apellido = models.CharField(max_length=80)
    email = models.EmailField()
    telefono = models.CharField('teléfono', max_length=30)
    direccion = models.CharField('dirección', max_length=200)
    ciudad = models.CharField(max_length=100)
    codigo_postal = models.CharField('código postal', max_length=10)
    notas = models.TextField('notas para la entrega', blank=True)

    # Importes
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    descuento = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    cupon = models.ForeignKey('promociones.Cupon', on_delete=models.SET_NULL, null=True, blank=True, related_name='pedidos')

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'pedido'
        verbose_name_plural = 'pedidos'

    def __str__(self):
        return self.codigo

    @property
    def codigo(self):
        return f'FR-{self.pk:06d}' if self.pk else 'FR-nuevo'

    @property
    def color_estado(self):
        return self.COLORES.get(self.estado, 'secondary')

    @property
    def cantidad_productos(self):
        return sum(d.cantidad for d in self.detalles.all())

    def get_absolute_url(self):
        return reverse('pedidos:detalle', args=[self.pk])

    def calcular_total(self):
        return sum((d.subtotal for d in self.detalles.all()), 0) - self.descuento


class DetallePedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey('tienda.Producto', on_delete=models.SET_NULL, null=True, related_name='detalles_pedido')
    # Copia de los datos para preservar el historial aunque el producto cambie (CU-26)
    nombre_producto = models.CharField(max_length=200)
    marca = models.CharField(max_length=80)
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        verbose_name = 'detalle de pedido'
        verbose_name_plural = 'detalles de pedido'

    def __str__(self):
        return f'{self.cantidad} x {self.nombre_producto}'

    def calcular_subtotal(self):
        return self.precio_unitario * self.cantidad

    def save(self, *args, **kwargs):
        self.subtotal = self.calcular_subtotal()
        super().save(*args, **kwargs)


class Pago(models.Model):
    class Metodo(models.TextChoices):
        CREDITO = 'credito', 'Tarjeta de crédito'
        DEBITO = 'debito', 'Tarjeta de débito'
        TRANSFERENCIA = 'transferencia', 'Transferencia bancaria'
        MERCADOPAGO = 'mercadopago', 'Mercado Pago'

    class Estado(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente'
        APROBADO = 'aprobado', 'Aprobado'
        ANULADO = 'anulado', 'Anulado'

    pedido = models.OneToOneField(Pedido, on_delete=models.CASCADE, related_name='pago')
    metodo = models.CharField('método', max_length=20, choices=Metodo.choices)
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    fecha = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)

    class Meta:
        verbose_name = 'pago'
        verbose_name_plural = 'pagos'

    def __str__(self):
        return f'{self.get_metodo_display()} - {self.pedido.codigo}'

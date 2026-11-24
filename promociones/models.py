from decimal import ROUND_HALF_UP, Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from tienda.utils import formato_pesos


class PromocionQuerySet(models.QuerySet):
    def vigentes(self, hoy=None):
        hoy = hoy or timezone.localdate()
        return self.filter(activa=True, fecha_inicio__lte=hoy, fecha_fin__gte=hoy)


class Promocion(models.Model):
    """Descuento porcentual aplicado a un conjunto de productos (CU-32 / CU-34)."""

    nombre = models.CharField(max_length=100)
    descripcion = models.CharField('descripción', max_length=250, blank=True)
    porcentaje_descuento = models.DecimalField(
        'descuento (%)', max_digits=5, decimal_places=2,
        validators=[MinValueValidator(Decimal('1')), MaxValueValidator(Decimal('90'))],
    )
    fecha_inicio = models.DateField('fecha de inicio', default=timezone.localdate)
    fecha_fin = models.DateField('fecha de fin')
    activa = models.BooleanField(default=True)
    productos = models.ManyToManyField('tienda.Producto', related_name='promociones', blank=True)

    objects = PromocionQuerySet.as_manager()

    class Meta:
        ordering = ['-fecha_inicio']
        verbose_name = 'promoción'
        verbose_name_plural = 'promociones'

    def __str__(self):
        return f'{self.nombre} ({self.porcentaje_descuento:.0f}% OFF)'

    def clean(self):
        if self.fecha_inicio and self.fecha_fin and self.fecha_fin < self.fecha_inicio:
            raise ValidationError({'fecha_fin': 'La fecha de fin no puede ser anterior a la de inicio.'})

    def verificar_vigencia(self):
        hoy = timezone.localdate()
        return self.activa and self.fecha_inicio <= hoy <= self.fecha_fin

    @property
    def estado(self):
        hoy = timezone.localdate()
        if not self.activa:
            return 'Inactiva'
        if hoy < self.fecha_inicio:
            return 'Programada'
        if hoy > self.fecha_fin:
            return 'Finalizada'
        return 'Vigente'


class CuponQuerySet(models.QuerySet):
    def disponibles(self):
        hoy = timezone.localdate()
        return self.filter(activo=True, fecha_vencimiento__gte=hoy).filter(
            Q(usos_maximos__isnull=True) | Q(usos__lt=F('usos_maximos'))
        )


class Cupon(models.Model):
    """Cupón de descuento sobre el total de la compra (CU-33 / CU-35 / CU-36)."""

    class Tipo(models.TextChoices):
        PORCENTAJE = 'PCT', 'Porcentaje (%)'
        MONTO = 'MONTO', 'Monto fijo ($)'

    codigo = models.CharField('código', max_length=30, unique=True)
    descripcion = models.CharField('descripción', max_length=150, blank=True)
    tipo = models.CharField(max_length=5, choices=Tipo.choices, default=Tipo.PORCENTAJE)
    valor = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    monto_minimo = models.DecimalField('compra mínima', max_digits=12, decimal_places=2, default=0)
    fecha_vencimiento = models.DateField('fecha de vencimiento')
    usos_maximos = models.PositiveIntegerField('usos máximos', null=True, blank=True, help_text='Dejar vacío para usos ilimitados.')
    usos = models.PositiveIntegerField(default=0, editable=False)
    activo = models.BooleanField(default=True)

    objects = CuponQuerySet.as_manager()

    class Meta:
        ordering = ['-id']
        verbose_name = 'cupón'
        verbose_name_plural = 'cupones'

    def __str__(self):
        return self.codigo

    def save(self, *args, **kwargs):
        self.codigo = self.codigo.strip().upper()
        super().save(*args, **kwargs)

    def clean(self):
        if self.tipo == self.Tipo.PORCENTAJE and self.valor and self.valor > 100:
            raise ValidationError({'valor': 'Un descuento porcentual no puede superar el 100%.'})

    @property
    def estado(self):
        if not self.activo:
            return 'Inactivo'
        if self.fecha_vencimiento < timezone.localdate():
            return 'Vencido'
        if self.usos_maximos is not None and self.usos >= self.usos_maximos:
            return 'Agotado'
        return 'Activo'

    @property
    def resumen(self):
        if self.tipo == self.Tipo.PORCENTAJE:
            return f'{self.valor:.0f}% OFF'
        return f'{formato_pesos(self.valor)} OFF'

    def validar(self, subtotal):
        """CU-36: Devuelve un mensaje de error o None si el cupón es aplicable."""
        hoy = timezone.localdate()
        if not self.activo:
            return 'El cupón no está activo.'
        if self.fecha_vencimiento < hoy:
            return 'El cupón está vencido.'
        if self.usos_maximos is not None and self.usos >= self.usos_maximos:
            return 'El cupón alcanzó su límite de usos.'
        if subtotal < self.monto_minimo:
            return f'Este cupón requiere una compra mínima de {formato_pesos(self.monto_minimo)}.'
        return None

    def calcular_descuento(self, subtotal):
        if self.tipo == self.Tipo.PORCENTAJE:
            descuento = subtotal * self.valor / Decimal('100')
        else:
            descuento = self.valor
        return min(descuento, subtotal).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

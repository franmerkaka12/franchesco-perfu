from decimal import ROUND_HALF_UP, Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Prefetch
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property

from .utils import ajustar_imagen_producto, slug_unico


class Categoria(models.Model):
    nombre = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    descripcion = models.TextField('descripción', blank=True)
    orden = models.PositiveIntegerField(default=0, help_text='Orden de aparición en el menú.')

    class Meta:
        ordering = ['orden', 'nombre']
        verbose_name = 'categoría'
        verbose_name_plural = 'categorías'

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slug_unico(self, self.nombre)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return f"{reverse('tienda:catalogo')}?categoria={self.slug}"

    def listar_productos(self):
        return self.productos.activos()


class ProductoQuerySet(models.QuerySet):
    def activos(self):
        return self.filter(activo=True)

    def principales(self):
        """Una sola tarjeta por perfume: excluye las presentaciones extra (otros ml)."""
        return self.filter(principal__isnull=True).prefetch_related(
            Prefetch('presentaciones', queryset=self.model.objects.con_promos())
        )

    def con_promos(self):
        """Precarga las promociones vigentes para evitar consultas repetidas."""
        from promociones.models import Promocion
        vigentes = Promocion.objects.vigentes().order_by('-porcentaje_descuento')
        return self.prefetch_related(
            Prefetch('promociones', queryset=vigentes, to_attr='promos_vigentes')
        )

    def en_oferta(self):
        hoy = timezone.localdate()
        return self.filter(
            promociones__activa=True,
            promociones__fecha_inicio__lte=hoy,
            promociones__fecha_fin__gte=hoy,
        ).distinct()


class Producto(models.Model):
    STOCK_BAJO = 5

    class Genero(models.TextChoices):
        FEMENINO = 'F', 'Femenino'
        MASCULINO = 'M', 'Masculino'
        UNISEX = 'U', 'Unisex'

    class Tipo(models.TextChoices):
        EDP = 'EDP', 'Eau de Parfum'
        EDT = 'EDT', 'Eau de Toilette'
        PARFUM = 'PARFUM', 'Parfum'
        EDC = 'EDC', 'Eau de Cologne'
        SET = 'SET', 'Set de regalo'
        CORPORAL = 'CORPORAL', 'Cuidado corporal'

    nombre = models.CharField(max_length=120)
    marca = models.CharField(max_length=80, db_index=True)
    slug = models.SlugField(max_length=170, unique=True, blank=True)
    descripcion = models.TextField('descripción', blank=True)
    notas = models.CharField(
        'notas olfativas', max_length=250, blank=True,
        help_text='Separadas por coma. Ej: Bergamota, Vainilla, Ámbar',
    )
    categoria = models.ForeignKey(
        Categoria, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='productos', verbose_name='categoría',
    )
    genero = models.CharField('género', max_length=1, choices=Genero.choices, default=Genero.UNISEX)
    tipo = models.CharField(max_length=10, choices=Tipo.choices, default=Tipo.EDP)
    volumen_ml = models.PositiveIntegerField('volumen (ml)', default=100)
    precio = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    stock = models.PositiveIntegerField(default=0)
    imagen = models.ImageField(upload_to='productos/', blank=True)
    activo = models.BooleanField('publicado', default=True, help_text='Si está desmarcado, no se muestra en la tienda.')
    destacado = models.BooleanField(default=False, help_text='Aparece en la sección "Destacados" del inicio.')
    es_nuevo = models.BooleanField('novedad', default=False, help_text='Muestra la etiqueta NUEVO.')
    # Otros tamaños del mismo perfume (ej: 50 ml y 100 ml en una misma publicación).
    # Cada presentación es un producto con su propio precio y stock.
    principal = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True,
        related_name='presentaciones', verbose_name='presentación de',
    )
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    objects = ProductoQuerySet.as_manager()

    class Meta:
        ordering = ['-creado']
        verbose_name = 'producto'
        verbose_name_plural = 'productos'

    def __str__(self):
        return f'{self.marca} - {self.nombre} ({self.volumen_ml} ml)'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slug_unico(self, f'{self.marca} {self.nombre} {self.volumen_ml}ml')
        # Foto recién subida: se recorta el blanco sobrante para que ocupe todo el recuadro
        if self.imagen and not getattr(self.imagen, '_committed', True):
            ajustada = ajustar_imagen_producto(self.imagen)
            if ajustada is not None:
                from pathlib import Path
                self.imagen.save(f'{Path(self.imagen.name).stem}.jpg', ajustada, save=False)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('tienda:detalle', args=[self.slug])

    # --- Presentaciones (varios ml en una misma publicación) ---
    CAMPOS_COMPARTIDOS = ('nombre', 'marca', 'descripcion', 'notas', 'categoria', 'genero', 'tipo',
                          'imagen', 'activo', 'destacado', 'es_nuevo')

    @property
    def raiz(self):
        return self.principal if self.principal_id else self

    @cached_property
    def familia(self):
        """Todas las presentaciones publicadas de este perfume, ordenadas por ml."""
        raiz = self.raiz
        miembros = [raiz] + [p for p in raiz.presentaciones.all() if p.activo]
        if self.pk not in {m.pk for m in miembros}:
            miembros.append(self)
        return sorted(miembros, key=lambda p: p.volumen_ml)

    def copiar_de_principal(self):
        for campo in self.CAMPOS_COMPARTIDOS:
            valor = getattr(self.principal, campo)
            setattr(self, campo, valor.name if campo == 'imagen' else valor)

    def sincronizar_presentaciones(self):
        for p in self.presentaciones.all():
            p.principal = self
            p.copiar_de_principal()
            p.save()

    # --- Disponibilidad / stock (RF-16) ---
    @property
    def disponible(self):
        return self.activo and self.stock > 0

    def consultar_disponibilidad(self, cantidad=1):
        return self.activo and self.stock >= cantidad

    @property
    def stock_bajo(self):
        return 0 < self.stock <= self.STOCK_BAJO

    # --- Precios y promociones ---
    @cached_property
    def promocion(self):
        if hasattr(self, 'promos_vigentes'):
            return self.promos_vigentes[0] if self.promos_vigentes else None
        from promociones.models import Promocion
        return Promocion.objects.vigentes().filter(productos=self).order_by('-porcentaje_descuento').first()

    @property
    def descuento_pct(self):
        return int(self.promocion.porcentaje_descuento) if self.promocion else 0

    @cached_property
    def precio_final(self):
        if not self.promocion:
            return self.precio
        factor = (Decimal('100') - self.promocion.porcentaje_descuento) / Decimal('100')
        return (self.precio * factor).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    # --- Presentación ---
    @property
    def lista_notas(self):
        return [n.strip() for n in self.notas.split(',') if n.strip()]

    @property
    def tono(self):
        """Color (hue) para dibujar el frasco ilustrado cuando no hay imagen."""
        return ((self.pk or 1) * 47) % 360

    @property
    def forma(self):
        return (self.pk or 0) % 3


class MarcaOculta(models.Model):
    """Marca que el administrador quitó de las sugerencias del formulario de productos."""
    nombre = models.CharField(max_length=80, unique=True)

    class Meta:
        verbose_name = 'marca oculta'
        verbose_name_plural = 'marcas ocultas'

    def __str__(self):
        return self.nombre

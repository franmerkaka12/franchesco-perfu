from decimal import Decimal, InvalidOperation

from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, render

from promociones.models import Cupon

from .models import Categoria, Producto

CONCENTRACIONES = [
    ('EDT', 'Eau de Toilette (EDT)'),
    ('EDP', 'Eau de Parfum (EDP)'),
    ('PARFUM', 'Parfum (P)'),
]

ORDENES = {
    'relevancia': ('Relevancia', ('-destacado', '-creado')),
    'precio_asc': ('Menor precio', ('precio',)),
    'precio_desc': ('Mayor precio', ('-precio',)),
    'nuevos': ('Más nuevos', ('-creado',)),
    'nombre': ('Marca A-Z', ('marca', 'nombre')),
}


def _decimal(valor):
    try:
        return Decimal(valor) if valor not in (None, '') else None
    except InvalidOperation:
        return None


def inicio(request):
    base = Producto.objects.activos().principales().con_promos()
    contexto = {
        'ofertas': base.en_oferta()[:12],
        'novedades': base.filter(es_nuevo=True)[:12],
        'destacados': list(base.filter(destacado=True)[:12]),
        'mas_vendidos': (
            base.annotate(vendidos=Sum('detalles_pedido__cantidad'))
            .filter(vendidos__gt=0).order_by('-vendidos')[:12]
        ),
        'cupon_destacado': Cupon.objects.disponibles().order_by('-valor').first(),
    }
    return render(request, 'tienda/inicio.html', contexto)


def catalogo(request):
    """CU-01 Consultar catálogo, CU-02 Buscar, CU-04 Filtrar por categoría/género."""
    qs = Producto.objects.activos().principales().select_related('categoria').con_promos()
    titulo = 'Perfumes'

    q = request.GET.get('q', '').strip()
    if q:
        for palabra in q.split():
            qs = qs.filter(
                Q(nombre__icontains=palabra) | Q(marca__icontains=palabra)
                | Q(notas__icontains=palabra) | Q(descripcion__icontains=palabra)
            )
        titulo = f'Resultados para “{q}”'

    categoria = None
    if slug := request.GET.get('categoria'):
        categoria = Categoria.objects.filter(slug=slug).first()
        if categoria:
            qs = qs.filter(categoria=categoria)
            titulo = categoria.nombre

    genero = request.GET.get('genero', '')
    if genero in Producto.Genero.values:
        qs = qs.filter(genero=genero)
        titulo = {'F': 'Perfumes de mujer', 'M': 'Perfumes de hombre', 'U': 'Perfumes unisex'}[genero]

    tipo = request.GET.get('tipo', '')
    if tipo in dict(CONCENTRACIONES):
        qs = qs.filter(tipo=tipo)

    marcas_sel = request.GET.getlist('marca')
    if marcas_sel:
        qs = qs.filter(marca__in=marcas_sel)
        if len(marcas_sel) == 1 and not q:
            titulo = marcas_sel[0]

    precio_min, precio_max = _decimal(request.GET.get('min')), _decimal(request.GET.get('max'))
    if precio_min is not None:
        qs = qs.filter(precio__gte=precio_min)
    if precio_max is not None:
        qs = qs.filter(precio__lte=precio_max)

    if request.GET.get('oferta'):
        qs = qs.en_oferta()
        titulo = 'Ofertas'
    if request.GET.get('nuevo'):
        qs = qs.filter(es_nuevo=True)
        titulo = 'Novedades'
    if request.GET.get('disponibles'):
        qs = qs.filter(stock__gt=0)

    orden = request.GET.get('orden', 'relevancia')
    if orden not in ORDENES:
        orden = 'relevancia'
    qs = qs.order_by(*ORDENES[orden][1])

    pagina = Paginator(qs, 12).get_page(request.GET.get('page'))
    filtros_activos = any(request.GET.get(k) for k in ('q', 'categoria', 'genero', 'tipo', 'marca', 'min', 'max', 'oferta', 'nuevo', 'disponibles'))

    return render(request, 'tienda/catalogo.html', {
        'pagina': pagina,
        'titulo': titulo,
        'q': q,
        'categoria_sel': categoria,
        'genero_sel': genero,
        'marcas_sel': marcas_sel,
        'precio_min': request.GET.get('min', ''),
        'precio_max': request.GET.get('max', ''),
        'orden': orden,
        'ordenes': [(k, v[0]) for k, v in ORDENES.items()],
        'generos': Producto.Genero.choices,
        'tipo_sel': tipo,
        'concentraciones': CONCENTRACIONES,
        'filtros_activos': filtros_activos,
    })


def detalle(request, slug):
    """CU-03: Consultar detalle del producto."""
    producto = get_object_or_404(Producto.objects.activos().select_related('categoria').con_promos(), slug=slug)
    relacionados = (
        Producto.objects.activos().principales().con_promos()
        .filter(genero=producto.genero).exclude(pk__in=[p.pk for p in producto.familia])
        .exclude(pk=producto.raiz.pk)
        .order_by('-destacado', '?')[:10]
    )
    return render(request, 'tienda/detalle.html', {
        'producto': producto,
        'relacionados': relacionados,
    })

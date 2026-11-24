from .models import Categoria, MarcaOculta, Producto


def marcas_visibles():
    """Marcas con productos publicados, sin las que el admin quitó desde el panel."""
    ocultas = {m.lower() for m in MarcaOculta.objects.values_list('nombre', flat=True)}
    marcas = Producto.objects.activos().order_by('marca').values_list('marca', flat=True).distinct()
    return [m for m in marcas if m.lower() not in ocultas]


def navegacion(request):
    """Datos disponibles en todas las plantillas: categorías y marcas para el menú."""
    if request.path.startswith('/django-admin/'):
        return {}
    return {
        'nav_categorias': Categoria.objects.all(),
        'nav_marcas': marcas_visibles(),
    }

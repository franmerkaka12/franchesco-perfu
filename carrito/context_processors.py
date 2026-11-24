from .carrito import Carrito


def carrito(request):
    if not hasattr(request, 'session'):
        return {}
    return {'carrito_cantidad': len(Carrito(request))}

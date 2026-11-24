from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from promociones.models import Cupon
from tienda.models import Producto
from tienda.utils import formato_pesos

from .carrito import Carrito


def _es_ajax(request):
    return request.headers.get('x-requested-with') == 'XMLHttpRequest'


def _volver(request, por_defecto='carrito:detalle'):
    destino = request.POST.get('next')
    if destino and url_has_allowed_host_and_scheme(destino, {request.get_host()}, request.is_secure()):
        return redirect(destino)
    return redirect(por_defecto)


def _cantidad(request):
    try:
        return int(request.POST.get('cantidad', 1))
    except (TypeError, ValueError):
        return 1


def detalle(request):
    """CU-15: Consultar carrito."""
    return render(request, 'carrito/detalle.html', {'carrito': Carrito(request)})


@require_POST
def agregar(request, producto_id):
    """CU-12: Agregar producto al carrito."""
    producto = get_object_or_404(Producto.objects.activos(), pk=producto_id)
    carrito = Carrito(request)
    ok, mensaje = carrito.agregar(producto, max(_cantidad(request), 1))
    if _es_ajax(request):
        return JsonResponse({'ok': ok, 'mensaje': mensaje, 'cantidad': len(carrito)})
    (messages.success if ok else messages.warning)(request, mensaje)
    return _volver(request)


@require_POST
def actualizar(request, producto_id):
    """CU-13: Modificar cantidad."""
    producto = get_object_or_404(Producto, pk=producto_id)
    carrito = Carrito(request)
    ok, mensaje = carrito.agregar(producto, _cantidad(request), reemplazar=True)
    if not ok:
        messages.warning(request, mensaje)
    return redirect('carrito:detalle')


@require_POST
def eliminar(request, producto_id):
    """CU-14: Eliminar producto del carrito."""
    Carrito(request).quitar(producto_id)
    messages.info(request, 'Producto eliminado del carrito.')
    return redirect('carrito:detalle')


@login_required
@require_POST
def aplicar_cupon(request):
    """CU-35 / CU-36: Aplicar y validar un cupón."""
    carrito = Carrito(request)
    codigo = request.POST.get('codigo', '').strip()
    cupon = Cupon.objects.filter(codigo__iexact=codigo).first()
    if not cupon:
        messages.error(request, f'El cupón “{codigo}” no existe.')
    elif error := cupon.validar(carrito.subtotal):
        messages.error(request, error)
    else:
        carrito.aplicar_cupon(cupon)
        ahorro = cupon.calcular_descuento(carrito.subtotal)
        messages.success(request, f'¡Cupón {cupon.codigo} aplicado! Ahorrás {formato_pesos(ahorro)}.')
    return _volver(request)


@require_POST
def quitar_cupon(request):
    Carrito(request).quitar_cupon()
    messages.info(request, 'Se quitó el cupón.')
    return _volver(request)

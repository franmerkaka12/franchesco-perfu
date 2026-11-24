from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from carrito.carrito import Carrito

from .forms import CheckoutForm
from .models import Pedido
from .services import CompraError, crear_pedido


@login_required
def checkout(request):
    """CU-17: Completar compra (RF-10: requiere sesión iniciada)."""
    carrito = Carrito(request)
    if carrito.vacio:
        messages.info(request, 'Tu carrito está vacío. ¡Agregá algún perfume!')
        return redirect('carrito:detalle')

    u = request.user
    inicial = {
        'nombre': u.first_name, 'apellido': u.last_name, 'telefono': u.telefono,
        'direccion': u.direccion, 'ciudad': u.ciudad, 'codigo_postal': u.codigo_postal,
    }
    form = CheckoutForm(request.POST or None, initial=inicial)

    if request.method == 'POST' and form.is_valid():
        datos = form.cleaned_data
        try:
            pedido = crear_pedido(u, carrito, datos)
        except CompraError as e:
            for err in e.errores:
                messages.error(request, err)
            return redirect('carrito:detalle')

        if datos.get('guardar_datos'):
            for campo in ('telefono', 'direccion', 'ciudad', 'codigo_postal'):
                setattr(u, campo, datos[campo])
            u.save(update_fields=['telefono', 'direccion', 'ciudad', 'codigo_postal'])

        carrito.limpiar()
        return redirect('pedidos:confirmacion', pk=pedido.pk)

    return render(request, 'pedidos/checkout.html', {'form': form, 'carrito': carrito})


@login_required
def confirmacion(request, pk):
    pedido = get_object_or_404(Pedido.objects.select_related('pago'), pk=pk, usuario=request.user)
    return render(request, 'pedidos/confirmacion.html', {'pedido': pedido})


@login_required
def mis_pedidos(request):
    """CU-29: Consultar pedidos propios."""
    pedidos = request.user.pedidos.select_related('pago').prefetch_related('detalles')
    return render(request, 'pedidos/mis_pedidos.html', {'pedidos': pedidos})


@login_required
def detalle(request, pk):
    pedido = get_object_or_404(
        Pedido.objects.select_related('pago', 'cupon').prefetch_related('detalles__producto'),
        pk=pk, usuario=request.user,
    )
    return render(request, 'pedidos/detalle.html', {'pedido': pedido})

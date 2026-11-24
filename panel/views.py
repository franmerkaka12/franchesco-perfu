"""Panel administrativo (RF-14, RF-15, RF-18, RF-19, RF-20)."""
from datetime import timedelta

from django.contrib import messages
from django.db import transaction
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from cuentas.decorators import admin_requerido
from cuentas.models import Usuario
from pedidos.models import DetallePedido, Pedido
from pedidos.services import CompraError, cambiar_estado
from promociones.models import Cupon, Promocion
from tienda.models import Categoria, MarcaOculta, Producto

from .forms import (CategoriaForm, CuponForm, EstadoPedidoForm, PresentacionFormSet, ProductoForm,
                    PromocionForm, UsuarioAdminForm)


def _paginar(request, qs, por_pagina=15):
    return Paginator(qs, por_pagina).get_page(request.GET.get('page'))


def _formulario(request, form_class, instancia, titulo, volver, seccion, **extra):
    """Vista genérica de alta/edición usada por todas las entidades."""
    form = form_class(request.POST or None, request.FILES or None, instance=instancia)
    if request.method == 'POST' and form.is_valid():
        objeto = form.save()
        messages.success(request, f'“{objeto}” se guardó correctamente.')
        return redirect(volver)
    if request.method == 'POST':
        messages.error(request, 'Revisá los campos marcados en rojo.')
    return render(request, 'panel/form.html', {
        'form': form, 'titulo': titulo, 'volver': volver, 'seccion': seccion,
        'instancia': instancia, **extra,
    })


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@admin_requerido
def dashboard(request):
    hoy = timezone.localdate()
    validos = Pedido.objects.exclude(estado=Pedido.Estado.CANCELADO)

    desde = hoy - timedelta(days=6)
    por_dia = dict(
        validos.filter(fecha__date__gte=desde)
        .annotate(dia=TruncDate('fecha')).values('dia')
        .annotate(total=Sum('total')).values_list('dia', 'total')
    )
    serie = [(desde + timedelta(days=i), por_dia.get(desde + timedelta(days=i), 0) or 0) for i in range(7)]
    maximo = max((t for _, t in serie), default=0) or 1
    ventas_semana = [{'dia': d, 'total': t, 'pct': int(t * 100 / maximo)} for d, t in serie]

    contexto = {
        'seccion': 'dashboard',
        'ventas_mes': validos.filter(fecha__date__gte=hoy.replace(day=1)).aggregate(t=Sum('total'))['t'] or 0,
        'pedidos_mes': validos.filter(fecha__date__gte=hoy.replace(day=1)).count(),
        'pedidos_pendientes': Pedido.objects.filter(estado=Pedido.Estado.PENDIENTE).count(),
        'total_clientes': Usuario.objects.filter(rol=Usuario.Rol.CLIENTE).count(),
        'productos_activos': Producto.objects.activos().count(),
        'stock_bajo': Producto.objects.activos().filter(stock__lte=Producto.STOCK_BAJO).order_by('stock')[:8],
        'ultimos_pedidos': Pedido.objects.select_related('usuario')[:6],
        'top_productos': (
            DetallePedido.objects.exclude(pedido__estado=Pedido.Estado.CANCELADO)
            .values('nombre_producto', 'marca').annotate(unidades=Sum('cantidad'), monto=Sum('subtotal'))
            .order_by('-unidades')[:5]
        ),
        'ventas_semana': ventas_semana,
    }
    return render(request, 'panel/dashboard.html', contexto)


# ---------------------------------------------------------------------------
# Productos (CU-23 a CU-26)
# ---------------------------------------------------------------------------
@admin_requerido
def productos(request):
    qs = Producto.objects.principales().select_related('categoria')
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(Q(nombre__icontains=q) | Q(marca__icontains=q))
    if g := request.GET.get('genero'):
        qs = qs.filter(genero=g)
    if c := request.GET.get('categoria'):
        qs = qs.filter(categoria_id=c)
    estado = request.GET.get('estado')
    if estado == 'publicados':
        qs = qs.filter(activo=True)
    elif estado == 'ocultos':
        qs = qs.filter(activo=False)
    return render(request, 'panel/productos.html', {
        'seccion': 'productos', 'pagina': _paginar(request, qs.order_by('marca', 'nombre')),
        'q': q, 'categorias': Categoria.objects.all(), 'generos': Producto.Genero.choices,
    })


def _marcas():
    """Marcas sugeridas en el formulario, sin las que el admin quitó."""
    ocultas = {m.lower() for m in MarcaOculta.objects.values_list('nombre', flat=True)}
    marcas = Producto.objects.order_by('marca').values_list('marca', flat=True).distinct()
    return [m for m in marcas if m.lower() not in ocultas]


@admin_requerido
@require_POST
def marca_ocultar(request):
    """Quita una marca de las sugerencias. Los productos que la usan no cambian."""
    nombre = request.POST.get('marca', '').strip()[:80]
    if nombre and not MarcaOculta.objects.filter(nombre__iexact=nombre).exists():
        MarcaOculta.objects.create(nombre=nombre)
    return JsonResponse({'ok': bool(nombre)})


def _producto_formulario(request, producto, titulo):
    """Alta/edición de un perfume junto con sus otras presentaciones (otros ml)."""
    form = ProductoForm(request.POST or None, request.FILES or None, instance=producto)
    volumen = request.POST.get('volumen_ml') if request.method == 'POST' else None
    try:
        volumen = int(volumen) if volumen else None
    except ValueError:
        volumen = None
    formset = PresentacionFormSet(request.POST or None, instance=producto or Producto(),
                                  prefix='pres', volumen_principal=volumen)
    if request.method == 'POST':
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                principal = form.save()
                # Si se vuelve a usar una marca quitada, vuelve a aparecer en la lista
                MarcaOculta.objects.filter(nombre__iexact=principal.marca).delete()
                formset.instance = principal
                nuevas = formset.save(commit=False)
                for p in nuevas:
                    p.principal = principal
                    p.copiar_de_principal()
                    p.save()
                for p in formset.deleted_objects:
                    if p.detalles_pedido.exists():
                        # Tiene ventas: se oculta y se separa para conservar el historial
                        p.principal, p.activo = None, False
                        p.save()
                    else:
                        p.delete()
                principal.sincronizar_presentaciones()
            messages.success(request, f'“{principal.marca} {principal.nombre}” se guardó correctamente.')
            return redirect('panel:productos')
        messages.error(request, 'Revisá los campos marcados en rojo.')
    return render(request, 'panel/form.html', {
        'form': form, 'presentaciones': formset, 'titulo': titulo, 'volver': 'panel:productos',
        'seccion': 'productos', 'instancia': producto, 'multipart': True, 'marcas': _marcas(),
    })


@admin_requerido
def producto_crear(request):
    return _producto_formulario(request, None, 'Nuevo producto')


@admin_requerido
def producto_editar(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    if producto.principal_id:
        # Las presentaciones se editan desde el perfume principal
        return redirect('panel:producto_editar', producto.principal_id)
    return _producto_formulario(request, producto, f'Editar: {producto.marca} {producto.nombre}')


@admin_requerido
@require_POST
def producto_eliminar(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    familia = [producto, *producto.presentaciones.all()]
    if any(p.detalles_pedido.exists() for p in familia):
        # Se preserva la información de las compras registradas (CU-26)
        producto.activo = False
        producto.save(update_fields=['activo'])
        producto.sincronizar_presentaciones()
        messages.warning(request, f'“{producto}” tiene ventas registradas: se ocultó del catálogo en lugar de eliminarse.')
    else:
        producto.delete()
        messages.success(request, f'“{producto}” fue eliminado.')
    return redirect('panel:productos')


# ---------------------------------------------------------------------------
# Stock (CU-27 / CU-28)
# ---------------------------------------------------------------------------
@admin_requerido
def stock(request):
    qs = Producto.objects.all()
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(Q(nombre__icontains=q) | Q(marca__icontains=q))
    filtro = request.GET.get('filtro')
    if filtro == 'bajo':
        qs = qs.filter(stock__gt=0, stock__lte=Producto.STOCK_BAJO)
    elif filtro == 'agotado':
        qs = qs.filter(stock=0)
    return render(request, 'panel/stock.html', {
        'seccion': 'stock', 'pagina': _paginar(request, qs.order_by('stock', 'marca'), 25), 'q': q,
        'filtro': filtro, 'umbral': Producto.STOCK_BAJO,
        'agotados': Producto.objects.filter(stock=0).count(),
        'bajos': Producto.objects.filter(stock__gt=0, stock__lte=Producto.STOCK_BAJO).count(),
        'unidades': Producto.objects.aggregate(t=Sum('stock'))['t'] or 0,
    })


@admin_requerido
@require_POST
def stock_actualizar(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    destino = request.POST.get('next', '')
    destino = destino if destino.startswith('/panel/') else 'panel:stock'
    try:
        valor = int(request.POST.get('valor', ''))
    except ValueError:
        messages.error(request, 'Ingresá un número entero válido.')
        return redirect(destino)

    if request.POST.get('modo') == 'sumar':
        nuevo = producto.stock + valor
    else:
        nuevo = valor
    if nuevo < 0:
        messages.error(request, 'El stock no puede quedar negativo.')
    else:
        producto.stock = nuevo
        producto.save(update_fields=['stock', 'actualizado'])
        messages.success(request, f'Stock de “{producto.nombre}” actualizado a {nuevo} unidades.')
    return redirect(destino)


# ---------------------------------------------------------------------------
# Categorías
# ---------------------------------------------------------------------------
@admin_requerido
def categorias(request):
    qs = Categoria.objects.annotate(cantidad=Count('productos')).order_by('orden', 'nombre')
    return render(request, 'panel/categorias.html', {'seccion': 'categorias', 'categorias': qs})


@admin_requerido
def categoria_crear(request):
    return _formulario(request, CategoriaForm, None, 'Nueva categoría', 'panel:categorias', 'categorias')


@admin_requerido
def categoria_editar(request, pk):
    cat = get_object_or_404(Categoria, pk=pk)
    return _formulario(request, CategoriaForm, cat, f'Editar categoría: {cat}', 'panel:categorias', 'categorias')


@admin_requerido
@require_POST
def categoria_eliminar(request, pk):
    cat = get_object_or_404(Categoria, pk=pk)
    cat.delete()
    messages.success(request, f'Categoría “{cat}” eliminada. Sus productos quedaron sin categoría.')
    return redirect('panel:categorias')


# ---------------------------------------------------------------------------
# Pedidos (CU-30 / CU-31)
# ---------------------------------------------------------------------------
@admin_requerido
def pedidos(request):
    qs = Pedido.objects.select_related('usuario', 'pago')
    q = request.GET.get('q', '').strip()
    if q:
        filtro = Q(email__icontains=q) | Q(apellido__icontains=q) | Q(nombre__icontains=q)
        numero = q.upper().replace('FR-', '')
        if numero.isdigit():
            filtro |= Q(pk=int(numero))
        qs = qs.filter(filtro)
    estado = request.GET.get('estado', '')
    if estado:
        qs = qs.filter(estado=estado)
    conteos = dict(Pedido.objects.values_list('estado').annotate(c=Count('id')))
    return render(request, 'panel/pedidos.html', {
        'seccion': 'pedidos', 'pagina': _paginar(request, qs), 'q': q, 'estado': estado,
        'estados': [(v, l, conteos.get(v, 0)) for v, l in Pedido.Estado.choices],
    })


@admin_requerido
def pedido_detalle(request, pk):
    pedido = get_object_or_404(
        Pedido.objects.select_related('usuario', 'pago', 'cupon').prefetch_related('detalles__producto'), pk=pk
    )
    form = EstadoPedidoForm(request.POST or None, initial={'estado': pedido.estado})
    if request.method == 'POST' and form.is_valid():
        try:
            cambiar_estado(pedido, form.cleaned_data['estado'])
            messages.success(request, f'Pedido {pedido.codigo} actualizado.')
        except CompraError as e:
            messages.error(request, e.errores[0])
        return redirect('panel:pedido_detalle', pk=pk)
    return render(request, 'panel/pedido_detalle.html', {'seccion': 'pedidos', 'pedido': pedido, 'form': form})


# ---------------------------------------------------------------------------
# Usuarios y perfiles de acceso (CU-10 / CU-11)
# ---------------------------------------------------------------------------
@admin_requerido
def usuarios(request):
    qs = Usuario.objects.annotate(num_pedidos=Count('pedidos')).order_by('-date_joined')
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(Q(email__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q))
    rol = request.GET.get('rol', '')
    if rol:
        qs = qs.filter(rol=rol)
    return render(request, 'panel/usuarios.html', {
        'seccion': 'usuarios', 'pagina': _paginar(request, qs), 'q': q, 'rol': rol,
        'roles': Usuario.Rol.choices,
    })


@admin_requerido
def usuario_editar(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    form = UsuarioAdminForm(request.POST or None, instance=usuario)
    if usuario == request.user:
        # Evita que un administrador se quite a sí mismo el acceso
        form.fields['rol'].disabled = True
        form.fields['is_active'].disabled = True
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Usuario {usuario.email} actualizado.')
        return redirect('panel:usuarios')
    pedidos_usuario = usuario.pedidos.all()[:10]
    return render(request, 'panel/form.html', {
        'form': form, 'titulo': f'Usuario: {usuario.email}', 'volver': 'panel:usuarios',
        'seccion': 'usuarios', 'instancia': usuario, 'pedidos_usuario': pedidos_usuario,
    })


# ---------------------------------------------------------------------------
# Promociones y cupones (CU-32 a CU-34)
# ---------------------------------------------------------------------------
@admin_requerido
def promociones(request):
    return render(request, 'panel/promociones.html', {
        'seccion': 'promociones',
        'promociones': Promocion.objects.annotate(cantidad=Count('productos')).order_by('-fecha_inicio'),
        'cupones': Cupon.objects.all(),
    })


@admin_requerido
def promocion_crear(request):
    return _formulario(request, PromocionForm, None, 'Nueva promoción', 'panel:promociones', 'promociones')


@admin_requerido
def promocion_editar(request, pk):
    promo = get_object_or_404(Promocion, pk=pk)
    return _formulario(request, PromocionForm, promo, f'Editar promoción: {promo.nombre}', 'panel:promociones', 'promociones')


@admin_requerido
@require_POST
def promocion_alternar(request, pk):
    promo = get_object_or_404(Promocion, pk=pk)
    promo.activa = not promo.activa
    promo.save(update_fields=['activa'])
    messages.success(request, f'Promoción “{promo.nombre}” {"activada" if promo.activa else "desactivada"}.')
    return redirect('panel:promociones')


@admin_requerido
def cupon_crear(request):
    return _formulario(request, CuponForm, None, 'Nuevo cupón', 'panel:promociones', 'promociones')


@admin_requerido
def cupon_editar(request, pk):
    cupon = get_object_or_404(Cupon, pk=pk)
    return _formulario(request, CuponForm, cupon, f'Editar cupón: {cupon.codigo}', 'panel:promociones', 'promociones')


@admin_requerido
@require_POST
def cupon_alternar(request, pk):
    cupon = get_object_or_404(Cupon, pk=pk)
    cupon.activo = not cupon.activo
    cupon.save(update_fields=['activo'])
    messages.success(request, f'Cupón {cupon.codigo} {"activado" if cupon.activo else "desactivado"}.')
    return redirect('panel:promociones')

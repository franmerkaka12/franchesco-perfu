from decimal import Decimal, InvalidOperation

from django import template

from tienda.utils import formato_pesos

register = template.Library()


@register.filter
def pesos(valor):
    """{{ producto.precio|pesos }} -> $202.000"""
    return formato_pesos(valor)


@register.filter
def cuota(valor, cuotas=6):
    """Valor de cada cuota sin interés."""
    try:
        return formato_pesos(Decimal(valor) / Decimal(cuotas))
    except (InvalidOperation, TypeError, ValueError, ZeroDivisionError):
        return ''


@register.filter
def sin_impuestos(valor):
    """Precio sin impuestos nacionales (IVA 21%), según la normativa argentina."""
    try:
        return formato_pesos(Decimal(valor) / Decimal('1.21'))
    except (InvalidOperation, TypeError, ValueError):
        return ''


@register.simple_tag(takes_context=True)
def url_con(context, **kwargs):
    """Devuelve la query string actual reemplazando los parámetros indicados."""
    query = context['request'].GET.copy()
    for clave, valor in kwargs.items():
        if valor in (None, ''):
            query.pop(clave, None)
        else:
            query[clave] = valor
    return '?' + query.urlencode() if query else '?'

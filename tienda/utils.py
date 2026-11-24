from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django.utils.text import slugify


def formato_pesos(valor):
    """Formatea un importe al estilo argentino: $202.000"""
    try:
        numero = Decimal(valor)
    except (InvalidOperation, TypeError, ValueError):
        return valor
    entero = int(numero.quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    signo = '-' if entero < 0 else ''
    return f'{signo}${abs(entero):,}'.replace(',', '.')


def slug_unico(instancia, texto, campo='slug', largo=150):
    """Genera un slug único para la instancia dentro de su modelo."""
    base = slugify(texto)[:largo] or 'item'
    slug, n = base, 2
    modelo = type(instancia)
    while modelo.objects.filter(**{campo: slug}).exclude(pk=instancia.pk).exists():
        slug = f'{base}-{n}'
        n += 1
    return slug


def ajustar_imagen_producto(archivo, margen=0.06, lado_max=1600):
    """Recorta los bordes blancos/transparentes de una foto de producto y la
    centra en un lienzo cuadrado blanco, para que el producto ocupe todo el
    recuadro en la tienda. Devuelve un ContentFile JPEG o None si no se pudo."""
    from io import BytesIO

    from django.core.files.base import ContentFile
    from PIL import Image, ImageChops

    try:
        img = Image.open(archivo)
        img.load()
    except Exception:
        return None
    if img.mode in ('RGBA', 'LA', 'P'):
        rgba = img.convert('RGBA')
        fondo = Image.new('RGBA', rgba.size, (255, 255, 255, 255))
        fondo.alpha_composite(rgba)
        img = fondo
    rgb = img.convert('RGB')
    blanco = Image.new('RGB', rgb.size, (255, 255, 255))
    mascara = ImageChops.difference(rgb, blanco).convert('L').point(lambda v: 255 if v > 18 else 0)
    bbox = mascara.getbbox()
    if not bbox:
        return None
    recorte = rgb.crop(bbox)
    w, h = recorte.size
    lado = int(max(w, h) * (1 + margen * 2))
    lienzo = Image.new('RGB', (lado, lado), (255, 255, 255))
    lienzo.paste(recorte, ((lado - w) // 2, (lado - h) // 2))
    if lado > lado_max:
        lienzo = lienzo.resize((lado_max, lado_max), Image.LANCZOS)
    buffer = BytesIO()
    lienzo.save(buffer, 'JPEG', quality=90, optimize=True)
    return ContentFile(buffer.getvalue())

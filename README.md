# Franchesco · Plataforma web de venta y control de stock

Proyecto del Seminario de Práctica de Analista en Software (Universidad Siglo 21).
E-commerce de perfumería desarrollado con **Python + Django**, **base de datos relacional (SQLite)**
y una interfaz **HTML / CSS / JavaScript + Bootstrap 5** adaptable a celulares.

## Cómo ejecutarlo

**Opción rápida (Windows):** doble clic en `iniciar.bat`.

**Opción manual:**

```bash
venv\Scripts\activate              # activar el entorno virtual
pip install -r requirements.txt    # solo la primera vez
python manage.py migrate           # crear la base de datos
python manage.py cargar_datos      # datos de ejemplo (solo la primera vez)
python manage.py runserver
```

Luego abrir <http://127.0.0.1:8000/>.

| Usuario de prueba | Email | Contraseña |
|---|---|---|
| Administrador | admin@franchesco.com | Admin1234! |
| Cliente | cliente@franchesco.com | Cliente1234! |

Cupones de prueba: `BIENVENIDA10` (10%), `FRAN5000` ($5.000 desde $100.000) y `VERANO2025` (vencido).

Pruebas automáticas: `python manage.py test`

## Estructura

```
franchesco/     Configuración del proyecto (settings, urls)
cuentas/        Módulo de usuarios: registro, login, perfil, roles (cliente / administrador)
tienda/         Módulo de catálogo: productos, categorías, búsqueda, filtros, stock
promociones/    Módulo de promociones, cupones y descuentos
carrito/        Módulo de carrito de compras (en sesión, funciona también para visitantes)
pedidos/        Módulo de compras, pedidos y pagos (services.py contiene la lógica de compra)
panel/          Módulo administrativo (dashboard, ABM de productos, stock, pedidos, usuarios, promos)
templates/      Plantillas HTML
static/         CSS, JavaScript e imágenes (logo)
media/          Imágenes de productos subidas desde el panel
```

## Trazabilidad con los requerimientos

| Requerimiento | Dónde se implementa |
|---|---|
| RF-01/02/03 Catálogo, búsqueda y filtros | `tienda/views.py` → `catalogo`, `detalle` |
| RF-04/05/07 Registro, login, cuenta | `cuentas/views.py` |
| RF-06, RNF-03/04 Permisos por rol | `Usuario.rol`, `cuentas/decorators.py` (`admin_requerido`) |
| RF-08/09 Carrito e importe | `carrito/carrito.py` |
| RF-10 Login obligatorio para comprar | `pedidos/views.py` → `checkout` (`@login_required`) |
| RF-11/12/16/17 Pago, pedido, verificación y descuento de stock | `pedidos/services.py` → `crear_pedido` (transacción atómica) |
| RF-13 Mis pedidos | `pedidos/views.py` → `mis_pedidos`, `detalle` |
| RF-14/15 ABM de productos y stock | `panel/views.py` → productos, stock |
| RF-18/19 Usuarios y pedidos | `panel/views.py` → usuarios, pedidos |
| RF-20/21 Promociones y cupones | `promociones/models.py`, `panel/views.py`, `carrito/views.py` |
| RF-22, RNF-02 Interfaz adaptable | Bootstrap 5 + `static/css/styles.css` |
| RNF-05 Integridad de datos | `transaction.atomic` + `select_for_update` en compras y cancelaciones |

## Notas

- Si un producto no tiene imagen cargada, la tienda dibuja un frasco ilustrado automáticamente.
- Al cancelar un pedido desde el panel, el stock y el uso del cupón se reponen.
- Eliminar un producto con ventas registradas lo oculta del catálogo para preservar el historial.
- El pago se registra como “pendiente” y el administrador lo confirma desde el panel; la
  integración con pasarelas de pago externas es el requerimiento candidato RC-05.

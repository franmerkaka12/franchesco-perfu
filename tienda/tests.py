"""Pruebas del catálogo, carrito, compra y panel administrativo."""
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from cuentas.models import Usuario
from pedidos.models import Pedido
from promociones.models import Cupon, Promocion
from tienda.models import Categoria, Producto


class BaseTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cat = Categoria.objects.create(nombre='Perfumes')
        cls.p1 = Producto.objects.create(nombre='Sauvage', marca='Dior', genero='M', precio=Decimal('100000'), stock=5, categoria=cls.cat)
        cls.p2 = Producto.objects.create(nombre='Good Girl', marca='Carolina Herrera', genero='F', precio=Decimal('50000'), stock=1, categoria=cls.cat)
        cls.oculto = Producto.objects.create(nombre='Oculto', marca='X', precio=Decimal('1000'), stock=3, activo=False)
        cls.cliente = Usuario.objects.create_user('cli@test.com', 'Clave-segura-123', first_name='Ana', last_name='Paz')
        cls.admin = Usuario.objects.create_user('adm@test.com', 'Clave-segura-123', rol=Usuario.Rol.ADMIN)

    def checkout_datos(self, **extra):
        datos = {'nombre': 'Ana', 'apellido': 'Paz', 'telefono': '123', 'direccion': 'Calle 1',
                 'ciudad': 'Córdoba', 'codigo_postal': '5000', 'metodo_pago': 'credito'}
        datos.update(extra)
        return datos


class CatalogoTests(BaseTest):
    def test_visitante_puede_navegar_sin_login(self):  # RF-01
        for url in (reverse('tienda:inicio'), reverse('tienda:catalogo'), self.p1.get_absolute_url()):
            self.assertEqual(self.client.get(url).status_code, 200)

    def test_busqueda_por_nombre_o_marca(self):  # RF-02
        r = self.client.get(reverse('tienda:catalogo'), {'q': 'dior'})
        self.assertContains(r, 'Sauvage')
        self.assertNotContains(r, 'Good Girl')

    def test_filtro_por_genero(self):  # RF-03
        r = self.client.get(reverse('tienda:catalogo'), {'genero': 'F'})
        self.assertContains(r, 'Good Girl')
        self.assertNotContains(r, 'Sauvage')

    def test_producto_oculto_no_se_muestra(self):
        self.assertEqual(self.client.get(self.oculto.get_absolute_url()).status_code, 404)

    def test_promocion_vigente_aplica_descuento(self):
        hoy = timezone.localdate()
        promo = Promocion.objects.create(nombre='Promo', porcentaje_descuento=Decimal('20'),
                                         fecha_inicio=hoy, fecha_fin=hoy + timedelta(days=1))
        promo.productos.add(self.p1)
        p = Producto.objects.con_promos().get(pk=self.p1.pk)
        self.assertEqual(p.precio_final, Decimal('80000.00'))


class CarritoYCompraTests(BaseTest):
    def agregar(self, producto, cantidad=1):
        return self.client.post(reverse('carrito:agregar', args=[producto.pk]), {'cantidad': cantidad})

    def test_visitante_agrega_al_carrito_pero_no_puede_comprar(self):  # CU-12 / RF-10
        self.agregar(self.p1)
        r = self.client.get(reverse('pedidos:checkout'))
        self.assertRedirects(r, f"{reverse('cuentas:login')}?next={reverse('pedidos:checkout')}")

    def test_carrito_no_supera_el_stock(self):  # CU-13
        self.agregar(self.p2, 5)
        self.assertEqual(self.client.session['carrito'][str(self.p2.pk)], 1)

    def test_compra_completa_descuenta_stock_y_registra_pedido(self):  # CU-17 a CU-22
        self.client.force_login(self.cliente)
        self.agregar(self.p1, 2)
        r = self.client.post(reverse('pedidos:checkout'), self.checkout_datos())
        pedido = Pedido.objects.get()
        self.assertRedirects(r, reverse('pedidos:confirmacion', args=[pedido.pk]))
        self.assertEqual(pedido.total, Decimal('200000'))
        self.assertEqual(pedido.detalles.get().cantidad, 2)
        self.assertEqual(pedido.pago.metodo, 'credito')
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.stock, 3)
        self.assertEqual(self.client.session['carrito'], {})

    def test_no_se_puede_comprar_sin_stock_suficiente(self):  # RF-16
        self.client.force_login(self.cliente)
        self.agregar(self.p2, 1)
        Producto.objects.filter(pk=self.p2.pk).update(stock=0)  # alguien compró antes
        self.client.post(reverse('pedidos:checkout'), self.checkout_datos())
        self.assertFalse(Pedido.objects.exists())

    def test_cupon_valido_y_vencido(self):  # CU-35 / CU-36
        hoy = timezone.localdate()
        Cupon.objects.create(codigo='DIEZ', valor=Decimal('10'), fecha_vencimiento=hoy + timedelta(days=5))
        Cupon.objects.create(codigo='VIEJO', valor=Decimal('10'), fecha_vencimiento=hoy - timedelta(days=1))
        self.client.force_login(self.cliente)
        self.agregar(self.p1, 1)
        self.client.post(reverse('carrito:aplicar_cupon'), {'codigo': 'viejo'})
        self.assertNotIn('cupon_id', self.client.session)
        self.client.post(reverse('carrito:aplicar_cupon'), {'codigo': 'diez'})
        self.client.post(reverse('pedidos:checkout'), self.checkout_datos())
        pedido = Pedido.objects.get()
        self.assertEqual(pedido.descuento, Decimal('10000.00'))
        self.assertEqual(pedido.total, Decimal('90000.00'))
        self.assertEqual(Cupon.objects.get(codigo='DIEZ').usos, 1)

    def test_cliente_solo_ve_sus_pedidos(self):  # CU-29
        self.client.force_login(self.cliente)
        self.agregar(self.p1)
        self.client.post(reverse('pedidos:checkout'), self.checkout_datos())
        pedido = Pedido.objects.get()
        otro = Usuario.objects.create_user('otro@test.com', 'Clave-segura-123')
        self.client.force_login(otro)
        self.assertEqual(self.client.get(pedido.get_absolute_url()).status_code, 404)


class PanelTests(BaseTest):
    def test_cliente_no_accede_al_panel(self):  # RNF-04
        self.client.force_login(self.cliente)
        r = self.client.get(reverse('panel:dashboard'))
        self.assertRedirects(r, reverse('tienda:inicio'))

    def test_admin_accede_a_todas_las_secciones(self):
        self.client.force_login(self.admin)
        for nombre in ('dashboard', 'productos', 'producto_crear', 'stock', 'categorias', 'pedidos',
                       'usuarios', 'promociones', 'promocion_crear', 'cupon_crear', 'categoria_crear'):
            self.assertEqual(self.client.get(reverse(f'panel:{nombre}')).status_code, 200, nombre)

    def test_admin_crea_producto(self):  # CU-23
        self.client.force_login(self.admin)
        r = self.client.post(reverse('panel:producto_crear'), {
            'nombre': 'Eros', 'marca': 'Versace', 'genero': 'M', 'tipo': 'EDT', 'volumen_ml': 100,
            'precio': '150000', 'stock': 7, 'activo': 'on', 'categoria': self.cat.pk,
            'pres-TOTAL_FORMS': 0, 'pres-INITIAL_FORMS': 0,
        })
        self.assertRedirects(r, reverse('panel:productos'))
        self.assertTrue(Producto.objects.filter(nombre='Eros', stock=7).exists())

    def test_actualizar_stock(self):  # CU-28
        self.client.force_login(self.admin)
        self.client.post(reverse('panel:stock_actualizar', args=[self.p1.pk]), {'modo': 'sumar', 'valor': 10})
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.stock, 15)

    def test_cancelar_pedido_repone_stock(self):  # CU-31
        self.client.force_login(self.cliente)
        self.client.post(reverse('carrito:agregar', args=[self.p1.pk]), {'cantidad': 2})
        self.client.post(reverse('pedidos:checkout'), self.checkout_datos())
        pedido = Pedido.objects.get()
        self.client.force_login(self.admin)
        self.client.post(reverse('panel:pedido_detalle', args=[pedido.pk]), {'estado': 'cancelado'})
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.stock, 5)

    def test_eliminar_producto_con_ventas_lo_oculta(self):  # CU-26
        self.client.force_login(self.cliente)
        self.client.post(reverse('carrito:agregar', args=[self.p1.pk]))
        self.client.post(reverse('pedidos:checkout'), self.checkout_datos())
        self.client.force_login(self.admin)
        self.client.post(reverse('panel:producto_eliminar', args=[self.p1.pk]))
        self.p1.refresh_from_db()
        self.assertFalse(self.p1.activo)


class PresentacionesTests(BaseTest):
    """Varios tamaños (ml) del mismo perfume en una sola publicación."""

    def crear_con_tamanos(self):
        self.client.force_login(self.admin)
        return self.client.post(reverse('panel:producto_crear'), {
            'nombre': 'Most Wanted', 'marca': 'Azzaro', 'genero': 'M', 'tipo': 'EDP', 'volumen_ml': 100,
            'precio': '236000', 'stock': 4, 'activo': 'on', 'categoria': self.cat.pk,
            'pres-TOTAL_FORMS': 1, 'pres-INITIAL_FORMS': 0,
            'pres-0-volumen_ml': 50, 'pres-0-precio': '160000', 'pres-0-stock': 3,
        })

    def test_admin_crea_producto_con_dos_tamanos(self):
        r = self.crear_con_tamanos()
        self.assertRedirects(r, reverse('panel:productos'))
        principal = Producto.objects.get(nombre='Most Wanted', volumen_ml=100)
        chico = principal.presentaciones.get()
        self.assertEqual((chico.volumen_ml, chico.precio, chico.stock), (50, Decimal('160000'), 3))
        self.assertEqual((chico.marca, chico.tipo, chico.genero), ('Azzaro', 'EDP', 'M'))

    def test_catalogo_muestra_una_sola_tarjeta_con_ambos_tamanos(self):
        self.crear_con_tamanos()
        r = self.client.get(reverse('tienda:catalogo'), {'q': 'Most Wanted'})
        self.assertEqual(len(r.context['pagina'].object_list), 1)
        self.assertContains(r, '50 ML')
        self.assertContains(r, '100 ML')

    def test_detalle_permite_elegir_tamano_y_comprarlo(self):
        self.crear_con_tamanos()
        chico = Producto.objects.get(nombre='Most Wanted', volumen_ml=50)
        r = self.client.get(Producto.objects.get(nombre='Most Wanted', volumen_ml=100).get_absolute_url())
        self.assertContains(r, chico.get_absolute_url())
        self.client.force_login(self.cliente)
        self.client.post(reverse('carrito:agregar', args=[chico.pk]), {'cantidad': 2})
        self.client.post(reverse('pedidos:checkout'), self.checkout_datos())
        chico.refresh_from_db()
        self.assertEqual(chico.stock, 1)
        self.assertEqual(Pedido.objects.get().detalles.get().nombre_producto, 'Most Wanted 50 ml')

    def test_editar_nombre_se_copia_a_los_tamanos(self):
        self.crear_con_tamanos()
        principal = Producto.objects.get(nombre='Most Wanted', volumen_ml=100)
        chico = principal.presentaciones.get()
        self.client.post(reverse('panel:producto_editar', args=[principal.pk]), {
            'nombre': 'Wanted Elixir', 'marca': 'Azzaro', 'genero': 'M', 'tipo': 'PARFUM', 'volumen_ml': 100,
            'precio': '236000', 'stock': 4, 'activo': 'on',
            'pres-TOTAL_FORMS': 1, 'pres-INITIAL_FORMS': 1,
            'pres-0-id': chico.pk, 'pres-0-principal': principal.pk,
            'pres-0-volumen_ml': 50, 'pres-0-precio': '170000', 'pres-0-stock': 3,
        })
        chico.refresh_from_db()
        self.assertEqual((chico.nombre, chico.tipo, chico.precio), ('Wanted Elixir', 'PARFUM', Decimal('170000')))

    def test_no_permite_tamano_repetido(self):
        self.client.force_login(self.admin)
        r = self.client.post(reverse('panel:producto_crear'), {
            'nombre': 'Repetido', 'marca': 'Azzaro', 'genero': 'M', 'tipo': 'EDP', 'volumen_ml': 100,
            'precio': '1000', 'stock': 1, 'activo': 'on',
            'pres-TOTAL_FORMS': 1, 'pres-INITIAL_FORMS': 0,
            'pres-0-volumen_ml': 100, 'pres-0-precio': '900', 'pres-0-stock': 1,
        })
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Producto.objects.filter(nombre='Repetido').exists())


class MarcasOcultasTests(BaseTest):
    def test_quitar_marca_de_la_lista_y_volver_a_usarla(self):
        self.client.force_login(self.admin)
        url = reverse('panel:producto_crear')
        self.assertIn('Dior', self.client.get(url).context['marcas'])
        r = self.client.post(reverse('panel:marca_ocultar'), {'marca': 'Dior'})
        self.assertEqual(r.json(), {'ok': True})
        self.assertNotIn('Dior', self.client.get(url).context['marcas'])
        # Tampoco aparece en el menú ni en el filtro de marcas de la tienda
        self.assertNotIn('Dior', self.client.get(reverse('tienda:catalogo')).context['nav_marcas'])
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.marca, 'Dior')  # los productos no cambian
        # Si se carga un producto con esa marca, vuelve a la lista
        self.client.post(url, {
            'nombre': 'Fahrenheit', 'marca': 'Dior', 'genero': 'M', 'tipo': 'EDT', 'volumen_ml': 100,
            'precio': '1000', 'stock': 1, 'activo': 'on', 'pres-TOTAL_FORMS': 0, 'pres-INITIAL_FORMS': 0,
        })
        self.assertIn('Dior', self.client.get(url).context['marcas'])
        self.assertIn('Dior', self.client.get(reverse('tienda:catalogo')).context['nav_marcas'])

    def test_cliente_no_puede_quitar_marcas(self):
        self.client.force_login(self.cliente)
        self.client.post(reverse('panel:marca_ocultar'), {'marca': 'Dior'})
        from tienda.models import MarcaOculta
        self.assertFalse(MarcaOculta.objects.exists())


class RecuperarPasswordTests(BaseTest):
    def test_recuperar_contrasena_por_mail(self):
        import re
        from django.core import mail
        r = self.client.post(reverse('cuentas:recuperar'), {'email': 'cli@test.com'})
        self.assertRedirects(r, reverse('cuentas:recuperar_enviado'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['cli@test.com'])
        enlace = re.search(r'https?://[^/]+(/cuentas/recuperar/[^\s]+/)', mail.outbox[0].body).group(1)
        r = self.client.get(enlace, follow=True)  # Django redirige al enlace "set-password"
        self.assertContains(r, 'Creá tu contraseña nueva')
        r = self.client.post(r.redirect_chain[-1][0], {'new_password1': 'Nueva.Clave2026', 'new_password2': 'Nueva.Clave2026'})
        self.assertRedirects(r, reverse('cuentas:recuperar_listo'))
        self.cliente.refresh_from_db()
        self.assertTrue(self.cliente.check_password('Nueva.Clave2026'))

    def test_correo_inexistente_no_revela_nada(self):
        from django.core import mail
        r = self.client.post(reverse('cuentas:recuperar'), {'email': 'nadie@test.com'})
        self.assertRedirects(r, reverse('cuentas:recuperar_enviado'))
        self.assertEqual(len(mail.outbox), 0)

    def test_login_tiene_enlace_para_recuperar(self):
        self.assertContains(self.client.get(reverse('cuentas:login')), reverse('cuentas:recuperar'))

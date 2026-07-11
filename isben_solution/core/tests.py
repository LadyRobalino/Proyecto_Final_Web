from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from .models import (
    Comprador, Empresa, Factura, Inventario, Pedido, Producto, Usuario, Vendedor,
)


def crear_usuario(username, rol, **kwargs):
    usuario = Usuario.objects.create_user(
        username=username, email=f"{username}@isben.test", password="Clave123!", rol=rol, **kwargs
    )
    return usuario


class ModelosTests(TestCase):
    """Pruebas de la lógica de negocio embebida en los modelos."""

    def test_empresa_tipo_ruc(self):
        usuario = crear_usuario('empresa1', 'empresa')
        empresa = Empresa.objects.create(
            usuario=usuario, ruc='1790012345001', razon_social='Distribuidora Test',
            representante_legal='Juan Pérez', direccion='Loja',
        )
        self.assertEqual(empresa.get_tipo_ruc(), 'Sociedad / Empresa')

    def test_inventario_stock_bajo(self):
        usuario = crear_usuario('empresa2', 'empresa')
        empresa = Empresa.objects.create(
            usuario=usuario, ruc='1790012345002', razon_social='Distribuidora 2',
            representante_legal='Ana Ruiz', direccion='Loja',
        )
        producto = Producto.objects.create(
            nombre='Producto A', precio_base=Decimal('5.00'), precio_venta=Decimal('8.00'),
            unidad_medida='caja', empresa=empresa,
        )
        inventario = Inventario.objects.create(producto=producto, stock_actual=2, stock_minimo=5, stock_maximo=100)
        self.assertTrue(inventario.stock_bajo())
        self.assertEqual(inventario.get_estado_stock(), 'Stock bajo')

    def test_factura_calcula_iva(self):
        usuario_empresa = crear_usuario('empresa3', 'empresa')
        empresa = Empresa.objects.create(
            usuario=usuario_empresa, ruc='1790012345003', razon_social='Distribuidora 3',
            representante_legal='Luis Vera', direccion='Loja',
        )
        usuario_comprador = crear_usuario('comprador1', 'comprador')
        comprador = Comprador.objects.create(
            usuario=usuario_comprador, tipo_negocio='Tienda', direccion_entrega='Av. Loja',
        )
        pedido = Pedido.objects.create(numero_pedido='PED-TEST-1', comprador=comprador, empresa=empresa, total=Decimal('100.00'))
        factura = Factura(pedido=pedido, numero_factura='FAC-TEST-1', subtotal=Decimal('100.00'))
        factura.calcular_iva()
        self.assertEqual(factura.iva, Decimal('15.00'))
        self.assertEqual(factura.total, Decimal('115.00'))

    def test_pedido_puede_cancelarse_segun_estado(self):
        usuario_empresa = crear_usuario('empresa4', 'empresa')
        empresa = Empresa.objects.create(
            usuario=usuario_empresa, ruc='1790012345004', razon_social='Distribuidora 4',
            representante_legal='Marta Soto', direccion='Loja',
        )
        usuario_comprador = crear_usuario('comprador2', 'comprador')
        comprador = Comprador.objects.create(
            usuario=usuario_comprador, tipo_negocio='Tienda', direccion_entrega='Av. Loja',
        )
        pedido = Pedido.objects.create(numero_pedido='PED-TEST-2', comprador=comprador, empresa=empresa)
        self.assertTrue(pedido.puede_cancelarse())
        pedido.estado = 'despachado'
        self.assertFalse(pedido.puede_cancelarse())


class AutenticacionTests(TestCase):
    """Pruebas del flujo de registro y control de acceso por rol."""

    def test_registro_crea_usuario_y_perfil_comprador(self):
        respuesta = self.client.post(reverse('registro'), {
            'rol': 'comprador', 'username': 'nuevo_comprador', 'first_name': 'Ana',
            'last_name': 'Gómez', 'email': 'ana@isben.test', 'telefono': '0999999999',
            'password1': 'ClaveSegura123', 'password2': 'ClaveSegura123',
            'tipo_negocio': 'Tienda de barrio', 'direccion_entrega': 'Calle Falsa 123',
        })
        self.assertEqual(respuesta.status_code, 302)
        usuario = Usuario.objects.get(username='nuevo_comprador')
        self.assertEqual(usuario.rol, 'comprador')
        self.assertTrue(Comprador.objects.filter(usuario=usuario).exists())

    def test_vista_protegida_redirige_a_login_si_no_autenticado(self):
        respuesta = self.client.get(reverse('lista_usuarios'))
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(reverse('login'), respuesta.url)

    def test_usuario_sin_rol_administrador_no_accede_a_gestion_usuarios(self):
        crear_usuario('comprador_normal', 'comprador')
        self.client.login(username='comprador_normal', password='Clave123!')
        respuesta = self.client.get(reverse('lista_usuarios'))
        self.assertEqual(respuesta.status_code, 403)


class FlujoPedidoTests(TestCase):
    """Prueba de extremo a extremo: pedido -> pago -> factura -> comisión (HU-12, HU-13, HU-16, HU-17)."""

    def setUp(self):
        self.usuario_empresa = crear_usuario('empresa_flujo', 'empresa')
        self.empresa = Empresa.objects.create(
            usuario=self.usuario_empresa, ruc='1790012345009', razon_social='Distribuidora Flujo',
            representante_legal='Carlos Nieto', direccion='Loja', estado='aprobado',
        )
        self.producto = Producto.objects.create(
            nombre='Producto Flujo', precio_base=Decimal('10.00'), precio_venta=Decimal('15.00'),
            unidad_medida='unidad', empresa=self.empresa,
        )
        self.usuario_vendedor = crear_usuario('vendedor_flujo', 'vendedor')
        self.vendedor = Vendedor.objects.create(usuario=self.usuario_vendedor, numero_identidad='1103344556')
        self.usuario_comprador = crear_usuario('comprador_flujo', 'comprador')
        self.comprador = Comprador.objects.create(
            usuario=self.usuario_comprador, tipo_negocio='Tienda', direccion_entrega='Av. Loja',
        )

    def test_validar_pago_genera_factura_y_comision(self):
        pedido = Pedido.objects.create(
            numero_pedido='PED-FLUJO-1', comprador=self.comprador, vendedor=self.vendedor,
            empresa=self.empresa, total=Decimal('150.00'),
        )
        from .models import Pago
        pago = Pago.objects.create(pedido=pedido, monto=Decimal('150.00'), tipo='total', metodo_pago='transferencia')

        self.client.login(username='empresa_flujo', password='Clave123!')
        respuesta = self.client.post(reverse('validar_pago', args=[pago.pk]))
        self.assertEqual(respuesta.status_code, 302)

        pago.refresh_from_db()
        pedido.refresh_from_db()
        self.assertEqual(pago.estado, 'validado')
        self.assertEqual(pedido.estado, 'confirmado')
        self.assertTrue(Factura.objects.filter(pedido=pedido).exists())
        self.assertTrue(pedido.comisiones.exists())

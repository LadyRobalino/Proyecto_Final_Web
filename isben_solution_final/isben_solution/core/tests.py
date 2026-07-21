from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from .models import (
    Calificacion, Comprador, DetallePedido, Empresa, Factura, Inventario,
    MovimientoPuntos, Notificacion, Pago, Pedido, Producto, SolicitudColaboracion,
    Usuario, Vendedor, PlanSuscripcion, Suscripcion, Curso, Evaluacion,
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
        self.assertEqual(pedido.estado, 'aceptado')
        self.assertTrue(Factura.objects.filter(pedido=pedido).exists())
        self.assertFalse(pedido.comisiones.exists())

        # Transition order to delivered to trigger commission generation
        self.client.post(reverse('cambiar_estado_pedido', args=[pedido.pk, 'preparando']))
        self.client.post(reverse('cambiar_estado_pedido', args=[pedido.pk, 'despachado']))
        self.client.post(reverse('cambiar_estado_pedido', args=[pedido.pk, 'entregado']))

        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, 'entregado')
        self.assertTrue(pedido.comisiones.exists())


class CoherenciaModulosTests(TestCase):
    """Pruebas de la Fase 1: rechazos con motivo, notificaciones, colaboración y flujo de pedido."""

    def setUp(self):
        self.usuario_admin = crear_usuario('admin_coherencia', 'administrador')
        self.usuario_admin.is_staff = True
        self.usuario_admin.save()

        self.usuario_empresa = crear_usuario('empresa_coherencia', 'empresa')
        self.empresa = Empresa.objects.create(
            usuario=self.usuario_empresa, ruc='1790012345010', razon_social='Distribuidora Coherencia',
            representante_legal='Rosa Nieto', direccion='Loja', estado='pendiente',
        )
        self.usuario_vendedor = crear_usuario('vendedor_coherencia', 'vendedor')
        self.vendedor = Vendedor.objects.create(
            usuario=self.usuario_vendedor, numero_identidad='1103344999', estado_aprobacion='aprobado',
        )
        self.usuario_comprador = crear_usuario('comprador_coherencia', 'comprador')
        self.comprador = Comprador.objects.create(
            usuario=self.usuario_comprador, tipo_negocio='Tienda', direccion_entrega='Av. Loja',
        )

    def test_rechazar_empresa_exige_motivo_y_notifica(self):
        self.client.login(username='admin_coherencia', password='Clave123!')
        respuesta = self.client.post(reverse('rechazar_empresa', args=[self.empresa.pk]), {'motivo': 'RUC inválido'})
        self.assertEqual(respuesta.status_code, 302)

        self.empresa.refresh_from_db()
        self.assertEqual(self.empresa.estado, 'rechazado')
        self.assertEqual(self.empresa.motivo_rechazo, 'RUC inválido')
        self.assertTrue(Notificacion.objects.filter(destinatario=self.usuario_empresa).exists())

    def test_solicitar_y_aceptar_colaboracion(self):
        self.empresa.estado = 'aprobado'
        self.empresa.save()

        self.client.login(username='vendedor_coherencia', password='Clave123!')
        respuesta = self.client.post(reverse('solicitar_colaboracion', args=[self.empresa.pk]))
        self.assertEqual(respuesta.status_code, 302)
        solicitud = SolicitudColaboracion.objects.get(vendedor=self.vendedor, empresa=self.empresa)
        self.assertEqual(solicitud.estado, 'pendiente')
        self.client.logout()

        self.client.login(username='empresa_coherencia', password='Clave123!')
        respuesta = self.client.post(reverse('responder_colaboracion', args=[solicitud.pk, 'aceptar']))
        self.assertEqual(respuesta.status_code, 302)

        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, 'aceptada')
        self.assertTrue(self.vendedor.empresas_aprobadoras.filter(pk=self.empresa.pk).exists())
        self.assertTrue(Notificacion.objects.filter(destinatario=self.usuario_vendedor).exists())

    def test_aceptar_pedido_descuenta_stock_y_rechazo_exige_motivo(self):
        self.empresa.estado = 'aprobado'
        self.empresa.save()
        producto = Producto.objects.create(
            nombre='Producto Coherencia', precio_base=Decimal('5.00'), precio_venta=Decimal('8.00'),
            unidad_medida='unidad', empresa=self.empresa,
        )
        inventario = Inventario.objects.create(producto=producto, stock_actual=10, stock_minimo=1, stock_maximo=100)
        pedido = Pedido.objects.create(
            numero_pedido='PED-COHERENCIA-1', comprador=self.comprador, empresa=self.empresa, total=Decimal('16.00'),
        )
        from .models import DetallePedido
        DetallePedido.objects.create(
            pedido=pedido, producto=producto, cantidad=3, precio_unitario=Decimal('8.00'), subtotal=Decimal('24.00'),
        )

        self.client.login(username='empresa_coherencia', password='Clave123!')
        respuesta = self.client.post(reverse('cambiar_estado_pedido', args=[pedido.pk, 'aceptado']))
        self.assertEqual(respuesta.status_code, 302)

        pedido.refresh_from_db()
        inventario.refresh_from_db()
        self.assertEqual(pedido.estado, 'aceptado')
        self.assertEqual(inventario.stock_actual, 7)
        self.assertTrue(Notificacion.objects.filter(destinatario=self.usuario_comprador).exists())

        # Un pedido ya aceptado no puede rechazarse sin pasar antes por pendiente.
        respuesta = self.client.post(reverse('cambiar_estado_pedido', args=[pedido.pk, 'rechazado']), {'motivo': 'sin stock'})
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, 'aceptado')

    def test_cerrar_incidencia_requiere_resolucion(self):
        calificacion = Calificacion.objects.create(
            autor=self.usuario_comprador, tipo_calificado='empresa', empresa_calificada=self.empresa,
            puntuacion=1, comentario='Producto dañado', es_incidencia=True,
        )
        self.assertEqual(calificacion.estado_incidencia, 'abierta')

        self.client.login(username='admin_coherencia', password='Clave123!')
        respuesta = self.client.post(reverse('cerrar_incidencia', args=[calificacion.pk]), {
            'resolucion': 'Se aprobó la devolución del producto.',
        })
        self.assertEqual(respuesta.status_code, 302)

        calificacion.refresh_from_db()
        self.assertEqual(calificacion.estado_incidencia, 'cerrada')
        self.assertIn('devolución', calificacion.resolucion)


class CarritoFidelizacionTests(TestCase):
    """Pruebas de la Fase 2/3: carrito multi-empresa, puntos de fidelización, calificación por pedido y repetir pedido."""

    def setUp(self):
        self.usuario_empresa1 = crear_usuario('empresa_carrito1', 'empresa')
        self.empresa1 = Empresa.objects.create(
            usuario=self.usuario_empresa1, ruc='1790012345020', razon_social='Distribuidora Uno',
            representante_legal='Pedro Ruiz', direccion='Loja', estado='aprobado',
        )
        self.usuario_empresa2 = crear_usuario('empresa_carrito2', 'empresa')
        self.empresa2 = Empresa.objects.create(
            usuario=self.usuario_empresa2, ruc='1790012345021', razon_social='Distribuidora Dos',
            representante_legal='Nora Vega', direccion='Loja', estado='aprobado',
        )
        self.producto1 = Producto.objects.create(
            nombre='Producto Uno', precio_base=Decimal('5.00'), precio_venta=Decimal('10.00'),
            unidad_medida='unidad', empresa=self.empresa1,
        )
        Inventario.objects.create(producto=self.producto1, stock_actual=50, stock_minimo=1, stock_maximo=200)
        self.producto2 = Producto.objects.create(
            nombre='Producto Dos', precio_base=Decimal('5.00'), precio_venta=Decimal('20.00'),
            unidad_medida='unidad', empresa=self.empresa2,
        )
        Inventario.objects.create(producto=self.producto2, stock_actual=50, stock_minimo=1, stock_maximo=200)

        self.usuario_comprador = crear_usuario('comprador_carrito', 'comprador')
        self.comprador = Comprador.objects.create(
            usuario=self.usuario_comprador, tipo_negocio='Tienda', direccion_entrega='Av. Loja',
        )

    def test_checkout_carrito_crea_un_pedido_por_empresa(self):
        self.client.login(username='comprador_carrito', password='Clave123!')
        self.client.post(reverse('agregar_al_carrito', args=[self.producto1.pk]), {'cantidad': 2})
        self.client.post(reverse('agregar_al_carrito', args=[self.producto2.pk]), {'cantidad': 1})

        respuesta = self.client.post(reverse('checkout_carrito'), {
            'direccion_nueva': 'Calle Nueva 123',
            'metodo_pago': 'transferencia',
        })
        self.assertEqual(respuesta.status_code, 302)
        pedidos = Pedido.objects.filter(comprador=self.comprador)
        self.assertEqual(pedidos.count(), 2)
        for pedido in pedidos:
            self.assertTrue(Pago.objects.filter(pedido=pedido, estado='pendiente').exists())
            self.assertEqual(pedido.direccion_entrega, 'Calle Nueva 123')

        self.assertEqual(self.client.session.get('carrito', {}), {})

    def test_entregar_pedido_otorga_puntos_y_sube_de_nivel(self):
        pedido = Pedido.objects.create(
            numero_pedido='PED-FIDE-1', comprador=self.comprador, empresa=self.empresa1,
            total=Decimal('600.00'), estado='despachado',
        )
        self.client.login(username='empresa_carrito1', password='Clave123!')
        respuesta = self.client.post(reverse('cambiar_estado_pedido', args=[pedido.pk, 'entregado']))
        self.assertEqual(respuesta.status_code, 302)

        self.comprador.refresh_from_db()
        self.assertEqual(self.comprador.puntos, 600)
        self.assertEqual(self.comprador.nivel, 'plata')
        self.assertTrue(MovimientoPuntos.objects.filter(comprador=self.comprador, pedido=pedido).exists())

    def test_crear_calificacion_desde_pedido_bloquea_objetivo_y_evita_duplicado(self):
        pedido = Pedido.objects.create(
            numero_pedido='PED-FIDE-2', comprador=self.comprador, empresa=self.empresa1,
            total=Decimal('50.00'), estado='entregado',
        )
        self.client.login(username='comprador_carrito', password='Clave123!')
        respuesta = self.client.post(
            reverse('crear_calificacion') + f'?pedido={pedido.pk}&tipo=empresa',
            {'puntuacion': 5, 'comentario': 'Excelente servicio'},
        )
        self.assertEqual(respuesta.status_code, 302)
        calificacion = Calificacion.objects.get(pedido=pedido, tipo_calificado='empresa')
        self.assertEqual(calificacion.empresa_calificada, self.empresa1)

        respuesta = self.client.get(reverse('crear_calificacion') + f'?pedido={pedido.pk}&tipo=empresa')
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(Calificacion.objects.filter(pedido=pedido, tipo_calificado='empresa').count(), 1)

    def test_repetir_pedido_reconstruye_carrito(self):
        pedido = Pedido.objects.create(
            numero_pedido='PED-FIDE-3', comprador=self.comprador, empresa=self.empresa1, total=Decimal('20.00'),
        )
        DetallePedido.objects.create(
            pedido=pedido, producto=self.producto1, cantidad=2,
            precio_unitario=Decimal('10.00'), subtotal=Decimal('20.00'),
        )
        self.client.login(username='comprador_carrito', password='Clave123!')
        respuesta = self.client.post(reverse('repetir_pedido', args=[pedido.pk]))
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(self.client.session['carrito'].get(str(self.producto1.pk)), 2)


class EstadisticasCanjeComparacionTests(TestCase):
    """Pruebas de: estadísticas de empresa, canje de puntos en checkout y comparación de productos."""

    def setUp(self):
        self.usuario_empresa = crear_usuario('empresa_estadisticas', 'empresa')
        self.empresa = Empresa.objects.create(
            usuario=self.usuario_empresa, ruc='1790012345030', razon_social='Distribuidora Estadísticas',
            representante_legal='Sara Leon', direccion='Loja', estado='aprobado', tiempo_entrega_dias=3,
        )
        self.producto1 = Producto.objects.create(
            nombre='Producto Top', precio_base=Decimal('10.00'), precio_venta=Decimal('20.00'),
            unidad_medida='unidad', empresa=self.empresa,
        )
        Inventario.objects.create(producto=self.producto1, stock_actual=50, stock_minimo=1, stock_maximo=200)
        self.producto2 = Producto.objects.create(
            nombre='Producto Bajo', precio_base=Decimal('5.00'), precio_venta=Decimal('9.00'),
            unidad_medida='unidad', empresa=self.empresa,
        )
        Inventario.objects.create(producto=self.producto2, stock_actual=50, stock_minimo=1, stock_maximo=200)

        self.usuario_comprador = crear_usuario('comprador_estadisticas', 'comprador')
        self.comprador = Comprador.objects.create(
            usuario=self.usuario_comprador, tipo_negocio='Tienda', ciudad='Loja',
            direccion_entrega='Av. Loja', puntos=1000,
        )

        pedido = Pedido.objects.create(
            numero_pedido='PED-ESTAD-1', comprador=self.comprador, empresa=self.empresa,
            total=Decimal('40.00'), estado='entregado',
        )
        DetallePedido.objects.create(
            pedido=pedido, producto=self.producto1, cantidad=2,
            precio_unitario=Decimal('20.00'), subtotal=Decimal('40.00'),
        )

    def test_estadisticas_empresa_incluye_productos_y_ciudad(self):
        self.client.login(username='empresa_estadisticas', password='Clave123!')
        respuesta = self.client.get(reverse('estadisticas_empresa'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Producto Top')
        self.assertContains(respuesta, 'Loja')

    def test_checkout_carrito_canjea_puntos_por_descuento(self):
        self.client.login(username='comprador_estadisticas', password='Clave123!')
        self.client.post(reverse('agregar_al_carrito', args=[self.producto1.pk]), {'cantidad': 1})

        respuesta = self.client.post(reverse('checkout_carrito'), {
            'direccion_nueva': 'Calle Canje 1', 'metodo_pago': 'efectivo', 'usar_puntos': 'on',
        })
        self.assertEqual(respuesta.status_code, 302)

        pedido = Pedido.objects.filter(comprador=self.comprador, numero_pedido__startswith='PED-2').latest('fecha_creacion')
        self.assertEqual(pedido.subtotal, Decimal('20.00'))
        self.assertEqual(pedido.descuento, Decimal('10.00'))
        self.assertEqual(pedido.iva, Decimal('1.50'))
        self.assertEqual(pedido.total, Decimal('11.50'))

        self.comprador.refresh_from_db()
        self.assertEqual(self.comprador.puntos, 0)
        self.assertTrue(MovimientoPuntos.objects.filter(comprador=self.comprador, puntos=-1000).exists())

    def test_comparar_productos_muestra_precio_stock_y_entrega(self):
        self.client.login(username='comprador_estadisticas', password='Clave123!')
        url = reverse('comparar_productos') + f'?productos={self.producto1.pk},{self.producto2.pk}'
        respuesta = self.client.get(url)
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Producto Top')
        self.assertContains(respuesta, 'Producto Bajo')
        self.assertContains(respuesta, '3 día(s)')


class SuscripcionesCursosCapacitacionTests(TestCase):
    """Pruebas del nuevo flujo de suscripción para vendedores, acceso controlado a cursos y toma de evaluaciones."""

    def setUp(self):
        self.usuario_admin = crear_usuario('admin_cap', 'administrador')
        self.usuario_admin.is_staff = True
        self.usuario_admin.save()

        self.usuario_vendedor = crear_usuario('vendedor_cap', 'vendedor')
        self.vendedor = Vendedor.objects.create(
            usuario=self.usuario_vendedor, numero_identidad='1103344666', estado_aprobacion='aprobado'
        )

        # Crear planes para vendedores y empresas
        self.plan_gratis = PlanSuscripcion.objects.create(
            nombre='Plan Gratuito', precio=Decimal('0.00'), tipo='vendedor'
        )
        self.plan_plus = PlanSuscripcion.objects.create(
            nombre='Plan Vendedor Plus', precio=Decimal('9.99'), tipo='vendedor'
        )

        # Crear cursos
        self.curso_libre = Curso.objects.create(
            titulo='Curso Libre', duracion_horas=2.0, activo=True
        )
        self.curso_plus = Curso.objects.create(
            titulo='Curso Plus', duracion_horas=5.0, activo=True, plan_requerido=self.plan_plus
        )

    def test_vendedor_suscripcion_y_control_acceso_curso(self):
        self.client.login(username='vendedor_cap', password='Clave123!')
        
        # 1. Por defecto no tiene suscripción. Intenta ingresar a curso_plus -> Redirigido a lista de suscripciones
        respuesta = self.client.get(reverse('detalle_curso', args=[self.curso_plus.pk]))
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(reverse('lista_suscripciones'), respuesta.url)

        # 2. Se suscribe al plan gratis. Sigue sin poder acceder al curso_plus
        self.client.post(reverse('suscribir_empresa', args=[self.plan_gratis.pk]))
        self.assertTrue(self.vendedor.suscripciones.filter(estado='activa', plan=self.plan_gratis).exists())
        respuesta = self.client.get(reverse('detalle_curso', args=[self.curso_plus.pk]))
        self.assertEqual(respuesta.status_code, 302)

        # 3. Se suscribe al plan plus. Ahora puede ingresar a curso_plus
        self.client.post(reverse('suscribir_empresa', args=[self.plan_plus.pk]))
        self.assertTrue(self.vendedor.suscripciones.filter(estado='activa', plan=self.plan_plus).exists())
        respuesta = self.client.get(reverse('detalle_curso', args=[self.curso_plus.pk]))
        self.assertEqual(respuesta.status_code, 200)

    def test_vendedor_realiza_evaluacion_y_obtiene_certificado(self):
        self.client.login(username='vendedor_cap', password='Clave123!')
        # Suscribir a plus para acceder
        self.client.post(reverse('suscribir_empresa', args=[self.plan_plus.pk]))

        # Realizar evaluación: responder todas correctas (q1=correct, q2=correct, q3=correct) -> obtiene 10/10 y aprueba
        respuesta = self.client.post(reverse('realizar_evaluacion', args=[self.curso_plus.pk]), {
            'q1': 'correct', 'q2': 'correct', 'q3': 'correct'
        })
        self.assertEqual(respuesta.status_code, 302)
        
        evaluacion = Evaluacion.objects.get(vendedor=self.vendedor, curso=self.curso_plus)
        self.assertTrue(evaluacion.aprobado)
        self.assertEqual(evaluacion.puntaje_obtenido, 10.0)

        # Verificar detalle de la evaluación muestra el certificado
        respuesta = self.client.get(reverse('detalle_evaluacion', args=[evaluacion.pk]))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Certificado Oficial ISBEN')

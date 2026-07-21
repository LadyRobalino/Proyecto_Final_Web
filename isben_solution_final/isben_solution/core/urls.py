from django.urls import path
from . import views

urlpatterns = [

    # Página principal
    path('', views.inicio, name='inicio'),

    # ==========================
    # Autenticación
    # ==========================
    path('cuenta/registro/', views.registro, name='registro'),
    path('cuenta/login/', views.iniciar_sesion, name='login'),
    path('cuenta/logout/', views.cerrar_sesion, name='logout'),
    path('cuenta/perfil/', views.mi_cuenta, name='mi_cuenta'),
    path('cuenta/perfil/password/', views.cambiar_password, name='cambiar_password'),

    # ==========================
    # Módulo Usuarios
    # ==========================
    path('usuarios/', views.lista_usuarios, name='lista_usuarios'),
    path('usuarios/crear/', views.crear_usuario, name='crear_usuario'),
    path('usuarios/<int:pk>/', views.detalle_usuario, name='detalle_usuario'),
    path('usuarios/<int:pk>/editar/', views.editar_usuario, name='editar_usuario'),
    path('usuarios/<int:pk>/eliminar/', views.eliminar_usuario, name='eliminar_usuario'),
    path('usuarios/<int:pk>/bloquear/', views.bloquear_usuario, name='bloquear_usuario'),

    # ==========================
    # Empresas
    # ==========================
    path('empresas/', views.lista_empresas, name='lista_empresas'),
    path('empresas/crear/', views.crear_empresa, name='crear_empresa'),
    path('empresas/<int:pk>/', views.detalle_empresa, name='detalle_empresa'),
    path('empresas/<int:pk>/editar/', views.editar_empresa, name='editar_empresa'),
    path('empresas/<int:pk>/eliminar/', views.eliminar_empresa, name='eliminar_empresa'),
    path('empresas/<int:pk>/aprobar/', views.aprobar_empresa, name='aprobar_empresa'),
    path('empresas/<int:pk>/rechazar/', views.rechazar_empresa, name='rechazar_empresa'),
    path('empresas/<int:pk_empresa>/solicitar-colaboracion/', views.solicitar_colaboracion, name='solicitar_colaboracion'),
    path('empresas/solicitudes-colaboracion/', views.lista_solicitudes_colaboracion, name='lista_solicitudes_colaboracion'),

    # ==========================
    # Vendedores
    # ==========================
    path('vendedores/', views.lista_vendedores, name='lista_vendedores'),
    path('vendedores/crear/', views.crear_vendedor, name='crear_vendedor'),
    path('vendedores/<int:pk>/', views.detalle_vendedor, name='detalle_vendedor'),
    path('vendedores/<int:pk>/editar/', views.editar_vendedor, name='editar_vendedor'),
    path('vendedores/<int:pk>/eliminar/', views.eliminar_vendedor, name='eliminar_vendedor'),
    path('vendedores/<int:pk>/autorizar/', views.autorizar_vendedor, name='autorizar_vendedor'),
    path('vendedores/<int:pk>/aprobar/', views.aprobar_vendedor, name='aprobar_vendedor'),
    path('vendedores/<int:pk>/rechazar/', views.rechazar_vendedor, name='rechazar_vendedor'),
    path('vendedores/<int:pk>/suspender/', views.suspender_vendedor, name='suspender_vendedor'),
    path('vendedores/<int:pk>/bloquear/', views.bloquear_vendedor, name='bloquear_vendedor'),
    path('solicitudes-colaboracion/<int:pk_solicitud>/<str:accion>/', views.responder_colaboracion, name='responder_colaboracion'),

    # ==========================
    # Compradores
    # ==========================
    path('compradores/', views.lista_compradores, name='lista_compradores'),
    path('compradores/<int:pk>/', views.detalle_comprador, name='detalle_comprador'),
    path('compradores/<int:pk>/desvincular/', views.desvincular_comprador, name='desvincular_comprador'),

    # ==========================
    # Categorías y Productos
    # ==========================
    path('categorias/', views.lista_categorias, name='lista_categorias'),
    path('categorias/crear/', views.crear_categoria, name='crear_categoria'),
    path('categorias/<int:pk>/editar/', views.editar_categoria, name='editar_categoria'),
    path('categorias/<int:pk>/eliminar/', views.eliminar_categoria, name='eliminar_categoria'),

    path('productos/', views.lista_productos, name='lista_productos'),
    path('productos/comparar/', views.comparar_productos, name='comparar_productos'),
    path('productos/crear/', views.crear_producto, name='crear_producto'),
    path('productos/<int:pk>/', views.detalle_producto, name='detalle_producto'),
    path('productos/<int:pk>/editar/', views.editar_producto, name='editar_producto'),
    path('productos/<int:pk>/eliminar/', views.eliminar_producto, name='eliminar_producto'),

    # ==========================
    # Inventario
    # ==========================
    path('inventario/', views.lista_inventario, name='lista_inventario'),
    path('inventario/crear/', views.crear_inventario, name='crear_inventario'),
    path('inventario/<int:pk>/editar/', views.editar_inventario, name='editar_inventario'),
    path('inventario/<int:pk>/eliminar/', views.eliminar_inventario, name='eliminar_inventario'),
    path('inventario/<int:pk>/actualizar-stock-rapido/', views.actualizar_stock_rapido, name='actualizar_stock_rapido'),

    # ==========================
    # Ventas: Pedidos
    # ==========================
    path('pedidos/', views.lista_pedidos, name='lista_pedidos'),
    path('pedidos/crear/', views.crear_pedido, name='crear_pedido'),
    path('pedidos/<int:pk>/', views.detalle_pedido, name='detalle_pedido'),
    path('pedidos/<int:pk>/estado/<str:estado>/', views.cambiar_estado_pedido, name='cambiar_estado_pedido'),


    # ==========================
    # Carrito y checkout (Comprador)
    # ==========================
    path('carrito/', views.ver_carrito, name='ver_carrito'),
    path('carrito/agregar/<int:pk_producto>/', views.agregar_al_carrito, name='agregar_al_carrito'),
    path('carrito/actualizar/<int:pk_producto>/', views.actualizar_carrito, name='actualizar_carrito'),
    path('carrito/quitar/<int:pk_producto>/', views.quitar_carrito, name='quitar_carrito'),
    path('carrito/checkout/', views.checkout_carrito, name='checkout_carrito'),
    path('pedidos/<int:pk>/repetir/', views.repetir_pedido, name='repetir_pedido'),

    # ==========================
    # Direcciones de entrega (Comprador)
    # ==========================
    path('direcciones/', views.lista_direcciones, name='lista_direcciones'),
    path('direcciones/crear/', views.crear_direccion, name='crear_direccion'),
    path('direcciones/<int:pk>/eliminar/', views.eliminar_direccion, name='eliminar_direccion'),

    # ==========================
    # Promociones (Empresa)
    # ==========================
    path('promociones/', views.lista_promociones, name='lista_promociones'),
    path('promociones/crear/', views.crear_promocion, name='crear_promocion'),
    path('promociones/<int:pk>/editar/', views.editar_promocion, name='editar_promocion'),
    path('promociones/<int:pk>/eliminar/', views.eliminar_promocion, name='eliminar_promocion'),

    # ==========================
    # Ventas: Pagos
    # ==========================
    path('pagos/', views.lista_pagos, name='lista_pagos'),
    path('pagos/crear/', views.crear_pago, name='crear_pago'),
    path('pagos/<int:pk>/', views.detalle_pago, name='detalle_pago'),
    path('pagos/<int:pk>/validar/', views.validar_pago, name='validar_pago'),


    # ==========================
    # Ventas: Facturas
    # ==========================
    path('facturas/', views.lista_facturas, name='lista_facturas'),
    path('facturas/<int:pk>/', views.detalle_factura, name='detalle_factura'),
    path('facturas/<int:pk>/autorizar/', views.autorizar_factura, name='autorizar_factura'),
    path('facturas/<int:pk>/eliminar/', views.eliminar_factura, name='eliminar_factura'),

    # ==========================
    # Plataforma: Gestión de Planes de Suscripción & Suscripciones
    # ==========================
    path('planes/', views.lista_planes, name='lista_planes'),
    path('planes/crear/', views.crear_plan, name='crear_plan'),
    path('planes/<int:pk>/editar/', views.editar_plan, name='editar_plan'),
    path('planes/<int:pk>/eliminar/', views.eliminar_plan, name='eliminar_plan'),
    path('planes/<int:pk>/publicar/', views.publicar_plan, name='publicar_plan'),

    path('suscripciones/', views.lista_suscripciones, name='lista_suscripciones'),
    path('suscripciones/suscribir/<int:pk_plan>/', views.suscribir_empresa, name='suscribir_empresa'),
    path('suscripciones/<int:pk_suscripcion>/cancelar/', views.cancelar_suscripcion_empresa, name='cancelar_suscripcion_empresa'),

    # ==========================
    # Plataforma: Comisiones
    # ==========================
    path('comisiones/', views.lista_comisiones, name='lista_comisiones'),
    path('comisiones/<int:pk>/', views.detalle_comision, name='detalle_comision'),
    path('comisiones/<int:pk>/pagar/', views.pagar_comision, name='pagar_comision'),

    # ==========================
    # Capacitación: Cursos y Evaluaciones
    # ==========================
    path('cursos/', views.lista_cursos, name='lista_cursos'),
    path('cursos/crear/', views.crear_curso, name='crear_curso'),
    path('cursos/<int:pk>/', views.detalle_curso, name='detalle_curso'),
    path('cursos/<int:pk>/editar/', views.editar_curso, name='editar_curso'),
    path('cursos/<int:pk>/eliminar/', views.eliminar_curso, name='eliminar_curso'),

    path('evaluaciones/', views.lista_evaluaciones, name='lista_evaluaciones'),
    path('evaluaciones/crear/', views.crear_evaluacion, name='crear_evaluacion'),
    path('evaluaciones/realizar/<int:pk_curso>/', views.realizar_evaluacion, name='realizar_evaluacion'),
    path('evaluaciones/<int:pk>/', views.detalle_evaluacion, name='detalle_evaluacion'),
    path('evaluaciones/<int:pk>/eliminar/', views.eliminar_evaluacion, name='eliminar_evaluacion'),

    # ==========================
    # Sistema: Calificaciones y Notificaciones
    # ==========================
    path('calificaciones/', views.lista_calificaciones, name='lista_calificaciones'),
    path('calificaciones/crear/', views.crear_calificacion, name='crear_calificacion'),
    path('calificaciones/<int:pk>/', views.detalle_calificacion, name='detalle_calificacion'),
    path('calificaciones/<int:pk>/eliminar/', views.eliminar_calificacion, name='eliminar_calificacion'),

    path('incidencias/', views.lista_incidencias, name='lista_incidencias'),
    path('incidencias/<int:pk>/cerrar/', views.cerrar_incidencia, name='cerrar_incidencia'),

    path('notificaciones/', views.lista_notificaciones, name='lista_notificaciones'),
    path('notificaciones/crear/', views.crear_notificacion, name='crear_notificacion'),
    path('notificaciones/<int:pk>/leida/', views.marcar_leida_notificacion, name='marcar_leida_notificacion'),
    path('notificaciones/<int:pk>/eliminar/', views.eliminar_notificacion, name='eliminar_notificacion'),

    # ==========================
    # Reportes (exclusivo Administrador)
    # ==========================
    path('reportes/', views.reportes, name='reportes'),
    path('estadisticas/', views.estadisticas_empresa, name='estadisticas_empresa'),
]

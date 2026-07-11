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

    # ==========================
    # Módulo Usuarios
    # ==========================
    path('usuarios/', views.lista_usuarios, name='lista_usuarios'),
    path('usuarios/crear/', views.crear_usuario, name='crear_usuario'),
    path('usuarios/<int:pk>/', views.detalle_usuario, name='detalle_usuario'),
    path('usuarios/<int:pk>/editar/', views.editar_usuario, name='editar_usuario'),
    path('usuarios/<int:pk>/eliminar/', views.eliminar_usuario, name='eliminar_usuario'),

    # ==========================
    # Empresas
    # ==========================
    path('empresas/', views.lista_empresas, name='lista_empresas'),
    path('empresas/crear/', views.crear_empresa, name='crear_empresa'),
    path('empresas/<int:pk>/', views.detalle_empresa, name='detalle_empresa'),
    path('empresas/<int:pk>/editar/', views.editar_empresa, name='editar_empresa'),
    path('empresas/<int:pk>/eliminar/', views.eliminar_empresa, name='eliminar_empresa'),

    # ==========================
    # Vendedores
    # ==========================
    path('vendedores/', views.lista_vendedores, name='lista_vendedores'),
    path('vendedores/crear/', views.crear_vendedor, name='crear_vendedor'),
    path('vendedores/<int:pk>/', views.detalle_vendedor, name='detalle_vendedor'),
    path('vendedores/<int:pk>/editar/', views.editar_vendedor, name='editar_vendedor'),
    path('vendedores/<int:pk>/eliminar/', views.eliminar_vendedor, name='eliminar_vendedor'),
    path('vendedores/<int:pk>/autorizar/', views.autorizar_vendedor, name='autorizar_vendedor'),

    # ==========================
    # Compradores
    # ==========================
    path('compradores/', views.lista_compradores, name='lista_compradores'),
    path('compradores/crear/', views.crear_comprador, name='crear_comprador'),
    path('compradores/<int:pk>/', views.detalle_comprador, name='detalle_comprador'),
    path('compradores/<int:pk>/editar/', views.editar_comprador, name='editar_comprador'),
    path('compradores/<int:pk>/eliminar/', views.eliminar_comprador, name='eliminar_comprador'),

    # ==========================
    # Categorías y Productos
    # ==========================
    path('categorias/', views.lista_categorias, name='lista_categorias'),
    path('categorias/crear/', views.crear_categoria, name='crear_categoria'),
    path('categorias/<int:pk>/editar/', views.editar_categoria, name='editar_categoria'),
    path('categorias/<int:pk>/eliminar/', views.eliminar_categoria, name='eliminar_categoria'),

    path('productos/', views.lista_productos, name='lista_productos'),
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

    # ==========================
    # Ventas: Pedidos
    # ==========================
    path('pedidos/', views.lista_pedidos, name='lista_pedidos'),
    path('pedidos/crear/', views.crear_pedido, name='crear_pedido'),
    path('pedidos/<int:pk>/', views.detalle_pedido, name='detalle_pedido'),
    path('pedidos/<int:pk>/estado/<str:estado>/', views.cambiar_estado_pedido, name='cambiar_estado_pedido'),
    path('pedidos/<int:pk>/eliminar/', views.eliminar_pedido, name='eliminar_pedido'),

    # ==========================
    # Ventas: Pagos
    # ==========================
    path('pagos/', views.lista_pagos, name='lista_pagos'),
    path('pagos/crear/', views.crear_pago, name='crear_pago'),
    path('pagos/<int:pk>/', views.detalle_pago, name='detalle_pago'),
    path('pagos/<int:pk>/validar/', views.validar_pago, name='validar_pago'),
    path('pagos/<int:pk>/eliminar/', views.eliminar_pago, name='eliminar_pago'),

    # ==========================
    # Ventas: Facturas
    # ==========================
    path('facturas/', views.lista_facturas, name='lista_facturas'),
    path('facturas/<int:pk>/', views.detalle_factura, name='detalle_factura'),
    path('facturas/<int:pk>/autorizar/', views.autorizar_factura, name='autorizar_factura'),
    path('facturas/<int:pk>/eliminar/', views.eliminar_factura, name='eliminar_factura'),

    # ==========================
    # Plataforma: Suscripciones
    # ==========================
    path('suscripciones/', views.lista_suscripciones, name='lista_suscripciones'),
    path('suscripciones/crear/', views.crear_suscripcion, name='crear_suscripcion'),
    path('suscripciones/<int:pk>/editar/', views.editar_suscripcion, name='editar_suscripcion'),
    path('suscripciones/<int:pk>/cancelar/', views.cancelar_suscripcion, name='cancelar_suscripcion'),

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
    path('evaluaciones/<int:pk>/', views.detalle_evaluacion, name='detalle_evaluacion'),
    path('evaluaciones/<int:pk>/eliminar/', views.eliminar_evaluacion, name='eliminar_evaluacion'),

    # ==========================
    # Sistema: Calificaciones y Notificaciones
    # ==========================
    path('calificaciones/', views.lista_calificaciones, name='lista_calificaciones'),
    path('calificaciones/crear/', views.crear_calificacion, name='crear_calificacion'),
    path('calificaciones/<int:pk>/', views.detalle_calificacion, name='detalle_calificacion'),
    path('calificaciones/<int:pk>/eliminar/', views.eliminar_calificacion, name='eliminar_calificacion'),

    path('notificaciones/', views.lista_notificaciones, name='lista_notificaciones'),
    path('notificaciones/crear/', views.crear_notificacion, name='crear_notificacion'),
    path('notificaciones/<int:pk>/leida/', views.marcar_leida_notificacion, name='marcar_leida_notificacion'),
    path('notificaciones/<int:pk>/eliminar/', views.eliminar_notificacion, name='eliminar_notificacion'),
]

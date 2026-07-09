from django.urls import path
from . import views

urlpatterns = [

    # ==========================
    # Inicio y Autenticación (¡NUEVO!)
    # ==========================
    path('', views.inicio, name='inicio'),
    path('entrando/login/', views.ingreso, name='login'),    # Lógica del AuthenticationForm
    path('saliendo/logout/', views.logout_view, name='logout'), # Lógica para cerrar sesión

    # ==========================
    # Empresas  (RF-02)
    # ==========================
    path('empresas/', views.lista_empresas, name='lista_empresas'),
    path('empresas/crear/', views.crear_empresa, name='crear_empresa'),
    path('empresas/<int:pk>/', views.detalle_empresa, name='detalle_empresa'),
    path('empresas/<int:pk>/editar/', views.editar_empresa, name='editar_empresa'),
    path('empresas/<int:pk>/eliminar/', views.eliminar_empresa, name='eliminar_empresa'),

    # ==========================
    # Vendedores  (RF-06)
    # ==========================
    path('vendedores/', views.lista_vendedores, name='lista_vendedores'),
    path('vendedores/crear/', views.crear_vendedor, name='crear_vendedor'),
    path('vendedores/<int:pk>/', views.detalle_vendedor, name='detalle_vendedor'),
    path('vendedores/<int:pk>/editar/', views.editar_vendedor, name='editar_vendedor'),
    path('vendedores/<int:pk>/eliminar/', views.eliminar_vendedor, name='eliminar_vendedor'),

    # ==========================
    # Compradores  (RF-01, RF-05)
    # ==========================
    path('compradores/', views.lista_compradores, name='lista_compradores'),
    path('compradores/crear/', views.crear_comprador, name='crear_comprador'),
    path('compradores/<int:pk>/', views.detalle_comprador, name='detalle_comprador'),
    path('compradores/<int:pk>/editar/', views.editar_comprador, name='editar_comprador'),
    path('compradores/<int:pk>/eliminar/', views.eliminar_comprador, name='eliminar_comprador'),

    # ==========================
    # Categorías de producto  (RF-03-05)
    # ==========================
    path('categorias/', views.lista_categorias, name='lista_categorias'),
    path('categorias/crear/', views.crear_categoria, name='crear_categoria'),
    path('categorias/<int:pk>/', views.detalle_categoria, name='detalle_categoria'),
    path('categorias/<int:pk>/editar/', views.editar_categoria, name='editar_categoria'),
    path('categorias/<int:pk>/eliminar/', views.eliminar_categoria, name='eliminar_categoria'),

    # ==========================
    # Productos  (RF-03)
    # ==========================
    path('productos/', views.lista_productos, name='lista_productos'),
    path('productos/crear/', views.crear_producto, name='crear_producto'),
    path('productos/<int:pk>/', views.detalle_producto, name='detalle_producto'),
    path('productos/<int:pk>/editar/', views.editar_producto, name='editar_producto'),
    path('productos/<int:pk>/eliminar/', views.eliminar_producto, name='eliminar_producto'),
    
    # Ruta Especial: Crear producto desde una empresa (¡NUEVA!)
    # Equivalente a la lógica de crear_numero_telefonico_estudiante
    path('empresas/<int:id>/productos/crear/', views.crear_producto_empresa, name='crear_producto_empresa'),

    # ==========================
    # Inventario  (RF-04)
    # ==========================
    path('inventario/', views.lista_inventario, name='lista_inventario'),
    path('inventario/<int:pk>/', views.detalle_inventario, name='detalle_inventario'),
    path('inventario/<int:pk>/editar/', views.editar_inventario, name='editar_inventario'), # Falta en tu original, pero está en tus views.py

    # ==========================
    # Pedidos  (RF-05)
    # ==========================
    path('pedidos/', views.lista_pedidos, name='lista_pedidos'),
    path('pedidos/crear/', views.crear_pedido, name='crear_pedido'),
    path('pedidos/<int:pk>/', views.detalle_pedido, name='detalle_pedido'),
    path('pedidos/<int:pk>/editar/', views.editar_pedido, name='editar_pedido'),
    path('pedidos/<int:pk>/eliminar/', views.eliminar_pedido, name='eliminar_pedido'),

    # ==========================
    # Pagos  (RF-08)
    # ==========================
    path('pagos/', views.lista_pagos, name='lista_pagos'),
    path('pagos/crear/', views.crear_pago, name='crear_pago'),
    path('pagos/<int:pk>/', views.detalle_pago, name='detalle_pago'),

    # ==========================
    # Comisiones  (RF-09)
    # ==========================
    path('comisiones/', views.lista_comisiones, name='lista_comisiones'),
    path('comisiones/<int:pk>/', views.detalle_comision, name='detalle_comision'),
    path('comisiones/crear/', views.crear_comision, name='crear_comision'), # Añadido según tus views.py

    # ==========================
    # Facturas  (RF-10)
    # ==========================
    path('facturas/', views.lista_facturas, name='lista_facturas'),
    path('facturas/<int:pk>/', views.detalle_factura, name='detalle_factura'),

    # ==========================
    # Suscripciones  (RF-11)
    # ==========================
    path('suscripciones/', views.lista_suscripciones, name='lista_suscripciones'),
    path('suscripciones/crear/', views.crear_suscripcion, name='crear_suscripcion'),
    path('suscripciones/<int:pk>/', views.detalle_suscripcion, name='detalle_suscripcion'),

    # ==========================
    # Cursos  (RF-07)
    # ==========================
    path('cursos/', views.lista_cursos, name='lista_cursos'),
    path('cursos/crear/', views.crear_curso, name='crear_curso'),
    path('cursos/<int:pk>/', views.detalle_curso, name='detalle_curso'),
    path('cursos/<int:pk>/editar/', views.editar_curso, name='editar_curso'),
    path('cursos/<int:pk>/eliminar/', views.eliminar_curso, name='eliminar_curso'),

    # ==========================
    # Evaluaciones  (RF-07-02)
    # ==========================
    path('evaluaciones/', views.lista_evaluaciones, name='lista_evaluaciones'),
    path('evaluaciones/crear/', views.crear_evaluacion, name='crear_evaluacion'), # Añadido según tus views.py
    path('evaluaciones/<int:pk>/', views.detalle_evaluacion, name='detalle_evaluacion'),

    # ==========================
    # Calificaciones  (RF-12)
    # ==========================
    path('calificaciones/', views.lista_calificaciones, name='lista_calificaciones'),
    path('calificaciones/crear/', views.crear_calificacion, name='crear_calificacion'),
    path('calificaciones/<int:pk>/', views.detalle_calificacion, name='detalle_calificacion'),

    # ==========================
    # Notificaciones  (RF-14)
    # ==========================
    path('notificaciones/', views.lista_notificaciones, name='lista_notificaciones'),
    path('notificaciones/<int:pk>/', views.detalle_notificacion, name='detalle_notificacion'),
]
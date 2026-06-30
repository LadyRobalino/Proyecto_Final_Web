from django.urls import path
from . import views

urlpatterns = [

    # Página principal
    path('', views.inicio, name='inicio'),

    # ==========================
    # Módulo Usuarios
    # ==========================
    path('usuarios/', views.lista_usuarios, name='lista_usuarios'),
    path('empresas/', views.lista_empresas, name='lista_empresas'),
    path('vendedores/', views.lista_vendedores, name='lista_vendedores'),
    path('compradores/', views.lista_compradores, name='lista_compradores'),

    # ==========================
    # Productos
    # ==========================
    path('categorias/', views.lista_categorias, name='lista_categorias'),
    path('productos/', views.lista_productos, name='lista_productos'),
    path('inventario/', views.lista_inventario, name='lista_inventario'),

    # ==========================
    # Ventas
    # ==========================
    path('pedidos/', views.lista_pedidos, name='lista_pedidos'),
    path('pagos/', views.lista_pagos, name='lista_pagos'),
    path('facturas/', views.lista_facturas, name='lista_facturas'),

    # ==========================
    # Plataforma
    # ==========================
    path('suscripciones/', views.lista_suscripciones, name='lista_suscripciones'),
    path('comisiones/', views.lista_comisiones, name='lista_comisiones'),

    # ==========================
    # Capacitación
    # ==========================
    path('cursos/', views.lista_cursos, name='lista_cursos'),
    path('evaluaciones/', views.lista_evaluaciones, name='lista_evaluaciones'),

    # ==========================
    # Sistema
    # ==========================
    path('calificaciones/', views.lista_calificaciones, name='lista_calificaciones'),
    path('notificaciones/', views.lista_notificaciones, name='lista_notificaciones'),
]
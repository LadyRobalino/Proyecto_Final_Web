from django.shortcuts import render
from django.http import HttpResponse
from .models import Empresa


# Página principal
def inicio(request):
    return render(request, 'core/inicio.html')


# ==========================
# Usuarios
# ==========================

def lista_usuarios(request):
    return HttpResponse("Lista de usuarios")


# ==========================
# Empresas
# ==========================

def lista_empresas(request):

    empresas = Empresa.objects.all()

    contexto = {
        'empresas': empresas
    }

    return render(
        request,
        'core/empresas/lista.html',
        contexto
    )


# ==========================
# Vendedores
# ==========================

def lista_vendedores(request):
    return HttpResponse("Lista de vendedores")


def lista_compradores(request):
    return HttpResponse("Lista de compradores")


# ==========================
# Productos
# ==========================

def lista_categorias(request):
    return HttpResponse("Lista de categorías")


def lista_productos(request):
    return HttpResponse("Lista de productos")


def lista_inventario(request):
    return HttpResponse("Lista de inventario")


# ==========================
# Ventas
# ==========================

def lista_pedidos(request):
    return HttpResponse("Lista de pedidos")


def lista_pagos(request):
    return HttpResponse("Lista de pagos")


def lista_facturas(request):
    return HttpResponse("Lista de facturas")


# ==========================
# Plataforma
# ==========================

def lista_suscripciones(request):
    return HttpResponse("Lista de suscripciones")


def lista_comisiones(request):
    return HttpResponse("Lista de comisiones")


# ==========================
# Capacitación
# ==========================

def lista_cursos(request):
    return HttpResponse("Lista de cursos")


def lista_evaluaciones(request):
    return HttpResponse("Lista de evaluaciones")


# ==========================
# Sistema
# ==========================

def lista_calificaciones(request):
    return HttpResponse("Lista de calificaciones")


def lista_notificaciones(request):
    return HttpResponse("Lista de notificaciones")
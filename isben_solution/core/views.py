from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm


from .models import (
    Usuario, Empresa, Vendedor, Comprador, Administrador,
    CategoriaProducto, Producto, Inventario,
    Suscripcion, Comision,
    Pedido, DetallePedido, Pago, Factura,
    Curso, Evaluacion, Calificacion, Notificacion
)
from .forms import (
    EmpresaForm, VendedorForm, CompradorForm,
    CategoriaProductoForm, ProductoForm, InventarioForm,
    PedidoForm, PagoForm, ComisionForm, SuscripcionForm,
    CursoForm, EvaluacionForm, CalificacionForm
)

# =============================================================================
# INICIO Y AUTENTICACIÓN
# =============================================================================

def inicio(request):
    contexto = {
        'total_empresas':   Empresa.objects.count(),
        'total_vendedores': Vendedor.objects.count(),
        'total_productos':  Producto.objects.count(),
        'total_pedidos':    Pedido.objects.count(),
    }
    return render(request, 'core/inicio.html', contexto)


def ingreso(request):
    if request.method == "POST":
        form = AuthenticationForm(request=request, data=request.POST)
        print(form.errors)
        if form.is_valid():
            username = form.data.get("username")
            raw_password = form.data.get("password")
            user = authenticate(username=username, password=raw_password)
            if user is not None:
                login(request, user)
                return redirect(inicio)
    else:
        form = AuthenticationForm()

    informacion_template = {'form': form}
    return render(request, 'registration/login.html', informacion_template)


def logout_view(request):
    logout(request)
    messages.info(request, "Has salido del sistema")
    return redirect(inicio)


# =============================================================================
# EMPRESAS (RF-02)
# =============================================================================

def lista_empresas(request):
    empresas = Empresa.objects.all()
    informacion_template = {'empresas': empresas, 'numero_empresas': len(empresas)}
    return render(request, 'core/empresas/lista.html', informacion_template)


def detalle_empresa(request, pk):
    empresa = get_object_or_404(Empresa, pk=pk)
    informacion_template = {'empresa': empresa}
    return render(request, 'core/empresas/detalle.html', informacion_template)


@login_required(login_url='/entrando/login/')
@permission_required('core.add_empresa', login_url="/entrando/login/")
def crear_empresa(request):
    if request.method == 'POST':
        formulario = EmpresaForm(request.POST)
        print(formulario.errors)
        if formulario.is_valid():
            formulario.save()
            return redirect('lista_empresas')
    else:
        formulario = EmpresaForm()
    diccionario = {'formulario': formulario}
    return render(request, 'core/empresas/crear.html', diccionario)


@login_required(login_url='/entrando/login/')
def editar_empresa(request, pk):
    empresa = get_object_or_404(Empresa, pk=pk)
    if request.method == 'POST':
        formulario = EmpresaForm(request.POST, instance=empresa)
        print(formulario.errors)
        if formulario.is_valid():
            formulario.save()
            return redirect('lista_empresas')
    else:
        formulario = EmpresaForm(instance=empresa)
    diccionario = {'formulario': formulario, 'empresa': empresa}
    return render(request, 'core/empresas/editar.html', diccionario)


@login_required(login_url='/entrando/login/')
def eliminar_empresa(request, pk):
    empresa = get_object_or_404(Empresa, pk=pk)
    if request.method == 'POST':
        empresa.delete()
        return redirect('lista_empresas')
    return render(request, 'core/empresas/eliminar.html', {'empresa': empresa})


# =============================================================================
# VENDEDORES (RF-06)
# =============================================================================

def lista_vendedores(request):
    vendedores = Vendedor.objects.all()
    informacion_template = {'vendedores': vendedores}
    return render(request, 'core/vendedores/lista.html', informacion_template)


def detalle_vendedor(request, pk):
    vendedor = get_object_or_404(Vendedor, pk=pk)
    return render(request, 'core/vendedores/detalle.html', {'vendedor': vendedor})


@login_required(login_url='/entrando/login/')
def crear_vendedor(request):
    if request.method == 'POST':
        formulario = VendedorForm(request.POST)
        print(formulario.errors)
        if formulario.is_valid():
            formulario.save()
            return redirect('lista_vendedores')
    else:
        formulario = VendedorForm()
    diccionario = {'formulario': formulario}
    return render(request, 'core/vendedores/crear.html', diccionario)


@login_required(login_url='/entrando/login/')
def editar_vendedor(request, pk):
    vendedor = get_object_or_404(Vendedor, pk=pk)
    if request.method == 'POST':
        formulario = VendedorForm(request.POST, instance=vendedor)
        print(formulario.errors)
        if formulario.is_valid():
            formulario.save()
            return redirect('lista_vendedores')
    else:
        formulario = VendedorForm(instance=vendedor)
    diccionario = {'formulario': formulario, 'vendedor': vendedor}
    return render(request, 'core/vendedores/editar.html', diccionario)


@login_required(login_url='/entrando/login/')
def eliminar_vendedor(request, pk):
    vendedor = get_object_or_404(Vendedor, pk=pk)
    if request.method == 'POST':
        vendedor.delete()
        return redirect('lista_vendedores')
    return render(request, 'core/vendedores/eliminar.html', {'vendedor': vendedor})


# =============================================================================
# COMPRADORES (RF-01)
# =============================================================================

def lista_compradores(request):
    compradores = Comprador.objects.all()
    return render(request, 'core/compradores/lista.html', {'compradores': compradores})


def detalle_comprador(request, pk):
    comprador = get_object_or_404(Comprador, pk=pk)
    return render(request, 'core/compradores/detalle.html', {'comprador': comprador})


@login_required(login_url='/entrando/login/')
def crear_comprador(request):
    if request.method == 'POST':
        formulario = CompradorForm(request.POST)
        print(formulario.errors)
        if formulario.is_valid():
            formulario.save()
            return redirect('lista_compradores')
    else:
        formulario = CompradorForm()
    diccionario = {'formulario': formulario}
    return render(request, 'core/compradores/crear.html', diccionario)


@login_required(login_url='/entrando/login/')
def editar_comprador(request, pk):
    comprador = get_object_or_404(Comprador, pk=pk)
    if request.method == 'POST':
        formulario = CompradorForm(request.POST, instance=comprador)
        print(formulario.errors)
        if formulario.is_valid():
            formulario.save()
            return redirect('lista_compradores')
    else:
        formulario = CompradorForm(instance=comprador)
    diccionario = {'formulario': formulario, 'comprador': comprador}
    return render(request, 'core/compradores/editar.html', diccionario)


@login_required(login_url='/entrando/login/')
def eliminar_comprador(request, pk):
    comprador = get_object_or_404(Comprador, pk=pk)
    if request.method == 'POST':
        comprador.delete()
        return redirect('lista_compradores')
    return render(request, 'core/compradores/eliminar.html', {'comprador': comprador})


# =============================================================================
# CATEGORÍAS (RF-03-05)
# =============================================================================

def lista_categorias(request):
    categorias = CategoriaProducto.objects.all()
    return render(request, 'core/categorias/lista.html', {'categorias': categorias})


def detalle_categoria(request, pk):
    categoria = get_object_or_404(CategoriaProducto, pk=pk)
    return render(request, 'core/categorias/detalle.html', {'categoria': categoria})


@login_required(login_url='/entrando/login/')
def crear_categoria(request):
    if request.method == 'POST':
        formulario = CategoriaProductoForm(request.POST)
        print(formulario.errors)
        if formulario.is_valid():
            formulario.save()
            return redirect('lista_categorias')
    else:
        formulario = CategoriaProductoForm()
    diccionario = {'formulario': formulario}
    return render(request, 'core/categorias/crear.html', diccionario)


@login_required(login_url='/entrando/login/')
def editar_categoria(request, pk):
    categoria = get_object_or_404(CategoriaProducto, pk=pk)
    if request.method == 'POST':
        formulario = CategoriaProductoForm(request.POST, instance=categoria)
        print(formulario.errors)
        if formulario.is_valid():
            formulario.save()
            return redirect('lista_categorias')
    else:
        formulario = CategoriaProductoForm(instance=categoria)
    diccionario = {'formulario': formulario, 'categoria': categoria}
    return render(request, 'core/categorias/editar.html', diccionario)


@login_required(login_url='/entrando/login/')
def eliminar_categoria(request, pk):
    categoria = get_object_or_404(CategoriaProducto, pk=pk)
    if request.method == 'POST':
        categoria.delete()
        return redirect('lista_categorias')
    return render(request, 'core/categorias/eliminar.html', {'categoria': categoria})


# =============================================================================
# PRODUCTOS (RF-03)
# =============================================================================

def lista_productos(request):
    productos = Producto.objects.all()
    return render(request, 'core/tablas_listado/lista_generica.html', {'productos': productos})


def detalle_producto(request, pk):
    producto = Producto.objects.get(pk=pk)
    return render(request, 'core/detalles/detalle.html', {'producto': producto})


@login_required(login_url='/entrando/login/')
def crear_producto(request):
    if request.method == 'POST':
        formulario = ProductoForm(request.POST)
        print(formulario.errors)
        if formulario.is_valid():
            formulario.save()
            return redirect('lista_productos')
    else:
        formulario = ProductoForm()
    diccionario = {'formulario': formulario}
    return render(request, 'core/formularios/formulario.html', diccionario)


# !!! AÑADE ESTA FUNCIÓN AQUÍ PARA ARREGLAR EL ERROR !!!
@login_required(login_url='/entrando/login/')
def crear_producto_empresa(request, id):
    """Lógica contextual idéntica a crear_numero_telefonico_estudiante"""
    empresa = Empresa.objects.get(pk=id)
    if request.method == 'POST':
        formulario = ProductoEmpresaForm(empresa, request.POST)
        print(formulario.errors)
        if formulario.is_valid():
            formulario.save()
            return redirect('lista_productos')
    else:
        formulario = ProductoEmpresaForm(empresa)
    diccionario = {'formulario': formulario, 'empresa': empresa}
    return render(request, 'core/formularios/contextual.html', diccionario)


@login_required(login_url='/entrando/login/')
def editar_producto(request, pk):
    producto = Producto.objects.get(pk=pk)
    if request.method == 'POST':
        formulario = ProductoForm(request.POST, instance=producto)
        print(formulario.errors)
        if formulario.is_valid():
            formulario.save()
            return redirect('lista_productos')
    else:
        formulario = ProductoForm(instance=producto)
    diccionario = {'formulario': formulario, 'producto': producto}
    return render(request, 'core/formularios/formulario.html', diccionario)


@login_required(login_url='/entrando/login/')
def eliminar_producto(request, pk):
    producto = Producto.objects.get(pk=pk)
    if request.method == 'POST':
        producto.delete()
        return redirect('lista_productos')
    return render(request, 'core/formularios/eliminar.html', {'producto': producto})

# =============================================================================
# INVENTARIO (RF-04)
# =============================================================================

def lista_inventario(request):
    inventarios = Inventario.objects.all()
    return render(request, 'core/inventario/lista.html', {'inventarios': inventarios})


def detalle_inventario(request, pk):
    inventario = get_object_or_404(Inventario, pk=pk)
    movimientos = inventario.movimientos.all()
    return render(request, 'core/inventario/detalle.html', {
        'inventario': inventario,
        'movimientos': movimientos
    })


@login_required(login_url='/entrando/login/')
def editar_inventario(request, pk):
    inventario = get_object_or_404(Inventario, pk=pk)
    stock_antes = inventario.stock_actual
    if request.method == 'POST':
        formulario = InventarioForm(request.POST, instance=inventario)
        print(formulario.errors)
        if formulario.is_valid():
            inventario_actualizado = formulario.save()
            stock_despues = inventario_actualizado.stock_actual
            if stock_despues != stock_antes:
                tipo = 'entrada' if stock_despues > stock_antes else 'salida'
                diferencia = abs(stock_despues - stock_antes)
                MovimientoInventario.objects.create(
                    inventario=inventario_actualizado,
                    tipo=tipo,
                    cantidad=diferencia,
                    stock_antes=stock_antes,
                    stock_despues=stock_despues,
                    motivo='Ajuste manual'
                )
            return redirect('lista_inventario')
    else:
        formulario = InventarioForm(instance=inventario)
    diccionario = {'formulario': formulario, 'inventario': inventario}
    return render(request, 'core/inventario/editar.html', diccionario)


# =============================================================================
# PEDIDOS (RF-05)
# =============================================================================

def lista_pedidos(request):
    pedidos = Pedido.objects.all()
    return render(request, 'core/pedidos/lista.html', {'pedidos': pedidos})


def detalle_pedido(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    return render(request, 'core/pedidos/detalle.html', {
        'pedido': pedido,
        'detalles': pedido.detalles.all(),
        'pagos': pedido.pagos.all(),
    })


@login_required(login_url='/entrando/login/')
def crear_pedido(request):
    if request.method == 'POST':
        formulario = PedidoForm(request.POST)
        print(formulario.errors)
        if formulario.is_valid():
            formulario.save()
            return redirect('lista_pedidos')
    else:
        formulario = PedidoForm()
    diccionario = {'formulario': formulario}
    return render(request, 'core/pedidos/crear.html', diccionario)


@login_required(login_url='/entrando/login/')
def editar_pedido(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    if request.method == 'POST':
        formulario = PedidoForm(request.POST, instance=pedido)
        print(formulario.errors)
        if formulario.is_valid():
            formulario.save()
            return redirect('lista_pedidos')
    else:
        formulario = PedidoForm(instance=pedido)
    diccionario = {'formulario': formulario, 'pedido': pedido}
    return render(request, 'core/pedidos/editar.html', diccionario)


@login_required(login_url='/entrando/login/')
def eliminar_pedido(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    if request.method == 'POST':
        pedido.delete()
        return redirect('lista_pedidos')
    return render(request, 'core/pedidos/eliminar.html', {'pedido': pedido})


# =============================================================================
# PAGOS (RF-08)
# =============================================================================

def lista_pagos(request):
    pagos = Pago.objects.all()
    return render(request, 'core/pagos/lista.html', {'pagos': pagos})


def detalle_pago(request, pk):
    pago = get_object_or_404(Pago, pk=pk)
    return render(request, 'core/pagos/detalle.html', {'pago': pago})


@login_required(login_url='/entrando/login/')
def crear_pago(request):
    if request.method == 'POST':
        formulario = PagoForm(request.POST)
        print(formulario.errors)
        if formulario.is_valid():
            formulario.save()
            return redirect('lista_pagos')
    else:
        formulario = PagoForm()
    diccionario = {'formulario': formulario}
    return render(request, 'core/pagos/crear.html', diccionario)


# =============================================================================
# COMISIONES (RF-09)
# =============================================================================

def lista_comisiones(request):
    comisiones = Comision.objects.all()
    return render(request, 'core/comisiones/lista.html', {'comisiones': comisiones})


def detalle_comision(request, pk):
    comision = get_object_or_404(Comision, pk=pk)
    return render(request, 'core/comisiones/detalle.html', {'comision': comision})


@login_required(login_url='/entrando/login/')
def crear_comision(request):
    if request.method == 'POST':
        formulario = ComisionForm(request.POST)
        print(formulario.errors)
        if formulario.is_valid():
            formulario.save()
            return redirect('lista_comisiones')
    else:
        formulario = ComisionForm()
    diccionario = {'formulario': formulario}
    return render(request, 'core/comisiones/crear.html', diccionario)


# =============================================================================
# FACTURAS (RF-10)
# =============================================================================

def lista_facturas(request):
    facturas = Factura.objects.all()
    return render(request, 'core/facturas/lista.html', {'facturas': facturas})


def detalle_factura(request, pk):
    factura = get_object_or_404(Factura, pk=pk)
    return render(request, 'core/facturas/detalle.html', {'factura': factura})


# =============================================================================
# SUSCRIPCIONES (RF-11)
# =============================================================================

def lista_suscripciones(request):
    suscripciones = Suscripcion.objects.all()
    return render(request, 'core/suscripciones/lista.html', {'suscripciones': suscripciones})


def detalle_suscripcion(request, pk):
    suscripcion = get_object_or_404(Suscripcion, pk=pk)
    return render(request, 'core/suscripciones/detalle.html', {'suscripcion': suscripcion})


@login_required(login_url='/entrando/login/')
def crear_suscripcion(request):
    if request.method == 'POST':
        formulario = SuscripcionForm(request.POST)
        print(formulario.errors)
        if formulario.is_valid():
            formulario.save()
            return redirect('lista_suscripciones')
    else:
        formulario = SuscripcionForm()
    diccionario = {'formulario': formulario}
    return render(request, 'core/suscripciones/crear.html', diccionario)


# =============================================================================
# CURSOS (RF-07)
# =============================================================================

def lista_cursos(request):
    cursos = Curso.objects.all()
    return render(request, 'core/cursos/lista.html', {'cursos': cursos})


def detalle_curso(request, pk):
    curso = get_object_or_404(Curso, pk=pk)
    return render(request, 'core/cursos/detalle.html', {'curso': curso})


@login_required(login_url='/entrando/login/')
def crear_curso(request):
    if request.method == 'POST':
        formulario = CursoForm(request.POST)
        print(formulario.errors)
        if formulario.is_valid():
            formulario.save()
            return redirect('lista_cursos')
    else:
        formulario = CursoForm()
    diccionario = {'formulario': formulario}
    return render(request, 'core/cursos/crear.html', diccionario)


@login_required(login_url='/entrando/login/')
def editar_curso(request, pk):
    curso = get_object_or_404(Curso, pk=pk)
    if request.method == 'POST':
        formulario = CursoForm(request.POST, instance=curso)
        print(formulario.errors)
        if formulario.is_valid():
            formulario.save()
            return redirect('lista_cursos')
    else:
        formulario = CursoForm(instance=curso)
    diccionario = {'formulario': formulario, 'curso': curso}
    return render(request, 'core/cursos/editar.html', diccionario)


@login_required(login_url='/entrando/login/')
def eliminar_curso(request, pk):
    curso = get_object_or_404(Curso, pk=pk)
    if request.method == 'POST':
        curso.delete()
        return redirect('lista_cursos')
    return render(request, 'core/cursos/eliminar.html', {'curso': curso})


# =============================================================================
# EVALUACIONES (RF-07-02)
# =============================================================================

def lista_evaluaciones(request):
    evaluaciones = Evaluacion.objects.all()
    return render(request, 'core/evaluaciones/lista.html', {'evaluaciones': evaluaciones})


def detalle_evaluacion(request, pk):
    evaluacion = get_object_or_404(Evaluacion, pk=pk)
    return render(request, 'core/evaluaciones/detalle.html', {'evaluacion': evaluacion})


@login_required(login_url='/entrando/login/')
def crear_evaluacion(request):
    if request.method == 'POST':
        formulario = EvaluacionForm(request.POST)
        print(formulario.errors)
        if formulario.is_valid():
            evaluacion = formulario.save(commit=False)
            evaluacion.save()
            evaluacion.verificar_aprobacion()
            return redirect('lista_evaluaciones')
    else:
        formulario = EvaluacionForm()
    diccionario = {'formulario': formulario}
    return render(request, 'core/evaluaciones/crear.html', diccionario)


# =============================================================================
# CALIFICACIONES (RF-12)
# =============================================================================

def lista_calificaciones(request):
    calificaciones = Calificacion.objects.all()
    return render(request, 'core/calificaciones/lista.html', {'calificaciones': calificaciones})


def detalle_calificacion(request, pk):
    calificacion = get_object_or_404(Calificacion, pk=pk)
    return render(request, 'core/calificaciones/detalle.html', {'calificacion': calificacion})


@login_required(login_url='/entrando/login/')
def crear_calificacion(request):
    if request.method == 'POST':
        formulario = CalificacionForm(request.POST)
        print(formulario.errors)
        if formulario.is_valid():
            formulario.save()
            return redirect('lista_calificaciones')
    else:
        formulario = CalificacionForm()
    diccionario = {'formulario': formulario}
    return render(request, 'core/calificaciones/crear.html', diccionario)


# =============================================================================
# NOTIFICACIONES (RF-14)
# =============================================================================

def lista_notificaciones(request):
    notificaciones = Notificacion.objects.all()
    return render(request, 'core/notificaciones/lista.html', {'notificaciones': notificaciones})


def detalle_notificacion(request, pk):
    notificacion = get_object_or_404(Notificacion, pk=pk)
    notificacion.marcar_leida()
    return render(request, 'core/notificaciones/detalle.html', {'notificacion': notificacion})
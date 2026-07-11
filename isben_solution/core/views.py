from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, F, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .decorators import rol_requerido
from .forms import (
    CalificacionForm, CategoriaProductoForm, ComisionForm, CompradorCreateForm,
    CompradorForm, CursoForm, DetallePedidoFormSet, EmpresaCreateForm, EmpresaForm,
    EvaluacionForm, FacturaForm, InventarioForm, NotificacionForm, PagoForm,
    PedidoForm, ProductoForm, RegistroForm, SuscripcionForm, UsuarioCreateForm,
    UsuarioForm, VendedorCreateForm, VendedorForm,
)
from .models import (
    Administrador, Calificacion, CategoriaProducto, Comision, Comprador, Curso,
    DetallePedido, Empresa, ESTADO_PEDIDO, Evaluacion, Factura, Inventario,
    Notificacion, Pago, Pedido, Producto, Suscripcion, Usuario, Vendedor,
)


def _paginar(request, queryset, por_pagina=10):
    return Paginator(queryset, por_pagina).get_page(request.GET.get('page'))


# =============================================================================
# AUTENTICACIÓN
# =============================================================================

def iniciar_sesion(request):
    if request.user.is_authenticated:
        return redirect('inicio')

    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            usuario = form.get_user()
            login(request, usuario)
            messages.success(request, f"Bienvenido, {usuario.get_full_name() or usuario.username}.")
            return redirect('inicio')
        messages.error(request, "Usuario o contraseña incorrectos.")
    return render(request, 'core/auth/login.html', {'form': form})


def cerrar_sesion(request):
    logout(request)
    messages.info(request, "Sesión cerrada correctamente.")
    return redirect('login')


def registro(request):
    if request.user.is_authenticated:
        return redirect('inicio')

    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            usuario = form.guardar()
            login(request, usuario)
            messages.success(request, "Cuenta creada correctamente. ¡Bienvenido a ISBEN Solution!")
            return redirect('inicio')
    else:
        form = RegistroForm()
    return render(request, 'core/auth/registro.html', {'form': form})


# =============================================================================
# INICIO / DASHBOARD
# =============================================================================

@login_required
def inicio(request):
    contexto = {
        'total_empresas': Empresa.objects.count(),
        'total_productos': Producto.objects.filter(activo=True).count(),
        'total_pedidos': Pedido.objects.count(),
        'total_vendedores': Vendedor.objects.count(),
        'pedidos_recientes': Pedido.objects.select_related(
            'comprador__usuario', 'empresa'
        ).order_by('-fecha_creacion')[:6],
        'stock_bajo': Inventario.objects.select_related('producto').filter(
            stock_actual__lte=F('stock_minimo')
        )[:6],
        'pedidos_por_estado': list(Pedido.objects.values('estado').annotate(total=Count('id'))),
        'notificaciones_no_leidas': request.user.notificaciones.filter(leida=False).count(),
    }
    return render(request, 'core/inicio.html', contexto)


# =============================================================================
# USUARIOS
# =============================================================================

@rol_requerido('administrador')
def lista_usuarios(request):
    usuarios = Usuario.objects.all().order_by('-date_joined')
    q = request.GET.get('q', '').strip()
    if q:
        usuarios = usuarios.filter(
            Q(username__icontains=q) | Q(first_name__icontains=q) |
            Q(last_name__icontains=q) | Q(email__icontains=q)
        )
    return render(request, 'core/usuarios/lista.html', {'usuarios': _paginar(request, usuarios)})


@rol_requerido('administrador')
def crear_usuario(request):
    if request.method == 'POST':
        form = UsuarioCreateForm(request.POST)
        if form.is_valid():
            form.guardar()
            messages.success(request, "Usuario creado correctamente.")
            return redirect('lista_usuarios')
    else:
        form = UsuarioCreateForm()
    return render(request, 'core/usuarios/crear.html', {'form': form})


@rol_requerido('administrador')
def detalle_usuario(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    return render(request, 'core/usuarios/detalle.html', {'usuario': usuario})


@rol_requerido('administrador')
def editar_usuario(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    form = UsuarioForm(request.POST or None, instance=usuario)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Usuario actualizado correctamente.")
        return redirect('detalle_usuario', pk=usuario.pk)
    return render(request, 'core/usuarios/editar.html', {'form': form, 'usuario': usuario})


@rol_requerido('administrador')
def eliminar_usuario(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    if request.method == 'POST':
        usuario.delete()
        messages.success(request, "Usuario eliminado correctamente.")
        return redirect('lista_usuarios')
    return render(request, 'core/usuarios/eliminar.html', {'usuario': usuario})


# =============================================================================
# EMPRESAS
# =============================================================================

@login_required
def lista_empresas(request):
    empresas = Empresa.objects.select_related('usuario').order_by('razon_social')
    q = request.GET.get('q', '').strip()
    if q:
        empresas = empresas.filter(Q(razon_social__icontains=q) | Q(ruc__icontains=q))
    return render(request, 'core/empresas/lista.html', {'empresas': _paginar(request, empresas)})


@rol_requerido('administrador')
def crear_empresa(request):
    if request.method == 'POST':
        form = EmpresaCreateForm(request.POST)
        if form.is_valid():
            form.guardar()
            messages.success(request, "Empresa registrada correctamente.")
            return redirect('lista_empresas')
    else:
        form = EmpresaCreateForm()
    return render(request, 'core/empresas/crear.html', {'form': form})


@login_required
def detalle_empresa(request, pk):
    empresa = get_object_or_404(Empresa, pk=pk)
    contexto = {
        'empresa': empresa,
        'productos': empresa.productos.filter(activo=True)[:8],
        'vendedores_autorizados': empresa.vendedores_aprobados.all()[:8],
    }
    return render(request, 'core/empresas/detalle.html', contexto)


@rol_requerido('administrador', 'empresa')
def editar_empresa(request, pk):
    empresa = get_object_or_404(Empresa, pk=pk)
    if request.user.rol == 'empresa' and empresa.usuario_id != request.user.id:
        raise PermissionDenied("No puedes editar el perfil de otra empresa.")

    form = EmpresaForm(request.POST or None, instance=empresa)
    if request.user.rol != 'administrador':
        form.fields.pop('estado', None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Empresa actualizada correctamente.")
        return redirect('detalle_empresa', pk=empresa.pk)
    return render(request, 'core/empresas/editar.html', {'form': form, 'empresa': empresa})


@rol_requerido('administrador')
def eliminar_empresa(request, pk):
    empresa = get_object_or_404(Empresa, pk=pk)
    if request.method == 'POST':
        empresa.usuario.delete()
        messages.success(request, "Empresa eliminada correctamente.")
        return redirect('lista_empresas')
    return render(request, 'core/empresas/eliminar.html', {'empresa': empresa})


# =============================================================================
# VENDEDORES
# =============================================================================

@login_required
def lista_vendedores(request):
    vendedores = Vendedor.objects.select_related('usuario').order_by('usuario__first_name')
    q = request.GET.get('q', '').strip()
    if q:
        vendedores = vendedores.filter(
            Q(usuario__first_name__icontains=q) | Q(usuario__last_name__icontains=q) |
            Q(numero_identidad__icontains=q)
        )
    return render(request, 'core/vendedores/lista.html', {'vendedores': _paginar(request, vendedores)})


@rol_requerido('administrador')
def crear_vendedor(request):
    if request.method == 'POST':
        form = VendedorCreateForm(request.POST)
        if form.is_valid():
            form.guardar()
            messages.success(request, "Vendedor registrado correctamente.")
            return redirect('lista_vendedores')
    else:
        form = VendedorCreateForm()
    return render(request, 'core/vendedores/crear.html', {'form': form})


@login_required
def detalle_vendedor(request, pk):
    vendedor = get_object_or_404(Vendedor, pk=pk)
    contexto = {
        'vendedor': vendedor,
        'autorizado_por_mi': (
            request.user.rol == 'empresa' and
            vendedor.empresas_aprobadoras.filter(pk=request.user.empresa.pk).exists()
        ),
    }
    return render(request, 'core/vendedores/detalle.html', contexto)


@rol_requerido('administrador')
def editar_vendedor(request, pk):
    vendedor = get_object_or_404(Vendedor, pk=pk)
    form = VendedorForm(request.POST or None, instance=vendedor)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Vendedor actualizado correctamente.")
        return redirect('detalle_vendedor', pk=vendedor.pk)
    return render(request, 'core/vendedores/editar.html', {'form': form, 'vendedor': vendedor})


@rol_requerido('administrador')
def eliminar_vendedor(request, pk):
    vendedor = get_object_or_404(Vendedor, pk=pk)
    if request.method == 'POST':
        vendedor.usuario.delete()
        messages.success(request, "Vendedor eliminado correctamente.")
        return redirect('lista_vendedores')
    return render(request, 'core/vendedores/eliminar.html', {'vendedor': vendedor})


@rol_requerido('empresa')
def autorizar_vendedor(request, pk):
    """Una empresa autoriza (o revoca) a un vendedor para comercializar sus productos (HU-08)."""
    vendedor = get_object_or_404(Vendedor, pk=pk)
    empresa = request.user.empresa
    if vendedor.empresas_aprobadoras.filter(pk=empresa.pk).exists():
        vendedor.empresas_aprobadoras.remove(empresa)
        messages.info(request, f"Se revocó la autorización de {vendedor.usuario.get_full_name()}.")
    else:
        vendedor.empresas_aprobadoras.add(empresa)
        messages.success(request, f"{vendedor.usuario.get_full_name()} ahora puede vender tus productos.")
    return redirect('detalle_vendedor', pk=vendedor.pk)


# =============================================================================
# COMPRADORES
# =============================================================================

@rol_requerido('administrador', 'empresa', 'vendedor')
def lista_compradores(request):
    compradores = Comprador.objects.select_related('usuario').order_by('usuario__first_name')
    q = request.GET.get('q', '').strip()
    if q:
        compradores = compradores.filter(
            Q(usuario__first_name__icontains=q) | Q(usuario__last_name__icontains=q) |
            Q(tipo_negocio__icontains=q)
        )
    return render(request, 'core/compradores/lista.html', {'compradores': _paginar(request, compradores)})


@rol_requerido('administrador')
def crear_comprador(request):
    if request.method == 'POST':
        form = CompradorCreateForm(request.POST)
        if form.is_valid():
            form.guardar()
            messages.success(request, "Comprador registrado correctamente.")
            return redirect('lista_compradores')
    else:
        form = CompradorCreateForm()
    return render(request, 'core/compradores/crear.html', {'form': form})


@rol_requerido('administrador', 'empresa', 'vendedor')
def detalle_comprador(request, pk):
    comprador = get_object_or_404(Comprador, pk=pk)
    return render(request, 'core/compradores/detalle.html', {'comprador': comprador})


@rol_requerido('administrador')
def editar_comprador(request, pk):
    comprador = get_object_or_404(Comprador, pk=pk)
    form = CompradorForm(request.POST or None, instance=comprador)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Comprador actualizado correctamente.")
        return redirect('detalle_comprador', pk=comprador.pk)
    return render(request, 'core/compradores/editar.html', {'form': form, 'comprador': comprador})


@rol_requerido('administrador')
def eliminar_comprador(request, pk):
    comprador = get_object_or_404(Comprador, pk=pk)
    if request.method == 'POST':
        comprador.usuario.delete()
        messages.success(request, "Comprador eliminado correctamente.")
        return redirect('lista_compradores')
    return render(request, 'core/compradores/eliminar.html', {'comprador': comprador})


# =============================================================================
# CATEGORÍAS DE PRODUCTO
# =============================================================================

@login_required
def lista_categorias(request):
    categorias = CategoriaProducto.objects.all().order_by('nombre')
    q = request.GET.get('q', '').strip()
    if q:
        categorias = categorias.filter(nombre__icontains=q)
    return render(request, 'core/categorias/lista.html', {'categorias': _paginar(request, categorias)})


@rol_requerido('administrador', 'empresa')
def crear_categoria(request):
    form = CategoriaProductoForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Categoría creada correctamente.")
        return redirect('lista_categorias')
    return render(request, 'core/categorias/crear.html', {'form': form})


@rol_requerido('administrador', 'empresa')
def editar_categoria(request, pk):
    categoria = get_object_or_404(CategoriaProducto, pk=pk)
    form = CategoriaProductoForm(request.POST or None, instance=categoria)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Categoría actualizada correctamente.")
        return redirect('lista_categorias')
    return render(request, 'core/categorias/editar.html', {'form': form, 'categoria': categoria})


@rol_requerido('administrador', 'empresa')
def eliminar_categoria(request, pk):
    categoria = get_object_or_404(CategoriaProducto, pk=pk)
    if request.method == 'POST':
        categoria.delete()
        messages.success(request, "Categoría eliminada correctamente.")
        return redirect('lista_categorias')
    return render(request, 'core/categorias/eliminar.html', {'categoria': categoria})


# =============================================================================
# PRODUCTOS
# =============================================================================

@login_required
def lista_productos(request):
    productos = Producto.objects.select_related('empresa', 'categoria', 'inventario').order_by('-fecha_creacion')
    if request.user.rol == 'empresa':
        productos = productos.filter(empresa=request.user.empresa)
    q = request.GET.get('q', '').strip()
    if q:
        productos = productos.filter(Q(nombre__icontains=q) | Q(empresa__razon_social__icontains=q))
    return render(request, 'core/productos/lista.html', {'productos': _paginar(request, productos)})


@rol_requerido('administrador', 'empresa')
def crear_producto(request):
    form = ProductoForm(request.POST or None)
    if request.user.rol == 'empresa':
        form.fields.pop('empresa', None)
    if request.method == 'POST' and form.is_valid():
        producto = form.save(commit=False)
        if request.user.rol == 'empresa':
            producto.empresa = request.user.empresa
        producto.save()
        messages.success(request, "Producto creado correctamente.")
        return redirect('lista_productos')
    return render(request, 'core/productos/crear.html', {'form': form})


@login_required
def detalle_producto(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    return render(request, 'core/productos/detalle.html', {'producto': producto})


@rol_requerido('administrador', 'empresa')
def editar_producto(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    form = ProductoForm(request.POST or None, instance=producto)
    if request.user.rol == 'empresa':
        form.fields.pop('empresa', None)
    if request.method == 'POST' and form.is_valid():
        producto = form.save(commit=False)
        if request.user.rol == 'empresa':
            producto.empresa = request.user.empresa
        producto.save()
        messages.success(request, "Producto actualizado correctamente.")
        return redirect('detalle_producto', pk=producto.pk)
    return render(request, 'core/productos/editar.html', {'form': form, 'producto': producto})


@rol_requerido('administrador', 'empresa')
def eliminar_producto(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST':
        producto.delete()
        messages.success(request, "Producto eliminado correctamente.")
        return redirect('lista_productos')
    return render(request, 'core/productos/eliminar.html', {'producto': producto})


# =============================================================================
# INVENTARIO
# =============================================================================

@rol_requerido('administrador', 'empresa')
def lista_inventario(request):
    inventarios = Inventario.objects.select_related('producto', 'producto__empresa').order_by('producto__nombre')
    if request.user.rol == 'empresa':
        inventarios = inventarios.filter(producto__empresa=request.user.empresa)
    q = request.GET.get('q', '').strip()
    if q:
        inventarios = inventarios.filter(producto__nombre__icontains=q)
    return render(request, 'core/inventario/lista.html', {'inventarios': _paginar(request, inventarios)})


@rol_requerido('administrador', 'empresa')
def crear_inventario(request):
    form = InventarioForm(request.POST or None)
    if request.user.rol == 'empresa':
        form.fields['producto'].queryset = form.fields['producto'].queryset.filter(empresa=request.user.empresa)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Inventario registrado correctamente.")
        return redirect('lista_inventario')
    return render(request, 'core/inventario/crear.html', {'form': form})


@rol_requerido('administrador', 'empresa')
def editar_inventario(request, pk):
    inventario = get_object_or_404(Inventario, pk=pk)
    form = InventarioForm(request.POST or None, instance=inventario)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Inventario actualizado correctamente.")
        return redirect('lista_inventario')
    return render(request, 'core/inventario/editar.html', {'form': form, 'inventario': inventario})


@rol_requerido('administrador', 'empresa')
def eliminar_inventario(request, pk):
    inventario = get_object_or_404(Inventario, pk=pk)
    if request.method == 'POST':
        inventario.delete()
        messages.success(request, "Registro de inventario eliminado.")
        return redirect('lista_inventario')
    return render(request, 'core/inventario/eliminar.html', {'inventario': inventario})


# =============================================================================
# VENTAS — Pedidos
# =============================================================================

@login_required
def lista_pedidos(request):
    pedidos = Pedido.objects.select_related(
        'comprador__usuario', 'vendedor__usuario', 'empresa'
    ).order_by('-fecha_creacion')

    if request.user.rol == 'comprador':
        pedidos = pedidos.filter(comprador=request.user.comprador)
    elif request.user.rol == 'vendedor':
        pedidos = pedidos.filter(vendedor=request.user.vendedor)
    elif request.user.rol == 'empresa':
        pedidos = pedidos.filter(empresa=request.user.empresa)

    estado = request.GET.get('estado', '').strip()
    if estado:
        pedidos = pedidos.filter(estado=estado)

    q = request.GET.get('q', '').strip()
    if q:
        pedidos = pedidos.filter(
            Q(numero_pedido__icontains=q) | Q(comprador__usuario__first_name__icontains=q)
        )

    return render(request, 'core/pedidos/lista.html', {
        'pedidos': _paginar(request, pedidos),
        'estados': ESTADO_PEDIDO,
    })


@rol_requerido('comprador', 'vendedor', 'administrador')
def crear_pedido(request):
    pedido_temporal = Pedido(estado='creado')
    formset = DetallePedidoFormSet(request.POST or None, instance=pedido_temporal, prefix='detalles')

    compradores = None
    if request.user.rol != 'comprador':
        compradores = Comprador.objects.select_related('usuario').all()

    if request.method == 'POST':
        comprador_id = request.POST.get('comprador')
        if formset.is_valid():
            detalles_validos = [
                f.cleaned_data for f in formset
                if f.cleaned_data and not f.cleaned_data.get('DELETE')
            ]
            if not detalles_validos:
                messages.error(request, "Debes agregar al menos un producto al pedido.")
            elif request.user.rol != 'comprador' and not comprador_id:
                messages.error(request, "Selecciona el comprador del pedido.")
            else:
                with transaction.atomic():
                    if request.user.rol == 'comprador':
                        comprador = request.user.comprador
                    else:
                        comprador = get_object_or_404(Comprador, pk=comprador_id)
                    vendedor = request.user.vendedor if request.user.rol == 'vendedor' else None
                    primer_producto = detalles_validos[0]['producto']

                    nuevo_pedido = Pedido.objects.create(
                        numero_pedido=f"PED-{int(timezone.now().timestamp())}",
                        comprador=comprador, vendedor=vendedor,
                        empresa=primer_producto.empresa,
                    )
                    for datos in detalles_validos:
                        detalle = DetallePedido(
                            pedido=nuevo_pedido,
                            producto=datos['producto'],
                            cantidad=datos['cantidad'],
                            precio_unitario=datos.get('precio_unitario') or datos['producto'].precio_venta,
                            descuento=datos.get('descuento') or 0,
                        )
                        detalle.calcular_subtotal()
                    nuevo_pedido.calcular_total()

                messages.success(request, f"Pedido {nuevo_pedido.numero_pedido} creado correctamente.")
                return redirect('detalle_pedido', pk=nuevo_pedido.pk)

    precios_productos = {p.id: str(p.precio_venta) for p in Producto.objects.filter(activo=True)}
    return render(request, 'core/pedidos/crear.html', {
        'formset': formset, 'compradores': compradores, 'precios_productos': precios_productos,
    })


@login_required
def detalle_pedido(request, pk):
    pedido = get_object_or_404(
        Pedido.objects.select_related('comprador__usuario', 'vendedor__usuario', 'empresa')
        .prefetch_related('detalles__producto', 'pagos', 'comisiones'),
        pk=pk,
    )
    factura = Factura.objects.filter(pedido=pedido).first()
    return render(request, 'core/pedidos/detalle.html', {'pedido': pedido, 'factura': factura})


@rol_requerido('empresa', 'vendedor', 'administrador')
def cambiar_estado_pedido(request, pk, estado):
    pedido = get_object_or_404(Pedido, pk=pk)
    estados_validos = dict(ESTADO_PEDIDO)
    if estado not in estados_validos:
        raise Http404("Estado de pedido no válido.")

    if estado == 'cancelado' and not pedido.puede_cancelarse():
        messages.error(request, "Este pedido ya fue despachado y no puede cancelarse.")
    else:
        pedido.estado = estado
        if estado == 'despachado':
            pedido.fecha_despacho = timezone.now()
        elif estado == 'entregado':
            pedido.fecha_entrega = timezone.now()
        pedido.save()
        messages.success(request, f"El pedido ahora está: {estados_validos[estado]}.")
    return redirect('detalle_pedido', pk=pedido.pk)


@rol_requerido('administrador')
def eliminar_pedido(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    if request.method == 'POST':
        pedido.delete()
        messages.success(request, "Pedido eliminado correctamente.")
        return redirect('lista_pedidos')
    return render(request, 'core/pedidos/eliminar.html', {'pedido': pedido})


# =============================================================================
# VENTAS — Pagos
# =============================================================================

@login_required
def lista_pagos(request):
    pagos = Pago.objects.select_related('pedido__comprador__usuario').order_by('-fecha_pago')
    if request.user.rol == 'comprador':
        pagos = pagos.filter(pedido__comprador=request.user.comprador)
    elif request.user.rol == 'empresa':
        pagos = pagos.filter(pedido__empresa=request.user.empresa)
    return render(request, 'core/pagos/lista.html', {'pagos': _paginar(request, pagos)})


@rol_requerido('comprador', 'administrador')
def crear_pago(request):
    form = PagoForm(request.POST or None)
    if request.user.rol == 'comprador':
        form.fields['pedido'].queryset = Pedido.objects.filter(
            comprador=request.user.comprador, estado__in=['creado', 'confirmado']
        )
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Pago registrado. Quedará confirmado tras su validación.")
        return redirect('lista_pagos')
    return render(request, 'core/pagos/crear.html', {'form': form})


@login_required
def detalle_pago(request, pk):
    pago = get_object_or_404(Pago, pk=pk)
    return render(request, 'core/pagos/detalle.html', {'pago': pago})


@rol_requerido('empresa', 'administrador')
def validar_pago(request, pk):
    """Valida el pago y automatiza la generación de factura y comisión (HU-13, HU-16, HU-17)."""
    pago = get_object_or_404(Pago, pk=pk)
    pago.estado = 'validado'
    pago.fecha_validacion = timezone.now()
    pago.save()

    pedido = pago.pedido
    if pedido.estado == 'creado':
        pedido.estado = 'confirmado'
        pedido.save()

    if not Factura.objects.filter(pedido=pedido).exists():
        factura = Factura(
            pedido=pedido,
            numero_factura=f"FAC-{pedido.numero_pedido}",
            subtotal=pedido.total,
        )
        factura.calcular_iva()

    if pedido.vendedor and not pedido.comisiones.exists():
        suscripcion = pedido.empresa.suscripciones.filter(estado='activa').first()
        porcentaje = suscripcion.comision_plataforma if suscripcion else 5.0
        Comision.objects.create(
            vendedor=pedido.vendedor, pedido=pedido, porcentaje=porcentaje,
            monto_comision=round(float(pedido.total) * porcentaje / 100, 2),
        )

    messages.success(request, "Pago validado. Se generó la factura y la comisión correspondiente.")
    return redirect('detalle_pedido', pk=pedido.pk)


@rol_requerido('administrador')
def eliminar_pago(request, pk):
    pago = get_object_or_404(Pago, pk=pk)
    if request.method == 'POST':
        pago.delete()
        messages.success(request, "Pago eliminado correctamente.")
        return redirect('lista_pagos')
    return render(request, 'core/pagos/eliminar.html', {'pago': pago})


# =============================================================================
# VENTAS — Facturas
# =============================================================================

@login_required
def lista_facturas(request):
    facturas = Factura.objects.select_related('pedido').order_by('-fecha_emision')
    if request.user.rol == 'comprador':
        facturas = facturas.filter(pedido__comprador=request.user.comprador)
    elif request.user.rol == 'empresa':
        facturas = facturas.filter(pedido__empresa=request.user.empresa)
    return render(request, 'core/facturas/lista.html', {'facturas': _paginar(request, facturas)})


@login_required
def detalle_factura(request, pk):
    factura = get_object_or_404(Factura, pk=pk)
    return render(request, 'core/facturas/detalle.html', {'factura': factura})


@rol_requerido('empresa', 'administrador')
def autorizar_factura(request, pk):
    factura = get_object_or_404(Factura, pk=pk)
    factura.estado_sri = 'AUTORIZADO'
    factura.clave_acceso = factura.clave_acceso or f"{factura.numero_factura}-{int(timezone.now().timestamp())}"
    factura.save()
    messages.success(request, "Factura autorizada por el SRI.")
    return redirect('detalle_factura', pk=factura.pk)


@rol_requerido('administrador')
def eliminar_factura(request, pk):
    factura = get_object_or_404(Factura, pk=pk)
    if request.method == 'POST':
        factura.delete()
        messages.success(request, "Factura eliminada correctamente.")
        return redirect('lista_facturas')
    return render(request, 'core/facturas/eliminar.html', {'factura': factura})


# =============================================================================
# PLATAFORMA — Suscripciones
# =============================================================================

@rol_requerido('administrador', 'empresa')
def lista_suscripciones(request):
    suscripciones = Suscripcion.objects.select_related('empresa').order_by('-fecha_creacion')
    if request.user.rol == 'empresa':
        suscripciones = suscripciones.filter(empresa=request.user.empresa)
    return render(request, 'core/suscripciones/lista.html', {'suscripciones': _paginar(request, suscripciones)})


@rol_requerido('administrador', 'empresa')
def crear_suscripcion(request):
    form = SuscripcionForm(request.POST or None)
    if request.user.rol == 'empresa':
        form.fields.pop('empresa', None)
    if request.method == 'POST' and form.is_valid():
        suscripcion = form.save(commit=False)
        if request.user.rol == 'empresa':
            suscripcion.empresa = request.user.empresa
        suscripcion.save()
        messages.success(request, "Suscripción contratada correctamente.")
        return redirect('lista_suscripciones')
    return render(request, 'core/suscripciones/crear.html', {'form': form})


@rol_requerido('administrador', 'empresa')
def editar_suscripcion(request, pk):
    suscripcion = get_object_or_404(Suscripcion, pk=pk)
    form = SuscripcionForm(request.POST or None, instance=suscripcion)
    if request.user.rol == 'empresa':
        form.fields.pop('empresa', None)
    if request.method == 'POST' and form.is_valid():
        suscripcion = form.save(commit=False)
        if request.user.rol == 'empresa':
            suscripcion.empresa = request.user.empresa
        suscripcion.save()
        messages.success(request, "Suscripción actualizada correctamente.")
        return redirect('lista_suscripciones')
    return render(request, 'core/suscripciones/editar.html', {'form': form, 'suscripcion': suscripcion})


@rol_requerido('administrador', 'empresa')
def cancelar_suscripcion(request, pk):
    suscripcion = get_object_or_404(Suscripcion, pk=pk)
    if request.method == 'POST':
        suscripcion.estado = 'cancelada'
        suscripcion.fecha_fin = timezone.now().date()
        suscripcion.save()
        messages.success(request, "Suscripción cancelada.")
        return redirect('lista_suscripciones')
    return render(request, 'core/suscripciones/eliminar.html', {'suscripcion': suscripcion})


# =============================================================================
# PLATAFORMA — Comisiones
# =============================================================================

@login_required
def lista_comisiones(request):
    comisiones = Comision.objects.select_related('vendedor__usuario', 'pedido').order_by('-fecha_generacion')
    if request.user.rol == 'vendedor':
        comisiones = comisiones.filter(vendedor=request.user.vendedor)
    elif request.user.rol == 'empresa':
        comisiones = comisiones.filter(pedido__empresa=request.user.empresa)
    return render(request, 'core/comisiones/lista.html', {'comisiones': _paginar(request, comisiones)})


@login_required
def detalle_comision(request, pk):
    comision = get_object_or_404(Comision, pk=pk)
    return render(request, 'core/comisiones/detalle.html', {'comision': comision})


@rol_requerido('administrador', 'empresa')
def pagar_comision(request, pk):
    comision = get_object_or_404(Comision, pk=pk)
    comision.estado = 'pagada'
    comision.fecha_pago = timezone.now()
    comision.save()
    messages.success(request, "Comisión marcada como pagada.")
    return redirect('detalle_comision', pk=comision.pk)


# =============================================================================
# CAPACITACIÓN — Cursos
# =============================================================================

@login_required
def lista_cursos(request):
    cursos = Curso.objects.select_related('empresa').order_by('-fecha_creacion')
    if request.user.rol == 'empresa':
        cursos = cursos.filter(empresa=request.user.empresa)
    elif request.user.rol == 'vendedor':
        cursos = cursos.filter(
            Q(vendedores=request.user.vendedor) | Q(empresa__isnull=True)
        ).distinct()
    return render(request, 'core/cursos/lista.html', {'cursos': _paginar(request, cursos)})


@rol_requerido('administrador', 'empresa')
def crear_curso(request):
    form = CursoForm(request.POST or None)
    if request.user.rol == 'empresa':
        form.fields.pop('empresa', None)
    if request.method == 'POST' and form.is_valid():
        curso = form.save(commit=False)
        if request.user.rol == 'empresa':
            curso.empresa = request.user.empresa
        curso.save()
        form.save_m2m()
        messages.success(request, "Curso creado correctamente.")
        return redirect('lista_cursos')
    return render(request, 'core/cursos/crear.html', {'form': form})


@login_required
def detalle_curso(request, pk):
    curso = get_object_or_404(Curso, pk=pk)
    return render(request, 'core/cursos/detalle.html', {'curso': curso})


@rol_requerido('administrador', 'empresa')
def editar_curso(request, pk):
    curso = get_object_or_404(Curso, pk=pk)
    form = CursoForm(request.POST or None, instance=curso)
    if request.user.rol == 'empresa':
        form.fields.pop('empresa', None)
    if request.method == 'POST' and form.is_valid():
        curso = form.save(commit=False)
        if request.user.rol == 'empresa':
            curso.empresa = request.user.empresa
        curso.save()
        form.save_m2m()
        messages.success(request, "Curso actualizado correctamente.")
        return redirect('detalle_curso', pk=curso.pk)
    return render(request, 'core/cursos/editar.html', {'form': form, 'curso': curso})


@rol_requerido('administrador', 'empresa')
def eliminar_curso(request, pk):
    curso = get_object_or_404(Curso, pk=pk)
    if request.method == 'POST':
        curso.delete()
        messages.success(request, "Curso eliminado correctamente.")
        return redirect('lista_cursos')
    return render(request, 'core/cursos/eliminar.html', {'curso': curso})


# =============================================================================
# CAPACITACIÓN — Evaluaciones
# =============================================================================

@login_required
def lista_evaluaciones(request):
    evaluaciones = Evaluacion.objects.select_related('vendedor__usuario', 'curso').order_by('-fecha_rendicion')
    if request.user.rol == 'vendedor':
        evaluaciones = evaluaciones.filter(vendedor=request.user.vendedor)
    return render(request, 'core/evaluaciones/lista.html', {'evaluaciones': _paginar(request, evaluaciones)})


@rol_requerido('administrador', 'empresa', 'vendedor')
def crear_evaluacion(request):
    form = EvaluacionForm(request.POST or None)
    if request.user.rol == 'vendedor':
        form.fields.pop('vendedor', None)
    if request.method == 'POST' and form.is_valid():
        evaluacion = form.save(commit=False)
        if request.user.rol == 'vendedor':
            evaluacion.vendedor = request.user.vendedor
        evaluacion.save()
        evaluacion.verificar_aprobacion()
        messages.success(request, "Evaluación registrada correctamente.")
        return redirect('detalle_evaluacion', pk=evaluacion.pk)
    return render(request, 'core/evaluaciones/crear.html', {'form': form})


@login_required
def detalle_evaluacion(request, pk):
    evaluacion = get_object_or_404(Evaluacion, pk=pk)
    return render(request, 'core/evaluaciones/detalle.html', {'evaluacion': evaluacion})


@rol_requerido('administrador')
def eliminar_evaluacion(request, pk):
    evaluacion = get_object_or_404(Evaluacion, pk=pk)
    if request.method == 'POST':
        evaluacion.delete()
        messages.success(request, "Evaluación eliminada correctamente.")
        return redirect('lista_evaluaciones')
    return render(request, 'core/evaluaciones/eliminar.html', {'evaluacion': evaluacion})


# =============================================================================
# SISTEMA — Calificaciones
# =============================================================================

@login_required
def lista_calificaciones(request):
    calificaciones = Calificacion.objects.select_related(
        'autor', 'vendedor_calificado__usuario', 'empresa_calificada'
    ).order_by('-fecha_calificacion')
    return render(request, 'core/calificaciones/lista.html', {'calificaciones': _paginar(request, calificaciones)})


@rol_requerido('comprador', 'administrador')
def crear_calificacion(request):
    form = CalificacionForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        calificacion = form.save(commit=False)
        calificacion.autor = request.user
        calificacion.save()
        messages.success(request, "¡Gracias por tu calificación!")
        return redirect('lista_calificaciones')
    return render(request, 'core/calificaciones/crear.html', {'form': form})


@login_required
def detalle_calificacion(request, pk):
    calificacion = get_object_or_404(Calificacion, pk=pk)
    return render(request, 'core/calificaciones/detalle.html', {'calificacion': calificacion})


@rol_requerido('administrador')
def eliminar_calificacion(request, pk):
    calificacion = get_object_or_404(Calificacion, pk=pk)
    if request.method == 'POST':
        calificacion.delete()
        messages.success(request, "Calificación eliminada correctamente.")
        return redirect('lista_calificaciones')
    return render(request, 'core/calificaciones/eliminar.html', {'calificacion': calificacion})


# =============================================================================
# SISTEMA — Notificaciones
# =============================================================================

@login_required
def lista_notificaciones(request):
    notificaciones = request.user.notificaciones.all()
    return render(request, 'core/notificaciones/lista.html', {
        'notificaciones': _paginar(request, notificaciones, 15)
    })


@rol_requerido('administrador')
def crear_notificacion(request):
    form = NotificacionForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Notificación enviada correctamente.")
        return redirect('lista_notificaciones')
    return render(request, 'core/notificaciones/crear.html', {'form': form})


@login_required
def marcar_leida_notificacion(request, pk):
    notificacion = get_object_or_404(Notificacion, pk=pk, destinatario=request.user)
    notificacion.marcar_leida()
    return redirect('lista_notificaciones')


@rol_requerido('administrador')
def eliminar_notificacion(request, pk):
    notificacion = get_object_or_404(Notificacion, pk=pk)
    if request.method == 'POST':
        notificacion.delete()
        messages.success(request, "Notificación eliminada correctamente.")
        return redirect('lista_notificaciones')
    return render(request, 'core/notificaciones/eliminar.html', {'notificacion': notificacion})

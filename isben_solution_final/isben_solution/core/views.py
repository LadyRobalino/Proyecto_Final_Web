from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Avg, Count, F, Max, Q, Sum
from django.db.models.functions import Coalesce
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from functools import wraps
from . import carrito
_PREFIJOS_POR_GRUPO = {
    'usuarios': ('/usuarios/', '/empresas/', '/vendedores/', '/compradores/'),
    'catalogo': ('/categorias/', '/productos/', '/inventario/', '/carrito/'),
    'ventas': ('/pedidos/', '/pagos/', '/facturas/'),
    'plataforma': ('/suscripciones/', '/comisiones/', '/promociones/', '/estadisticas/'),
    'capacitacion': ('/cursos/', '/evaluaciones/'),
    'sistema': ('/calificaciones/', '/incidencias/', '/notificaciones/', '/reportes/'),
}

def render_con_contexto(request, template_name, context=None, **kwargs):
    context = context or {}
    if request.user.is_authenticated:
        context['notificaciones_no_leidas_global'] = request.user.notificaciones.filter(leida=False).count()
        if request.user.rol == 'comprador':
            datos = request.session.setdefault('carrito', {})
            context['carrito_cantidad_global'] = sum(datos.values())
            
    grupo_activo = None
    for grupo, prefijos in _PREFIJOS_POR_GRUPO.items():
        if request.path.startswith(prefijos):
            grupo_activo = grupo
            break
    context['grupo_menu_activo'] = grupo_activo
    
    from django.shortcuts import render
    return render(request, template_name, context, **kwargs)


def rol_requerido(*roles):
    def decorador(vista):
        @wraps(vista)
        @login_required
        def envoltura(request, *args, **kwargs):
            if request.user.rol not in roles:
                raise PermissionDenied("No tienes permiso para acceder a este módulo.")
            return vista(request, *args, **kwargs)
        return envoltura
    return decorador
from .forms import (
    AdministradorPerfilForm, CalificacionForm, CategoriaProductoForm, ComisionForm,
    CompradorCreateForm, CompradorForm, CursoForm, DetallePedidoFormSet,
    DireccionEntregaForm, EmpresaCreateForm, EmpresaForm, EvaluacionForm, FacturaForm,
    InventarioForm, NotificacionForm, PagoForm, PedidoForm, PerfilUsuarioForm,
    ProductoForm, PromocionForm, RegistroForm, SuscripcionForm, UsuarioCreateForm,
    UsuarioForm, VendedorCreateForm, VendedorForm, PlanSuscripcionForm,
)
from .models import (
    Administrador, Calificacion, CategoriaProducto, Comision, Comprador, Curso,
    DetallePedido, DireccionEntrega, Empresa, ESTADO_PEDIDO, Evaluacion, Factura,
    Inventario, MovimientoPuntos, NIVEL_FIDELIZACION, Notificacion, Pago, Pedido,
    PLANES_SUSCRIPCION, Producto, Promocion, SolicitudColaboracion, Suscripcion,
    UMBRALES_NIVEL, Usuario, Vendedor, PlanSuscripcion,
)

METODOS_PAGO = [
    ('transferencia', 'Transferencia bancaria'),
    ('tarjeta', 'Tarjeta de crédito/débito'),
    ('efectivo', 'Efectivo contra entrega'),
]

# Tasa de conversión para canjear puntos de fidelización por descuento en el checkout.
PUNTOS_POR_DOLAR = 100


def _notificar(usuario, titulo, mensaje, tipo='general'):
    """Crea una notificación in-app para un usuario. Punto único de envío (RF de notificaciones automáticas)."""
    Notificacion.objects.create(destinatario=usuario, tipo=tipo, titulo=titulo, mensaje=mensaje)


# Estados de pedido que representan una venta ya aceptada por la empresa (para reportes/ventas).
ESTADOS_VENTA = ['aceptado', 'preparando', 'despachado', 'entregado']


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
            if not request.POST.get('recordar'):
                request.session.set_expiry(0)
            messages.success(request, f"Bienvenido, {usuario.get_full_name() or usuario.username}.")
            return redirect('inicio')
        messages.error(request, "Usuario o contraseña incorrectos.")
    return render_con_contexto(request, 'core/auth/login.html', {'form': form})


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
    return render_con_contexto(request, 'core/auth/registro.html', {'form': form})


# =============================================================================
# INICIO / DASHBOARD
# =============================================================================

@login_required
def inicio(request):
    rol = request.user.rol
    contexto = {'rol': rol}

    if rol == 'administrador':
        contexto.update(_dashboard_administrador())
    elif rol == 'empresa':
        contexto.update(_dashboard_empresa(request.user.empresa))
    elif rol == 'vendedor':
        contexto.update(_dashboard_vendedor(request.user.vendedor))
    elif rol == 'comprador':
        contexto.update(_dashboard_comprador(request.user.comprador))

    return render_con_contexto(request, 'core/inicio.html', contexto)


def _dashboard_administrador():
    hoy = timezone.now().date()
    ventas_qs = Pedido.objects.filter(estado__in=ESTADOS_VENTA)
    ventas_hoy = ventas_qs.filter(fecha_creacion__date=hoy).aggregate(t=Sum('total'))['t'] or 0
    ventas_mes = ventas_qs.filter(
        fecha_creacion__year=hoy.year, fecha_creacion__month=hoy.month
    ).aggregate(t=Sum('total'))['t'] or 0

    productos_mas_vendidos = Producto.objects.annotate(
        unidades_vendidas=Sum('detalles_pedido__cantidad')
    ).filter(unidades_vendidas__gt=0).order_by('-unidades_vendidas')[:5]

    empresas_mayores_ventas = Empresa.objects.annotate(
        total_ventas=Sum('pedidos__total', filter=Q(pedidos__estado__in=ESTADOS_VENTA))
    ).filter(total_ventas__gt=0).order_by('-total_ventas')[:5]

    vendedores_mayores_comisiones = Vendedor.objects.annotate(
        total_comisiones=Sum('comisiones__monto_comision')
    ).filter(total_comisiones__gt=0).order_by('-total_comisiones')[:5]

    return {
        'total_empresas': Empresa.objects.count(),
        'empresas_pendientes': Empresa.objects.filter(estado='pendiente').count(),
        'total_vendedores': Vendedor.objects.count(),
        'vendedores_pendientes': Vendedor.objects.filter(estado_aprobacion='pendiente').count(),
        'total_compradores': Comprador.objects.count(),
        'total_productos': Producto.objects.filter(activo=True).count(),
        'total_pedidos': Pedido.objects.count(),
        'pedidos_pendientes': Pedido.objects.filter(estado='pendiente').count(),
        'pedidos_por_estado': list(Pedido.objects.values('estado').annotate(total=Count('id'))),
        'ventas_hoy': ventas_hoy,
        'ventas_mes': ventas_mes,
        'productos_mas_vendidos': productos_mas_vendidos,
        'empresas_mayores_ventas': empresas_mayores_ventas,
        'vendedores_mayores_comisiones': vendedores_mayores_comisiones,
        'suscripciones_activas': Suscripcion.objects.filter(estado='activa').count(),
        'suscripciones_vencidas': Suscripcion.objects.filter(estado='vencida').count(),
        'pedidos_recientes': Pedido.objects.select_related(
            'comprador__usuario', 'empresa'
        ).order_by('-fecha_creacion')[:6],
        'empresas_pendientes_lista': Empresa.objects.filter(
            estado='pendiente'
        ).select_related('usuario')[:5],
        'vendedores_pendientes_lista': Vendedor.objects.filter(
            estado_aprobacion='pendiente'
        ).select_related('usuario')[:5],
    }


def _dashboard_empresa(empresa):
    hoy = timezone.now().date()
    productos_qs = empresa.productos.all()
    pedidos_qs = empresa.pedidos.all()
    ventas_hoy_qs = pedidos_qs.filter(estado__in=ESTADOS_VENTA, fecha_creacion__date=hoy)
    ganancias = pedidos_qs.filter(estado__in=ESTADOS_VENTA).aggregate(t=Sum('total'))['t'] or 0
    stock_bajo_count = Inventario.objects.filter(
        producto__empresa=empresa, stock_actual__lte=F('stock_minimo')
    ).count()
    return {
        'empresa': empresa,
        'total_productos_activos': productos_qs.filter(activo=True).count(),
        'total_productos_inactivos': productos_qs.filter(activo=False).count(),
        'total_pedidos': pedidos_qs.count(),
        'pedidos_por_estado': list(pedidos_qs.values('estado').annotate(total=Count('id'))),
        'pedidos_pendientes': pedidos_qs.filter(estado='pendiente').count(),
        'ventas_hoy': ventas_hoy_qs.aggregate(t=Sum('total'))['t'] or 0,
        'ganancias': ganancias,
        'stock_bajo_count': stock_bajo_count,
        'stock_bajo': Inventario.objects.select_related('producto').filter(
            producto__empresa=empresa, stock_actual__lte=F('stock_minimo')
        )[:6],
        'suscripcion_actual': empresa.suscripciones.filter(estado='activa').first(),
        'vendedores_autorizados_count': empresa.vendedores_aprobados.count(),
        'solicitudes_colaboracion_pendientes': empresa.solicitudes_colaboracion.filter(
            estado='pendiente'
        ).select_related('vendedor__usuario')[:5],
        'pedidos_recientes': pedidos_qs.select_related(
            'comprador__usuario'
        ).order_by('-fecha_creacion')[:6],
    }


def _dashboard_vendedor(vendedor):
    comisiones_qs = vendedor.comisiones.all()
    pendiente = comisiones_qs.filter(estado='pendiente').aggregate(t=Sum('monto_comision'))['t'] or 0
    pagada = comisiones_qs.filter(estado='pagada').aggregate(t=Sum('monto_comision'))['t'] or 0
    cursos_aprobados_ids = Evaluacion.objects.filter(
        vendedor=vendedor, aprobado=True
    ).values_list('curso_id', flat=True)
    cursos_pendientes = vendedor.cursos_asignados.exclude(id__in=list(cursos_aprobados_ids))
    hoy = timezone.now().date()
    ventas_hoy = vendedor.pedidos.filter(
        estado__in=ESTADOS_VENTA, fecha_creacion__date=hoy
    ).aggregate(t=Sum('total'))['t'] or 0
    clientes_count = vendedor.pedidos.values('comprador').distinct().count()
    empresas_trabajo = vendedor.empresas_aprobadoras.all()
    return {
        'vendedor': vendedor,
        'empresas_aprobadoras_count': vendedor.empresas_aprobadoras.count(),
        'empresas_trabajo': empresas_trabajo,
        'total_pedidos': vendedor.pedidos.count(),
        'pedidos_pendientes': vendedor.pedidos.filter(estado='pendiente').count(),
        'ventas_hoy': ventas_hoy,
        'clientes_count': clientes_count,
        'comision_pendiente': pendiente,
        'comision_pagada': pagada,
        'cursos_pendientes': cursos_pendientes[:6],
        'solicitudes_colaboracion_pendientes': vendedor.solicitudes_colaboracion.filter(
            estado='pendiente'
        ).select_related('empresa')[:5],
        'pedidos_recientes': vendedor.pedidos.select_related(
            'comprador__usuario', 'empresa'
        ).order_by('-fecha_creacion')[:6],
    }


def _dashboard_comprador(comprador):
    from datetime import timedelta
    rango_nivel = list(UMBRALES_NIVEL.keys())
    nivel_rango = rango_nivel.index(comprador.nivel)
    promociones_disponibles = [
        promo for promo in Promocion.objects.filter(activo=True).select_related('empresa')
        if promo.esta_vigente() and rango_nivel.index(promo.nivel_minimo) <= nivel_rango
    ][:5]

    limite_nuevo = timezone.now() - timedelta(days=7)
    productos_nuevos = Producto.objects.filter(activo=True, fecha_creacion__gte=limite_nuevo).order_by('-fecha_creacion')[:8]
    if not productos_nuevos.exists():
        productos_nuevos = Producto.objects.filter(activo=True).order_by('-fecha_creacion')[:8]

    empresas_destacadas = Empresa.objects.filter(estado='aprobado')[:6]

    return {
        'comprador': comprador,
        'promociones_disponibles': promociones_disponibles,
        'productos_nuevos': productos_nuevos,
        'empresas_destacadas': empresas_destacadas,
        'puntos_para_siguiente_nivel': comprador.puntos_para_siguiente_nivel(),
    }


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
    return render_con_contexto(request, 'core/usuarios/lista.html', {'usuarios': _paginar(request, usuarios)})


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
    return render_con_contexto(request, 'core/usuarios/crear.html', {'form': form})


@rol_requerido('administrador')
def detalle_usuario(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    return render_con_contexto(request, 'core/usuarios/detalle.html', {'usuario': usuario})


@rol_requerido('administrador')
def editar_usuario(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    form = UsuarioForm(request.POST or None, instance=usuario)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Usuario actualizado correctamente.")
        return redirect('detalle_usuario', pk=usuario.pk)
    return render_con_contexto(request, 'core/usuarios/editar.html', {'form': form, 'usuario': usuario})


@rol_requerido('administrador')
def eliminar_usuario(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    if request.method == 'POST':
        usuario.delete()
        messages.success(request, "Usuario eliminado correctamente.")
        return redirect('lista_usuarios')
    return render_con_contexto(request, 'core/usuarios/eliminar.html', {'usuario': usuario})


@rol_requerido('administrador')
def bloquear_usuario(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    if usuario == request.user:
        messages.error(request, "No puedes bloquear tu propia cuenta.")
    else:
        usuario.is_active = not usuario.is_active
        usuario.save()
        messages.success(
            request,
            "Cuenta desbloqueada correctamente." if usuario.is_active else "Cuenta bloqueada correctamente."
        )
    return redirect('detalle_usuario', pk=usuario.pk)


# =============================================================================
# EMPRESAS
# =============================================================================

@login_required
def lista_empresas(request):
    if request.user.rol == 'vendedor' and not request.user.vendedor.esta_aprobado():
        messages.error(request, "Tu cuenta de vendedor debe ser aprobada por el administrador antes de ver las empresas.")
        return redirect('inicio')
    empresas = Empresa.objects.select_related('usuario').order_by('razon_social')
    if request.user.rol == 'vendedor':
        empresas = empresas.filter(estado='aprobado')
    q = request.GET.get('q', '').strip()
    if q:
        empresas = empresas.filter(Q(razon_social__icontains=q) | Q(ruc__icontains=q))
    estado = request.GET.get('estado', '').strip()
    if estado:
        empresas = empresas.filter(estado=estado)
    return render_con_contexto(request, 'core/empresas/lista.html', {'empresas': _paginar(request, empresas)})


@rol_requerido('administrador')
def aprobar_empresa(request, pk):
    empresa = get_object_or_404(Empresa, pk=pk)
    empresa.estado = 'aprobado'
    empresa.motivo_rechazo = ''
    empresa.fecha_verificacion = timezone.now()
    empresa.save()
    _notificar(
        empresa.usuario, "Tu empresa fue aprobada",
        f"Felicidades, {empresa.razon_social} fue aprobada y ya puedes publicar productos en la plataforma."
    )
    messages.success(request, f"Empresa {empresa.razon_social} aprobada correctamente.")
    return redirect('detalle_empresa', pk=empresa.pk)


@rol_requerido('administrador')
def rechazar_empresa(request, pk):
    empresa = get_object_or_404(Empresa, pk=pk)
    if request.method == 'POST':
        motivo = request.POST.get('motivo', '').strip()
        if not motivo:
            messages.error(request, "Debes indicar el motivo del rechazo.")
        else:
            empresa.estado = 'rechazado'
            empresa.motivo_rechazo = motivo
            empresa.save()
            _notificar(
                empresa.usuario, "Tu empresa fue rechazada",
                f"Tu solicitud para {empresa.razon_social} fue rechazada. Motivo: {motivo}"
            )
            messages.success(request, f"Empresa {empresa.razon_social} rechazada.")
    return redirect('detalle_empresa', pk=empresa.pk)


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
    return render_con_contexto(request, 'core/empresas/crear.html', {'form': form})


@login_required
def detalle_empresa(request, pk):
    if request.user.rol == 'vendedor' and not request.user.vendedor.esta_aprobado():
        messages.error(request, "Tu cuenta de vendedor debe ser aprobada por el administrador antes de ver los detalles de una empresa.")
        return redirect('inicio')
    empresa = get_object_or_404(Empresa, pk=pk)
    es_dueño = request.user.rol == 'administrador' or (
        request.user.rol == 'empresa' and empresa.usuario_id == request.user.id
    )
    contexto = {
        'empresa': empresa,
        'productos': empresa.productos.filter(activo=True)[:8],
        'vendedores_autorizados': empresa.vendedores_aprobados.all()[:8],
        'es_dueño': es_dueño,
    }
    if es_dueño:
        contexto['pedidos_recientes'] = empresa.pedidos.select_related(
            'comprador__usuario', 'vendedor__usuario'
        ).order_by('-fecha_creacion')[:6]
        contexto['solicitudes_pendientes'] = empresa.solicitudes_colaboracion.filter(
            estado='pendiente'
        ).select_related('vendedor__usuario')
    if request.user.rol == 'vendedor':
        contexto['mi_solicitud'] = SolicitudColaboracion.objects.filter(
            vendedor=request.user.vendedor, empresa=empresa
        ).first()
    return render_con_contexto(request, 'core/empresas/detalle.html', contexto)


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
    return render_con_contexto(request, 'core/empresas/editar.html', {'form': form, 'empresa': empresa})


@rol_requerido('administrador')
def eliminar_empresa(request, pk):
    empresa = get_object_or_404(Empresa, pk=pk)
    if request.method == 'POST':
        empresa.usuario.delete()
        messages.success(request, "Empresa eliminada correctamente.")
        return redirect('lista_empresas')
    return render_con_contexto(request, 'core/empresas/eliminar.html', {'empresa': empresa})


# =============================================================================
# VENDEDORES
# =============================================================================

@login_required
def lista_vendedores(request):
    vendedores = Vendedor.objects.select_related('usuario').order_by('usuario__first_name')
    if request.user.rol == 'empresa':
        empresa = request.user.empresa
        vendedores = vendedores.filter(empresas_aprobadoras=empresa)
    q = request.GET.get('q', '').strip()
    if q:
        vendedores = vendedores.filter(
            Q(usuario__first_name__icontains=q) | Q(usuario__last_name__icontains=q) |
            Q(numero_identidad__icontains=q)
        )
    estado = request.GET.get('estado', '').strip()
    if estado:
        vendedores = vendedores.filter(estado_aprobacion=estado)
    
    page_obj = _paginar(request, vendedores)
    if request.user.rol == 'empresa':
        empresa = request.user.empresa
        for v in page_obj.object_list:
            pedidos_v = v.pedidos.filter(empresa=empresa, estado__in=ESTADOS_VENTA)
            v.ventas_realizadas = pedidos_v.count()
            v.clientes_atendidos = pedidos_v.values('comprador').distinct().count()
            v.comisiones_generadas = v.comisiones.filter(pedido__empresa=empresa).aggregate(t=Sum('monto_comision'))['t'] or Decimal('0.00')
            v.calificacion_empresa = v.calificaciones.filter(pedido__empresa=empresa).aggregate(a=Avg('puntuacion'))['a'] or 0.0

    return render_con_contexto(request, 'core/vendedores/lista.html', {'vendedores': page_obj})


@rol_requerido('administrador')
def aprobar_vendedor(request, pk):
    vendedor = get_object_or_404(Vendedor, pk=pk)
    vendedor.estado_aprobacion = 'aprobado'
    vendedor.motivo_rechazo = ''
    vendedor.save()
    _notificar(
        vendedor.usuario, "Tu cuenta fue aprobada",
        "Tu identidad fue verificada. Ya puedes solicitar colaboración con empresas de la plataforma."
    )
    messages.success(request, f"Vendedor {vendedor.usuario.get_full_name()} aprobado correctamente.")
    return redirect('detalle_vendedor', pk=vendedor.pk)


@rol_requerido('administrador')
def rechazar_vendedor(request, pk):
    vendedor = get_object_or_404(Vendedor, pk=pk)
    if request.method == 'POST':
        motivo = request.POST.get('motivo', '').strip()
        if not motivo:
            messages.error(request, "Debes indicar el motivo del rechazo.")
        else:
            vendedor.estado_aprobacion = 'rechazado'
            vendedor.motivo_rechazo = motivo
            vendedor.save()
            _notificar(
                vendedor.usuario, "Tu cuenta fue rechazada",
                f"Tu solicitud de registro fue rechazada. Motivo: {motivo}"
            )
            messages.success(request, f"Vendedor {vendedor.usuario.get_full_name()} rechazado.")
    return redirect('detalle_vendedor', pk=vendedor.pk)


@rol_requerido('administrador')
def suspender_vendedor(request, pk):
    vendedor = get_object_or_404(Vendedor, pk=pk)
    vendedor.estado_aprobacion = 'suspendido'
    vendedor.save()
    _notificar(
        vendedor.usuario, "Tu cuenta fue suspendida",
        "Tu cuenta fue suspendida temporalmente por el administrador. Contacta a soporte para más información."
    )
    messages.success(request, f"Vendedor {vendedor.usuario.get_full_name()} suspendido.")
    return redirect('detalle_vendedor', pk=vendedor.pk)


@rol_requerido('administrador')
def bloquear_vendedor(request, pk):
    vendedor = get_object_or_404(Vendedor, pk=pk)
    vendedor.estado_aprobacion = 'bloqueado'
    vendedor.save()
    _notificar(
        vendedor.usuario, "Tu cuenta fue bloqueada",
        "Tu cuenta fue bloqueada por el administrador y ya no puedes operar en la plataforma."
    )
    messages.success(request, f"Vendedor {vendedor.usuario.get_full_name()} bloqueado.")
    return redirect('detalle_vendedor', pk=vendedor.pk)


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
    return render_con_contexto(request, 'core/vendedores/crear.html', {'form': form})


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
    if request.user.rol == 'empresa':
        contexto['solicitud_de_mi_empresa'] = SolicitudColaboracion.objects.filter(
            vendedor=vendedor, empresa=request.user.empresa
        ).first()
    return render_con_contexto(request, 'core/vendedores/detalle.html', contexto)


@rol_requerido('administrador')
def editar_vendedor(request, pk):
    vendedor = get_object_or_404(Vendedor, pk=pk)
    form = VendedorForm(request.POST or None, instance=vendedor)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Vendedor actualizado correctamente.")
        return redirect('detalle_vendedor', pk=vendedor.pk)
    return render_con_contexto(request, 'core/vendedores/editar.html', {'form': form, 'vendedor': vendedor})


@rol_requerido('administrador')
def eliminar_vendedor(request, pk):
    vendedor = get_object_or_404(Vendedor, pk=pk)
    if request.method == 'POST':
        vendedor.usuario.delete()
        messages.success(request, "Vendedor eliminado correctamente.")
        return redirect('lista_vendedores')
    return render_con_contexto(request, 'core/vendedores/eliminar.html', {'vendedor': vendedor})


@rol_requerido('empresa')
def autorizar_vendedor(request, pk):
    """Una empresa revoca el acceso de un vendedor ya autorizado a comercializar sus productos."""
    vendedor = get_object_or_404(Vendedor, pk=pk)
    empresa = request.user.empresa
    if vendedor.empresas_aprobadoras.filter(pk=empresa.pk).exists():
        vendedor.empresas_aprobadoras.remove(empresa)
        SolicitudColaboracion.objects.filter(vendedor=vendedor, empresa=empresa).delete()
        _notificar(
            vendedor.usuario, "Colaboración revocada",
            f"{empresa.razon_social} revocó tu autorización para comercializar sus productos."
        )
        messages.info(request, f"Se revocó la autorización de {vendedor.usuario.get_full_name()}.")
    return redirect('detalle_vendedor', pk=vendedor.pk)


@rol_requerido('vendedor')
def solicitar_colaboracion(request, pk_empresa):
    """El vendedor solicita comercializar los productos de una empresa aprobada."""
    empresa = get_object_or_404(Empresa, pk=pk_empresa, estado='aprobado')
    vendedor = request.user.vendedor
    if not vendedor.esta_aprobado():
        messages.error(request, "Tu cuenta debe ser aprobada por el administrador antes de solicitar colaboración.")
        return redirect('detalle_empresa', pk=empresa.pk)

    solicitud, creada = SolicitudColaboracion.objects.get_or_create(
        vendedor=vendedor, empresa=empresa, defaults={'estado': 'pendiente'},
    )
    if not creada:
        if solicitud.estado == 'rechazada':
            solicitud.estado = 'pendiente'
            solicitud.motivo_rechazo = ''
            solicitud.fecha_respuesta = None
            solicitud.save()
        elif solicitud.estado == 'aceptada':
            messages.info(request, f"Ya trabajas con {empresa.razon_social}.")
            return redirect('detalle_empresa', pk=empresa.pk)

    _notificar(
        empresa.usuario, "Nueva solicitud de colaboración",
        f"{vendedor.usuario.get_full_name()} solicita comercializar tus productos."
    )
    messages.success(request, f"Solicitud enviada a {empresa.razon_social}. Espera su respuesta.")
    return redirect('detalle_empresa', pk=empresa.pk)


@rol_requerido('empresa')
def responder_colaboracion(request, pk_solicitud, accion):
    """La empresa acepta o rechaza una solicitud de colaboración de un vendedor."""
    solicitud = get_object_or_404(
        SolicitudColaboracion, pk=pk_solicitud, empresa=request.user.empresa, estado='pendiente'
    )
    if accion not in ('aceptar', 'rechazar'):
        raise Http404("Acción no válida.")

    if accion == 'aceptar':
        solicitud.estado = 'aceptada'
        solicitud.fecha_respuesta = timezone.now()
        solicitud.save()
        solicitud.vendedor.empresas_aprobadoras.add(solicitud.empresa)
        _notificar(
            solicitud.vendedor.usuario, "Solicitud aceptada",
            f"{solicitud.empresa.razon_social} aceptó tu solicitud. Ya puedes vender sus productos."
        )
        messages.success(request, f"Aceptaste a {solicitud.vendedor.usuario.get_full_name()}.")
    else:
        motivo = request.POST.get('motivo', '').strip()
        if not motivo:
            messages.error(request, "Debes indicar el motivo del rechazo.")
            return redirect('detalle_vendedor', pk=solicitud.vendedor.pk)
        solicitud.estado = 'rechazada'
        solicitud.motivo_rechazo = motivo
        solicitud.fecha_respuesta = timezone.now()
        solicitud.save()
        _notificar(
            solicitud.vendedor.usuario, "Solicitud rechazada",
            f"{solicitud.empresa.razon_social} rechazó tu solicitud. Motivo: {motivo}"
        )
        messages.success(request, f"Rechazaste la solicitud de {solicitud.vendedor.usuario.get_full_name()}.")
    return redirect('detalle_vendedor', pk=solicitud.vendedor.pk)


@rol_requerido('empresa')
def lista_solicitudes_colaboracion(request):
    solicitudes = request.user.empresa.solicitudes_colaboracion.filter(estado='pendiente').select_related('vendedor__usuario')
    return render_con_contexto(request, 'core/empresas/solicitudes_colaboracion.html', {'solicitudes': _paginar(request, solicitudes)})


# =============================================================================
# COMPRADORES
# =============================================================================

@rol_requerido('administrador', 'empresa', 'vendedor')
def lista_compradores(request):
    compradores = Comprador.objects.select_related('usuario').order_by('usuario__first_name')
    if request.user.rol == 'vendedor':
        # Solo muestra compradores con al menos un pedido atendido por este vendedor
        ids_compradores = (
            Pedido.objects.filter(vendedor=request.user.vendedor)
            .values_list('comprador_id', flat=True)
            .distinct()
        )
        compradores = compradores.filter(pk__in=ids_compradores)
    q = request.GET.get('q', '').strip()
    if q:
        compradores = compradores.filter(
            Q(usuario__first_name__icontains=q) | Q(usuario__last_name__icontains=q) |
            Q(tipo_negocio__icontains=q)
        )
    nivel = request.GET.get('nivel', '').strip()
    if nivel:
        compradores = compradores.filter(nivel=nivel)
    return render_con_contexto(request, 'core/compradores/lista.html', {
        'compradores': _paginar(request, compradores),
        'niveles': NIVEL_FIDELIZACION,
    })


@rol_requerido('administrador', 'empresa', 'vendedor')
def detalle_comprador(request, pk):
    comprador = get_object_or_404(Comprador, pk=pk)
    return render_con_contexto(request, 'core/compradores/detalle.html', {'comprador': comprador})


@rol_requerido('vendedor')
def desvincular_comprador(request, pk):
    """
    Desvincula un comprador de la cartera del vendedor: pone a NULL el campo
    vendedor en todos los pedidos futuros pendientes y quita la relación
    implícita. NO elimina al comprador, NO lo bloquea, NO modifica su cuenta.
    """
    comprador = get_object_or_404(Comprador, pk=pk)
    if request.method == 'POST':
        # Desvincular: poner vendedor=None en pedidos pendientes/activos de este comprador con este vendedor
        Pedido.objects.filter(
            vendedor=request.user.vendedor,
            comprador=comprador,
            estado__in=['pendiente']
        ).update(vendedor=None)
        messages.success(
            request,
            f"{comprador.usuario.get_full_name()} ha sido desvinculado de tu cartera de clientes."
        )
    return redirect('lista_compradores')


# =============================================================================
# CATEGORÍAS DE PRODUCTO
# =============================================================================

@login_required
def lista_categorias(request):
    categorias = CategoriaProducto.objects.all().order_by('nombre')
    q = request.GET.get('q', '').strip()
    if q:
        categorias = categorias.filter(nombre__icontains=q)
    return render_con_contexto(request, 'core/categorias/lista.html', {'categorias': _paginar(request, categorias)})


@rol_requerido('administrador')
def crear_categoria(request):
    form = CategoriaProductoForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Categoría creada correctamente.")
        return redirect('lista_categorias')
    return render_con_contexto(request, 'core/categorias/crear.html', {'form': form})


@rol_requerido('administrador')
def editar_categoria(request, pk):
    categoria = get_object_or_404(CategoriaProducto, pk=pk)
    form = CategoriaProductoForm(request.POST or None, instance=categoria)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Categoría actualizada correctamente.")
        return redirect('lista_categorias')
    return render_con_contexto(request, 'core/categorias/editar.html', {'form': form, 'categoria': categoria})


@rol_requerido('administrador')
def eliminar_categoria(request, pk):
    categoria = get_object_or_404(CategoriaProducto, pk=pk)
    if request.method == 'POST':
        categoria.delete()
        messages.success(request, "Categoría eliminada correctamente.")
        return redirect('lista_categorias')
    return render_con_contexto(request, 'core/categorias/eliminar.html', {'categoria': categoria})


# =============================================================================
# PRODUCTOS
# =============================================================================

@login_required
def lista_productos(request):
    productos = Producto.objects.select_related('empresa', 'categoria', 'inventario').order_by('-fecha_creacion')
    if request.user.rol == 'empresa':
        productos = productos.filter(empresa=request.user.empresa)
    else:
        productos = productos.filter(activo=True)
        if request.user.rol == 'vendedor':
            productos = productos.filter(empresa__in=request.user.vendedor.empresas_aprobadoras.all())
    
    categoria_id = request.GET.get('categoria', '').strip()
    if categoria_id:
        productos = productos.filter(categoria_id=categoria_id)

    q = request.GET.get('q', '').strip()
    if q:
        productos = productos.filter(Q(nombre__icontains=q) | Q(empresa__razon_social__icontains=q))
        
    categorias = CategoriaProducto.objects.all().order_by('nombre')
    return render_con_contexto(request, 'core/productos/lista.html', {
        'productos': _paginar(request, productos),
        'categorias': categorias,
        'categoria_actual': int(categoria_id) if categoria_id and categoria_id.isdigit() else None
    })


@rol_requerido('empresa')
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
    return render_con_contexto(request, 'core/productos/crear.html', {'form': form})


@login_required
def detalle_producto(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    return render_con_contexto(request, 'core/productos/detalle.html', {'producto': producto})


@rol_requerido('comprador')
def comparar_productos(request):
    ids = [int(pk) for pk in request.GET.get('productos', '').split(',') if pk.strip().isdigit()]
    productos = Producto.objects.filter(pk__in=ids, activo=True).select_related(
        'empresa', 'inventario', 'categoria'
    ).annotate(
        calificacion_empresa=Avg(
            'empresa__calificaciones__puntuacion',
            filter=Q(empresa__calificaciones__tipo_calificado='empresa'),
        )
    )
    return render_con_contexto(request, 'core/productos/comparar.html', {'productos': productos})


@rol_requerido('empresa')
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
    return render_con_contexto(request, 'core/productos/editar.html', {'form': form, 'producto': producto})


@rol_requerido('empresa')
def eliminar_producto(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST':
        producto.delete()
        messages.success(request, "Producto eliminado correctamente.")
        return redirect('lista_productos')
    return render_con_contexto(request, 'core/productos/eliminar.html', {'producto': producto})


# =============================================================================
# INVENTARIO
# =============================================================================

@rol_requerido('empresa', 'vendedor')
def lista_inventario(request):
    inventarios = Inventario.objects.select_related('producto', 'producto__empresa').order_by('producto__nombre')
    if request.user.rol == 'empresa':
        inventarios = inventarios.filter(producto__empresa=request.user.empresa)
    
    stock_bajo = request.GET.get('stock_bajo') == 'true'
    if stock_bajo:
        inventarios = inventarios.filter(stock_actual__lte=F('stock_minimo'))

    q = request.GET.get('q', '').strip()
    if q:
        inventarios = inventarios.filter(producto__nombre__icontains=q)
        
    return render_con_contexto(request, 'core/inventario/lista.html', {
        'inventarios': _paginar(request, inventarios),
        'stock_bajo_filtrado': stock_bajo
    })


@rol_requerido('empresa')
def crear_inventario(request):
    form = InventarioForm(request.POST or None)
    if request.user.rol == 'empresa':
        form.fields['producto'].queryset = form.fields['producto'].queryset.filter(empresa=request.user.empresa)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Inventario registrado correctamente.")
        return redirect('lista_inventario')
    return render_con_contexto(request, 'core/inventario/crear.html', {'form': form})


@rol_requerido('empresa')
def editar_inventario(request, pk):
    inventario = get_object_or_404(Inventario, pk=pk)
    form = InventarioForm(request.POST or None, instance=inventario)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Inventario actualizado correctamente.")
        return redirect('lista_inventario')
    return render_con_contexto(request, 'core/inventario/editar.html', {'form': form, 'inventario': inventario})


@rol_requerido('empresa')
def eliminar_inventario(request, pk):
    inventario = get_object_or_404(Inventario, pk=pk)
    if request.method == 'POST':
        inventario.delete()
        messages.success(request, "Registro de inventario eliminado.")
        return redirect('lista_inventario')
    return render_con_contexto(request, 'core/inventario/eliminar.html', {'inventario': inventario})


@rol_requerido('empresa')
def actualizar_stock_rapido(request, pk):
    inventario = get_object_or_404(Inventario, pk=pk, producto__empresa=request.user.empresa)
    if request.method == 'POST':
        accion = request.POST.get('accion')
        if accion == 'aumentar':
            inventario.stock_actual += 1
        elif accion == 'disminuir':
            inventario.stock_actual = max(0, inventario.stock_actual - 1)
        else:
            cantidad = request.POST.get('cantidad')
            if cantidad is not None and cantidad.isdigit():
                inventario.stock_actual = int(cantidad)
        inventario.save()
        messages.success(request, f"Stock de {inventario.producto.nombre} actualizado a {inventario.stock_actual}.")
    return redirect('lista_inventario')


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

    return render_con_contexto(request, 'core/pedidos/lista.html', {
        'pedidos': _paginar(request, pedidos),
        'estados': ESTADO_PEDIDO,
    })


def _crear_pedido_desde_detalles(comprador, empresa, vendedor, detalles, direccion_entrega=''):
    """
    Crea un Pedido + sus DetallePedido y notifica a la empresa. Reutilizado tanto por
    la creación manual (formulario de comprador/vendedor/admin) como por el checkout del carrito.
    `detalles`: lista de dicts con claves producto, cantidad, precio_unitario (opcional), descuento (opcional).
    """
    with transaction.atomic():
        import uuid
        nuevo_pedido = Pedido.objects.create(
            numero_pedido=f"PED-{timezone.now().strftime('%Y%m%d%H%M%S%f')}-{uuid.uuid4().hex[:4].upper()}",
            comprador=comprador, vendedor=vendedor, empresa=empresa,
            direccion_entrega=direccion_entrega,
        )
        for datos in detalles:
            detalle = DetallePedido(
                pedido=nuevo_pedido,
                producto=datos['producto'],
                cantidad=datos['cantidad'],
                precio_unitario=datos.get('precio_unitario') or datos['producto'].precio_venta,
                descuento=datos.get('descuento') or 0,
            )
            detalle.calcular_subtotal()
        nuevo_pedido.calcular_total()

    _notificar(
        empresa.usuario, "Nuevo pedido recibido",
        f"Recibiste el pedido {nuevo_pedido.numero_pedido} de "
        f"{comprador.usuario.get_full_name()} por ${nuevo_pedido.total}.",
        tipo='pedido',
    )
    return nuevo_pedido


@rol_requerido('comprador', 'vendedor')
def crear_pedido(request):
    if request.user.rol == 'vendedor':
        vendedor_actual = request.user.vendedor
        if not vendedor_actual.esta_aprobado() or not vendedor_actual.empresas_aprobadoras.exists():
            messages.error(
                request,
                "Aún no puedes crear pedidos: necesitas ser aprobado por el administrador "
                "y por al menos una empresa."
            )
            return redirect('lista_pedidos')

    pedido_temporal = Pedido(estado='pendiente')
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
                primer_producto = detalles_validos[0]['producto']
                vendedor = request.user.vendedor if request.user.rol == 'vendedor' else None

                capacitacion_pendiente = False
                if vendedor:
                    empresa_pedido = primer_producto.empresa
                    requiere_capacitacion = Curso.objects.filter(
                        empresa=empresa_pedido, vendedores=vendedor
                    ).exists()
                    if requiere_capacitacion and not Evaluacion.objects.filter(
                        vendedor=vendedor, curso__empresa=empresa_pedido, aprobado=True
                    ).exists():
                        capacitacion_pendiente = True
                        messages.error(
                            request,
                            "Debes aprobar la capacitación de esta empresa antes de vender sus productos."
                        )

                if not capacitacion_pendiente:
                    if request.user.rol == 'comprador':
                        comprador = request.user.comprador
                    else:
                        comprador = get_object_or_404(Comprador, pk=comprador_id)

                    nuevo_pedido = _crear_pedido_desde_detalles(
                        comprador, primer_producto.empresa, vendedor, detalles_validos,
                    )
                    messages.success(request, f"Pedido {nuevo_pedido.numero_pedido} creado correctamente.")
                    return redirect('detalle_pedido', pk=nuevo_pedido.pk)

    precios_productos = {p.id: str(p.precio_venta) for p in Producto.objects.filter(activo=True)}
    return render_con_contexto(request, 'core/pedidos/crear.html', {
        'formset': formset, 'compradores': compradores, 'precios_productos': precios_productos,
    })


_PASOS_SEGUIMIENTO = [
    ('pendiente', 'Pendiente'), ('aceptado', 'Aceptado'), ('preparando', 'Preparando'),
    ('despachado', 'Despachado'), ('en_camino', 'En camino'), ('entregado', 'Entregado'),
]


def _calcular_pasos_seguimiento(pedido):
    if pedido.estado in ('rechazado', 'cancelado'):
        return []
    indice_actual = [clave for clave, _ in _PASOS_SEGUIMIENTO].index(pedido.estado) \
        if pedido.estado in dict(_PASOS_SEGUIMIENTO) else -1
    return [
        {'clave': clave, 'label': label, 'completado': i < indice_actual, 'actual': i == indice_actual}
        for i, (clave, label) in enumerate(_PASOS_SEGUIMIENTO)
    ]


@login_required
def detalle_pedido(request, pk):
    pedido = get_object_or_404(
        Pedido.objects.select_related('comprador__usuario', 'vendedor__usuario', 'empresa')
        .prefetch_related('detalles__producto', 'pagos', 'comisiones'),
        pk=pk,
    )
    factura = Factura.objects.filter(pedido=pedido).first()

    calificacion_empresa = calificacion_vendedor = None
    if request.user.rol == 'comprador' and pedido.estado == 'entregado':
        calificacion_empresa = pedido.calificaciones.filter(tipo_calificado='empresa').exists()
        calificacion_vendedor = pedido.calificaciones.filter(tipo_calificado='vendedor').exists()

    return render_con_contexto(request, 'core/pedidos/detalle.html', {
        'pedido': pedido, 'factura': factura,
        'pasos_seguimiento': _calcular_pasos_seguimiento(pedido),
        'calificacion_empresa': calificacion_empresa,
        'calificacion_vendedor': calificacion_vendedor,
    })


# Estados de origen permitidos para llegar a cada estado destino del pedido.
_ORIGENES_PEDIDO = {
    'aceptado':   ['pendiente'],
    'rechazado':  ['pendiente'],
    'preparando': ['aceptado'],
    'despachado': ['preparando'],
    'en_camino':  ['despachado'],
    'entregado':  ['en_camino', 'despachado'],
    'cancelado':  ['pendiente', 'aceptado', 'preparando'],
}


def _aceptar_pedido(pedido):
    """
    Acepta un pedido si hay stock suficiente: descuenta el inventario y notifica.
    Retorna la lista de productos sin stock (vacía si se aceptó correctamente).
    """
    detalles = list(pedido.detalles.select_related('producto__inventario'))
    faltantes = [
        d.producto.nombre for d in detalles
        if not hasattr(d.producto, 'inventario') or d.producto.inventario.stock_actual < d.cantidad
    ]
    if faltantes:
        return faltantes

    with transaction.atomic():
        for detalle in detalles:
            inventario = detalle.producto.inventario
            inventario.stock_actual = max(0, inventario.stock_actual - detalle.cantidad)
            inventario.stock_reservado = max(0, inventario.stock_reservado + detalle.cantidad)
            inventario.save()
        pedido.estado = 'aceptado'
        pedido.save()

    _notificar(
        pedido.comprador.usuario, "Tu pedido fue aceptado",
        f"El pedido {pedido.numero_pedido} fue aceptado y pronto comenzará su preparación.", tipo='pedido',
    )
    if pedido.vendedor:
        _notificar(
            pedido.vendedor.usuario, "Pedido aceptado",
            f"La empresa {pedido.empresa.razon_social} aceptó el pedido {pedido.numero_pedido}.", tipo='pedido',
        )
    return []


def _otorgar_puntos_fidelizacion(pedido):
    """Otorga puntos de fidelización al comprador al entregarse un pedido (1 punto ≈ $1)."""
    comprador = pedido.comprador
    puntos_ganados = int(pedido.total)
    if puntos_ganados <= 0:
        return
    comprador.puntos += puntos_ganados
    comprador.save()
    MovimientoPuntos.objects.create(
        comprador=comprador, pedido=pedido, puntos=puntos_ganados,
        motivo=f"Compra en pedido {pedido.numero_pedido}",
    )
    subio_de_nivel = comprador.recalcular_nivel()
    mensaje = f"Ganaste {puntos_ganados} puntos por tu pedido {pedido.numero_pedido}."
    if subio_de_nivel:
        mensaje += f" ¡Subiste al nivel {comprador.get_nivel_display()}!"
    _notificar(comprador.usuario, "Puntos de fidelización acreditados", mensaje, tipo='general')


@rol_requerido('empresa')
def cambiar_estado_pedido(request, pk, estado):
    pedido = get_object_or_404(Pedido, pk=pk)
    estados_validos = dict(ESTADO_PEDIDO)
    if estado not in estados_validos:
        raise Http404("Estado de pedido no válido.")

    if pedido.estado not in _ORIGENES_PEDIDO.get(estado, []):
        messages.error(request, f"El pedido no puede pasar de \"{estados_validos[pedido.estado]}\" a \"{estados_validos[estado]}\".")
        return redirect('detalle_pedido', pk=pedido.pk)

    if estado == 'rechazado':
        motivo = request.POST.get('motivo', '').strip()
        if not motivo:
            messages.error(request, "Debes indicar el motivo del rechazo.")
            return redirect('detalle_pedido', pk=pedido.pk)
        pedido.estado = 'rechazado'
        pedido.motivo_rechazo = motivo
        pedido.save()
        _notificar(
            pedido.comprador.usuario, "Tu pedido fue rechazado",
            f"El pedido {pedido.numero_pedido} fue rechazado. Motivo: {motivo}", tipo='pedido',
        )
    elif estado == 'aceptado':
        faltantes = _aceptar_pedido(pedido)
        if faltantes:
            messages.error(
                request,
                "No hay stock suficiente para: " + ", ".join(faltantes) +
                ". Rechaza el pedido indicando el motivo."
            )
            return redirect('detalle_pedido', pk=pedido.pk)
    else:
        pedido.estado = estado
        if estado == 'despachado':
            pedido.fecha_despacho = timezone.now()
            # Liberar stock reservado — los productos ya salieron del almacén
            with transaction.atomic():
                for detalle in pedido.detalles.select_related('producto__inventario'):
                    try:
                        inv = detalle.producto.inventario
                        inv.stock_reservado = max(0, inv.stock_reservado - detalle.cantidad)
                        inv.save()
                    except Exception:
                        pass
        elif estado == 'entregado':
            pedido.fecha_entrega = timezone.now()
        pedido.save()
        _notificar(
            pedido.comprador.usuario, "Actualización de tu pedido",
            f"El pedido {pedido.numero_pedido} ahora está: {estados_validos[estado]}.", tipo='pedido',
        )
        if estado == 'entregado':
            _otorgar_puntos_fidelizacion(pedido)
            if pedido.vendedor and not pedido.comisiones.exists():
                suscripcion = pedido.empresa.suscripciones.filter(estado='activa').first()
                porcentaje = suscripcion.plan.comision_plataforma if (suscripcion and suscripcion.plan) else 5.0
                monto = round(pedido.total * Decimal(str(porcentaje)) / 100, 2)
                Comision.objects.create(
                    vendedor=pedido.vendedor, pedido=pedido, porcentaje=porcentaje,
                    monto_comision=monto,
                )
                _notificar(
                    pedido.vendedor.usuario,
                    "Comisión generada",
                    f"Se generó una comisión de ${monto} ({porcentaje}%) por el pedido {pedido.numero_pedido}.",
                    tipo='general',
                )
    messages.success(request, f"El pedido ahora está: {estados_validos[estado]}.")
    return redirect('detalle_pedido', pk=pedido.pk)


# =============================================================================
# CARRITO (Comprador)
# =============================================================================

@rol_requerido('comprador')
def agregar_al_carrito(request, pk_producto):
    producto = get_object_or_404(Producto, pk=pk_producto, activo=True)
    try:
        cantidad = int(request.POST.get('cantidad', 1))
    except ValueError:
        cantidad = 1
    cantidad = max(1, cantidad)

    if not producto.tiene_stock():
        messages.error(request, f"{producto.nombre} no tiene stock disponible.")
    else:
        carrito.agregar(request, producto.pk, cantidad)
        messages.success(request, f"{producto.nombre} agregado al carrito.")
    return redirect(request.META.get('HTTP_REFERER') or 'lista_productos')


@rol_requerido('comprador')
def ver_carrito(request):
    lineas = carrito.obtener_items(request)
    grupos = carrito.agrupar_por_empresa(lineas, comprador=request.user.comprador)
    return render_con_contexto(request, 'core/carrito/ver.html', {'grupos': grupos})


@rol_requerido('comprador')
def actualizar_carrito(request, pk_producto):
    if request.method == 'POST':
        try:
            cantidad = int(request.POST.get('cantidad', 0))
        except ValueError:
            cantidad = 0
        carrito.actualizar(request, pk_producto, cantidad)
    return redirect('ver_carrito')


@rol_requerido('comprador')
def quitar_carrito(request, pk_producto):
    carrito.eliminar(request, pk_producto)
    return redirect('ver_carrito')


@rol_requerido('comprador')
def checkout_carrito(request):
    comprador = request.user.comprador
    lineas = carrito.obtener_items(request)
    grupos = carrito.agrupar_por_empresa(lineas, comprador=comprador)

    if not grupos:
        messages.error(request, "Tu carrito está vacío.")
        return redirect('ver_carrito')

    subtotal_general = sum((grupo['subtotal'] for grupo in grupos), Decimal('0'))
    valor_maximo_canje = min(Decimal(comprador.puntos) / PUNTOS_POR_DOLAR, subtotal_general)

    if request.method == 'POST':
        direccion_id = request.POST.get('direccion')
        direccion_nueva = request.POST.get('direccion_nueva', '').strip()
        metodo_pago = request.POST.get('metodo_pago')
        usar_puntos = request.POST.get('usar_puntos') == 'on'

        direccion_texto = direccion_nueva
        if not direccion_texto and direccion_id:
            direccion_obj = comprador.direcciones.filter(pk=direccion_id).first()
            direccion_texto = direccion_obj.direccion if direccion_obj else ''

        if not direccion_texto:
            messages.error(request, "Selecciona o escribe una dirección de entrega.")
        elif metodo_pago not in dict(METODOS_PAGO):
            messages.error(request, "Selecciona un método de pago válido.")
        else:
            faltantes = [
                f"{linea['producto'].nombre} (disponible: {linea['producto'].inventario.stock_actual if hasattr(linea['producto'], 'inventario') else 0})"
                for grupo in grupos for linea in grupo['lineas']
                if not hasattr(linea['producto'], 'inventario') or linea['producto'].inventario.stock_actual < linea['cantidad']
            ]
            if faltantes:
                messages.error(request, "Sin stock suficiente para: " + ", ".join(faltantes))
            else:
                descuento_total = valor_maximo_canje if usar_puntos else Decimal('0')
                pedidos_creados = []
                for grupo in grupos:
                    descuento_puntos_grupo = (
                        round(descuento_total * (grupo['subtotal'] / subtotal_general), 2)
                        if descuento_total and subtotal_general else Decimal('0')
                    )
                    descuento_total_grupo = descuento_puntos_grupo + grupo['descuento_promocion']
                    detalles = []
                    descuento_acumulado = Decimal('0')
                    for i, l in enumerate(grupo['lineas']):
                        if descuento_total_grupo and grupo['subtotal']:
                            if i == len(grupo['lineas']) - 1:
                                descuento_linea = descuento_total_grupo - descuento_acumulado
                            else:
                                descuento_linea = round(descuento_total_grupo * (l['subtotal'] / grupo['subtotal']), 2)
                                descuento_acumulado += descuento_linea
                        else:
                            descuento_linea = Decimal('0')
                        detalles.append({
                            'producto': l['producto'], 'cantidad': l['cantidad'],
                            'precio_unitario': l['precio_unitario'], 'descuento': descuento_linea,
                        })
                    pedido = _crear_pedido_desde_detalles(
                        comprador, grupo['empresa'], None, detalles, direccion_entrega=direccion_texto,
                    )
                    Pago.objects.create(
                        pedido=pedido, monto=pedido.total, tipo='total',
                        metodo_pago=dict(METODOS_PAGO)[metodo_pago], estado='pendiente',
                    )
                    pedidos_creados.append(pedido)

                if descuento_total > 0:
                    puntos_usados = int(descuento_total * PUNTOS_POR_DOLAR)
                    comprador.puntos = max(0, comprador.puntos - puntos_usados)
                    comprador.save()
                    comprador.recalcular_nivel()
                    MovimientoPuntos.objects.create(
                        comprador=comprador, puntos=-puntos_usados,
                        motivo="Canje de puntos por descuento en checkout",
                    )

                carrito.vaciar(request)
                mensaje = f"Se crearon {len(pedidos_creados)} pedido(s): " + ", ".join(p.numero_pedido for p in pedidos_creados)
                if descuento_total > 0:
                    mensaje += f" (descuento de ${descuento_total} aplicado con tus puntos)."
                messages.success(request, mensaje)
                return redirect('lista_pedidos')

    return render_con_contexto(request, 'core/carrito/checkout.html', {
        'grupos': grupos,
        'direcciones': comprador.direcciones.all(),
        'metodos_pago': METODOS_PAGO,
        'puntos_disponibles': comprador.puntos,
        'valor_maximo_canje': valor_maximo_canje,
    })


@rol_requerido('comprador')
def repetir_pedido(request, pk):
    pedido_anterior = get_object_or_404(Pedido, pk=pk, comprador=request.user.comprador)
    agregados = 0
    omitidos = 0
    for detalle in pedido_anterior.detalles.select_related('producto'):
        if detalle.producto.activo:
            carrito.agregar(request, detalle.producto.pk, detalle.cantidad)
            agregados += 1
        else:
            omitidos += 1

    if agregados:
        mensaje = f"Se agregaron {agregados} producto(s) de tu pedido anterior al carrito."
        if omitidos:
            mensaje += f" ({omitidos} ya no están disponibles.)"
        messages.success(request, mensaje)
    else:
        messages.error(request, "Ninguno de los productos de ese pedido está disponible actualmente.")
    return redirect('ver_carrito')


# =============================================================================
# DIRECCIONES DE ENTREGA (Comprador)
# =============================================================================

@rol_requerido('comprador')
def lista_direcciones(request):
    direcciones = request.user.comprador.direcciones.all()
    return render_con_contexto(request, 'core/direcciones/lista.html', {'direcciones': direcciones})


@rol_requerido('comprador')
def crear_direccion(request):
    form = DireccionEntregaForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        direccion = form.save(commit=False)
        direccion.comprador = request.user.comprador
        direccion.save()
        messages.success(request, "Dirección agregada correctamente.")
        return redirect('lista_direcciones')
    return render_con_contexto(request, 'core/direcciones/crear.html', {'form': form})


@rol_requerido('comprador')
def eliminar_direccion(request, pk):
    direccion = get_object_or_404(DireccionEntrega, pk=pk, comprador=request.user.comprador)
    if request.method == 'POST':
        direccion.delete()
        messages.success(request, "Dirección eliminada correctamente.")
        return redirect('lista_direcciones')
    return render_con_contexto(request, 'core/direcciones/eliminar.html', {'direccion': direccion})


# =============================================================================
# FIDELIZACIÓN — Promociones (Empresa)
# =============================================================================

@rol_requerido('empresa')
def lista_promociones(request):
    promociones = request.user.empresa.promociones.all().order_by('-fecha_creacion')
    return render_con_contexto(request, 'core/promociones/lista.html', {'promociones': _paginar(request, promociones)})


@rol_requerido('empresa')
def crear_promocion(request):
    form = PromocionForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        promocion = form.save(commit=False)
        promocion.empresa = request.user.empresa
        promocion.save()
        messages.success(request, "Promoción creada correctamente.")
        return redirect('lista_promociones')
    return render_con_contexto(request, 'core/promociones/crear.html', {'form': form})


@rol_requerido('empresa')
def editar_promocion(request, pk):
    promocion = get_object_or_404(Promocion, pk=pk, empresa=request.user.empresa)
    form = PromocionForm(request.POST or None, instance=promocion)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Promoción actualizada correctamente.")
        return redirect('lista_promociones')
    return render_con_contexto(request, 'core/promociones/editar.html', {'form': form, 'promocion': promocion})


@rol_requerido('empresa')
def eliminar_promocion(request, pk):
    promocion = get_object_or_404(Promocion, pk=pk, empresa=request.user.empresa)
    if request.method == 'POST':
        promocion.delete()
        messages.success(request, "Promoción eliminada correctamente.")
        return redirect('lista_promociones')
    return render_con_contexto(request, 'core/promociones/eliminar.html', {'promocion': promocion})


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
    return render_con_contexto(request, 'core/pagos/lista.html', {'pagos': _paginar(request, pagos)})


@rol_requerido('comprador')
def crear_pago(request):
    form = PagoForm(request.POST or None)
    if request.user.rol == 'comprador':
        form.fields['pedido'].queryset = Pedido.objects.filter(
            comprador=request.user.comprador, estado__in=['pendiente', 'aceptado']
        )
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Pago registrado. Quedará confirmado tras su validación.")
        return redirect('lista_pagos')
    return render_con_contexto(request, 'core/pagos/crear.html', {'form': form})


@login_required
def detalle_pago(request, pk):
    pago = get_object_or_404(Pago, pk=pk)
    return render_con_contexto(request, 'core/pagos/detalle.html', {'pago': pago})


@rol_requerido('empresa')
def validar_pago(request, pk):
    """Valida el pago y automatiza la generación de factura y comisión (HU-13, HU-16, HU-17)."""
    pago = get_object_or_404(Pago, pk=pk)
    pago.estado = 'validado'
    pago.fecha_validacion = timezone.now()
    pago.save()

    pedido = pago.pedido
    if pedido.estado == 'pendiente':
        _aceptar_pedido(pedido)

    if not Factura.objects.filter(pedido=pedido).exists():
        factura = Factura(
            pedido=pedido,
            numero_factura=f"FAC-{pedido.numero_pedido}",
            subtotal=pedido.subtotal - pedido.descuento,
            iva=pedido.iva,
            total=pedido.total,
        )
        factura.save()
        
    _notificar(
        pedido.comprador.usuario, "Pago validado",
        f"Tu pago de ${pago.monto} para el pedido {pedido.numero_pedido} ha sido validado.",
        tipo='pago'
    )

    messages.success(request, "Pago validado. Se generó la factura correspondiente.")
    return redirect('detalle_pedido', pk=pedido.pk)


@rol_requerido('empresa')
def rechazar_pago(request, pk):
    """Rechaza el pago y notifica al comprador."""
    pago = get_object_or_404(Pago, pk=pk)
    if request.method == 'POST':
        pago.estado = 'rechazado'
        pago.fecha_validacion = timezone.now()
        pago.save()
        
        _notificar(
            pago.pedido.comprador.usuario, "Pago rechazado",
            f"Tu pago de ${pago.monto} para el pedido {pago.pedido.numero_pedido} ha sido rechazado. Por favor, comunícate con la empresa.",
            tipo='pago'
        )
        messages.success(request, "Pago rechazado correctamente.")
    return redirect('detalle_pedido', pk=pago.pedido.pk)


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
    return render_con_contexto(request, 'core/facturas/lista.html', {'facturas': _paginar(request, facturas)})


@login_required
def detalle_factura(request, pk):
    factura = get_object_or_404(Factura, pk=pk)
    return render_con_contexto(request, 'core/facturas/detalle.html', {'factura': factura})


@rol_requerido('empresa')
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
    return render_con_contexto(request, 'core/facturas/eliminar.html', {'factura': factura})


# =============================================================================
# PLATAFORMA — Suscripciones
# =============================================================================

# =============================================================================
# PLANES DE SUSCRIPCIÓN (Administrador CRUD)
# =============================================================================

@rol_requerido('administrador')
def lista_planes(request):
    planes = PlanSuscripcion.objects.all().order_by('-fecha_creacion')
    return render_con_contexto(request, 'core/planes/lista.html', {'planes': _paginar(request, planes)})


@rol_requerido('administrador')
def crear_plan(request):
    form = PlanSuscripcionForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Plan de suscripción creado exitosamente.")
        return redirect('lista_planes')
    return render_con_contexto(request, 'core/planes/crear.html', {'form': form})


@rol_requerido('administrador')
def editar_plan(request, pk):
    plan = get_object_or_404(PlanSuscripcion, pk=pk)
    form = PlanSuscripcionForm(request.POST or None, instance=plan)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Plan de suscripción actualizado exitosamente.")
        return redirect('lista_planes')
    return render_con_contexto(request, 'core/planes/editar.html', {'form': form, 'plan': plan})


@rol_requerido('administrador')
def eliminar_plan(request, pk):
    plan = get_object_or_404(PlanSuscripcion, pk=pk)
    if request.method == 'POST':
        plan.delete()
        messages.success(request, "Plan de suscripción eliminado exitosamente.")
        return redirect('lista_planes')
    return render_con_contexto(request, 'core/planes/eliminar.html', {'plan': plan})


@rol_requerido('administrador')
def publicar_plan(request, pk):
    plan = get_object_or_404(PlanSuscripcion, pk=pk)
    if request.method == 'POST':
        plan.activo = not plan.activo
        plan.save()
        estado_str = "publicado" if plan.activo else "desactivado"
        messages.success(request, f"Plan '{plan.nombre}' {estado_str} correctamente.")
    return redirect('lista_planes')


# =============================================================================
# SUSCRIPCIONES (Empresa y Supervisión de Admin)
# =============================================================================

@rol_requerido('administrador', 'empresa', 'vendedor')
def lista_suscripciones(request):
    suscripciones = Suscripcion.objects.select_related('empresa', 'vendedor__usuario', 'plan').order_by('-fecha_creacion')
    if request.user.rol == 'empresa':
        suscripciones = suscripciones.filter(empresa=request.user.empresa)
        planes_disponibles = PlanSuscripcion.objects.filter(activo=True, tipo='empresa')
        suscripcion_activa = suscripciones.filter(estado='activa').first()
        return render_con_contexto(request, 'core/suscripciones/lista.html', {
            'suscripciones': _paginar(request, suscripciones),
            'planes_disponibles': planes_disponibles,
            'suscripcion_activa': suscripcion_activa
        })
    elif request.user.rol == 'vendedor':
        suscripciones = suscripciones.filter(vendedor=request.user.vendedor)
        planes_disponibles = PlanSuscripcion.objects.filter(activo=True, tipo='vendedor')
        suscripcion_activa = suscripciones.filter(estado='activa').first()
        return render_con_contexto(request, 'core/suscripciones/lista.html', {
            'suscripciones': _paginar(request, suscripciones),
            'planes_disponibles': planes_disponibles,
            'suscripcion_activa': suscripcion_activa
        })
    return render_con_contexto(request, 'core/suscripciones/lista_admin.html', {'suscripciones': _paginar(request, suscripciones)})


@rol_requerido('empresa', 'vendedor')
def suscribir_empresa(request, pk_plan):
    plan = get_object_or_404(PlanSuscripcion, pk=pk_plan, activo=True)
    if request.user.rol == 'empresa':
        if plan.tipo != 'empresa':
            messages.error(request, "Este plan no corresponde a tu tipo de cuenta.")
            return redirect('lista_suscripciones')
        empresa = request.user.empresa
        Suscripcion.objects.filter(empresa=empresa, estado='activa').update(
            estado='cancelada', fecha_fin=timezone.now().date()
        )
        Suscripcion.objects.create(
            empresa=empresa,
            plan=plan,
            estado='activa',
            fecha_inicio=timezone.now().date(),
        )
    elif request.user.rol == 'vendedor':
        if plan.tipo != 'vendedor':
            messages.error(request, "Este plan no corresponde a tu tipo de cuenta.")
            return redirect('lista_suscripciones')
        vendedor = request.user.vendedor
        Suscripcion.objects.filter(vendedor=vendedor, estado='activa').update(
            estado='cancelada', fecha_fin=timezone.now().date()
        )
        Suscripcion.objects.create(
            vendedor=vendedor,
            plan=plan,
            estado='activa',
            fecha_inicio=timezone.now().date(),
        )
    messages.success(request, f"Te has suscrito al plan {plan.nombre} exitosamente.")
    return redirect('lista_suscripciones')


@rol_requerido('empresa', 'vendedor')
def cancelar_suscripcion_empresa(request, pk_suscripcion):
    if request.user.rol == 'empresa':
        suscripcion = get_object_or_404(Suscripcion, pk=pk_suscripcion, empresa=request.user.empresa)
    else:
        suscripcion = get_object_or_404(Suscripcion, pk=pk_suscripcion, vendedor=request.user.vendedor)
    if request.method == 'POST':
        suscripcion.estado = 'cancelada'
        suscripcion.fecha_fin = timezone.now().date()
        suscripcion.save()
        messages.success(request, "Suscripción cancelada correctamente.")
    return redirect('lista_suscripciones')


# =============================================================================
# PLATAFORMA — Comisiones
# =============================================================================

@rol_requerido('empresa', 'vendedor')
def lista_comisiones(request):
    comisiones = Comision.objects.select_related(
        'vendedor__usuario', 'pedido__empresa'
    ).order_by('-fecha_generacion')
    if request.user.rol == 'vendedor':
        comisiones = comisiones.filter(vendedor=request.user.vendedor)
    elif request.user.rol == 'empresa':
        comisiones = comisiones.filter(pedido__empresa=request.user.empresa)

    resumen = comisiones.aggregate(
        pendiente=Sum('monto_comision', filter=Q(estado='pendiente')),
        pagada=Sum('monto_comision', filter=Q(estado='pagada')),
        anuladas=Count('id', filter=Q(estado='anulada')),
    )

    estado = request.GET.get('estado', '').strip()
    if estado:
        comisiones = comisiones.filter(estado=estado)

    orden = request.GET.get('orden', '-fecha_generacion')
    if orden in ('-fecha_generacion', 'fecha_generacion', '-monto_comision', 'monto_comision'):
        comisiones = comisiones.order_by(orden)

    return render_con_contexto(request, 'core/comisiones/lista.html', {
        'comisiones': _paginar(request, comisiones),
        'total_pendiente': resumen['pendiente'] or 0,
        'total_pagada': resumen['pagada'] or 0,
        'total_anuladas': resumen['anuladas'] or 0,
    })


@rol_requerido('empresa', 'vendedor')
def detalle_comision(request, pk):
    comision = get_object_or_404(
        Comision.objects.select_related('vendedor__usuario', 'pedido__empresa', 'pedido__comprador__usuario')
        .prefetch_related('pedido__detalles__producto'),
        pk=pk,
    )
    return render_con_contexto(request, 'core/comisiones/detalle.html', {'comision': comision})


@rol_requerido('empresa')
def pagar_comision(request, pk):
    comision = get_object_or_404(Comision, pk=pk)
    comision.estado = 'pagada'
    comision.fecha_pago = timezone.now()
    comision.save()
    # Notificar al vendedor que su comisión fue pagada
    _notificar(
        comision.vendedor.usuario,
        "Comisión pagada",
        f"La empresa {comision.pedido.empresa.razon_social} marcó como pagada tu comisión de "
        f"${comision.monto_comision} del pedido {comision.pedido.numero_pedido}.",
        tipo='general',
    )
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
    return render_con_contexto(request, 'core/cursos/lista.html', {'cursos': _paginar(request, cursos)})


@rol_requerido('administrador')
def crear_curso(request):
    form = CursoForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Curso creado correctamente.")
        return redirect('lista_cursos')
    return render_con_contexto(request, 'core/cursos/crear.html', {'form': form})


@login_required
def detalle_curso(request, pk):
    curso = get_object_or_404(Curso, pk=pk)
    if request.user.rol == 'vendedor' and curso.plan_requerido:
        suscripcion = request.user.vendedor.suscripciones.filter(estado='activa').first()
        if not suscripcion or (suscripcion.plan.precio < curso.plan_requerido.precio):
            messages.warning(request, f"Este curso requiere el plan '{curso.plan_requerido.nombre}' o superior. Por favor, actualiza tu suscripción.")
            return redirect('lista_suscripciones')
    return render_con_contexto(request, 'core/cursos/detalle.html', {'curso': curso})


@rol_requerido('administrador')
def editar_curso(request, pk):
    curso = get_object_or_404(Curso, pk=pk)
    form = CursoForm(request.POST or None, instance=curso)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Curso actualizado correctamente.")
        return redirect('detalle_curso', pk=curso.pk)
    return render_con_contexto(request, 'core/cursos/editar.html', {'form': form, 'curso': curso})


@rol_requerido('administrador')
def eliminar_curso(request, pk):
    curso = get_object_or_404(Curso, pk=pk)
    if request.method == 'POST':
        curso.delete()
        messages.success(request, "Curso eliminado correctamente.")
        return redirect('lista_cursos')
    return render_con_contexto(request, 'core/cursos/eliminar.html', {'curso': curso})


# =============================================================================
# CAPACITACIÓN — Evaluaciones
# =============================================================================

@login_required
def lista_evaluaciones(request):
    evaluaciones = Evaluacion.objects.select_related('vendedor__usuario', 'curso').order_by('-fecha_rendicion')
    if request.user.rol == 'vendedor':
        evaluaciones = evaluaciones.filter(vendedor=request.user.vendedor)
    elif request.user.rol == 'empresa':
        evaluaciones = evaluaciones.filter(vendedor__empresas_aprobadoras=request.user.empresa)
    return render_con_contexto(request, 'core/evaluaciones/lista.html', {'evaluaciones': _paginar(request, evaluaciones)})


@rol_requerido('administrador')
def crear_evaluacion(request):
    """Solo el administrador registra el resultado de una evaluación."""
    form = EvaluacionForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        evaluacion = form.save()
        evaluacion.verificar_aprobacion()
        messages.success(request, "Evaluación registrada correctamente.")
        return redirect('detalle_evaluacion', pk=evaluacion.pk)
    return render_con_contexto(request, 'core/evaluaciones/crear.html', {'form': form})


@rol_requerido('vendedor')
def realizar_evaluacion(request, pk_curso):
    curso = get_object_or_404(Curso, pk=pk_curso, activo=True)
    vendedor = request.user.vendedor

    # Control de acceso según el plan
    if curso.plan_requerido:
        suscripcion = vendedor.suscripciones.filter(estado='activa').first()
        if not suscripcion or (suscripcion.plan.precio < curso.plan_requerido.precio):
            messages.warning(request, f"Este curso requiere el plan '{curso.plan_requerido.nombre}' o superior. Por favor, actualiza tu suscripción.")
            return redirect('lista_suscripciones')

    eval_existente = Evaluacion.objects.filter(vendedor=vendedor, curso=curso, aprobado=True).first()
    if eval_existente:
        messages.info(request, "Ya has aprobado la evaluación para este curso.")
        return redirect('detalle_evaluacion', pk=eval_existente.pk)

    if request.method == 'POST':
        ans1 = request.POST.get('q1')
        ans2 = request.POST.get('q2')
        ans3 = request.POST.get('q3')

        puntaje = 0.0
        if ans1 == 'correct':
            puntaje += 3.33
        if ans2 == 'correct':
            puntaje += 3.33
        if ans3 == 'correct':
            puntaje += 3.34

        puntaje = round(puntaje, 2)
        evaluacion = Evaluacion.objects.create(
            vendedor=vendedor,
            curso=curso,
            puntaje_obtenido=puntaje,
            puntaje_minimo=7.0
        )
        evaluacion.verificar_aprobacion()

        if evaluacion.aprobado:
            messages.success(request, f"¡Felicidades! Aprobaste la evaluación del curso '{curso.titulo}' con {puntaje}/10 y has obtenido tu certificado.")
        else:
            messages.error(request, f"Has reprobado la evaluación del curso '{curso.titulo}' con {puntaje}/10. Inténtalo de nuevo.")
        
        return redirect('detalle_evaluacion', pk=evaluacion.pk)

    return render_con_contexto(request, 'core/evaluaciones/realizar.html', {'curso': curso})


@login_required
def detalle_evaluacion(request, pk):
    evaluacion = get_object_or_404(Evaluacion, pk=pk)
    return render_con_contexto(request, 'core/evaluaciones/detalle.html', {'evaluacion': evaluacion})


@rol_requerido('administrador')
def eliminar_evaluacion(request, pk):
    evaluacion = get_object_or_404(Evaluacion, pk=pk)
    if request.method == 'POST':
        evaluacion.delete()
        messages.success(request, "Evaluación eliminada correctamente.")
        return redirect('lista_evaluaciones')
    return render_con_contexto(request, 'core/evaluaciones/eliminar.html', {'evaluacion': evaluacion})


# =============================================================================
# SISTEMA — Calificaciones
# =============================================================================

@login_required
def lista_calificaciones(request):
    calificaciones = Calificacion.objects.select_related(
        'autor', 'vendedor_calificado__usuario', 'empresa_calificada'
    ).order_by('-fecha_calificacion')
    if request.user.rol == 'vendedor':
        calificaciones = calificaciones.filter(vendedor_calificado=request.user.vendedor)
    elif request.user.rol == 'empresa':
        calificaciones = calificaciones.filter(empresa_calificada=request.user.empresa)
    elif request.user.rol == 'comprador':
        calificaciones = calificaciones.filter(autor=request.user)
    if request.GET.get('es_incidencia'):
        calificaciones = calificaciones.filter(es_incidencia=True)

    # Estadísticas de resumen para Vendedor
    resumen = None
    if request.user.rol == 'vendedor':
        agg = calificaciones.aggregate(
            promedio=Avg('puntuacion'),
            total=Count('id'),
        )
        resumen = {
            'promedio': round(agg['promedio'], 1) if agg['promedio'] else 0,
            'total': agg['total'],
            'estrellas': '★' * int(round(agg['promedio'] or 0)) + '☆' * (5 - int(round(agg['promedio'] or 0))),
        }

    return render_con_contexto(request, 'core/calificaciones/lista.html', {
        'calificaciones': _paginar(request, calificaciones),
        'resumen': resumen,
    })


@rol_requerido('administrador')
def lista_incidencias(request):
    incidencias = Calificacion.objects.filter(es_incidencia=True).select_related(
        'autor', 'vendedor_calificado__usuario', 'empresa_calificada'
    ).order_by('estado_incidencia', '-fecha_calificacion')
    return render_con_contexto(request, 'core/calificaciones/lista.html', {
        'calificaciones': _paginar(request, incidencias),
        'es_incidencias_view': True,
    })


@rol_requerido('administrador')
def cerrar_incidencia(request, pk):
    calificacion = get_object_or_404(Calificacion, pk=pk, es_incidencia=True)
    if request.method == 'POST':
        resolucion = request.POST.get('resolucion', '').strip()
        devolucion_autorizada = request.POST.get('devolucion_autorizada') == 'on'
        if not resolucion:
            messages.error(request, "Debes indicar cómo se resolvió la incidencia.")
        else:
            calificacion.devolucion_autorizada = devolucion_autorizada
            calificacion.cerrar_incidencia(resolucion)
            
            if calificacion.pedido:
                _notificar(
                    calificacion.pedido.empresa.usuario, "Incidencia cerrada",
                    f"Se resolvió la incidencia del pedido {calificacion.pedido.numero_pedido}. Resolución: {resolucion}"
                )
                if calificacion.pedido.vendedor:
                    _notificar(
                        calificacion.pedido.vendedor.usuario, "Incidencia cerrada",
                        f"Se resolvió la incidencia del pedido {calificacion.pedido.numero_pedido}. Resolución: {resolucion}"
                      )
            messages.success(request, "Incidencia cerrada correctamente.")
    return redirect('detalle_calificacion', pk=calificacion.pk)


@rol_requerido('comprador')
def crear_calificacion(request):
    """
    Uso contextual (`?pedido=<id>&tipo=empresa|vendedor`): se llega desde el detalle
    de un pedido entregado; se bloquea el objetivo de la calificación al de ese pedido
    y se evita duplicar la reseña. No se permite crear sin pedido.
    """
    pedido_id = request.GET.get('pedido') or request.POST.get('pedido')
    tipo = request.GET.get('tipo') or request.POST.get('tipo')
    
    if not pedido_id or not tipo:
        messages.error(request, "Debes seleccionar un pedido entregado para calificar.")
        return redirect('lista_calificaciones')
        
    pedido = get_object_or_404(
        Pedido, pk=pedido_id, comprador=request.user.comprador, estado='entregado'
    )
    if tipo not in ('empresa', 'vendedor'):
        raise Http404("Tipo de calificación no válido.")
    if tipo == 'vendedor' and not pedido.vendedor:
        messages.error(request, "Este pedido no tiene un vendedor asociado para calificar.")
        return redirect('detalle_pedido', pk=pedido.pk)
    if Calificacion.objects.filter(pedido=pedido, tipo_calificado=tipo).exists():
        messages.info(request, "Ya calificaste esto para este pedido.")
        return redirect('detalle_pedido', pk=pedido.pk)

    form = CalificacionForm(request.POST or None)
    form.fields.pop('tipo_calificado', None)
    form.fields.pop('vendedor_calificado', None)
    form.fields.pop('empresa_calificada', None)

    if request.method == 'POST' and form.is_valid():
        calificacion = form.save(commit=False)
        calificacion.autor = request.user
        calificacion.pedido = pedido
        calificacion.tipo_calificado = tipo
        if tipo == 'vendedor':
            calificacion.vendedor_calificado = pedido.vendedor
        else:
            calificacion.empresa_calificada = pedido.empresa
        calificacion.save()
        messages.success(request, "Calificación registrada con éxito. ¡Gracias por tu opinión!")
        return redirect('detalle_calificacion', pk=calificacion.pk)

    return render_con_contexto(request, 'core/calificaciones/crear.html', {
        'form': form,
        'pedido': pedido,
        'tipo': tipo,
    })


@login_required
def detalle_calificacion(request, pk):
    calificacion = get_object_or_404(Calificacion, pk=pk)
    return render_con_contexto(request, 'core/calificaciones/detalle.html', {'calificacion': calificacion})


@rol_requerido('administrador')
def eliminar_calificacion(request, pk):
    calificacion = get_object_or_404(Calificacion, pk=pk)
    if request.method == 'POST':
        calificacion.delete()
        messages.success(request, "Calificación eliminada correctamente.")
        return redirect('lista_calificaciones')
    return render_con_contexto(request, 'core/calificaciones/eliminar.html', {'calificacion': calificacion})


# =============================================================================
# SISTEMA — Notificaciones
# =============================================================================

@login_required
def lista_notificaciones(request):
    notificaciones = request.user.notificaciones.all()
    return render_con_contexto(request, 'core/notificaciones/lista.html', {
        'notificaciones': _paginar(request, notificaciones, 15)
    })


@rol_requerido('administrador')
def crear_notificacion(request):
    form = NotificacionForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Notificación enviada correctamente.")
        return redirect('lista_notificaciones')
    return render_con_contexto(request, 'core/notificaciones/crear.html', {'form': form})


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
    return render_con_contexto(request, 'core/notificaciones/eliminar.html', {'notificacion': notificacion})


# =============================================================================
# REPORTES (exclusivo Administrador)
# =============================================================================

@rol_requerido('administrador')
def reportes(request):
    ventas_totales = Pedido.objects.filter(
        estado__in=ESTADOS_VENTA
    ).aggregate(t=Sum('total'))['t'] or 0

    empresas_mas_activas = Empresa.objects.annotate(
        total_pedidos=Count('pedidos')
    ).order_by('-total_pedidos')[:5]

    vendedores_top_comisiones = Vendedor.objects.annotate(
        total_comisiones=Sum('comisiones__monto_comision', filter=Q(comisiones__estado='pagada'))
    ).filter(total_comisiones__gt=0).order_by('-total_comisiones')[:5]

    productos_mas_vendidos = Producto.objects.annotate(
        unidades_vendidas=Sum('detalles_pedido__cantidad')
    ).filter(unidades_vendidas__gt=0).order_by('-unidades_vendidas')[:5]

    hace_30_dias = timezone.now() - timezone.timedelta(days=30)
    empresas_inactivas = Empresa.objects.filter(estado='aprobado').annotate(
        ultimo_pedido=Max('pedidos__fecha_creacion')
    ).filter(Q(ultimo_pedido__isnull=True) | Q(ultimo_pedido__lt=hace_30_dias))

    contexto = {
        'ventas_totales': ventas_totales,
        'total_pedidos': Pedido.objects.count(),
        'total_comisiones_pagadas': Comision.objects.filter(estado='pagada').aggregate(
            t=Sum('monto_comision')
        )['t'] or 0,
        'empresas_mas_activas': empresas_mas_activas,
        'vendedores_top_comisiones': vendedores_top_comisiones,
        'productos_mas_vendidos': productos_mas_vendidos,
        'stock_bajo_global': Inventario.objects.select_related('producto__empresa').filter(
            stock_actual__lte=F('stock_minimo')
        )[:10],
        'pedidos_cancelados': Pedido.objects.filter(estado='cancelado').order_by('-fecha_creacion')[:10],
        'total_pedidos_cancelados': Pedido.objects.filter(estado='cancelado').count(),
        'pagos_pendientes': Pago.objects.filter(estado='pendiente').select_related(
            'pedido__comprador__usuario'
        )[:10],
        'empresas_inactivas': empresas_inactivas[:10],
    }
    return render_con_contexto(request, 'core/reportes/index.html', contexto)


@rol_requerido('empresa')
def estadisticas_empresa(request):
    empresa = request.user.empresa
    productos_qs = empresa.productos.filter(activo=True).annotate(
        unidades_vendidas=Coalesce(Sum('detalles_pedido__cantidad'), 0)
    )
    ciudades_mayor_venta = Pedido.objects.filter(
        empresa=empresa, estado__in=ESTADOS_VENTA
    ).exclude(comprador__ciudad='').values('comprador__ciudad').annotate(
        total_ventas=Sum('total')
    ).order_by('-total_ventas')[:5]

    contexto = {
        'productos_mas_vendidos': productos_qs.order_by('-unidades_vendidas')[:5],
        'productos_menos_vendidos': productos_qs.order_by('unidades_vendidas')[:5],
        'ciudades_mayor_venta': ciudades_mayor_venta,
    }
    return render_con_contexto(request, 'core/estadisticas/empresa.html', contexto)


# =============================================================================
# MI CUENTA
# =============================================================================

@login_required
def mi_cuenta(request):
    perfil_form = None
    if request.user.rol == 'empresa' and hasattr(request.user, 'empresa'):
        perfil_form = EmpresaForm(request.POST or None, instance=request.user.empresa)
        perfil_form.fields.pop('estado', None)
    elif request.user.rol == 'vendedor' and hasattr(request.user, 'vendedor'):
        perfil_form = VendedorForm(request.POST or None, instance=request.user.vendedor)
        perfil_form.fields.pop('estado_aprobacion', None)
        perfil_form.fields.pop('empresas_aprobadoras', None)
    elif request.user.rol == 'comprador' and hasattr(request.user, 'comprador'):
        perfil_form = CompradorForm(request.POST or None, instance=request.user.comprador)
        perfil_form.fields.pop('limite_credito', None)
    elif request.user.rol == 'administrador' and hasattr(request.user, 'administrador'):
        perfil_form = AdministradorPerfilForm(request.POST or None, instance=request.user.administrador)

    usuario_form = PerfilUsuarioForm(request.POST or None, instance=request.user)

    if request.method == 'POST':
        usuario_valido = usuario_form.is_valid()
        perfil_valido = perfil_form.is_valid() if perfil_form else True
        if usuario_valido and perfil_valido:
            usuario_form.save()
            if perfil_form:
                perfil_form.save()
            messages.success(request, "Tu perfil se actualizó correctamente.")
            return redirect('mi_cuenta')

    return render_con_contexto(request, 'core/cuenta/mi_cuenta.html', {
        'usuario_form': usuario_form, 'perfil_form': perfil_form,
    })


@login_required
def cambiar_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            usuario = form.save()
            update_session_auth_hash(request, usuario)
            messages.success(request, "Contraseña actualizada correctamente.")
            return redirect('mi_cuenta')
    else:
        form = PasswordChangeForm(request.user)
    return render_con_contexto(request, 'core/cuenta/cambiar_password.html', {'form': form})

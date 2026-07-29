from decimal import Decimal

from django.db import models
from django.db.models import Sum, Count, Q
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


# =============================================================================
# CHOICES (listas de opciones)
# =============================================================================

ESTADO_APROBACION = [
    ('pendiente',   'Pendiente'),
    ('aprobado',    'Aprobado'),
    ('rechazado',   'Rechazado'),
    ('suspendido',  'Suspendido'),
    ('bloqueado',   'Bloqueado'),
]

ESTADO_PEDIDO = [
    ('pendiente',  'Pendiente'),
    ('aceptado',   'Aceptado'),
    ('preparando', 'Preparando'),
    ('despachado', 'Despachado'),
    ('en_camino',  'En camino'),
    ('entregado',  'Entregado'),
    ('rechazado',  'Rechazado'),
    ('cancelado',  'Cancelado'),
]

ESTADO_SOLICITUD_COLABORACION = [
    ('pendiente', 'Pendiente'),
    ('aceptada',  'Aceptada'),
    ('rechazada', 'Rechazada'),
]

ESTADO_INCIDENCIA = [
    ('', 'No es incidencia'),
    ('abierta', 'Abierta'),
    ('cerrada', 'Cerrada'),
]

ESTADO_PAGO = [
    ('pendiente', 'Pendiente'),
    ('validado',  'Validado'),
    ('rechazado', 'Rechazado'),
]

TIPO_PAGO = [
    ('parcial', 'Parcial (50%)'),
    ('total',   'Total (100%)'),
]

ESTADO_COMISION = [
    ('pendiente', 'Pendiente'),
    ('pagada',    'Pagada'),
    ('anulada',   'Anulada'),
]

ESTADO_SUSCRIPCION = [
    ('activa',    'Activa'),
    ('vencida',   'Vencida'),
    ('cancelada', 'Cancelada'),
]

TIPO_PLAN = [
    ('mensual',  'Mensual'),
    ('anual',    'Anual'),
    ('comision', 'Por Comisión'),
]

# Planes predefinidos que una empresa puede contratar por sí misma (sin tocar
# precio/comisión). El administrador sigue teniendo control total vía CRUD.
PLANES_SUSCRIPCION = {
    'mensual': {
        'nombre': 'Mensual', 'precio': Decimal('29.99'), 'comision': 6.0,
        'descripcion': 'Pago mes a mes, sin permanencia.',
    },
    'anual': {
        'nombre': 'Anual', 'precio': Decimal('299.99'), 'comision': 4.0,
        'descripcion': 'Ahorra pagando el año completo por adelantado.',
    },
    'comision': {
        'nombre': 'Por comisión', 'precio': Decimal('0.00'), 'comision': 10.0,
        'descripcion': 'Sin cuota fija: solo pagas comisión por cada venta.',
    },
}

TIPO_CALIFICADO = [
    ('vendedor', 'Vendedor'),
    ('empresa',  'Empresa'),
]

TIPO_NOTIFICACION = [
    ('pedido',     'Pedido'),
    ('pago',       'Pago'),
    ('inventario', 'Inventario'),
    ('general',    'General'),
]

NIVEL_FIDELIZACION = [
    ('bronce',   'Bronce'),
    ('plata',    'Plata'),
    ('oro',      'Oro'),
    ('diamante', 'Diamante'),
]

# Puntos mínimos acumulados para alcanzar cada nivel (1 punto ≈ $1 gastado).
UMBRALES_NIVEL = {
    'bronce': 0,
    'plata': 500,
    'oro': 1500,
    'diamante': 4000,
}

ROL_USUARIO = [
    ('empresa',       'Empresa'),
    ('vendedor',      'Vendedor'),
    ('comprador',     'Comprador'),
    ('administrador', 'Administrador'),
]


# =============================================================================
# CAPA: USUARIOS
# =============================================================================

class Usuario(AbstractUser):
    email    = models.EmailField(unique=True)
    telefono = models.CharField(max_length=20, blank=True)
    rol      = models.CharField(max_length=20, choices=ROL_USUARIO)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    REQUIRED_FIELDS = ['email', 'rol']

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return "%s - %s (%s)" % (self.get_full_name(), self.email, self.rol)

    def get_nombre_completo(self):
        return self.get_full_name()

    def es_empresa(self):
        return self.rol == 'empresa'

    def es_vendedor(self):
        return self.rol == 'vendedor'

    def es_comprador(self):
        return self.rol == 'comprador'

    def es_administrador(self):
        return self.rol == 'administrador'


class Empresa(models.Model):
    usuario             = models.OneToOneField(Usuario, on_delete=models.CASCADE,
                                               related_name='empresa')
    ruc                 = models.CharField(max_length=13, unique=True)
    razon_social        = models.CharField(max_length=200)
    representante_legal = models.CharField(max_length=200)
    direccion           = models.TextField()
    logo_url            = models.URLField(blank=True)
    estado              = models.CharField(max_length=20, choices=ESTADO_APROBACION,
                                           default='pendiente')
    motivo_rechazo      = models.TextField(blank=True)
    tiempo_entrega_dias = models.PositiveIntegerField(default=2)
    fecha_verificacion  = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'

    def __str__(self):
        return "%s - RUC: %s" % (self.razon_social, self.ruc)

    def esta_activa(self):
        """Verifica si la empresa está aprobada y activa."""
        return self.estado == 'aprobado'

    def get_tipo_ruc(self):
        """
        Retorna el tipo de contribuyente según el tercer dígito del RUC.
        En Ecuador: 0-5 = persona natural, 6 = entidad pública, 9 = sociedad.
        """
        if len(self.ruc) < 3:
            return "RUC inválido"
        tercer_digito = int(self.ruc[2])
        if tercer_digito <= 5:
            return "Persona Natural"
        elif tercer_digito == 6:
            return "Entidad Pública"
        elif tercer_digito == 9:
            return "Sociedad / Empresa"
        return "Desconocido"


class Vendedor(models.Model):
    usuario               = models.OneToOneField(Usuario, on_delete=models.CASCADE,
                                                 related_name='vendedor')
    numero_identidad      = models.CharField(max_length=20, unique=True)
    calificacion_promedio = models.FloatField(default=0.0)
    estado_aprobacion     = models.CharField(max_length=20, choices=ESTADO_APROBACION,
                                             default='pendiente')
    motivo_rechazo        = models.TextField(blank=True)
    experiencia           = models.TextField(blank=True, default='')
    empresas_aprobadoras  = models.ManyToManyField(Empresa, blank=True,
                                                   related_name='vendedores_aprobados')

    class Meta:
        verbose_name = 'Vendedor'
        verbose_name_plural = 'Vendedores'

    def __str__(self):
        return "%s - Identidad: %s (%s)" % (
            self.usuario.get_nombre_completo(),
            self.numero_identidad,
            self.estado_aprobacion
        )

    def esta_aprobado(self):
        """Verifica si el vendedor está aprobado."""
        return self.estado_aprobacion == 'aprobado'

    def get_calificacion_label(self):
        """
        Retorna una etiqueta descriptiva según el promedio de calificación.
        Escala de 1 a 5 estrellas.
        """
        if self.calificacion_promedio >= 4.5:
            return "Excelente"
        elif self.calificacion_promedio >= 3.5:
            return "Bueno"
        elif self.calificacion_promedio >= 2.5:
            return "Regular"
        else:
            return "Deficiente"


class SolicitudColaboracion(models.Model):
    """Solicitud de un vendedor para comercializar los productos de una empresa."""
    vendedor         = models.ForeignKey(Vendedor, on_delete=models.CASCADE,
                                         related_name='solicitudes_colaboracion')
    empresa          = models.ForeignKey(Empresa, on_delete=models.CASCADE,
                                         related_name='solicitudes_colaboracion')
    estado           = models.CharField(max_length=20, choices=ESTADO_SOLICITUD_COLABORACION,
                                        default='pendiente')
    motivo_rechazo   = models.TextField(blank=True)
    fecha_solicitud  = models.DateTimeField(auto_now_add=True)
    fecha_respuesta  = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Solicitud de colaboración'
        verbose_name_plural = 'Solicitudes de colaboración'
        unique_together = [('vendedor', 'empresa')]

    def __str__(self):
        return "%s -> %s (%s)" % (
            self.vendedor.usuario.get_nombre_completo(), self.empresa.razon_social, self.estado
        )

    def esta_pendiente(self):
        return self.estado == 'pendiente'


class Comprador(models.Model):
    usuario           = models.OneToOneField(Usuario, on_delete=models.CASCADE,
                                             related_name='comprador')
    tipo_negocio      = models.CharField(max_length=100)
    ruc               = models.CharField(max_length=13, blank=True)
    ciudad            = models.CharField(max_length=100, blank=True)
    direccion_entrega = models.TextField()
    limite_credito    = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    calificacion_promedio = models.FloatField(default=0.0)
    puntos            = models.IntegerField(default=0)
    nivel             = models.CharField(max_length=20, choices=NIVEL_FIDELIZACION, default='bronce')

    class Meta:
        verbose_name = 'Comprador'
        verbose_name_plural = 'Compradores'

    def __str__(self):
        return "%s - %s" % (self.usuario.get_nombre_completo(), self.tipo_negocio)

    def tiene_ruc(self):
        """Verifica si el comprador tiene RUC registrado (puede emitir facturas)."""
        return self.ruc != ''

    def recalcular_nivel(self):
        """Ajusta el nivel de fidelización según los puntos acumulados."""
        nuevo_nivel = 'bronce'
        for nivel, umbral in UMBRALES_NIVEL.items():
            if self.puntos >= umbral:
                nuevo_nivel = nivel
        if nuevo_nivel != self.nivel:
            self.nivel = nuevo_nivel
            self.save()
            return True
        return False

    def puntos_para_siguiente_nivel(self):
        """Retorna los puntos que faltan para el siguiente nivel, o None si ya está en el máximo."""
        niveles_ordenados = list(UMBRALES_NIVEL.items())
        for nivel, umbral in niveles_ordenados:
            if self.puntos < umbral:
                return umbral - self.puntos
        return None


class DireccionEntrega(models.Model):
    comprador     = models.ForeignKey(Comprador, on_delete=models.CASCADE,
                                      related_name='direcciones')
    etiqueta      = models.CharField(max_length=50)
    direccion     = models.TextField()
    predeterminada = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Dirección de entrega'
        verbose_name_plural = 'Direcciones de entrega'

    def __str__(self):
        return "%s: %s" % (self.etiqueta, self.direccion)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.predeterminada:
            self.comprador.direcciones.exclude(pk=self.pk).update(predeterminada=False)


class MovimientoPuntos(models.Model):
    comprador = models.ForeignKey(Comprador, on_delete=models.CASCADE,
                                  related_name='movimientos_puntos')
    pedido    = models.ForeignKey('Pedido', on_delete=models.SET_NULL,
                                  null=True, blank=True, related_name='movimientos_puntos')
    puntos    = models.IntegerField()
    motivo    = models.CharField(max_length=200)
    fecha     = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Movimiento de puntos'
        verbose_name_plural = 'Movimientos de puntos'
        ordering = ['-fecha']

    def __str__(self):
        return "%s: %+d puntos (%s)" % (self.comprador.usuario.get_nombre_completo(), self.puntos, self.motivo)


class Administrador(models.Model):
    usuario      = models.OneToOneField(Usuario, on_delete=models.CASCADE,
                                        related_name='administrador')
    nivel_acceso = models.IntegerField(default=1)
    area_trabajo = models.CharField(max_length=100)

    class Meta:
        verbose_name = 'Administrador'
        verbose_name_plural = 'Administradores'

    def __str__(self):
        return "%s - Nivel %s - %s" % (
            self.usuario.get_nombre_completo(),
            self.nivel_acceso,
            self.area_trabajo
        )

    def tiene_acceso_total(self):
        """Nivel 3 o más = acceso completo a la plataforma."""
        return self.nivel_acceso >= 3


# =============================================================================
# CAPA: COMERCIAL — Categorías y Productos
# =============================================================================

class CategoriaProducto(models.Model):
    nombre      = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    activo      = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Categoría de producto'
        verbose_name_plural = 'Categorías de producto'

    def __str__(self):
        return "%s (%s)" % (self.nombre, "activa" if self.activo else "inactiva")

    def contar_productos(self):
        """Retorna cuántos productos activos tiene esta categoría."""
        return self.productos.filter(activo=True).count()


class Producto(models.Model):
    nombre        = models.CharField(max_length=200)
    descripcion   = models.TextField(blank=True)
    precio_base   = models.DecimalField(max_digits=12, decimal_places=2)
    precio_venta  = models.DecimalField(max_digits=12, decimal_places=2)
    unidad_medida = models.CharField(max_length=50)
    activo        = models.BooleanField(default=True)
    empresa       = models.ForeignKey(Empresa, on_delete=models.CASCADE,
                                      related_name='productos')
    categoria     = models.ForeignKey(CategoriaProducto, on_delete=models.SET_NULL,
                                      null=True, blank=True, related_name='productos')
    fecha_creacion      = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'

    def __str__(self):
        return "%s - $%s (%s)" % (self.nombre, self.precio_venta, self.empresa.razon_social)

    def get_margen(self):
        """Calcula el margen de ganancia sobre el precio base."""
        if self.precio_base > 0:
            return round((self.precio_venta - self.precio_base) / self.precio_base * 100, 2)
        return 0

    def tiene_stock(self):
        """Verifica si el producto tiene stock disponible en inventario."""
        try:
            return self.inventario.stock_actual > 0
        except Inventario.DoesNotExist:
            return False

# =============================================================================
# CAPA: INVENTARIO
# =============================================================================

class Inventario(models.Model):
    producto         = models.OneToOneField(Producto, on_delete=models.CASCADE,
                                            related_name='inventario')
    stock_actual     = models.IntegerField(default=0)
    stock_reservado  = models.IntegerField(default=0, help_text="Unidades comprometidas en pedidos aceptados pendientes de despacho")
    stock_minimo     = models.IntegerField(default=0)
    stock_maximo     = models.IntegerField(default=0)
    ubicacion        = models.CharField(max_length=200, blank=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Inventario'
        verbose_name_plural = 'Inventarios'

    def __str__(self):
        return "Inventario: %s | Stock: %s unidades" % (self.producto.nombre, self.stock_actual)

    def stock_bajo(self):
        """Retorna True si el stock actual está por debajo del mínimo."""
        return self.stock_actual <= self.stock_minimo

    def get_estado_stock(self):
        """
        Retorna el estado del stock como texto.
        Se usa para mostrar alertas en el panel de inventario (RF-04-02).
        """
        if self.stock_actual == 0:
            return "Sin stock"
        elif self.stock_actual <= self.stock_minimo:
            return "Stock bajo"
        elif self.stock_actual >= self.stock_maximo:
            return "Stock lleno"
        return "Normal"


class Promocion(models.Model):
    """Promoción exclusiva que una empresa crea para compradores de cierto nivel de fidelización."""
    empresa              = models.ForeignKey(Empresa, on_delete=models.CASCADE,
                                             related_name='promociones')
    titulo               = models.CharField(max_length=200)
    descripcion          = models.TextField(blank=True)
    nivel_minimo         = models.CharField(max_length=20, choices=NIVEL_FIDELIZACION, default='bronce')
    descuento_porcentaje = models.FloatField(default=0)
    activo               = models.BooleanField(default=True)
    fecha_inicio         = models.DateField(null=True, blank=True)
    fecha_fin            = models.DateField(null=True, blank=True)
    fecha_creacion       = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Promoción'
        verbose_name_plural = 'Promociones'

    def __str__(self):
        return "%s - %s%% (%s+)" % (self.titulo, self.descuento_porcentaje, self.get_nivel_minimo_display())

    def esta_vigente(self):
        """Verifica si la promoción está activa y dentro de su rango de fechas (si tiene)."""
        if not self.activo:
            return False
        from django.utils import timezone
        hoy = timezone.now().date()
        if self.fecha_inicio and hoy < self.fecha_inicio:
            return False
        if self.fecha_fin and hoy > self.fecha_fin:
            return False
        return True


# =============================================================================
# CAPA: PLATAFORMA — Suscripciones y Comisiones
# =============================================================================

class PlanSuscripcion(models.Model):
    nombre              = models.CharField(max_length=100)
    precio              = models.DecimalField(max_digits=12, decimal_places=2)
    duracion_meses      = models.IntegerField(default=1, help_text="Duración en meses del plan")
    comision_plataforma = models.FloatField(default=5.0, help_text="Porcentaje de comisión para la plataforma")
    beneficios          = models.TextField(blank=True, help_text="Beneficios incluidos, separados por comas o líneas")
    limite_productos    = models.IntegerField(default=100, help_text="Límite máximo de productos activos")
    activo              = models.BooleanField(default=True)
    tipo                = models.CharField(max_length=20, choices=[('empresa', 'Empresa'), ('vendedor', 'Vendedor')], default='empresa')
    fecha_creacion      = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Plan de Suscripción'
        verbose_name_plural = 'Planes de Suscripción'

    def __str__(self):
        return f"{self.nombre} - ${self.precio} ({self.comision_plataforma}%)"


class Suscripcion(models.Model):
    empresa             = models.ForeignKey(Empresa, on_delete=models.CASCADE,
                                            related_name='suscripciones', null=True, blank=True)
    vendedor            = models.ForeignKey(Vendedor, on_delete=models.CASCADE,
                                            related_name='suscripciones', null=True, blank=True)
    plan                = models.ForeignKey(PlanSuscripcion, on_delete=models.PROTECT,
                                            related_name='suscripciones_empresas', null=True, blank=True)
    estado              = models.CharField(max_length=20, choices=ESTADO_SUSCRIPCION,
                                           default='activa')
    fecha_inicio        = models.DateField()
    fecha_fin           = models.DateField(null=True, blank=True)
    fecha_creacion      = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Suscripción'
        verbose_name_plural = 'Suscripciones'

    def __str__(self):
        plan_nombre = self.plan.nombre if self.plan else "Sin plan"
        entidad = self.empresa.razon_social if self.empresa else (self.vendedor.usuario.get_full_name() if self.vendedor else "Sin entidad")
        return "%s - %s (%s)" % (entidad, plan_nombre, self.estado)

    def esta_vigente(self):
        """Verifica si la suscripción está activa."""
        return self.estado == 'activa'

    def cancelar(self):
        self.estado = 'cancelada'
        self.fecha_fin = timezone.now().date()
        self.save()

    @classmethod
    def obtener_para_cancelar(cls, usuario, pk_suscripcion):
        if usuario.rol == 'empresa':
            return cls.objects.get(pk=pk_suscripcion, empresa=usuario.empresa)
        else:
            return cls.objects.get(pk=pk_suscripcion, vendedor=usuario.vendedor)

    def get_costo_mensual(self):
        """
        Retorna el costo mensual equivalente.
        Divide el precio entre la duración en meses.
        """
        if self.plan:
            if self.plan.duracion_meses > 0:
                return round(self.plan.precio / self.plan.duracion_meses, 2)
            return self.plan.precio
        return Decimal('0.00')


class Comision(models.Model):
    vendedor         = models.ForeignKey(Vendedor, on_delete=models.CASCADE,
                                         related_name='comisiones')
    pedido           = models.ForeignKey('Pedido', on_delete=models.CASCADE,
                                         related_name='comisiones')
    porcentaje       = models.FloatField()
    monto_comision   = models.DecimalField(max_digits=12, decimal_places=2)
    estado           = models.CharField(max_length=20, choices=ESTADO_COMISION,
                                        default='pendiente')
    fecha_generacion = models.DateTimeField(auto_now_add=True)
    fecha_pago       = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Comisión'
        verbose_name_plural = 'Comisiones'

    def __str__(self):
        return "Comision %s%% - $%s - %s (%s)" % (
            self.porcentaje,
            self.monto_comision,
            self.vendedor.usuario.get_nombre_completo(),
            self.estado
        )

    def esta_pagada(self):
        """Verifica si la comisión ya fue pagada al vendedor."""
        return self.estado == 'pagada'

    @classmethod
    def obtener_comisiones_y_resumen(cls, usuario, estado=None, orden='-fecha_generacion'):
        comisiones = cls.objects.select_related(
            'vendedor__usuario', 'pedido__empresa'
        ).order_by('-fecha_generacion')

        if usuario.rol == 'vendedor':
            comisiones = comisiones.filter(vendedor=usuario.vendedor)
        elif usuario.rol == 'empresa':
            comisiones = comisiones.filter(pedido__empresa=usuario.empresa)

        resumen = comisiones.aggregate(
            pendiente=Sum('monto_comision', filter=Q(estado='pendiente')),
            pagada=Sum('monto_comision', filter=Q(estado='pagada')),
            anuladas=Count('id', filter=Q(estado='anulada')),
        )

        if estado:
            comisiones = comisiones.filter(estado=estado)

        if orden in ('-fecha_generacion', 'fecha_generacion', '-monto_comision', 'monto_comision'):
            comisiones = comisiones.order_by(orden)

        return comisiones, resumen


# =============================================================================
# CAPA: VENTAS — Pedidos, Detalles, Pagos, Facturas
# =============================================================================

class Pedido(models.Model):
    numero_pedido  = models.CharField(max_length=30, unique=True)
    estado         = models.CharField(max_length=20, choices=ESTADO_PEDIDO, default='pendiente')
    subtotal       = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    descuento      = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    iva            = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total          = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    motivo_rechazo = models.TextField(blank=True)
    direccion_entrega = models.TextField(blank=True)
    comprador      = models.ForeignKey(Comprador, on_delete=models.CASCADE,
                                       related_name='pedidos')
    vendedor       = models.ForeignKey(Vendedor, on_delete=models.SET_NULL,
                                       null=True, blank=True, related_name='pedidos')
    empresa        = models.ForeignKey(Empresa, on_delete=models.CASCADE,
                                       related_name='pedidos')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_despacho = models.DateTimeField(null=True, blank=True)
    fecha_entrega  = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Pedido'
        verbose_name_plural = 'Pedidos'

    def __str__(self):
        return "Pedido %s - %s - $%s (%s)" % (
            self.numero_pedido,
            self.comprador.usuario.get_nombre_completo(),
            self.total,
            self.estado
        )

    def esta_entregado(self):
        """Verifica si el pedido fue entregado."""
        return self.estado == 'entregado'

    def puede_cancelarse(self):
        """
        Un pedido solo se puede cancelar si aún no fue despachado (RF-05-03).
        """
        return self.estado in ['pendiente', 'aceptado', 'preparando']

    def calcular_total(self):
        """
        Suma todos los subtotales de los detalles del pedido.
        Útil para recalcular el total antes de confirmar.
        """
        detalles = self.detalles.all()
        self.subtotal = sum(d.cantidad * d.precio_unitario for d in detalles)
        self.descuento = sum(d.descuento for d in detalles)
        base_imponible = self.subtotal - self.descuento
        self.iva = round(base_imponible * Decimal('0.15'), 2)
        self.total = base_imponible + self.iva
        self.save()
        return self.total


class DetallePedido(models.Model):
    pedido          = models.ForeignKey(Pedido, on_delete=models.CASCADE,
                                        related_name='detalles')
    producto        = models.ForeignKey(Producto, on_delete=models.CASCADE,
                                        related_name='detalles_pedido')
    cantidad        = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    subtotal        = models.DecimalField(max_digits=14, decimal_places=2)
    descuento       = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        verbose_name = 'Detalle de pedido'
        verbose_name_plural = 'Detalles de pedido'

    def __str__(self):
        return "%s x%s - $%s (Pedido: %s)" % (
            self.producto.nombre,
            self.cantidad,
            self.subtotal,
            self.pedido.numero_pedido
        )

    def calcular_subtotal(self):
        """Calcula el subtotal aplicando el descuento."""
        bruto = self.cantidad * self.precio_unitario
        self.subtotal = bruto - self.descuento
        self.save()
        return self.subtotal


class Pago(models.Model):
    pedido          = models.ForeignKey(Pedido, on_delete=models.CASCADE,
                                        related_name='pagos')
    monto           = models.DecimalField(max_digits=14, decimal_places=2)
    tipo            = models.CharField(max_length=20, choices=TIPO_PAGO)
    estado          = models.CharField(max_length=20, choices=ESTADO_PAGO, default='pendiente')
    metodo_pago     = models.CharField(max_length=100)
    referencia_pago = models.CharField(max_length=200, blank=True)
    comprobante     = models.FileField(upload_to='pagos_comprobantes/', null=True, blank=True)
    fecha_pago      = models.DateTimeField(auto_now_add=True)
    fecha_validacion = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Pago'
        verbose_name_plural = 'Pagos'

    def __str__(self):
        return "Pago %s - $%s - %s (%s)" % (
            self.tipo, self.monto, self.metodo_pago, self.estado
        )

    def esta_validado(self):
        """Verifica si el pago fue validado por la pasarela."""
        return self.estado == 'validado'

    def es_pago_parcial(self):
        """Retorna True si el pago es del 50% (anticipo)."""
        return self.tipo == 'parcial'


class Factura(models.Model):
    pedido         = models.OneToOneField(Pedido, on_delete=models.CASCADE,
                                          related_name='factura', null=True, blank=True)
    numero_factura = models.CharField(max_length=50, unique=True)
    fecha_emision  = models.DateTimeField(auto_now_add=True)
    subtotal       = models.DecimalField(max_digits=14, decimal_places=2)
    iva            = models.DecimalField(max_digits=12, decimal_places=2)
    total          = models.DecimalField(max_digits=14, decimal_places=2)
    estado_sri     = models.CharField(max_length=50, blank=True)
    clave_acceso   = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = 'Factura'
        verbose_name_plural = 'Facturas'

    def __str__(self):
        return "Factura %s - $%s - SRI: %s" % (
            self.numero_factura, self.total, self.estado_sri or "pendiente"
        )

    def esta_autorizada(self):
        """Verifica si la factura fue autorizada por el SRI."""
        return self.estado_sri == 'AUTORIZADO'

    def calcular_iva(self):
        """
        Calcula el IVA sobre el subtotal.
        En Ecuador la tarifa vigente es 15% (puede ajustarse).
        """
        self.iva = round(self.subtotal * Decimal('0.15'), 2)
        self.total = round(self.subtotal + self.iva, 2)
        self.save()
        return self.iva


# =============================================================================
# CAPA: CAPACITACIÓN — Cursos y Evaluaciones
# =============================================================================

class Curso(models.Model):
    empresa        = models.ForeignKey(Empresa, on_delete=models.CASCADE,
                                       related_name='cursos', null=True, blank=True)
    titulo         = models.CharField(max_length=200)
    descripcion    = models.TextField(blank=True)
    duracion_horas = models.FloatField()
    url_contenido  = models.URLField(blank=True)
    imagen         = models.URLField(blank=True, null=True, help_text="URL de la imagen del curso (opcional)")
    plan_requerido = models.ForeignKey('PlanSuscripcion', on_delete=models.SET_NULL, null=True, blank=True, related_name='cursos')
    activo         = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    vendedores     = models.ManyToManyField(Vendedor, blank=True,
                                            related_name='cursos_asignados')

    class Meta:
        verbose_name = 'Curso'
        verbose_name_plural = 'Cursos'

    def __str__(self):
        return "%s - %sh" % (
            self.titulo,
            self.duracion_horas
        )

    def contar_inscritos(self):
        """Retorna cuántos vendedores están asignados al curso."""
        return self.vendedores.count()


class Evaluacion(models.Model):
    vendedor         = models.ForeignKey(Vendedor, on_delete=models.CASCADE,
                                         related_name='evaluaciones')
    curso            = models.ForeignKey(Curso, on_delete=models.CASCADE,
                                         related_name='evaluaciones')
    puntaje_obtenido = models.FloatField()
    puntaje_minimo   = models.FloatField()
    aprobado         = models.BooleanField(default=False)
    fecha_rendicion  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Evaluación'
        verbose_name_plural = 'Evaluaciones'

    def __str__(self):
        estado = "Aprobado" if self.aprobado else "Reprobado"
        return "%s - %s: %s/%s (%s)" % (
            self.vendedor.usuario.get_nombre_completo(),
            self.curso.titulo,
            self.puntaje_obtenido,
            self.puntaje_minimo,
            estado
        )

    def verificar_aprobacion(self):
        """
        Actualiza el campo aprobado comparando puntaje obtenido vs mínimo.
        Llamar después de registrar el puntaje.
        """
        self.aprobado = self.puntaje_obtenido >= self.puntaje_minimo
        self.save()
        return self.aprobado


# =============================================================================
# CALIFICACIONES Y NOTIFICACIONES
# =============================================================================

class Calificacion(models.Model):
    autor               = models.ForeignKey(Usuario, on_delete=models.SET_NULL,
                                            null=True, related_name='calificaciones_emitidas')
    pedido              = models.ForeignKey('Pedido', on_delete=models.SET_NULL,
                                            null=True, blank=True, related_name='calificaciones')
    tipo_calificado     = models.CharField(max_length=20, choices=TIPO_CALIFICADO)
    vendedor_calificado = models.ForeignKey(Vendedor, on_delete=models.CASCADE,
                                            null=True, blank=True, related_name='calificaciones')
    empresa_calificada  = models.ForeignKey(Empresa, on_delete=models.CASCADE,
                                            null=True, blank=True, related_name='calificaciones')
    puntuacion          = models.FloatField()
    comentario          = models.TextField(blank=True)
    es_incidencia       = models.BooleanField(default=False)
    estado_incidencia   = models.CharField(max_length=20, choices=ESTADO_INCIDENCIA, blank=True, default='')
    resolucion          = models.TextField(blank=True)
    devolucion_autorizada = models.BooleanField(default=False)
    fecha_calificacion  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Calificación'
        verbose_name_plural = 'Calificaciones'

    def __str__(self):
        objetivo = self.vendedor_calificado or self.empresa_calificada
        return "Calificacion %s/5 a %s (%s)" % (
            self.puntuacion, objetivo, self.tipo_calificado
        )

    def get_estrellas(self):
        """
        Convierte la puntuación numérica a representación de estrellas.
        Ejemplo: 4.0 → '★★★★☆'
        """
        llenas = int(self.puntuacion)
        vacias = 5 - llenas
        return '★' * llenas + '☆' * vacias

    def es_positiva(self):
        """Una calificación >= 3 se considera positiva."""
        return self.puntuacion >= 3

    def save(self, *args, **kwargs):
        if self.es_incidencia and not self.estado_incidencia:
            self.estado_incidencia = 'abierta'
        super().save(*args, **kwargs)

    def cerrar_incidencia(self, resolucion):
        """Cierra la incidencia registrando cómo se resolvió (incluye devoluciones aprobadas)."""
        self.estado_incidencia = 'cerrada'
        self.resolucion = resolucion
        self.save()


class Notificacion(models.Model):
    destinatario  = models.ForeignKey(Usuario, on_delete=models.CASCADE,
                                      related_name='notificaciones')
    tipo          = models.CharField(max_length=20, choices=TIPO_NOTIFICACION)
    titulo        = models.CharField(max_length=200)
    mensaje       = models.TextField()
    leida         = models.BooleanField(default=False)
    fecha_envio   = models.DateTimeField(auto_now_add=True)
    fecha_lectura = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-fecha_envio']
        verbose_name = 'Notificación'
        verbose_name_plural = 'Notificaciones'

    def __str__(self):
        estado = "leida" if self.leida else "no leida"
        return "[%s] %s → %s (%s)" % (
            self.tipo,
            self.titulo,
            self.destinatario.get_nombre_completo(),
            estado
        )

    def marcar_leida(self):
        """Marca la notificación como leída y registra la fecha."""
        from django.utils import timezone
        self.leida = True
        self.fecha_lectura = timezone.now()
        self.save()
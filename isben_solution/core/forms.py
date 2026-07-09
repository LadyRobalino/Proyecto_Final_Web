from django import forms
from django.utils.translation import gettext_lazy as _
from .models import (
    Empresa, Vendedor, Comprador,
    CategoriaProducto, Producto, Inventario,
    Pedido, DetallePedido, Pago, Factura,
    Suscripcion, Comision,
    Curso, Evaluacion, Calificacion, Notificacion
)

# ==========================
# Empresas 
# ==========================

class EmpresaForm(forms.ModelForm):
    class Meta:
        model = Empresa
        fields = [
            'ruc', 'razon_social', 'representante_legal',
            'direccion', 'logo_url', 'estado'
        ]
        widgets = {
            'ruc':                 forms.TextInput(attrs={'class': 'form-control'}),
            'razon_social':        forms.TextInput(attrs={'class': 'form-control'}),
            'representante_legal': forms.TextInput(attrs={'class': 'form-control'}),
            'direccion':           forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'logo_url':            forms.URLInput(attrs={'class': 'form-control'}),
            'estado':              forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'ruc':                 _('Ingrese RUC por favor'),
            'razon_social':        _('Ingrese razón social por favor'),
            'representante_legal': _('Ingrese representante legal por favor'),
            'direccion':           _('Ingrese dirección por favor'),
            'logo_url':            _('Ingrese URL del logo por favor'),
            'estado':              _('Seleccione el estado por favor'),
        }

    def clean_ruc(self):
        valor = self.cleaned_data['ruc']
        if len(valor) != 13:
            raise forms.ValidationError("Ingrese un RUC válido con 13 dígitos")
        return valor

    def clean_razon_social(self):
        valor = self.cleaned_data['razon_social']
        num_palabras = len(valor.split())
        if num_palabras < 2:
            raise forms.ValidationError("Ingrese una razón social completa (mínimo 2 palabras)")
        return valor

    def clean_representante_legal(self):
        valor = self.cleaned_data['representante_legal']
        num_palabras = len(valor.split())
        if num_palabras < 2:
            raise forms.ValidationError("Ingrese dos nombres y apellidos por favor")
        return valor


# ==========================
# Vendedores  (RF-06)
# ==========================

# ==========================
# Vendedores  (RF-06)
# ==========================

class VendedorForm(forms.ModelForm):
    class Meta:
        model = Vendedor
        # Cambiado a 'estado_aprobacion' con barra baja para que coincida con tu base de datos
        fields = ['numero_identidad', 'estado_aprobacion', 'empresas_aprobadoras']
        widgets = {
            'numero_identidad':     forms.TextInput(attrs={'class': 'form-control'}),
            'estado_aprobacion':    forms.Select(attrs={'class': 'form-select'}),
            'empresas_aprobadoras': forms.SelectMultiple(attrs={'class': 'form-select'}),
        }
        labels = {
            'numero_identidad':     _('Ingrese número de identidad por favor'),
            'estado_aprobacion':    _('Seleccione el estado de aprobación por favor'),
            'empresas_aprobadoras': _('Seleccione las empresas aprobadoras por favor'),
        }

    def clean_numero_identidad(self):
        valor = self.cleaned_data['numero_identidad']
        if len(valor) != 10:
            raise forms.ValidationError("Ingrese cédula con 10 dígitos")
        return valor

# ==========================
# Compradores  (RF-01)
# ==========================

class CompradorForm(forms.ModelForm):
    class Meta:
        model = Comprador
        fields = ['tipo_negocio', 'ruc', 'direccion_entrega', 'limite_credito']
        widgets = {
            'tipo_negocio':      forms.TextInput(attrs={'class': 'form-control'}),
            'ruc':               forms.TextInput(attrs={'class': 'form-control'}),
            'direccion_entrega': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'limite_credito':    forms.NumberInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'tipo_negocio':      _('Ingrese tipo de negocio por favor'),
            'ruc':               _('Ingrese RUC (opcional) por favor'),
            'direccion_entrega': _('Ingrese dirección de entrega por favor'),
            'limite_credito':    _('Ingrese límite de crédito por favor'),
        }

    def clean_ruc(self):
        valor = self.cleaned_data['ruc']
        if valor and len(valor) != 13:
            raise forms.ValidationError("Si ingresa un RUC, debe contener exactamente 13 dígitos")
        return valor


# ==========================
# Categorías  (RF-03-05)
# ==========================

class CategoriaProductoForm(forms.ModelForm):
    class Meta:
        model = CategoriaProducto
        fields = ['nombre', 'descripcion', 'activo']
        widgets = {
            'nombre':      forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'activo':      forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'nombre':      _('Ingrese nombre de la categoría por favor'),
            'descripcion': _('Ingrese descripción por favor'),
            'activo':      _('Marque si está activa por favor'),
        }


# ==========================
# Productos  (RF-03)
# ==========================

class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = [
            'nombre', 'descripcion', 'precio_base', 'precio_venta',
            'unidad_medida', 'activo', 'empresa', 'categoria'
        ]
        widgets = {
            'nombre':        forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion':   forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'precio_base':   forms.NumberInput(attrs={'class': 'form-control'}),
            'precio_venta':  forms.NumberInput(attrs={'class': 'form-control'}),
            'unidad_medida': forms.TextInput(attrs={'class': 'form-control'}),
            'activo':        forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'empresa':       forms.Select(attrs={'class': 'form-select'}),
            'categoria':     forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'nombre':        _('Ingrese nombre del producto por favor'),
            'descripcion':   _('Ingrese descripción por favor'),
            'precio_base':   _('Ingrese precio base por favor'),
            'precio_venta':  _('Ingrese precio de venta por favor'),
            'unidad_medida': _('Ingrese unidad de medida por favor'),
            'activo':        _('Marque si está activo por favor'),
            'empresa':       _('Seleccione la empresa por favor'),
            'categoria':     _('Seleccione la categoría por favor'),
        }


class ProductoEmpresaForm(forms.ModelForm):
    def __init__(self, empresa, *args, **kwargs):
        super(ProductoEmpresaForm, self).__init__(*args, **kwargs)
        self.initial['empresa'] = empresa
        self.fields["empresa"].widget = forms.widgets.HiddenInput()

    class Meta:
        model = Producto
        fields = [
            'nombre', 'descripcion', 'precio_base', 'precio_venta',
            'unidad_medida', 'activo', 'empresa', 'categoria'
        ]
        widgets = {
            'nombre':        forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion':   forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'precio_base':   forms.NumberInput(attrs={'class': 'form-control'}),
            'precio_venta':  forms.NumberInput(attrs={'class': 'form-control'}),
            'unidad_medida': forms.TextInput(attrs={'class': 'form-control'}),
            'activo':        forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'categoria':     forms.Select(attrs={'class': 'form-select'}),
        }


# ==========================
# Inventario  (RF-04)
# ==========================

# ==========================
# Inventario  (RF-04)
# ==========================

class InventarioForm(forms.ModelForm):
    class Meta:
        model = Inventario
        # Usamos los nombres de campos reales de tu modelo en la base de datos
        fields = ['stock_actual', 'stock_minimo', 'stock_maximo', 'ubicacion']
        widgets = {
            'stock_actual': forms.NumberInput(attrs={'class': 'form-control'}),
            'stock_minimo': forms.NumberInput(attrs={'class': 'form-control'}),
            'stock_maximo': forms.NumberInput(attrs={'class': 'form-control'}),
            'ubicacion':    forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'stock_actual': _('Ingrese stock actual por favor'),
            'stock_minimo': _('Ingrese stock mínimo por favor'),
            'stock_maximo': _('Ingrese stock máximo por favor'),
            'ubicacion':    _('Ingrese ubicación en bodega por favor'),
        }

# ==========================
# Pedidos  (RF-05)
# ==========================

class PedidoForm(forms.ModelForm):
    class Meta:
        model = Pedido
        fields = ['numero_pedido', 'estado', 'comprador', 'vendedor', 'empresa']
        widgets = {
            'numero_pedido': forms.TextInput(attrs={'class': 'form-control'}),
            'estado':        forms.Select(attrs={'class': 'form-select'}),
            'comprador':     forms.Select(attrs={'class': 'form-select'}),
            'vendedor':      forms.Select(attrs={'class': 'form-select'}),
            'empresa':       forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'numero_pedido': _('Ingrese el número de pedido por favor'),
            'estado':        _('Seleccione el estado del pedido por favor'),
            'comprador':     _('Seleccione el comprador por favor'),
            'vendedor':      _('Seleccione el vendedor por favor'),
            'empresa':       _('Seleccione la empresa por favor'),
        }


class DetallePedidoForm(forms.ModelForm):
    def __init__(self, pedido, *args, **kwargs):
        super(DetallePedidoForm, self).__init__(*args, **kwargs)
        self.initial['pedido'] = pedido
        self.fields["pedido"].widget = forms.widgets.HiddenInput()

    class Meta:
        model = DetallePedido
        fields = ['pedido', 'producto', 'cantidad', 'precio_unitario', 'descuento']
        widgets = {
            'producto':        forms.Select(attrs={'class': 'form-select'}),
            'content':         forms.NumberInput(attrs={'class': 'form-control'}),
            'precio_unitario': forms.NumberInput(attrs={'class': 'form-control'}),
            'descuento':       forms.NumberInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'producto':        _('Seleccione el producto por favor'),
            'cantidad':        _('Ingrese cantidad por favor'),
            'precio_unitario': _('Ingrese precio unitario por favor'),
            'descuento':       _('Ingrese descuento por favor'),
        }


# ==========================
# Pagos  (RF-08)
# ==========================

class PagoForm(forms.ModelForm):
    class Meta:
        model = Pago
        fields = ['pedido', 'monto', 'tipo', 'metodo_pago', 'referencia_pago']
        widgets = {
            'pedido':          forms.Select(attrs={'class': 'form-select'}),
            'monto':           forms.NumberInput(attrs={'class': 'form-control'}),
            'tipo':            forms.Select(attrs={'class': 'form-select'}),
            'metodo_pago':     forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'PayPhone, Kushki, transferencia...'}),
            'referencia_pago': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'pedido':          _('Seleccione el pedido por favor'),
            'monto':           _('Ingrese el monto por favor'),
            'tipo':            _('Seleccione el tipo de pago por favor'),
            'metodo_pago':     _('Ingrese el método de pago por favor'),
            'referencia_pago': _('Ingrese la referencia de pago por favor'),
        }


# ==========================
# Comisiones  (RF-09)
# ==========================

class ComisionForm(forms.ModelForm):
    class Meta:
        model = Comision
        fields = ['vendedor', 'pedido', 'porcentaje', 'monto_comision', 'estado']
        widgets = {
            'vendedor':       forms.Select(attrs={'class': 'form-select'}),
            'pedido':         forms.Select(attrs={'class': 'form-select'}),
            'porcentaje':     forms.NumberInput(attrs={'class': 'form-control'}),
            'monto_comision': forms.NumberInput(attrs={'class': 'form-control'}),
            'estado':         forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'vendedor':       _('Seleccione el vendedor por favor'),
            'pedido':         _('Seleccione el pedido por favor'),
            'porcentaje':     _('Ingrese el porcentaje por favor'),
            'monto_comision': _('Ingrese el monto de la comisión por favor'),
            'estado':         _('Seleccione el estado por favor'),
        }


# ==========================
# Suscripciones  (RF-11)
# ==========================
class SuscripcionForm(forms.ModelForm):
    class Meta:
        model = Suscripcion
        # Corregido con guion bajo para que coincida exactamente con tu base de datos real
        fields = [
            'empresa', 'tipo_plan', 'precio',
            'comision_plataforma', 'estado', 'fecha_inicio', 'fecha_fin'
        ]
        widgets = {
            'empresa':              forms.Select(attrs={'class': 'form-select'}),
            'tipo_plan':            forms.Select(attrs={'class': 'form-select'}),
            'precio':               forms.NumberInput(attrs={'class': 'form-control'}),
            'comision_plataforma':  forms.NumberInput(attrs={'class': 'form-control'}),
            'estado':               forms.Select(attrs={'class': 'form-select'}),
            'fecha_inicio':         forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'fecha_fin':            forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
        labels = {
            'empresa':             _('Seleccione la empresa por favor'),
            'tipo_plan':           _('Seleccione el plan por favor'),
            'precio':              _('Ingrese el precio por favor'),
            'comision_plataforma': _('Ingrese la comisión de la plataforma por favor'),
            'estado':              _('Seleccione el estado por favor'),
            'fecha_inicio':        _('Seleccione la fecha de inicio por favor'),
            'fecha_fin':           _('Seleccione la fecha de fin por favor'),
        }


# ==========================
# Cursos  (RF-07)
# ==========================

class CursoForm(forms.ModelForm):
    class Meta:
        model = Curso
        fields = ['empresa', 'titulo', 'descripcion', 'duracion_horas', 'url_contenido', 'activo', 'vendedores']
        widgets = {
            'empresa':        forms.Select(attrs={'class': 'form-select'}),
            'titulo':         forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion':    forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'duracion_horas': forms.NumberInput(attrs={'class': 'form-control'}),
            'url_contenido':  forms.URLInput(attrs={'class': 'form-control'}),
            'activo':         forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'vendedores':     forms.SelectMultiple(attrs={'class': 'form-select'}),
        }
        labels = {
            'empresa':        _('Seleccione la empresa por favor'),
            'titulo':         _('Ingrese el título del curso por favor'),
            'descripcion':    _('Ingrese la descripción por favor'),
            'duracion_horas': _('Ingrese la duración en horas por favor'),
            'url_contenido':  _('Ingrese la URL del contenido por favor'),
            'activo':         _('Marque si está activo por favor'),
            'vendedores':     _('Seleccione los vendedores asignados por favor'),
        }


# ==========================
# Evaluaciones  (RF-07-02)
# ==========================

class EvaluacionForm(forms.ModelForm):
    class Meta:
        model = Evaluacion
        fields = ['vendedor', 'curso', 'puntaje_obtenido', 'puntaje_minimo']
        widgets = {
            'vendedor':         forms.Select(attrs={'class': 'form-select'}),
            'curso':            forms.Select(attrs={'class': 'form-select'}),
            'puntaje_obtenido': forms.NumberInput(attrs={'class': 'form-control'}),
            'puntaje_minimo':   forms.NumberInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'vendedor':         _('Seleccione el vendedor por favor'),
            'curso':            _('Seleccione el curso por favor'),
            'puntaje_obtenido': _('Ingrese el puntaje obtenido por favor'),
            'puntaje_minimo':   _('Ingrese el puntaje mínimo por favor'),
        }


# ==========================
# Calificaciones  (RF-12)
# ==========================

class CalificacionForm(forms.ModelForm):
    class Meta:
        model = Calificacion
        fields = [
            'tipo_calificado', 'vendedor_calificado', 'empresa_calificada',
            'puntuacion', 'comentario', 'es_incidencia'
        ]
        widgets = {
            'tipo_calificado':     forms.Select(attrs={'class': 'form-select'}),
            'vendedor_calificado': forms.Select(attrs={'class': 'form-select'}),
            'empresa_calificada':  forms.Select(attrs={'class': 'form-select'}),
            'puntuacion':          forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 5, 'step': 0.5}),
            'comentario':          forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'es_incidencia':       forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'tipo_calificado':     _('Seleccione el tipo a calificar por favor'),
            'vendedor_calificado': _('Seleccione el vendedor por favor'),
            'empresa_calificada':  _('Seleccione la empresa por favor'),
            'puntuacion':          _('Ingrese la puntuación por favor'),
            'comentario':          _('Ingrese un comentario por favor'),
            'es_incidencia':       _('Marque si corresponde a una incidencia por favor'),
        }
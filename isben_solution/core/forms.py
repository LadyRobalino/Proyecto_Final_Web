from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import (
    Usuario, Empresa, Vendedor, Comprador, Administrador,
    CategoriaProducto, Producto, Inventario,
    Suscripcion, Comision,
    Pedido, DetallePedido, Pago, Factura,
    Curso, Evaluacion, Calificacion, Notificacion,
    ROL_USUARIO,
)


# =============================================================================
# USUARIOS Y AUTENTICACIÓN
# =============================================================================

class UsuarioBaseForm(forms.Form):
    """Base reutilizable para formularios que crean un Usuario + su perfil."""
    username = forms.CharField(max_length=150, label="Usuario")
    first_name = forms.CharField(max_length=150, label="Nombres")
    last_name = forms.CharField(max_length=150, label="Apellidos")
    email = forms.EmailField(label="Correo electrónico")
    telefono = forms.CharField(max_length=20, required=False, label="Teléfono")
    password1 = forms.CharField(widget=forms.PasswordInput, label="Contraseña")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirmar contraseña")

    def clean_username(self):
        username = self.cleaned_data['username']
        if Usuario.objects.filter(username=username).exists():
            raise ValidationError("Ese nombre de usuario ya existe.")
        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        if Usuario.objects.filter(email=email).exists():
            raise ValidationError("Ese correo ya está registrado.")
        return email

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get('password1'), cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            raise ValidationError("Las contraseñas no coinciden.")
        if p1:
            validate_password(p1)
        return cleaned

    def crear_usuario(self, rol):
        datos = self.cleaned_data
        usuario = Usuario(
            username=datos['username'],
            first_name=datos['first_name'],
            last_name=datos['last_name'],
            email=datos['email'],
            telefono=datos.get('telefono', ''),
            rol=rol,
        )
        usuario.set_password(datos['password1'])
        usuario.save()
        return usuario


class RegistroForm(UsuarioBaseForm):
    ROLES_PUBLICOS = [c for c in ROL_USUARIO if c[0] != 'administrador']

    rol = forms.ChoiceField(choices=ROLES_PUBLICOS, label="Tipo de cuenta")

    # Empresa
    ruc = forms.CharField(max_length=13, required=False, label="RUC")
    razon_social = forms.CharField(max_length=200, required=False, label="Razón social")
    representante_legal = forms.CharField(max_length=200, required=False, label="Representante legal")
    direccion = forms.CharField(widget=forms.Textarea(attrs={'rows': 2}), required=False, label="Dirección")

    # Vendedor
    numero_identidad = forms.CharField(max_length=20, required=False, label="Cédula / Identidad")

    # Comprador
    tipo_negocio = forms.CharField(max_length=100, required=False, label="Tipo de negocio")
    direccion_entrega = forms.CharField(widget=forms.Textarea(attrs={'rows': 2}), required=False,
                                         label="Dirección de entrega")

    def clean(self):
        cleaned = super().clean()
        rol = cleaned.get('rol')
        requeridos = {
            'empresa': ['ruc', 'razon_social', 'representante_legal', 'direccion'],
            'vendedor': ['numero_identidad'],
            'comprador': ['tipo_negocio', 'direccion_entrega'],
        }.get(rol, [])
        for campo in requeridos:
            if not cleaned.get(campo):
                self.add_error(campo, "Este campo es obligatorio para el rol seleccionado.")
        return cleaned

    @transaction.atomic
    def guardar(self):
        rol = self.cleaned_data['rol']
        usuario = self.crear_usuario(rol)
        if rol == 'empresa':
            Empresa.objects.create(
                usuario=usuario, ruc=self.cleaned_data['ruc'],
                razon_social=self.cleaned_data['razon_social'],
                representante_legal=self.cleaned_data['representante_legal'],
                direccion=self.cleaned_data['direccion'],
            )
        elif rol == 'vendedor':
            Vendedor.objects.create(
                usuario=usuario, numero_identidad=self.cleaned_data['numero_identidad'],
            )
        elif rol == 'comprador':
            Comprador.objects.create(
                usuario=usuario, tipo_negocio=self.cleaned_data['tipo_negocio'],
                direccion_entrega=self.cleaned_data['direccion_entrega'],
            )
        return usuario


class UsuarioCreateForm(RegistroForm):
    """Variante de RegistroForm para uso administrativo: permite crear cualquier rol."""
    rol = forms.ChoiceField(choices=ROL_USUARIO, label="Rol")
    area_trabajo = forms.CharField(max_length=100, required=False, label="Área de trabajo")
    nivel_acceso = forms.IntegerField(required=False, initial=1, label="Nivel de acceso")

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('rol') == 'administrador' and not cleaned.get('area_trabajo'):
            self.add_error('area_trabajo', "Este campo es obligatorio para el rol seleccionado.")
        return cleaned

    @transaction.atomic
    def guardar(self):
        if self.cleaned_data['rol'] == 'administrador':
            usuario = self.crear_usuario('administrador')
            Administrador.objects.create(
                usuario=usuario, area_trabajo=self.cleaned_data['area_trabajo'],
                nivel_acceso=self.cleaned_data.get('nivel_acceso') or 1,
            )
            return usuario
        return super().guardar()


class UsuarioForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ['username', 'first_name', 'last_name', 'email', 'telefono', 'rol', 'is_active']
        labels = {
            'username': 'Usuario', 'first_name': 'Nombres', 'last_name': 'Apellidos',
            'email': 'Correo electrónico', 'telefono': 'Teléfono', 'rol': 'Rol',
            'is_active': 'Cuenta activa',
        }


# =============================================================================
# EMPRESAS
# =============================================================================

class EmpresaCreateForm(UsuarioBaseForm):
    ruc = forms.CharField(max_length=13, label="RUC")
    razon_social = forms.CharField(max_length=200, label="Razón social")
    representante_legal = forms.CharField(max_length=200, label="Representante legal")
    direccion = forms.CharField(widget=forms.Textarea(attrs={'rows': 2}), label="Dirección")
    logo_url = forms.URLField(required=False, label="URL del logo")

    @transaction.atomic
    def guardar(self):
        usuario = self.crear_usuario('empresa')
        return Empresa.objects.create(
            usuario=usuario, ruc=self.cleaned_data['ruc'],
            razon_social=self.cleaned_data['razon_social'],
            representante_legal=self.cleaned_data['representante_legal'],
            direccion=self.cleaned_data['direccion'],
            logo_url=self.cleaned_data['logo_url'],
        )


class EmpresaForm(forms.ModelForm):
    class Meta:
        model = Empresa
        fields = ['ruc', 'razon_social', 'representante_legal', 'direccion', 'logo_url', 'estado']
        widgets = {'direccion': forms.Textarea(attrs={'rows': 2})}


# =============================================================================
# VENDEDORES
# =============================================================================

class VendedorCreateForm(UsuarioBaseForm):
    numero_identidad = forms.CharField(max_length=20, label="Cédula / Identidad")

    @transaction.atomic
    def guardar(self):
        usuario = self.crear_usuario('vendedor')
        return Vendedor.objects.create(
            usuario=usuario, numero_identidad=self.cleaned_data['numero_identidad'],
        )


class VendedorForm(forms.ModelForm):
    class Meta:
        model = Vendedor
        fields = ['numero_identidad', 'estado_aprobacion', 'empresas_aprobadoras']


# =============================================================================
# COMPRADORES
# =============================================================================

class CompradorCreateForm(UsuarioBaseForm):
    tipo_negocio = forms.CharField(max_length=100, label="Tipo de negocio")
    ruc = forms.CharField(max_length=13, required=False, label="RUC (opcional)")
    direccion_entrega = forms.CharField(widget=forms.Textarea(attrs={'rows': 2}), label="Dirección de entrega")
    limite_credito = forms.DecimalField(max_digits=12, decimal_places=2, required=False,
                                         initial=0, label="Límite de crédito")

    @transaction.atomic
    def guardar(self):
        usuario = self.crear_usuario('comprador')
        return Comprador.objects.create(
            usuario=usuario, tipo_negocio=self.cleaned_data['tipo_negocio'],
            ruc=self.cleaned_data.get('ruc', ''),
            direccion_entrega=self.cleaned_data['direccion_entrega'],
            limite_credito=self.cleaned_data.get('limite_credito') or 0,
        )


class CompradorForm(forms.ModelForm):
    class Meta:
        model = Comprador
        fields = ['tipo_negocio', 'ruc', 'direccion_entrega', 'limite_credito']
        widgets = {'direccion_entrega': forms.Textarea(attrs={'rows': 2})}


# =============================================================================
# PRODUCTOS Y CATEGORÍAS
# =============================================================================

class CategoriaProductoForm(forms.ModelForm):
    class Meta:
        model = CategoriaProducto
        fields = ['nombre', 'descripcion', 'activo']
        widgets = {'descripcion': forms.Textarea(attrs={'rows': 2})}


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['nombre', 'descripcion', 'categoria', 'precio_base', 'precio_venta',
                  'unidad_medida', 'empresa', 'activo']
        widgets = {'descripcion': forms.Textarea(attrs={'rows': 2})}


# =============================================================================
# INVENTARIO
# =============================================================================

class InventarioForm(forms.ModelForm):
    class Meta:
        model = Inventario
        fields = ['producto', 'stock_actual', 'stock_minimo', 'stock_maximo', 'ubicacion']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields.pop('producto', None)
        else:
            self.fields['producto'].queryset = Producto.objects.filter(inventario__isnull=True)


# =============================================================================
# PLATAFORMA — Suscripciones y Comisiones
# =============================================================================

class SuscripcionForm(forms.ModelForm):
    class Meta:
        model = Suscripcion
        fields = ['empresa', 'tipo_plan', 'precio', 'comision_plataforma', 'estado',
                  'fecha_inicio', 'fecha_fin']
        widgets = {
            'fecha_inicio': forms.DateInput(attrs={'type': 'date'}),
            'fecha_fin': forms.DateInput(attrs={'type': 'date'}),
        }


class ComisionForm(forms.ModelForm):
    class Meta:
        model = Comision
        fields = ['vendedor', 'pedido', 'porcentaje', 'monto_comision', 'estado']


# =============================================================================
# VENTAS — Pedidos, Pagos, Facturas
# =============================================================================

class PedidoForm(forms.ModelForm):
    class Meta:
        model = Pedido
        fields = ['comprador', 'vendedor', 'empresa', 'estado']


class DetallePedidoForm(forms.ModelForm):
    class Meta:
        model = DetallePedido
        fields = ['producto', 'cantidad', 'precio_unitario', 'descuento']


DetallePedidoFormSet = forms.inlineformset_factory(
    Pedido, DetallePedido, form=DetallePedidoForm,
    extra=1, can_delete=True,
)


class PagoForm(forms.ModelForm):
    class Meta:
        model = Pago
        fields = ['pedido', 'monto', 'tipo', 'metodo_pago', 'referencia_pago', 'estado']


class FacturaForm(forms.ModelForm):
    class Meta:
        model = Factura
        fields = ['pedido', 'subtotal', 'estado_sri', 'clave_acceso']


# =============================================================================
# CAPACITACIÓN
# =============================================================================

class CursoForm(forms.ModelForm):
    class Meta:
        model = Curso
        fields = ['empresa', 'titulo', 'descripcion', 'duracion_horas', 'url_contenido',
                  'activo', 'vendedores']
        widgets = {'descripcion': forms.Textarea(attrs={'rows': 3})}


class EvaluacionForm(forms.ModelForm):
    class Meta:
        model = Evaluacion
        fields = ['vendedor', 'curso', 'puntaje_obtenido', 'puntaje_minimo']


# =============================================================================
# CALIFICACIONES Y NOTIFICACIONES
# =============================================================================

class CalificacionForm(forms.ModelForm):
    class Meta:
        model = Calificacion
        fields = ['tipo_calificado', 'vendedor_calificado', 'empresa_calificada',
                  'puntuacion', 'comentario', 'es_incidencia']
        widgets = {'comentario': forms.Textarea(attrs={'rows': 3})}


class NotificacionForm(forms.ModelForm):
    class Meta:
        model = Notificacion
        fields = ['destinatario', 'tipo', 'titulo', 'mensaje']
        widgets = {'mensaje': forms.Textarea(attrs={'rows': 3})}

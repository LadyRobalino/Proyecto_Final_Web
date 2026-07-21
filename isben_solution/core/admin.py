from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    Usuario, Empresa, Vendedor, Comprador, Administrador,
    CategoriaProducto, Producto, Inventario,
    Suscripcion, Comision,
    Pedido, DetallePedido, Pago, Factura,
    Curso, Evaluacion, Calificacion, Notificacion, SolicitudColaboracion,
    DireccionEntrega, MovimientoPuntos, Promocion,
)


class UsuarioAdmin(UserAdmin):
    list_display = ['username', 'email', 'rol', 'is_active', 'is_staff']
    fieldsets = UserAdmin.fieldsets + (
        ('Datos ISBEN', {'fields': ('rol', 'telefono')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Datos ISBEN', {'fields': ('rol', 'telefono', 'email')}),
    )


admin.site.register(Usuario, UsuarioAdmin)
admin.site.register(Empresa)
admin.site.register(Vendedor)
admin.site.register(Comprador)
admin.site.register(Administrador)
admin.site.register(CategoriaProducto)
admin.site.register(Producto)
admin.site.register(Inventario)
admin.site.register(Suscripcion)
admin.site.register(Comision)
admin.site.register(Pedido)
admin.site.register(DetallePedido)
admin.site.register(Pago)
admin.site.register(Factura)
admin.site.register(Curso)
admin.site.register(Evaluacion)
admin.site.register(Calificacion)
admin.site.register(Notificacion)
admin.site.register(SolicitudColaboracion)
admin.site.register(DireccionEntrega)
admin.site.register(MovimientoPuntos)
admin.site.register(Promocion)
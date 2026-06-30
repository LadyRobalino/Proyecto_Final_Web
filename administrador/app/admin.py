from django.contrib import admin
from .models import (
    Usuario, Empresa, Vendedor, Comprador, Administrador,
    CategoriaProducto, Producto, Inventario,
    Suscripcion, Comision,
    Pedido, DetallePedido, Pago, Factura,
    Curso, Evaluacion, Calificacion, Notificacion
)

admin.site.register(Usuario)
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
from decimal import Decimal
from django.utils import timezone
from .models import Producto, Promocion

def get_carrito(request):
    return request.session.setdefault('carrito', {})

def guardar_carrito(request, carrito):
    request.session['carrito'] = carrito
    request.session.modified = True

def agregar(request, producto_pk, cantidad):
    carrito = get_carrito(request)
    pk_str = str(producto_pk)
    if pk_str in carrito:
        carrito[pk_str] += cantidad
    else:
        carrito[pk_str] = cantidad
    guardar_carrito(request, carrito)

def actualizar(request, producto_pk, cantidad):
    carrito = get_carrito(request)
    pk_str = str(producto_pk)
    if cantidad > 0:
        carrito[pk_str] = cantidad
    else:
        if pk_str in carrito:
            del carrito[pk_str]
    guardar_carrito(request, carrito)

def eliminar(request, producto_pk):
    carrito = get_carrito(request)
    pk_str = str(producto_pk)
    if pk_str in carrito:
        del carrito[pk_str]
        guardar_carrito(request, carrito)

def vaciar(request):
    request.session['carrito'] = {}
    request.session.modified = True

def obtener_items(request):
    carrito = get_carrito(request)
    lineas = []
    for pk, cantidad in carrito.items():
        try:
            producto = Producto.objects.get(pk=pk)
            lineas.append({
                'producto': producto,
                'cantidad': cantidad,
                'precio_unitario': producto.precio_venta,
                'subtotal': producto.precio_venta * cantidad
            })
        except Producto.DoesNotExist:
            pass
    return lineas

def agrupar_por_empresa(lineas, comprador=None):
    grupos = {}
    ahora = timezone.now()
    for linea in lineas:
        empresa = linea['producto'].empresa
        if empresa not in grupos:
            grupos[empresa] = {
                'empresa': empresa,
                'lineas': [],
                'subtotal': Decimal('0.00'),
                'descuento_promocion': Decimal('0.00'),
                'total': Decimal('0.00')
            }
        
        precio = linea['producto'].precio_venta
        cantidad = linea['cantidad']
        descuento_promocion = Decimal('0.00')
        
        if comprador:
            # Simple promo logic matching models
            promociones = Promocion.objects.filter(
                empresa=empresa, 
                activo=True,
                fecha_inicio__lte=ahora,
                fecha_fin__gte=ahora
            ).order_by('-descuento_porcentaje')
            
            for promo in promociones:
                # NIVELES_PESO helps compare levels hierarchically rather than alphabetically
                pesos = {'bronce': 1, 'plata': 2, 'oro': 3, 'diamante': 4}
                if pesos.get(promo.nivel_minimo, 0) <= pesos.get(comprador.nivel, 0):
                    descuento_promocion = (precio * cantidad * Decimal(str(promo.descuento_porcentaje))) / Decimal('100')
                    break
        
        subtotal = precio * cantidad
        
        grupos[empresa]['lineas'].append(linea)
        grupos[empresa]['subtotal'] += subtotal
        grupos[empresa]['descuento_promocion'] += descuento_promocion
        grupos[empresa]['total'] += (subtotal - descuento_promocion)
        
    return grupos.values()

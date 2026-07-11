def notificaciones(request):
    if request.user.is_authenticated:
        return {
            'notificaciones_no_leidas_global': request.user.notificaciones.filter(leida=False).count(),
        }
    return {}

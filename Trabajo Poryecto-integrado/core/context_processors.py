from .models import Reclamo, Pedido

def notificaciones_globales(request):
    """
    Context processor para mostrar notificaciones en toda la aplicación.
    """
    context = {}
    
    if request.user.is_authenticated:
        # Notificaciones para el admin
        if request.user.rol == 'administrador' or request.user.is_staff:
            # Reclamos nuevos sin responder
            reclamos_pendientes = Reclamo.objects.filter(
                estado__in=['nuevo', 'en_revision']
            ).count()
            
            # Pedidos pendientes de aprobación
            pedidos_pendientes_cocina = Pedido.objects.filter(
                estado='pendiente'
            ).count()
            
            context['reclamos_pendientes'] = reclamos_pendientes
            context['pedidos_pendientes_cocina'] = pedidos_pendientes_cocina
        
        # Notificaciones para cocina
        elif request.user.rol == 'cocina':
            pedidos_pendientes_cocina = Pedido.objects.filter(
                estado='pendiente'
            ).count()
            context['pedidos_pendientes_cocina'] = pedidos_pendientes_cocina
        
        # Notificaciones para clientes
        elif request.user.rol == 'cliente':
            # Reclamos del cliente sin calificar
            reclamos_sin_calificar = Reclamo.objects.filter(
                cliente=request.user,
                estado__in=['resuelto', 'cerrado'],
                calificacion_atencion__isnull=True
            ).count()
            context['reclamos_sin_calificar'] = reclamos_sin_calificar
    
    return context
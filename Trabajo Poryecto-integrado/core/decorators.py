# core/decorators.py
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

def admin_required(view_func):
    """
    Decorador para vistas que requieren permisos de administrador.
    Verifica si el usuario es staff, superusuario o tiene rol='administrador'
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Verificar autenticaciÃ³n
        if not request.user.is_authenticated:
            messages.warning(request, 'Debes iniciar sesiÃ³n para acceder a esta secciÃ³n.')
            return redirect('login')
        
        # Verificar permisos de administrador
        # Acepta: is_staff, is_superuser o rol='administrador'
        if not (request.user.is_staff or 
                request.user.is_superuser or 
                getattr(request.user, 'rol', None) == 'administrador'):
            messages.error(request, 'No tienes permisos de administrador para acceder a esta secciÃ³n.')
            return redirect('home')
        
        return view_func(request, *args, **kwargs)
    return wrapper


def repartidor_required(view_func):
    """
    Decorador para vistas que requieren permisos de repartidor.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'Debes iniciar sesiÃ³n para acceder a esta secciÃ³n.')
            return redirect('login')
        
        if not (getattr(request.user, 'rol', None) == 'repartidor' or
                request.user.is_staff or 
                request.user.is_superuser):
            messages.error(request, 'No tienes permisos de repartidor para acceder a esta secciÃ³n.')
            return redirect('home')
        
        return view_func(request, *args, **kwargs)
    return wrapper


def cajero_or_admin_required(view_func):
    """
    Decorador para vistas que requieren permisos de cajero o administrador (POS).
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'Debes iniciar sesiÃ³n para acceder a esta secciÃ³n.')
            return redirect('login')
        
        user_rol = getattr(request.user, 'rol', None)
        if not (user_rol in ['cajero', 'administrador'] or 
                request.user.is_staff or 
                request.user.is_superuser):
            messages.error(request, 'No tienes permisos para acceder al punto de venta.')
            return redirect('home')
        
        return view_func(request, *args, **kwargs)
    return wrapper

def cocina_required(view_func):
    """
    Decorador para vistas que requieren permisos de cocina.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'Debes iniciar sesión para acceder a esta sección.')
            return redirect('login')
        
        if not (getattr(request.user, 'rol', None) == 'cocina' or
                request.user.is_staff or 
                request.user.is_superuser):
            messages.error(request, 'No tienes permisos de cocina para acceder a esta sección.')
            return redirect('home')
        
        return view_func(request, *args, **kwargs)
    return wrapper
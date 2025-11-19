from urllib import request
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.urls import reverse
from transbank.webpay.webpay_plus.transaction import Transaction
from django.contrib.auth.tokens import default_token_generator
from django.contrib import messages
from .decorators import admin_required, repartidor_required, cajero_or_admin_required
from django.db import models
from django.db import transaction
from django.http import JsonResponse
from .forms import ( 
    RegistroForm, LoginForm, PerfilForm, ProductoForm,
    RecuperarPasswordForm, ResetPasswordForm, CheckoutForm, ReclamoForm, RepartidorForm, CalificarPedidoForm,ReclamoRapidoForm,ReclamoRapidoForm
)
from .models import Carrito, Producto, Usuario, Categoria, ItemCarrito, Pedido, Slide,MetodoPago, DetallePedido,Reclamo,Repartidor
from .forms import RepartidorForm, RegistroForm, LoginForm, PerfilForm, RecuperarPasswordForm, ResetPasswordForm, ProductoForm, CheckoutForm, ReclamoForm, CalificarPedidoForm,Pedido
from django.contrib.auth.hashers import make_password
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.sites.shortcuts import get_current_site
from django.utils import timezone
from django.db.models import Sum    
from datetime import timedelta
import json


def home(request):
    slides = Slide.objects.filter(activo=True).order_by('orden')
    # Obtener productos en promociÃ³n (mÃ¡ximo 6 para el carrusel)
    productos_promocion = Producto.objects.filter(
        activo=True,
        en_promocion=True,
        stock__gt=0
    ).select_related('categoria').order_by('-fecha_actualizacion')[:6]

    contexto = {
        'slides': slides,
        'productos_promocion': productos_promocion
    }
    return render(request, 'core/home.html', contexto)


def catalogo_productos_view(request):
    """Vista para que los clientes y visitantes vean el catÃ¡logo de productos (HU10)"""
    
    busqueda = request.GET.get('q', '')
    categoria_id = request.GET.get('categoria')
    ver_todo = request.GET.get('ver_todo')
    
    # SOLUCIÃ“N: Mostrar productos siempre que haya algÃºn filtro activo
    # O cuando se acceda directamente sin parÃ¡metros (primera carga)
    tiene_filtros = bool(busqueda or categoria_id or ver_todo)
    
    if tiene_filtros:
        # Si hay filtros, cargar productos activos con stock
        productos = Producto.objects.filter(
            activo=True, 
            stock__gt=0
        ).select_related('categoria').order_by('nombre')
        
        # Aplicar filtro de bÃºsqueda
        if busqueda:
            productos = productos.filter(nombre__icontains=busqueda)
        
        # Aplicar filtro de categorÃ­a
        if categoria_id:
            productos = productos.filter(categoria_id=categoria_id)
    else:
        # Si no hay filtros, mostrar queryset vacÃ­o (para mostrar categorÃ­as)
        productos = Producto.objects.none()
    
    contexto = {
        'productos': productos,
        'categorias': Categoria.objects.filter(activo=True).order_by('nombre'),
        'busqueda': busqueda,
        'categoria_seleccionada': categoria_id,
        'ver_todo': ver_todo,
    }
    return render(request, 'core/catalogo_productos.html', contexto)

# ========== AUTENTICACIÃ“N ==========

def registro_view(request):
    """Vista de registro de usuarios (HU05)"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Crear carrito automÃ¡ticamente para el nuevo usuario
            Carrito.objects.create(usuario=user)
            
            # Iniciar sesiÃ³n automÃ¡ticamente despuÃ©s del registro
            login(request, user)
            
            messages.success(request, f'Â¡Bienvenido {user.first_name}! Tu cuenta ha sido creada exitosamente.')
            return redirect('home')
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario.')
    else:
        form = RegistroForm()
    
    return render(request, 'core/registro.html', {'form': form})


def login_view(request):
    """Vista de inicio de sesiÃ³n (HU06)"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, f'Â¡Bienvenido de nuevo, {user.first_name}!')
                
                # Redirigir segÃºn el rol del usuario
                if user.rol == 'administrador':
                    return redirect('admin_dashboard')
                elif user.rol == 'repartidor':
                    return redirect('repartidor_pedidos')
                else:
                    return redirect('home')
            else:
                messages.error(request, 'Usuario o contraseÃ±a incorrectos.')
        else:
            messages.error(request, 'Usuario o contraseÃ±a incorrectos.')
    else:
        form = LoginForm()
    
    return render(request, 'core/login.html', {'form': form})


def logout_view(request):
    """Vista de cierre de sesiÃ³n"""
    logout(request)
    messages.info(request, 'Has cerrado sesiÃ³n correctamente.')
    return redirect('home')

def recuperar_password_view(request):
    """Vista para solicitar recuperaciÃ³n de contraseÃ±a (HU07)"""
    if request.method == 'POST':
        form = RecuperarPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                usuario = Usuario.objects.get(email=email)
                
                # Generar token
                token = default_token_generator.make_token(usuario)
                uid = urlsafe_base64_encode(force_bytes(usuario.pk))
                
                # Construir URL de reset
                current_site = get_current_site(request)
                reset_url = f"http://{current_site.domain}/reset/{uid}/{token}/"
                
                # Enviar email
                mensaje = f"""
                            Hola {usuario.first_name},

                            Recibimos una solicitud para restablecer tu contraseÃ±a en Cosmofood.

                            Para crear una nueva contraseÃ±a, haz clic en el siguiente enlace:
                            {reset_url}

                            Este enlace expirarÃ¡ en 24 horas.

                            Si no solicitaste este cambio, ignora este correo.

                            Saludos,
                            El equipo de Cosmofood
                """
                
                send_mail(
                    subject='RecuperaciÃ³n de ContraseÃ±a - Cosmofood',
                    message=mensaje,
                    from_email='cosmofood@grivyzom.com',
                    recipient_list=[email],
                    fail_silently=False,
                )
                
                messages.success(request, 'Te hemos enviado un correo con instrucciones para restablecer tu contraseÃ±a.')
                return redirect('login')
            except Usuario.DoesNotExist:
                messages.error(request, 'No existe una cuenta con ese correo electrÃ³nico.')
    else:
        form = RecuperarPasswordForm()
    
    return render(request, 'core/recuperar_password.html', {'form': form})

def reset_password_view(request, uidb64, token):
    """Vista para restablecer contraseÃ±a con token (HU07)"""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        usuario = Usuario.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, Usuario.DoesNotExist):
        usuario = None
    
    if usuario is not None and default_token_generator.check_token(usuario, token):
        if request.method == 'POST':
            form = ResetPasswordForm(request.POST)
            if form.is_valid():
                usuario.set_password(form.cleaned_data['password1'])
                usuario.save()
                messages.success(request, 'Â¡Tu contraseÃ±a ha sido restablecida! Ahora puedes iniciar sesiÃ³n.')
                return redirect('login')
        else:
            form = ResetPasswordForm()
        return render(request, 'core/reset_password.html', {'form': form, 'validlink': True})
    else:
        messages.error(request, 'El enlace de recuperaciÃ³n es invÃ¡lido o ha expirado.')
        return render(request, 'core/reset_password.html', {'validlink': False})

# ========== PERFIL DE USUARIO ==========

@login_required
def perfil_view(request):
    """Vista para ver datos personales (HU08)"""
    return render(request, 'core/perfil.html', {'usuario': request.user})

@login_required
def editar_perfil_view(request):
    """Vista para editar datos personales (HU09)"""
    if request.method == 'POST':
        form = PerfilForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tu perfil ha sido actualizado exitosamente.')
            return redirect('perfil')
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario.')
    else:
        form = PerfilForm(instance=request.user)
    
    return render(request, 'core/editar_perfil.html', {'form': form})

# ========== PEDIDOS DE USUARIO ==========

@login_required
def mis_pedidos_view(request):
    """Vista para que el usuario vea su historial de pedidos."""
    pedidos = Pedido.objects.filter(cliente=request.user).prefetch_related('detalles', 'detalles__producto').order_by('-fecha_creacion')
    
    contexto = {
        'pedidos': pedidos
    }
    return render(request, 'core/mis_pedidos.html', contexto)

# ========== CARRITO DE COMPRAS ==========

@login_required
def ver_carrito_view(request):
    """Vista para que el usuario vea su carrito de compras (HU11)"""
    try:
        carrito = request.user.carrito
        items = carrito.items.all().select_related('producto')
    except Carrito.DoesNotExist:
        carrito = Carrito.objects.create(usuario=request.user)
        items = []

    contexto = {
        'carrito': carrito,
        'items': items
    }
    return render(request, 'core/carrito.html', contexto)

@login_required
def agregar_al_carrito_view(request):

    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        cantidad = int(request.POST.get('cantidad', 1))

        producto = get_object_or_404(Producto, id=product_id)

        # Validar que el producto estÃ© activo y haya suficiente stock
        if not producto.activo:
            messages.error(request, f'El producto "{producto.nombre}" no estÃ¡ disponible actualmente.')
            return redirect('catalogo_productos')
        if producto.stock < cantidad:
            messages.error(request, f'No hay suficiente stock de "{producto.nombre}". Solo quedan {producto.stock} unidades.')
            return redirect('catalogo_productos')

        carrito, created = Carrito.objects.get_or_create(usuario=request.user)

        item_carrito, item_created = ItemCarrito.objects.get_or_create(
            carrito=carrito,
            producto=producto,
            defaults={'cantidad': 0}
        )
        item_carrito.cantidad += cantidad
        item_carrito.save()

        messages.success(request, f'"{producto.nombre}" ha sido agregado al carrito. Cantidad actual: {item_carrito.cantidad}.')
        return redirect('catalogo_productos')
    return redirect('catalogo_productos')

@login_required
def actualizar_cantidad_carrito_view(request):
    """Vista para aumentar o disminuir la cantidad de un item en el carrito."""
    if request.method == 'POST':
        item_id = request.POST.get('item_id')
        action = request.POST.get('action')
        
        item = get_object_or_404(ItemCarrito, id=item_id)
        
        if item.carrito.usuario != request.user:
            messages.error(request, "AcciÃ³n no permitida.")
            return redirect('ver_carrito')

        if action == 'increase':
            if item.producto.stock > item.cantidad:
                item.cantidad += 1
                item.save()
            else:
                messages.warning(request, f'No hay mÃ¡s stock disponible para "{item.producto.nombre}".')
        elif action == 'decrease':
            item.cantidad -= 1
            if item.cantidad > 0:
                item.save()
            else:
                item.delete()
                messages.info(request, f'"{item.producto.nombre}" ha sido eliminado del carrito.')
    
    return redirect('ver_carrito')

@login_required
def eliminar_item_carrito_view(request):
    """Vista para eliminar un item completo del carrito."""
    if request.method == 'POST':
        item_id = request.POST.get('item_id')
        item = get_object_or_404(ItemCarrito, id=item_id)

        if item.carrito.usuario == request.user:
            nombre_producto = item.producto.nombre
            item.delete()
            messages.success(request, f'"{nombre_producto}" ha sido eliminado de tu carrito.')
        else:
            messages.error(request, "AcciÃ³n no permitida.")
    return redirect('ver_carrito')

# ========== DASHBOARD (ADMIN) ==========

@login_required
def admin_dashboard_view(request):
    """Muestra el panel principal del administrador con estadÃ­sticas clave."""


    # --- Manejo de CreaciÃ³n de CategorÃ­a desde el Modal ---
    if request.method == 'POST' and request.POST.get('action') == 'crear_categoria':
        nombre = request.POST.get('nombre', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        activo = request.POST.get('activo') == 'on'
        
        if nombre:
            try:
                Categoria.objects.create(
                    nombre=nombre,
                    descripcion=descripcion if descripcion else None,
                    activo=activo
                )
                messages.success(request, f'La categorÃ­a "{nombre}" ha sido creada exitosamente.')
            except Exception as e:
                messages.error(request, f'Error al crear la categorÃ­a: {str(e)}')
        else:
            messages.error(request, 'El nombre de la categorÃ­a es obligatorio.')
        
        return redirect('admin_dashboard')

    # --- CÃ¡lculos para las Tarjetas KPI ---
    today = timezone.now().date()

    # 1. Ventas de Hoy
    ventas_hoy = Pedido.objects.filter(
        fecha_creacion__date=today,
        estado__in=['confirmado', 'en_preparacion', 'listo', 'en_camino', 'entregado']
    ).aggregate(total_ventas=Sum('total'))['total_ventas'] or 0

    # 2. Pedidos de Hoy
    pedidos_hoy = Pedido.objects.filter(fecha_creacion__date=today).count()
    # Después de las otras métricas, agregar:
    pedidos_pendientes_cocina = Pedido.objects.filter(estado='pendiente').count()

# Y en el contexto:
    contexto = {
    # ... otros valores
    'pedidos_pendientes_cocina': pedidos_pendientes_cocina,
}
    # 3. Clientes Totales
    total_clientes = Usuario.objects.filter(rol='cliente').count()

    # 4. Productos Activos
    total_productos_activos = Producto.objects.filter(activo=True).count()

    # 5. Pedidos pendientes para la lista
    pedidos_recientes = Pedido.objects.filter(
        estado__in=['confirmado', 'en_preparacion']
    ).order_by('-fecha_creacion')[:5]

    # --- CÃ¡lculo para el GrÃ¡fico "Ventas de la Semana" ---
    dias_espanol = {
        'Mon': 'Lun', 'Tue': 'Mar', 'Wed': 'MiÃ©', 
        'Thu': 'Jue', 'Fri': 'Vie', 'Sat': 'SÃ¡b', 'Sun': 'Dom'
    }
    
    dias = []
    ventas_por_dia = []
    for i in range(7):
        dia = today - timedelta(days=i)
        dia_ingles = dia.strftime('%a')
        dia_espanol = dias_espanol.get(dia_ingles, dia_ingles)
        dias.append(dia_espanol)
        ventas_dia = Pedido.objects.filter(
            fecha_creacion__date=dia,
            estado__in=['confirmado', 'en_preparacion', 'listo', 'en_camino', 'entregado']
        ).aggregate(total=Sum('total'))['total'] or 0
        ventas_por_dia.append(float(ventas_dia))
    dias.reverse()
    ventas_por_dia.reverse()

    detalles_hoy = DetallePedido.objects.filter(
        pedido__fecha_creacion__date=today,
        pedido__estado__in=['confirmado', 'en_preparacion', 'listo', 'en_camino', 'entregado']
    )
    productos_populares_hoy = detalles_hoy.values('producto__nombre') \
                                          .annotate(cantidad_vendida=Sum('cantidad')) \
                                          .order_by('-cantidad_vendida')[:5]
    productos_bajo_stock = Producto.objects.filter(
        activo=True,
        stock__lte=10
    ).select_related('categoria').order_by('stock', 'nombre')[:10]

    contexto = {
        'ventas_hoy': ventas_hoy,
        'pedidos_hoy': pedidos_hoy,
        'total_clientes': total_clientes,
        'total_productos_activos': total_productos_activos,
        'pedidos_recientes': pedidos_recientes,
        'titulo': 'Dashboard',
        'chart_labels': json.dumps(dias),
        'chart_data': json.dumps(ventas_por_dia),
        'productos_populares': productos_populares_hoy,
        'productos_bajo_stock': productos_bajo_stock,
    }

    return render(request, 'core/admin/dashboard.html', contexto)



# ========== GESTIÃ“N DE PRODUCTOS (ADMIN) ==========

@login_required
def admin_productos_lista(request):
    """Listar todos los productos (HU01) y mostrar estadÃ­sticas."""

    
    productos_base = Producto.objects.all().select_related('categoria')
    
    total_productos = productos_base.count()
    productos_activos = productos_base.filter(activo=True).count()
    stock_bajo = productos_base.filter(activo=True, stock__lte=10).count() 
    total_categorias = Categoria.objects.filter(activo=True).count()

    productos_filtrados = productos_base
    
    busqueda = request.GET.get('q', '')
    if busqueda:
        productos_filtrados = productos_filtrados.filter(
            models.Q(nombre__icontains=busqueda) | 
            models.Q(descripcion__icontains=busqueda) 
        )
    
    categoria_id = request.GET.get('categoria')
    if categoria_id:
        try:
            productos_filtrados = productos_filtrados.filter(categoria_id=int(categoria_id))
        except (ValueError, TypeError):
            pass 
            
    status_filter = request.GET.get('status', 'all') 
    if status_filter == 'active':
        productos_filtrados = productos_filtrados.filter(activo=True)
    elif status_filter == 'inactive':
        productos_filtrados = productos_filtrados.filter(activo=False)
    elif status_filter == 'low-stock':
         productos_filtrados = productos_filtrados.filter(activo=True, stock__lte=10)
         
    sort_by = request.GET.get('sort', 'nombre') 
    if sort_by == 'precio':
        productos_filtrados = productos_filtrados.order_by('precio')
    elif sort_by == 'stock':
        productos_filtrados = productos_filtrados.order_by('stock')
    elif sort_by == 'categoria':
        productos_filtrados = productos_filtrados.order_by('categoria__nombre')
    else: 
        productos_filtrados = productos_filtrados.order_by('nombre')
        
    contexto = {
        'productos': productos_filtrados, 
        'categorias': Categoria.objects.filter(activo=True).order_by('nombre'),
        'busqueda': busqueda,
        'categoria_seleccionada': categoria_id, 
        'status_filter': status_filter, 
        'sort_by': sort_by, 
        'total_productos': total_productos,
        'productos_activos': productos_activos,
        'stock_bajo': stock_bajo,
        'total_categorias': total_categorias,
        'titulo': 'GestiÃ³n de Productos' 
    }
    return render(request, 'core/admin/productos_lista.html', contexto)

@login_required
def admin_producto_crear(request):
    """Crear nuevo producto (HU02)"""

    
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES)
        if form.is_valid():
            producto = form.save()
            messages.success(request, f'El producto "{producto.nombre}" ha sido creado exitosamente.')
            return redirect('admin_productos_lista')
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario.')
    else:
        form = ProductoForm()
        form.fields['categoria'].queryset = Categoria.objects.filter(activo=True).order_by('nombre') 
    
    contexto = {
        'form': form,
        'titulo': 'Crear Nuevo Producto'
    }
    return render(request, 'core/admin/producto_form.html', contexto)

@login_required
def admin_producto_editar(request, pk):

    
    producto = get_object_or_404(Producto, pk=pk)
    
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES, instance=producto)
        if form.is_valid():
            form.save()
            messages.success(request, f'El producto "{producto.nombre}" ha sido actualizado exitosamente.')
            return redirect('admin_productos_lista')
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario.')
    else:
        form = ProductoForm(instance=producto)
        form.fields['categoria'].queryset = Categoria.objects.filter(activo=True).order_by('nombre')
        
    contexto = {
        'form': form,
        'producto': producto,
        'titulo': f'Editar Producto: {producto.nombre}'
    }
    return render(request, 'core/admin/producto_form.html', contexto)

@login_required
def admin_producto_desactivar(request, pk):
    """Activa o Desactiva un producto (HU04)"""

        
    if request.method == 'POST':
        producto = get_object_or_404(Producto, pk=pk)
        producto.activo = not producto.activo
        producto.save()
        
        estado = "activado" if producto.activo else "desactivado"
        messages.success(request, f'El producto "{producto.nombre}" ha sido {estado}.')
    
    return redirect('admin_productos_lista')

# ========== GESTIÃ“N DE PEDIDOS (ADMIN) ==========

@login_required
def admin_pedidos_lista_view(request):
    """Vista para que el admin vea y filtre todos los pedidos."""


    pedidos = Pedido.objects.all().select_related('cliente').order_by('-fecha_creacion')

    busqueda = request.GET.get('q', '')
    if busqueda:
        pedidos = pedidos.filter(
            models.Q(numero_pedido__icontains=busqueda) |
            models.Q(cliente__username__icontains=busqueda) |
            models.Q(cliente__first_name__icontains=busqueda) |
            models.Q(cliente__last_name__icontains=busqueda)
        )

    estado_filtro = request.GET.get('estado', '')
    if estado_filtro:
        pedidos = pedidos.filter(estado=estado_filtro)

    contexto = {
        'pedidos': pedidos,
        'busqueda': busqueda,
        'estado_seleccionado': estado_filtro,
        'estados_posibles': Pedido.ESTADO_CHOICES,
    }
    return render(request, 'core/admin/pedidos_lista.html', contexto)

@login_required
def admin_pedido_detalle_view(request, pk):
    """Vista para que el admin vea el detalle de un pedido, cambie su estado Y ASIGNE REPARTIDOR."""


    pedido = get_object_or_404(Pedido.objects.select_related('cliente', 'metodo_pago', 'repartidor__usuario')
                                           .prefetch_related('detalles', 'detalles__producto'), pk=pk)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'cambiar_estado':
            nuevo_estado = request.POST.get('estado')
            if nuevo_estado in [estado[0] for estado in Pedido.ESTADO_CHOICES]:
                pedido.estado = nuevo_estado
                if nuevo_estado == 'confirmado' and not pedido.fecha_confirmacion:
                     pedido.fecha_confirmacion = timezone.now()
                elif nuevo_estado == 'en_preparacion' and not pedido.fecha_preparacion:
                     pedido.fecha_preparacion = timezone.now()
                pedido.save()
                messages.success(request, f'Estado del pedido #{pedido.numero_pedido} actualizado a "{pedido.get_estado_display()}".')
            else:
                messages.error(request, 'Estado no vÃ¡lido.')

        elif action == 'asignar_repartidor':
            repartidor_usuario_id = request.POST.get('repartidor_asignado')
            if repartidor_usuario_id:
                try:
                    repartidor_a_asignar = Repartidor.objects.get(usuario_id=int(repartidor_usuario_id), disponible=True)
                    pedido.repartidor = repartidor_a_asignar
                    pedido.save()
                    messages.success(request, f'Repartidor "{repartidor_a_asignar.usuario.username}" asignado al pedido #{pedido.numero_pedido}.')
                except (Repartidor.DoesNotExist, ValueError):
                    messages.error(request, 'Repartidor seleccionado no vÃ¡lido o no disponible.')
            else:
                 pedido.repartidor = None
                 pedido.save()
                 messages.info(request, f'Repartidor desasignado del pedido #{pedido.numero_pedido}.')

        return redirect('admin_pedido_detalle', pk=pedido.pk)

    else:
        repartidores_disponibles = Repartidor.objects.filter(disponible=True).select_related('usuario').order_by('usuario__username')

        contexto = {
            'pedido': pedido,
            'estados_posibles': Pedido.ESTADO_CHOICES,
            'repartidores_disponibles': repartidores_disponibles,
            'titulo': f'Detalle Pedido #{pedido.numero_pedido}'
        }
        return render(request, 'core/admin/pedido_detalle.html', contexto)

# ========== PUNTO DE VENTA (POS - HU24, HU25) ==========

@login_required
def pos_view(request):
    """Muestra la interfaz del Punto de Venta y procesa ventas locales."""


    if request.method == 'POST':
        try:
            items_json = request.POST.get('items')
            total_venta = float(request.POST.get('total', 0))
            metodo_pago_nombre = request.POST.get('metodo_pago')
            nombre_referencia = request.POST.get('nombre_referencia', '')

            if not items_json or total_venta <= 0 or not metodo_pago_nombre:
                messages.error(request, 'Faltan datos para registrar la venta.')
                return redirect('pos_view')

            items = json.loads(items_json)

            metodo_pago_obj, created = MetodoPago.objects.get_or_create(
                nombre=metodo_pago_nombre,
                defaults={'tipo': 'local', 'activo': True}
            )

            with transaction.atomic():
                try:
                    usuario_generico = Usuario.objects.get(username='clientelocal')
                except Usuario.DoesNotExist:
                    messages.warning(request, "Usuario 'clientelocal' no encontrado. Asignando pedido al usuario actual.")
                    usuario_generico = request.user

                nuevo_pedido = Pedido.objects.create(cliente=usuario_generico,
                    nombre_referencia_cliente=nombre_referencia,
                    metodo_pago=metodo_pago_obj,
                    tipo_orden='local',
                    estado='en_preparacion',
                    subtotal=total_venta,
                    costo_envio=0,
                    total=total_venta,
                )

                for item_data in items:
                    producto = Producto.objects.select_for_update().get(pk=item_data['id'])
                    cantidad = int(item_data['cantidad'])

                    if producto.stock < cantidad:
                        raise ValueError(f"Stock insuficiente para {producto.nombre}")

                    DetallePedido.objects.create(
                        pedido=nuevo_pedido,
                        producto=producto,
                        cantidad=cantidad,
                        precio_unitario=producto.precio,
                    )
                    producto.stock -= cantidad
                    producto.save()

            messages.success(request, f'Venta #{nuevo_pedido.numero_pedido} registrada exitosamente.')
            return redirect('pos_view')

        except Producto.DoesNotExist:
            messages.error(request, 'Error: Uno de los productos seleccionados ya no existe.')
            return redirect('pos_view')
        except ValueError as e:
             messages.error(request, f'Error al registrar venta: {e}')
             return redirect('pos_view')
        except Usuario.DoesNotExist:
             messages.error(request, "Error crÃ­tico: No se pudo asignar un cliente al pedido. Contacta al administrador.")
             return redirect('pos_view')
        except Exception as e:
            messages.error(request, f'Error inesperado al registrar venta: {e}')
            return redirect('pos_view')

    else:
        productos_pos = Producto.objects.filter(activo=True).select_related('categoria').order_by('categoria__nombre', 'nombre')
        categorias_pos = Categoria.objects.filter(activo=True, productos__in=productos_pos).distinct().order_by('nombre')

        contexto = {
            'productos_pos': productos_pos,
            'categorias_pos': categorias_pos,
            'titulo': 'Punto de Venta (POS)'
        }
        return render(request, 'core/admin/pos.html', contexto)
    
# ========== GESTIÃ“N DE RECLAMOS (ADMIN - HU21, HU22) ==========

@login_required
def admin_reclamos_lista(request):
    """Muestra una lista de todos los reclamos de clientes."""


    reclamos = Reclamo.objects.select_related('cliente', 'pedido').order_by('estado', '-fecha_creacion')

    estado_filtro = request.GET.get('estado', '')
    if estado_filtro:
        reclamos = reclamos.filter(estado=estado_filtro)

    contexto = {
        'reclamos': reclamos,
        'estados_posibles': Reclamo.ESTADO_CHOICES,
        'estado_seleccionado': estado_filtro,
        'titulo': 'GestiÃ³n de Reclamos'
    }
    return render(request, 'core/admin/reclamos_lista.html', contexto)

@login_required
def admin_reclamo_detalle(request, pk_reclamo):


    reclamo = get_object_or_404(Reclamo.objects.select_related('cliente', 'pedido', 'atendido_por'), pk=pk_reclamo)

    if request.method == 'POST':
        nuevo_estado = request.POST.get('estado')
        respuesta_admin = request.POST.get('respuesta', '').strip()

        if nuevo_estado not in [estado[0] for estado in Reclamo.ESTADO_CHOICES]:
            messages.error(request, 'Estado seleccionado no vÃ¡lido.')
        else:
            reclamo.estado = nuevo_estado
            reclamo.respuesta = respuesta_admin
            reclamo.atendido_por = request.user
            reclamo.fecha_respuesta = timezone.now()
            reclamo.save()

            messages.success(request, f'Reclamo #{reclamo.id} actualizado exitosamente.')
            return redirect('admin_reclamo_detalle', pk_reclamo=reclamo.pk)

    contexto = {
        'reclamo': reclamo,
        'estados_posibles': Reclamo.ESTADO_CHOICES,
        'titulo': f'Detalle Reclamo #{reclamo.id}'
    }
    return render(request, 'core/admin/reclamo_detalle.html', contexto)

# ========== GESTIÃ“N DE REPARTIDORES (ADMIN) ==========

@login_required
def admin_repartidores_lista(request):


    repartidores = Repartidor.objects.all().select_related('usuario').order_by('usuario__username')

    contexto = {
        'repartidores': repartidores,
        'titulo': 'GestiÃ³n de Repartidores'
    }
    return render(request, 'core/admin/repartidores_lista.html', contexto)

@login_required
def admin_repartidor_crear(request):

    if request.method == 'POST':
        form = RepartidorForm(request.POST)
        if form.is_valid():
            try:
                usuario = Usuario.objects.create(
                    username=form.cleaned_data['username'],
                    email=form.cleaned_data['email'],
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name'],
                    telefono=form.cleaned_data['telefono'],
                    password=make_password(form.cleaned_data['password']),
                    rol='repartidor'
                )
                Repartidor.objects.create(
                    usuario=usuario,
                    vehiculo=form.cleaned_data.get('vehiculo'),
                    placa_vehiculo=form.cleaned_data.get('placa_vehiculo'),
                    disponible=form.cleaned_data.get('disponible', True)
                )
                messages.success(request, f'Repartidor "{usuario.username}" creado exitosamente.')
                return redirect('admin_repartidores_lista')
            except Exception as e:
                messages.error(request, f'Error al crear repartidor: {e}')
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario.')
    else:
        form = RepartidorForm()

    contexto = {
        'form': form,
        'titulo': 'Crear Nuevo Repartidor'
    }
    return render(request, 'core/admin/repartidor_form.html', contexto)

@login_required
def admin_repartidor_editar(request, pk_usuario):
    """Muestra y procesa el formulario para editar un repartidor existente."""


    usuario_repartidor = get_object_or_404(Usuario, pk=pk_usuario, rol='repartidor')
    repartidor_perfil = Repartidor.objects.filter(usuario=usuario_repartidor).first()

    if request.method == 'POST':
        form = RepartidorForm(request.POST, instance=usuario_repartidor, instance_perfil=repartidor_perfil, initial={'username': usuario_repartidor.username})
        if form.is_valid():
            try:
                usuario_repartidor.email = form.cleaned_data['email']
                usuario_repartidor.first_name = form.cleaned_data['first_name']
                usuario_repartidor.last_name = form.cleaned_data['last_name']
                usuario_repartidor.telefono = form.cleaned_data['telefono']
                password = form.cleaned_data.get('password')
                if password:
                    usuario_repartidor.set_password(password)
                usuario_repartidor.save()

                if repartidor_perfil:
                    repartidor_perfil.vehiculo = form.cleaned_data.get('vehiculo')
                    repartidor_perfil.placa_vehiculo = form.cleaned_data.get('placa_vehiculo')
                    repartidor_perfil.disponible = form.cleaned_data.get('disponible')
                    repartidor_perfil.save()
                else:
                     Repartidor.objects.create(
                        usuario=usuario_repartidor,
                        vehiculo=form.cleaned_data.get('vehiculo'),
                        placa_vehiculo=form.cleaned_data.get('placa_vehiculo'),
                        disponible=form.cleaned_data.get('disponible', True)
                    )

                messages.success(request, f'Repartidor "{usuario_repartidor.username}" actualizado.')
                return redirect('admin_repartidores_lista')
            except Exception as e:
                 messages.error(request, f'Error al actualizar repartidor: {e}')
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario.')
    else:
        form = RepartidorForm(instance=usuario_repartidor, instance_perfil=repartidor_perfil, initial={'username': usuario_repartidor.username})

    contexto = {
        'form': form,
        'repartidor_usuario': usuario_repartidor,
        'titulo': f'Editar Repartidor: {usuario_repartidor.username}'
    }
    return render(request, 'core/admin/repartidor_form.html', contexto)

@login_required
def admin_repartidor_toggle_disponible(request, pk_usuario):
    """Cambia el estado 'disponible' de un repartidor."""


    if request.method == 'POST':
        usuario_repartidor = get_object_or_404(Usuario, pk=pk_usuario, rol='repartidor')
        repartidor_perfil = Repartidor.objects.filter(usuario=usuario_repartidor).first()

        if repartidor_perfil:
            repartidor_perfil.disponible = not repartidor_perfil.disponible
            repartidor_perfil.save()
            estado = "disponible" if repartidor_perfil.disponible else "no disponible"
            messages.success(request, f'El repartidor "{usuario_repartidor.username}" ahora estÃ¡ {estado}.')
        else:
            messages.error(request, f'El perfil de repartidor para "{usuario_repartidor.username}" no existe.')

    return redirect('admin_repartidores_lista')

# ========== BÃšSQUEDA DE PEDIDO (AJAX) ==========

@login_required
def buscar_pedido_view(request):

    
    query = request.GET.get('q', '').strip()
    
    if not query:
        return JsonResponse({'success': False, 'error': 'ParÃ¡metro de bÃºsqueda vacÃ­o'})
    
    try:
        pedido = Pedido.objects.filter(numero_pedido=query).first()
        
        if not pedido:
            try:
                pedido_id = int(query)
                pedido = Pedido.objects.filter(pk=pedido_id).first()
            except (ValueError, TypeError):
                pass
        
        if pedido:
            return JsonResponse({
                'success': True,
                'pedido_id': pedido.pk,
                'numero_pedido': pedido.numero_pedido
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Pedido no encontrado'
            })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

# ========== VISTA DEL REPARTIDOR (HU18) ==========

@login_required
def repartidor_pedidos_view(request):
    """
    Vista para que el repartidor gestione las entregas asignadas.
    HU18: Ver pedidos asignados y actualizar estado de entrega.
    """
    
    try:
        perfil_repartidor = request.user.perfil_repartidor
    except Repartidor.DoesNotExist:
        messages.error(request, 'No tienes un perfil de repartidor asociado. Contacta al administrador.')
        return redirect('home')
    
    if request.method == 'POST':
        pedido_id = request.POST.get('pedido_id')
        nuevo_estado = request.POST.get('nuevo_estado')
        
        if not pedido_id or not nuevo_estado:
            messages.error(request, 'Datos incompletos para actualizar el pedido.')
            return redirect('repartidor_pedidos')
        
        try:
            pedido = Pedido.objects.get(pk=pedido_id, repartidor=perfil_repartidor)
            
            estados_permitidos = ['en_preparacion', 'listo', 'en_camino', 'entregado']
            if nuevo_estado not in estados_permitidos:
                messages.error(request, 'Estado no permitido.')
                return redirect('repartidor_pedidos')
            
            estado_anterior = pedido.estado
            pedido.estado = nuevo_estado
            
            if nuevo_estado == 'en_preparacion' and not pedido.fecha_preparacion:
                pedido.fecha_preparacion = timezone.now()
            elif nuevo_estado == 'listo' and not pedido.fecha_listo:
                pedido.fecha_listo = timezone.now()
            elif nuevo_estado == 'entregado' and not pedido.fecha_entrega:
                pedido.fecha_entrega = timezone.now()
            
            pedido.save()
            
            messages.success(request, f'Pedido #{pedido.numero_pedido} actualizado de "{pedido.get_estado_display()}" a "{dict(Pedido.ESTADO_CHOICES)[nuevo_estado]}".')
            
        except Pedido.DoesNotExist:
            messages.error(request, 'Pedido no encontrado o no tienes permisos para modificarlo.')
        except Exception as e:
            messages.error(request, f'Error al actualizar el pedido: {str(e)}')
        
        return redirect('repartidor_pedidos')
    
    pedidos_asignados = Pedido.objects.filter(
        repartidor=perfil_repartidor,
        estado__in=['confirmado', 'en_preparacion', 'listo', 'en_camino']
    ).select_related('cliente', 'metodo_pago').prefetch_related('detalles__producto').order_by('estado', 'fecha_creacion')
    
    hace_24_horas = timezone.now() - timedelta(hours=24)
    pedidos_entregados_recientes = Pedido.objects.filter(
        repartidor=perfil_repartidor,
        estado='entregado',
        fecha_entrega__gte=hace_24_horas
    ).select_related('cliente', 'metodo_pago').prefetch_related('detalles__producto').order_by('-fecha_entrega')
    
    total_asignados = pedidos_asignados.count()
    total_en_camino = pedidos_asignados.filter(estado='en_camino').count()
    total_entregados_hoy = Pedido.objects.filter(
        repartidor=perfil_repartidor,
        estado='entregado',
        fecha_entrega__date=timezone.now().date()
    ).count()
    
    contexto = {
        'pedidos_asignados': pedidos_asignados,
        'pedidos_entregados_recientes': pedidos_entregados_recientes,
        'total_asignados': total_asignados,
        'total_en_camino': total_en_camino,
        'total_entregados_hoy': total_entregados_hoy,
        'perfil_repartidor': perfil_repartidor,
        'titulo': 'Mis Entregas',
        'estados_disponibles': Pedido.ESTADO_CHOICES,
    }
    
    return render(request, 'core/repartidor_pedidos.html', contexto)

# Reemplaza la funciÃ³n checkout_view en views.py con esta versiÃ³n:

@login_required
def checkout_view(request):
    """Vista para procesar el checkout y crear el pedido desde el carrito (HU12)"""
    try:
        carrito = request.user.carrito
        items = carrito.items.all().select_related('producto')
    except Carrito.DoesNotExist:
        messages.error(request, 'No tienes un carrito activo.')
        return redirect('ver_carrito')
    
    if not items:
        messages.warning(request, 'Tu carrito estÃ¡ vacÃ­o. Agrega productos antes de finalizar la compra.')
        return redirect('catalogo_productos')
    
    # Validar stock disponible antes de mostrar el formulario
    for item in items:
        if item.producto.stock < item.cantidad:
            messages.error(
                request, 
                f'El producto "{item.producto.nombre}" no tiene suficiente stock. '
                f'Disponible: {item.producto.stock}, solicitado: {item.cantidad}.'
            )
            return redirect('ver_carrito')
    
    if request.method == 'POST':
        form = CheckoutForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Obtener datos del formulario
                    tipo_orden = form.cleaned_data['tipo_orden']
                    costo_envio = 2000 if tipo_orden == 'delivery' else 0
                    subtotal = carrito.total_precio
                    
                    # Crear el pedido
                    # Crear el pedido
                    pedido = Pedido.objects.create(
                    cliente=request.user,
                    nombre_referencia_cliente=form.cleaned_data.get('nombre_completo'),
                    tipo_orden=tipo_orden,
                    metodo_pago=form.cleaned_data['metodo_pago'],
                    direccion_entrega=form.cleaned_data.get('direccion_entrega', ''),
                    referencia_direccion=form.cleaned_data.get('referencia_direccion', ''),
                    notas_cliente=form.cleaned_data.get('notas', ''),
                    subtotal=subtotal,
                    costo_envio=costo_envio,
                    total=subtotal + costo_envio,
                    estado='pendiente',  # ✅ Estado inicial: pendiente de aprobación de cocina
)
                    
                    # Crear los detalles del pedido y actualizar stock
                    for item in items:
                        # Validar stock nuevamente (por si cambiÃ³ durante el proceso)
                        producto = Producto.objects.select_for_update().get(pk=item.producto.pk)
                        
                        if producto.stock < item.cantidad:
                            raise ValueError(
                                f'Stock insuficiente para {producto.nombre}. '
                                f'Disponible: {producto.stock}'
                            )
                        
                        DetallePedido.objects.create(
                            pedido=pedido,
                            producto=producto,
                            cantidad=item.cantidad,
                            precio_unitario=producto.precio
                        )
                        
                        # Reducir stock
                        producto.stock -= item.cantidad
                        producto.save()
                    
                    # Vaciar el carrito
                    carrito.items.all().delete()
                    
                    messages.success(
                        request, 
                        f'Â¡Pedido #{pedido.numero_pedido} creado exitosamente! '
                        f'Total: ${pedido.total:,.0f}. Puedes ver el estado en "Mis Pedidos".'
                    )
                    return redirect('mis_pedidos')
                    
            except ValueError as e:
                messages.error(request, str(e))
                return redirect('ver_carrito')
            except Exception as e:
                messages.error(request, f'Error al procesar el pedido: {str(e)}')
                return redirect('ver_carrito')
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario.')
    else:
        # Prellenar el formulario con datos del usuario
        initial_data = {
            'nombre_completo': request.user.get_full_name() or request.user.username,
            'telefono': request.user.telefono or '',
            'direccion_entrega': request.user.direccion or '',
        }
        form = CheckoutForm(initial=initial_data, user=request.user)
    
    # Calcular costos
    subtotal = carrito.total_precio
    costo_envio_delivery = 2000
    
    contexto = {
        'form': form,
        'carrito': carrito,
        'items': items,
        'subtotal': subtotal,
        'total': subtotal + costo_envio_delivery,  # Total inicial con delivery
        'metodos_pago': MetodoPago.objects.filter(activo=True),
    }
    return render(request, 'core/checkout.html', contexto)

@login_required
def crear_reclamo_view(request, pk_pedido):
    """Vista para que el cliente cree un reclamo sobre un pedido entregado."""
    pedido = get_object_or_404(Pedido, pk=pk_pedido, cliente=request.user)
    
    # Verificar que el pedido puede ser reclamado
    if not pedido.puede_reclamar():
        messages.error(request, 'Este pedido no puede ser reclamado en este momento.')
        return redirect('mis_pedidos')
    
    if request.method == 'POST':
        form = ReclamoForm(request.POST)
        if form.is_valid():
            reclamo = form.save(commit=False)
            reclamo.cliente = request.user
            reclamo.pedido = pedido
            reclamo.estado = 'nuevo'
            reclamo.save()
            
            messages.success(
                request, 
                f'Tu reclamo #{reclamo.id} ha sido registrado. '
                f'Nuestro equipo lo revisarÃ¡ pronto.'
            )
            return redirect('mis_pedidos')
    else:
        form = ReclamoForm()
    
    contexto = {
        'form': form,
        'pedido': pedido,
        'titulo': f'Crear Reclamo - Pedido #{pedido.numero_pedido}'
    }
    return render(request, 'core/crear_reclamo.html', contexto)



@login_required
def calificar_pedido_view(request, pk_pedido):
    """
    Vista para que el cliente evalúe un pedido.
    Incluye opción para crear un reclamo directamente.
    """
    pedido = get_object_or_404(Pedido, pk=pk_pedido, cliente=request.user)
    
    # Verificar que el pedido PUEDE ser calificado
    if not pedido.puede_ser_calificado():
        messages.error(
            request, 
            'Este pedido no puede ser evaluado en este momento. '
            'Solo se pueden evaluar pedidos entregados o cancelados que aún no tengan evaluación.'
        )
        return redirect('mis_pedidos')
    
    if request.method == 'POST':
        form_calificacion = CalificarPedidoForm(request.POST)
        form_reclamo = ReclamoRapidoForm(request.POST)
        
        if form_calificacion.is_valid():
            # Guardar la calificación
            pedido.calificacion = int(form_calificacion.cleaned_data['calificacion'])
            pedido.comentario_calificacion = form_calificacion.cleaned_data['comentario']
            pedido.fecha_calificacion = timezone.now()
            pedido.save()
            
            # ✅ VERIFICAR SI MARCÓ QUE TIENE RECLAMO
            tiene_reclamo = form_calificacion.cleaned_data.get('tiene_reclamo', False)
            
            if tiene_reclamo and form_reclamo.is_valid():
                # Crear el reclamo
                reclamo = form_reclamo.save(commit=False)
                reclamo.cliente = request.user
                reclamo.pedido = pedido
                reclamo.estado = 'nuevo'
                reclamo.save()
                
                # Notificar al administrador
                from django.contrib.auth.models import User
                admins = Usuario.objects.filter(rol='administrador')
                
                # Aquí podrías enviar email o notificación
                # Por ahora solo guardamos el reclamo
                
                messages.success(
                    request,
                    f'¡Gracias por tu evaluación! Tu reclamo #{reclamo.id} ha sido registrado. '
                    f'Nuestro equipo lo revisará pronto.'
                )
            else:
                messages.success(
                    request, 
                    '¡Gracias por tu evaluación! Tu opinión nos ayuda a mejorar.'
                )
            
            # Actualizar calificación del repartidor si existe
            if pedido.repartidor:
                from django.db.models import Avg
                pedidos_calificados = Pedido.objects.filter(
                    repartidor=pedido.repartidor,
                    calificacion__isnull=False
                )
                promedio = pedidos_calificados.aggregate(
                    promedio=Avg('calificacion')
                )['promedio']
                
                if promedio:
                    pedido.repartidor.calificacion_promedio = promedio
                    pedido.repartidor.save()
            
            return redirect('mis_pedidos')
    else:
        form_calificacion = CalificarPedidoForm()
        form_reclamo = ReclamoRapidoForm()
    
    contexto = {
        'form': form_calificacion,
        'form_reclamo': form_reclamo,
        'pedido': pedido,
        'titulo': f'Evaluar Pedido #{pedido.numero_pedido}'
    }
    return render(request, 'core/calificar_pedido.html', contexto)
@login_required
def mis_reclamos_view(request):
    """Vista para que el cliente vea sus reclamos."""
    reclamos = Reclamo.objects.filter(
        cliente=request.user
    ).select_related('pedido', 'atendido_por').order_by('-fecha_creacion')
    
    contexto = {
        'reclamos': reclamos,
        'titulo': 'Mis Reclamos'
    }
    return render(request, 'core/mis_reclamos.html', contexto)




# ========== VISTA DE COCINA (HU - Cocina) ==========
@login_required
def cocina_view(request):
    """Vista para que el personal de cocina gestione los pedidos."""
    
    # Si se actualiza el estado de un pedido
    if request.method == 'POST':
        pedido_id = request.POST.get('pedido_id')
        nuevo_estado = request.POST.get('nuevo_estado')
        notas_cocina = request.POST.get('notas_cocina', '')
        
        if pedido_id and nuevo_estado:
            try:
                pedido = Pedido.objects.get(pk=pedido_id)
                
                # Validar que solo pueda cambiar a estados permitidos
                estados_permitidos = ['confirmado', 'en_preparacion', 'listo']
                if nuevo_estado in estados_permitidos:
                    estado_anterior = pedido.estado
                    pedido.estado = nuevo_estado
                    
                    # Actualizar fechas según el estado
                    if nuevo_estado == 'confirmado' and not pedido.fecha_confirmacion:
                        pedido.fecha_confirmacion = timezone.now()
                    elif nuevo_estado == 'en_preparacion' and not pedido.fecha_preparacion:
                        pedido.fecha_preparacion = timezone.now()
                    elif nuevo_estado == 'listo' and not pedido.fecha_listo:
                        pedido.fecha_listo = timezone.now()
                    
                    # Guardar notas de cocina si existen
                    if notas_cocina:
                        pedido.notas_cocina = notas_cocina
                    
                    pedido.save()
                    
                    messages.success(
                        request,
                        f'Pedido #{pedido.numero_pedido} actualizado de "{dict(Pedido.ESTADO_CHOICES)[estado_anterior]}" a "{dict(Pedido.ESTADO_CHOICES)[nuevo_estado]}".'
                    )
                else:
                    messages.error(request, 'Estado no permitido para cocina.')
                    
            except Pedido.DoesNotExist:
                messages.error(request, 'Pedido no encontrado.')
            except Exception as e:
                messages.error(request, f'Error al actualizar el pedido: {str(e)}')
        
        return redirect('cocina_view')
    
    # ✅ NUEVO: Obtener pedidos PENDIENTES (esperando aprobación)
    pedidos_pendientes_aprobacion = Pedido.objects.filter(
        estado='pendiente'
    ).select_related('cliente', 'metodo_pago').prefetch_related('detalles__producto').order_by('fecha_creacion')
    
    # Obtener pedidos confirmados y en preparación
    pedidos_en_proceso = Pedido.objects.filter(
        estado__in=['confirmado', 'en_preparacion']
    ).select_related('cliente', 'metodo_pago').prefetch_related('detalles__producto').order_by('fecha_creacion')
    
    # Obtener pedidos listos (últimas 2 horas)
    hace_2_horas = timezone.now() - timedelta(hours=2)
    pedidos_listos = Pedido.objects.filter(
        estado='listo',
        fecha_listo__gte=hace_2_horas
    ).select_related('cliente', 'metodo_pago').prefetch_related('detalles__producto').order_by('-fecha_listo')
    
    # Estadísticas
    total_pendientes_aprobacion = pedidos_pendientes_aprobacion.count()
    total_en_proceso = pedidos_en_proceso.count()
    total_en_preparacion = pedidos_en_proceso.filter(estado='en_preparacion').count()
    total_listos_hoy = Pedido.objects.filter(
        estado='listo',
        fecha_listo__date=timezone.now().date()
    ).count()
    
    contexto = {
        'pedidos_pendientes_aprobacion': pedidos_pendientes_aprobacion,
        'pedidos_en_proceso': pedidos_en_proceso,
        'pedidos_listos': pedidos_listos,
        'total_pendientes_aprobacion': total_pendientes_aprobacion,
        'total_en_proceso': total_en_proceso,
        'total_en_preparacion': total_en_preparacion,
        'total_listos_hoy': total_listos_hoy,
        'titulo': 'Panel de Cocina',
        'estados_disponibles': Pedido.ESTADO_CHOICES,
    }
    
    return render(request, 'core/admin/cocina_view.html', contexto)

# En views.py agregar:
@login_required
@admin_required
def admin_clientes_lista(request):
    """HU01: Visualizar todos los clientes"""
    clientes = Usuario.objects.filter(rol='cliente').select_related()
    busqueda = request.GET.get('q', '')
    return render(request, 'admin/clientes_lista.html', {
        'clientes': clientes,
        'busqueda': busqueda
    })

@login_required
@admin_required
def admin_cliente_eliminar(request, pk):
    """HU02: Eliminar cliente"""
    cliente = get_object_or_404(Usuario, pk=pk, rol='cliente')
    
    if request.method == 'POST':
        # Soft delete - marcar como inactivo
        cliente.activo = False
        cliente.save()
        messages.success(request, f'Cliente {cliente.username} desactivado')
        return redirect('admin_clientes_lista')
    
    return render(request, 'admin/cliente_confirmar_eliminar.html', {
        'cliente': cliente
    })
# En views.py - Crear vista para Webpay


@login_required
def iniciar_pago_webpay(request, pedido_id):
    """Iniciar transacción con Webpay"""
    pedido = get_object_or_404(Pedido, pk=pedido_id, cliente=request.user)
    
    # Configurar transacción
    buy_order = str(pedido.numero_pedido)
    session_id = str(request.session.session_key)
    amount = int(pedido.total)
    return_url = request.build_absolute_uri(reverse('confirmar_pago_webpay'))
    
    # Crear transacción
    response = Transaction().create(buy_order, session_id, amount, return_url)
    
    return redirect(response['url'] + '?token_ws=' + response['token'])

@login_required
def confirmar_pago_webpay(request):
    """Confirmar pago desde Webpay"""
    token = request.GET.get('token_ws')
    
    if token:
        response = Transaction().commit(token)
        
        if response['response_code'] == 0:  # Aprobado
            pedido = Pedido.objects.get(numero_pedido=response['buy_order'])
            pedido.estado = 'confirmado'
            pedido.save()
            messages.success(request, 'Pago procesado exitosamente')
        else:
            messages.error(request, 'Pago rechazado')
    
    return redirect('mis_pedidos')
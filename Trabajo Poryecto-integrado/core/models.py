from django import forms
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class Usuario(AbstractUser):
      ROLES = [

            ('cliente', 'Cliente'),
            ('administrador', 'Administrador'),
            ('cajero', 'Cajero'),
            ('repartidor', 'Repartidor'),
            ('cocina', 'Cocina'),

      ]

      telefono = models.CharField(max_length=15, blank=True, null=True )
      direccion = models.TextField(blank=True, null=True)
      rol = models.CharField(max_length=20, blank=True, null=True,choices=ROLES)
      email_verificado = models.BooleanField(default=True)
      fecha_creacion = models.DateTimeField(auto_now_add=True)
      activo = models.BooleanField(default=True)

      class Meta:
            verbose_name = 'Usuario'
            verbose_name_plural = 'Usuarios'

      def __str__(self):
            return f"{self.username} - {self.get_rol_display()}"

class Categoria(models.Model):
      nombre = models.CharField(max_length=100, unique=True)
      descripcion = models.CharField(max_length=500, blank=True, null=True)
      activo = models.BooleanField(default=True)
      fecha_creacion = models.DateField(auto_now_add=True)

      class Meta:
            verbose_name = 'CategorÃ­a'
            verbose_name_plural = 'CategorÃ­as'
            ordering = ['nombre']  # â† AgreguÃ© ordenamiento
      def __str__(self):
            return self.nombre

class Producto(models.Model):
      nombre = models.CharField(max_length=100, unique=True)
      descripcion = models.CharField(max_length=500, blank=True, null=True)
      precio = models.DecimalField(max_digits=10, decimal_places= 2)
      imagen = models.ImageField(upload_to='productos/', blank=True, null=True)
      stock = models.IntegerField(default=0)
      activo = models.BooleanField(default=True)
      categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, related_name='productos')
      en_promocion = models.BooleanField(default=False, verbose_name='En PromociÃ³n')
      fecha_creacion = models.DateField(auto_now_add=True)
      fecha_actualizacion = models.DateField(auto_now=True)
      class Meta:
            verbose_name = 'Producto'
            verbose_name_plural = 'Productos'

      def __str__(self):
            return f"{self.nombre} - ${self.precio}"

      @property
      def disponible(self):
            """Verifica si el producto estÃ¡ disponible para la venta"""
            return self.activo and self.stock > 0

class Repartidor(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name='perfil_repartidor')
    vehiculo = models.CharField(max_length=100, blank=True, null=True)
    placa_vehiculo = models.CharField(max_length=20, blank=True, null=True)
    disponible = models.BooleanField(default=True)
    calificacion_promedio = models.DecimalField(max_digits=3, decimal_places=2, default=5.0)

    class Meta:
        verbose_name = 'Repartidor'
        verbose_name_plural = 'Repartidores'

    def __str__(self):
        return f"{self.usuario.get_full_name()} - {'Disponible' if self.disponible else 'No disponible'}"

class Carrito(models.Model):
      usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name="carrito")
      fecha_creacion = models.DateTimeField(auto_now_add=True)
      fecha_actualizacion = models.DateTimeField(auto_now=True)
      class Meta:
            verbose_name = 'Carrito'
            verbose_name_plural = 'Carritos'

      def __str__(self):
            return f"Carrito de {self.usuario.username}"

      @property
      def total_items(self):
            return sum(item.cantidad for item in self.items.all())

      @property
      def total_precio(self):
            return sum(item.subtotal for item in self.items.all())

class ItemCarrito(models.Model):
      carrito = models. ForeignKey(Carrito, on_delete=models.CASCADE, related_name="items")
      producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
      cantidad = models.PositiveIntegerField(default=1)
      fecha_agregado = models.DateTimeField(auto_now_add=True)

      class Meta:
            verbose_name = 'Item del Carrito'
            verbose_name_plural = 'Items del Carrito'
            unique_together = ['carrito', 'producto']
      def __str__(self):
            return f"{self.cantidad} x {self.producto.nombre}"

      @property
      def subtotal(self):
            return self.producto.precio * self.cantidad

class MetodoPago(models.Model):
      """Metodos de pagos disponibles"""
      TIPO_CHOICES = [
            ('efectivo', 'Efectivo'),
            ('tarjeta', 'Tarjeta'),
            ('transferencia', 'Transferencia'),
            ('webpay', 'Webpay'),
      ]

      nombre = models.CharField(max_length=50)
      tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
      activo = models.BooleanField(default=True)

      class Meta:
            verbose_name = 'MÃ©todo de Pago'
            verbose_name_plural = 'MÃ©todos de Pago'

      def __str__(self):
            return self.nombre

# Se crea la clase pedido y se le hereda (models.Model) lo que significa que django
# CrearÃ¡ automaticamente la tabla Pedido en la BD para guardar los pedidos
# ============================================================================
# CLASE PEDIDO - VERSIÓN COMPLETA Y CORREGIDA
# ============================================================================
class Pedido(models.Model):
    """
    Modelo que representa un pedido realizado por un cliente.
    Incluye toda la información necesaria para gestionar el pedido
    desde su creación hasta su entrega y evaluación.
    """
    
    # ========== OPCIONES DE ESTADO ==========
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('confirmado', 'Confirmado'),
        ('en_preparacion', 'En Preparación'),
        ('listo', 'Listo para Entregar'),
        ('en_camino', 'En Camino'),
        ('entregado', 'Entregado'),
        ('cancelado', 'Cancelado'),
    ]

    # ========== OPCIONES DE TIPO DE ORDEN ==========
    TIPO_ORDEN_CHOICES = [
        ('local', 'Para Comer en Local'),
        ('retiro', 'Para Retirar'),
        ('delivery', 'Delivery a Domicilio'),
    ]

    # ========== RELACIONES CON OTRAS TABLAS ==========
    cliente = models.ForeignKey(
        Usuario, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='pedidos',
        verbose_name='Cliente'
    )
    repartidor = models.ForeignKey(
        'Repartidor',  # Usa comillas si Repartidor está definido después
        on_delete=models.SET_NULL,
        null=True, 
        blank=True,
        related_name='pedidos_asignados',
        verbose_name='Repartidor'
    )
    metodo_pago = models.ForeignKey(
        'MetodoPago',
        on_delete=models.PROTECT,
        verbose_name='Método de Pago'
    )

    # ========== INFORMACIÓN BÁSICA DEL PEDIDO ==========
    numero_pedido = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        verbose_name='Número de Pedido'
    )
    tipo_orden = models.CharField(
        max_length=20,
        choices=TIPO_ORDEN_CHOICES,
        default='local',
        verbose_name='Tipo de Orden'
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='pendiente',
        verbose_name='Estado'
    )

    # ========== INFORMACIÓN DE ENTREGA ==========
    direccion_entrega = models.TextField(
        max_length=1200,
        null=True,
        blank=True,
        verbose_name='Dirección de Entrega'
    )
    referencia_direccion = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name='Referencia de Dirección'
    )
    nombre_referencia_cliente = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='Nombre de Referencia'
    )

    # ========== INFORMACIÓN FINANCIERA ==========
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Subtotal'
    )
    costo_envio = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Costo de Envío'
    )
    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Total'
    )

    # ========== NOTAS Y OBSERVACIONES ==========
    notas_cliente = models.TextField(
        blank=True,
        null=True,
        verbose_name='Notas del Cliente'
    )
    notas_cocina = models.TextField(
        blank=True,
        null=True,
        verbose_name='Notas de Cocina'
    )

    # ========== FECHAS Y TIMESTAMPS ==========
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de Creación'
    )
    fecha_confirmacion = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha de Confirmación'
    )
    fecha_preparacion = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha de Preparación'
    )
    fecha_listo = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha Listo'
    )
    fecha_entrega = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha de Entrega'
    )

    # ========== CAMPOS PARA EVALUACIÓN DEL PEDIDO ==========
    calificacion = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Calificación del 1 al 5",
        verbose_name='Calificación'
    )
    comentario_calificacion = models.TextField(
        blank=True,
        null=True,
        help_text="Comentario opcional sobre el pedido",
        verbose_name='Comentario de Calificación'
    )
    fecha_calificacion = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha de Calificación'
    )

    # ========== METADATA ==========
    class Meta:
        verbose_name = 'Pedido'
        verbose_name_plural = 'Pedidos'
        ordering = ['-fecha_creacion']
        indexes = [
            models.Index(fields=['estado', '-fecha_creacion']),
            models.Index(fields=['numero_pedido']),
            models.Index(fields=['cliente', '-fecha_creacion']),
        ]

    # ========== MÉTODOS DE REPRESENTACIÓN ==========
    def __str__(self):
        """Representación en string del pedido"""
        cliente_str = (
            self.nombre_referencia_cliente or
            (self.cliente.username if self.cliente else "N/A")
        )
        return f"#{self.numero_pedido} - Pedido de {cliente_str}"

    # ========== MÉTODO SAVE PERSONALIZADO ==========
    def save(self, *args, **kwargs):
        """
        Método save personalizado para generar número de pedido automático
        si no existe uno.
        """
        if not self.numero_pedido:
            import random
            import string

            # Generar número aleatorio de 8 dígitos
            self.numero_pedido = ''.join(random.choices(string.digits, k=8))
            
            # Asegurar que sea único
            while Pedido.objects.filter(numero_pedido=self.numero_pedido).exists():
                self.numero_pedido = ''.join(random.choices(string.digits, k=8))
        
        super().save(*args, **kwargs)

    # ========== MÉTODOS DE VALIDACIÓN Y LÓGICA DE NEGOCIO ==========
    def puede_ser_calificado(self):
        """
        Verifica si el pedido puede ser calificado por el cliente.
        
        Returns:
            bool: True si el pedido está entregado o cancelado y no tiene calificación
        """
        return (
            self.estado in ['entregado', 'cancelado'] and
            self.calificacion is None
        )

    def puede_reclamar(self):
        """
        Verifica si el pedido puede tener un reclamo.
        
        Returns:
            bool: True si el pedido está entregado y no tiene reclamos activos
        """
        if self.estado != 'entregado':
            return False
        
        # Verificar si ya tiene un reclamo (asume relación reclamos)
        if hasattr(self, 'reclamos'):
            return not self.reclamos.exists()
        
        return True

    def puede_cancelarse(self):
        """
        Verifica si el pedido puede ser cancelado.
        
        Returns:
            bool: True si el pedido está en estado que permite cancelación
        """
        return self.estado in ['pendiente', 'confirmado']

    def esta_en_proceso(self):
        """
        Verifica si el pedido está en proceso de preparación/entrega.
        
        Returns:
            bool: True si el pedido está en preparación o camino
        """
        return self.estado in ['en_preparacion', 'listo', 'en_camino']

    def esta_finalizado(self):
        """
        Verifica si el pedido ya fue finalizado.
        
        Returns:
            bool: True si el pedido está entregado o cancelado
        """
        return self.estado in ['entregado', 'cancelado']

    # ========== MÉTODOS PARA CALCULAR TIEMPOS ==========
    def tiempo_total_preparacion(self):
        """
        Calcula el tiempo total de preparación del pedido.
        
        Returns:
            timedelta o None: Tiempo entre creación y estar listo
        """
        if self.fecha_listo and self.fecha_creacion:
            return self.fecha_listo - self.fecha_creacion
        return None

    def tiempo_entrega(self):
        """
        Calcula el tiempo de entrega del pedido.
        
        Returns:
            timedelta o None: Tiempo entre creación y entrega
        """
        if self.fecha_entrega and self.fecha_creacion:
            return self.fecha_entrega - self.fecha_creacion
        return None

    # ========== PROPIEDADES CALCULADAS ==========
    @property
    def tiene_calificacion(self):
        """Verifica si el pedido tiene calificación"""
        return self.calificacion is not None

    @property
    def calificacion_estrellas(self):
        """
        Retorna la calificación en formato de estrellas.
        
        Returns:
            str: String con estrellas llenas y vacías
        """
        if not self.calificacion:
            return "Sin calificar"
        
        estrellas_llenas = "★" * self.calificacion
        estrellas_vacias = "☆" * (5 - self.calificacion)
        return estrellas_llenas + estrellas_vacias

    @property
    def es_delivery(self):
        """Verifica si el pedido es de tipo delivery"""
        return self.tipo_orden == 'delivery'

    @property
    def requiere_repartidor(self):
        """Verifica si el pedido requiere asignación de repartidor"""
        return self.es_delivery and self.estado in [
            'confirmado', 'en_preparacion', 'listo', 'en_camino'
        ]

    @property
    def dias_desde_creacion(self):
        """
        Calcula los días transcurridos desde la creación del pedido.
        
        Returns:
            int: Número de días
        """
        if self.fecha_creacion:
            delta = timezone.now() - self.fecha_creacion
            return delta.days
        return 0


class DetallePedido(models.Model):
      pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='detalles')
      producto = models.ForeignKey(Producto, on_delete=models.PROTECT) # PROTECT evita borrar producto si estÃ¡ en un pedido
      cantidad = models.PositiveIntegerField()
      precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
      subtotal = models.DecimalField(max_digits=10, decimal_places=2) # Se calcula al guardar

      class Meta:
            verbose_name = 'Detalle del Pedido'
            verbose_name_plural = 'Detalles del Pedido'

      def __str__(self):
            return f"{self.cantidad}x {self.producto.nombre} - {self.pedido.numero_pedido}"

      def save(self, *args, **kwargs):
            self.subtotal = self.precio_unitario * self.cantidad
            super().save(*args, **kwargs)

# En core/models.py
# BUSCAR la clase Reclamo y REEMPLAZAR con esta versión completa:

class Reclamo(models.Model):
    """
    Modelo para gestionar reclamos de clientes sobre pedidos.
    Incluye sistema de seguimiento y calificación de atención.
    """
    
    # ========== OPCIONES DE MOTIVO ==========
    MOTIVO_CHOICES = [
        ('pedido_incorrecto', 'Pedido Incorrecto'),
        ('producto_danado', 'Producto Dañado'),
        ('demora_excesiva', 'Demora Excesiva'),
        ('mala_atencion', 'Mala Atención'),
        ('calidad_producto', 'Mala Calidad del Producto'),
        ('producto_faltante', 'Producto Faltante'),
        ('otro', 'Otro'),
    ]

    # ========== OPCIONES DE ESTADO ==========
    ESTADO_CHOICES = [
        ('nuevo', 'Nuevo'),
        ('en_revision', 'En Revisión'),
        ('respondido', 'Respondido'),
        ('resuelto', 'Resuelto'),
        ('cerrado', 'Cerrado'),
    ]

    # ========== RELACIONES ==========
    cliente = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='reclamos',
        verbose_name='Cliente'
    )
    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name='reclamos',
        verbose_name='Pedido'
    )

    # ========== INFORMACIÓN DEL RECLAMO ==========
    motivo = models.CharField(
        max_length=20,
        choices=MOTIVO_CHOICES,
        verbose_name='Motivo'
    )
    descripcion = models.TextField(
        verbose_name='Descripción del Problema'
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='nuevo',
        verbose_name='Estado'
    )

    # ========== RESPUESTA DEL ADMINISTRADOR ==========
    respuesta = models.TextField(
        blank=True,
        null=True,
        verbose_name='Respuesta del Administrador'
    )
    atendido_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reclamos_atendidos',
        verbose_name='Atendido Por'
    )

    # ========== FECHAS ==========
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de Creación'
    )
    fecha_respuesta = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha de Respuesta'
    )

    # ========== CALIFICACIÓN DE ATENCIÓN ==========
    calificacion_atencion = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Calificación de 1 a 5 sobre cómo fue atendido el reclamo",
        verbose_name='Calificación de Atención'
    )

    # ========== METADATA ==========
    class Meta:
        verbose_name = 'Reclamo'
        verbose_name_plural = 'Reclamos'
        ordering = ['-fecha_creacion']
        indexes = [
            models.Index(fields=['estado', '-fecha_creacion']),
            models.Index(fields=['cliente', '-fecha_creacion']),
        ]

    # ========== MÉTODOS ==========
    def __str__(self):
        return f"#{self.id} Reclamo - {self.cliente.username} - {self.get_motivo_display()}"

    def puede_ser_calificado(self):
        """Retorna True si el reclamo puede ser calificado por el cliente"""
        return (
            self.estado in ['resuelto', 'cerrado'] and
            self.calificacion_atencion is None
        )

    def esta_pendiente(self):
        """Verifica si el reclamo está pendiente de atención"""
        return self.estado in ['nuevo', 'en_revision']

    def fue_atendido(self):
        """Verifica si el reclamo ya fue atendido"""
        return self.estado in ['respondido', 'resuelto', 'cerrado']

    @property
    def dias_sin_respuesta(self):
        """Calcula días desde creación sin respuesta"""
        if self.fecha_respuesta:
            return 0
        from django.utils import timezone
        delta = timezone.now() - self.fecha_creacion
        return delta.days

    @property
    def es_urgente(self):
        """Marca como urgente si lleva más de 2 días sin respuesta"""
        return self.dias_sin_respuesta > 2 and self.esta_pendiente()
    
class Meta:
        verbose_name = 'Reclamo'
        verbose_name_plural = 'Reclamos'
        ordering = ['-fecha_creacion']
        
def puede_ser_calificado(self):
        """Retorna True si el reclamo fue resuelto/cerrado y no tiene calificaciÃ³n"""
        return self.estado in ['resuelto', 'cerrado'] and self.calificacion_atencion is None

class Slide(models.Model):
      """Modelo para gestionar los slides del carrusel de la pÃ¡gina de inicio."""
      imagen = models.ImageField(upload_to='slides/', blank=True, null=True, help_text="TamaÃ±o recomendado: 1200x600px")
      titulo = models.CharField(max_length=100, blank=True, null=True, help_text="TÃ­tulo principal que aparece sobre la imagen.")
      subtitulo = models.CharField(max_length=200, blank=True, null=True, help_text="Texto secundario debajo del tÃ­tulo.")
      texto_boton = models.CharField(max_length=50, default="Ver mÃ¡s")
      link_boton = models.CharField(max_length=200, help_text="Enlace del botÃ³n. Ej: /catalogo/?categoria=1 o /#seccion")
      orden = models.PositiveIntegerField(default=0, help_text="NÃºmero para ordenar los slides. Menor nÃºmero aparece primero.")
      activo = models.BooleanField(default=True, help_text="Marcar para mostrar este slide en el carrusel.")

      class Meta:
            verbose_name = 'Slide del Carrusel'
            verbose_name_plural = 'Slides del Carrusel'
            ordering = ['orden']

      def __str__(self):
            return self.titulo or f"Slide {self.id}"
      

class PersonalizacionPedido(models.Model):
    """Personalizaciones de productos en pedidos"""
    detalle_pedido = models.ForeignKey(
        DetallePedido, 
        on_delete=models.CASCADE,
        related_name='personalizaciones'
    )
    tipo = models.CharField(max_length=20, choices=[
        ('agregar', 'Agregar'),
        ('quitar', 'Quitar'),
        ('cambiar', 'Cambiar'),
    ])
    ingrediente = models.CharField(max_length=100)
    costo_adicional = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=0
    )
    
    def __str__(self):
        return f"{self.get_tipo_display()} {self.ingrediente}"

# En checkout agregar campo para personalizaciones
class CheckoutForm(forms.Form):
    # ... campos existentes
    personalizaciones = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'placeholder': 'Ej: Sin cebolla, Extra queso, etc.'
        })
    )
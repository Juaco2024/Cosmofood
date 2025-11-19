from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import Usuario, Producto, Repartidor, MetodoPago, Reclamo, Pedido
from django.core.exceptions import ValidationError
import re

# Clases de Tailwind CSS para inputs
TAILWIND_INPUT_CLASSES = 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent transition'
TAILWIND_TEXTAREA_CLASSES = 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent transition'
TAILWIND_SELECT_CLASSES = 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent transition'
TAILWIND_CHECKBOX_CLASSES = 'h-4 w-4 text-primary focus:ring-primary border-gray-300 rounded'

class RegistroForm(UserCreationForm):
    """Formulario de registro de usuarios (HU05)"""
    
    # Nota: Usamos los nombres de campo del modelo Usuario (email, first_name, last_name)
    # pero los etiquetamos como quieras mostrarlos al usuario
    
    email = forms.EmailField(
        required=True,
        label='Correo ElectrÃ³nico',
        widget=forms.EmailInput(attrs={
            'class': TAILWIND_INPUT_CLASSES, 
            'placeholder': 'tucorreo@ejemplo.com'
        })
    )
    
    first_name = forms.CharField(
        max_length=150, 
        required=True, 
        label='Nombres',
        widget=forms.TextInput(attrs={
            'class': TAILWIND_INPUT_CLASSES,
            'placeholder': 'Ingresa tu nombre'
        })
    )
    
    last_name = forms.CharField(
        max_length=150, 
        required=True, 
        label='Apellidos',
        widget=forms.TextInput(attrs={
            'class': TAILWIND_INPUT_CLASSES,
            'placeholder': 'Ingresa tu apellido'
        })
    )
    
    telefono = forms.CharField(
        max_length=15, 
        required=False, 
        label='TelÃ©fono',
        widget=forms.TextInput(attrs={
            'class': TAILWIND_INPUT_CLASSES,
            'placeholder': '+569 1234 5678'
        })
    )
    
    direccion = forms.CharField(
        required=False, 
        label='DirecciÃ³n',
        widget=forms.Textarea(attrs={
            'class': TAILWIND_TEXTAREA_CLASSES,
            'rows': 3,
            'placeholder': 'Ingresa tu direcciÃ³n (opcional)'
        })
    )
    
    class Meta:
        model = Usuario
        # IMPORTANTE: Estos nombres DEBEN coincidir con los campos del modelo Usuario
        fields = ['username', 'email', 'first_name', 'last_name', 'telefono', 'direccion', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': TAILWIND_INPUT_CLASSES, 
                'placeholder': 'Nombre de usuario'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # AÃ±adir clases de Tailwind a los campos de contraseÃ±a
        self.fields['password1'].widget.attrs.update({
            'class': TAILWIND_INPUT_CLASSES, 
            'placeholder': 'ContraseÃ±a'
        })
        self.fields['password2'].widget.attrs.update({
            'class': TAILWIND_INPUT_CLASSES,
            'placeholder': 'Confirmar contraseÃ±a'
        })
        
        # Personalizar mensajes de ayuda
        self.fields['password1'].help_text = 'MÃ­nimo 8 caracteres, debe contener una mayÃºscula y un nÃºmero'
    
    def clean_email(self):
        """Validar que el email no estÃ© registrado (HU05)"""
        email = self.cleaned_data.get('email')
        if Usuario.objects.filter(email=email).exists():
            raise ValidationError('Este correo electrÃ³nico ya estÃ¡ registrado.')
        return email
    
    def clean_password1(self):
        """Validar requisitos de contraseÃ±a: mÃ­nimo 8 caracteres, una mayÃºscula y un nÃºmero (HU05)"""
        password = self.cleaned_data.get('password1')
        
        if len(password) < 8:
            raise ValidationError('La contraseÃ±a debe tener al menos 8 caracteres.')
        
        if not re.search(r'[A-Z]', password):
            raise ValidationError('La contraseÃ±a debe contener al menos una letra mayÃºscula.')
        
        if not re.search(r'\d', password):
            raise ValidationError('La contraseÃ±a debe contener al menos un nÃºmero.')
        
        return password
    
    def save(self, commit=True):
        """Guardar usuario con rol de cliente por defecto"""
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.rol = 'cliente'  # Por defecto todos son clientes
        
        if commit:
            user.save()
        return user
        
class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label='Usuario',
        widget=forms.TextInput(attrs={
            'class': TAILWIND_INPUT_CLASSES,
            'placeholder': 'Nombre de usuario',
            'autofocus': True
        })
    )
    password = forms.CharField(
          label='ContraseÃ±a',
          widget=forms.PasswordInput(attrs={
              'class': TAILWIND_INPUT_CLASSES, 
              'placeholder': 'ContraseÃ±a'
          })
    )
    
class PerfilForm(forms.ModelForm):
      
    class Meta:
        model = Usuario
        fields = ['first_name', 'last_name', 'email', 'telefono', 'direccion']
        labels = {
            'first_name': 'Nombres',
            'last_name': 'Apellidos',
            'email': 'Correo ElectrÃ³nico',
            'telefono': 'TelÃ©fono',
            'direccion': 'DirecciÃ³n'
        }
        widgets = {
            'first_name': forms.TextInput(attrs={'class': TAILWIND_INPUT_CLASSES}),
            'last_name': forms.TextInput(attrs={'class': TAILWIND_INPUT_CLASSES}),
            'email': forms.EmailInput(attrs={'class': TAILWIND_INPUT_CLASSES}),
            'telefono': forms.TextInput(attrs={'class': TAILWIND_INPUT_CLASSES}),
            'direccion': forms.Textarea(attrs={'class': TAILWIND_TEXTAREA_CLASSES, 'rows': 3})
        }
        
class RecuperarPasswordForm(forms.Form):
    email = forms.EmailField(
        label='Correo ElectrÃ³nico',
        widget=forms.EmailInput(attrs={
            'class': TAILWIND_INPUT_CLASSES,
            'placeholder': 'tucorreo@ejemplo.com'
        }),
        help_text='Ingresa el correo con el que te registraste'
    )

class ResetPasswordForm(forms.Form):
    password1 = forms.CharField(
        label='Nueva ContraseÃ±a',
        widget=forms.PasswordInput(attrs={
            'class': TAILWIND_INPUT_CLASSES,
            'placeholder': 'Ingresa tu nueva contraseÃ±a'
        })
    )
    password2 = forms.CharField(
        label='Confirmar Nueva ContraseÃ±a',
        widget=forms.PasswordInput(attrs={
            'class': TAILWIND_INPUT_CLASSES,
            'placeholder': 'Confirma tu nueva contraseÃ±a'
        })
    )

class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = [ 'nombre', 'descripcion', 'precio', 'imagen', 'stock', 'categoria', 'activo', 'en_promocion' ]
        widgets = {
                'nombre': forms.TextInput(attrs={'class': TAILWIND_INPUT_CLASSES}),
                'descripcion': forms.Textarea(attrs={'class': TAILWIND_TEXTAREA_CLASSES, 'rows': 3}),
                'precio': forms.NumberInput(attrs={'class': TAILWIND_INPUT_CLASSES, 'step': '0.01'}),
                # Nota: El widget para un ImageField/FileField es FileInput
                'imagen': forms.FileInput(attrs={'class': TAILWIND_INPUT_CLASSES}),
                'stock': forms.NumberInput(attrs={'class': TAILWIND_INPUT_CLASSES}),
                'categoria':forms.Select(attrs={'class': TAILWIND_SELECT_CLASSES}),
                'activo': forms.CheckboxInput(attrs={'class': TAILWIND_CHECKBOX_CLASSES}),
                'en_promocion': forms.CheckboxInput(attrs={'class': TAILWIND_CHECKBOX_CLASSES}),
            }

class RepartidorForm(forms.Form):
    username = forms.CharField(
        label='Nombre de Usuario', required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: juanito_delivery'}) 
    )
    email = forms.EmailField(
        label='Correo ElectrÃ³nico', required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'correo@ejemplo.com'}) 
    )
    first_name = forms.CharField(
        label='Nombres', required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}) 
    )
    last_name = forms.CharField(
        label='Apellidos', required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}) 
    )
    telefono = forms.CharField(
        label='TelÃ©fono', required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+569...'}) 
    )
    # Campos para contraseÃ±a
    password = forms.CharField(
        label='ContraseÃ±a', required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control'}), 
        help_text="Dejar en blanco para no cambiar la contraseÃ±a existente."
    )
    password_confirm = forms.CharField(
        label='Confirmar ContraseÃ±a', required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

    # Campos del Modelo Repartidor
    vehiculo = forms.CharField(
        label='VehÃ­culo', required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Moto Honda CB190R'})
    )
    placa_vehiculo = forms.CharField(
        label='Placa Patente', required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: ABCD12'}) 
    )
    disponible = forms.BooleanField(
        label='Disponible para entregas', required=False, initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}) 
    )

    # Constructor para manejar ediciÃ³n
    def __init__(self, *args, **kwargs):
        instance_usuario = kwargs.pop('instance', None)
        instance_perfil = kwargs.pop('instance_perfil', None)
        super().__init__(*args, **kwargs)

        if instance_usuario: # Editando
            self.fields['username'].initial = instance_usuario.username
            self.fields['username'].widget.attrs['readonly'] = True
            self.fields['email'].initial = instance_usuario.email
            self.fields['first_name'].initial = instance_usuario.first_name
            self.fields['last_name'].initial = instance_usuario.last_name
            self.fields['telefono'].initial = instance_usuario.telefono
            self.fields['password'].required = False
            self.fields['password_confirm'].required = False

            if instance_perfil:
                self.fields['vehiculo'].initial = instance_perfil.vehiculo
                self.fields['placa_vehiculo'].initial = instance_perfil.placa_vehiculo
                self.fields['disponible'].initial = instance_perfil.disponible
        else: # Creando
             self.fields['password'].required = True
             self.fields['password_confirm'].required = True

    # ValidaciÃ³n contraseÃ±as
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")
        if password and password != password_confirm:
            self.add_error('password_confirm', "Las contraseÃ±as no coinciden.")
        return cleaned_data

    # ValidaciÃ³n username Ãºnico (al crear)
    def clean_username(self):
        username = self.cleaned_data['username']
        if not self.initial and Usuario.objects.filter(username=username).exists():
            raise forms.ValidationError("Este nombre de usuario ya estÃ¡ en uso.")
        return username

    # ValidaciÃ³n email Ãºnico
    def clean_email(self):
        email = self.cleaned_data['email']
        username = self.cleaned_data.get('username')
        query = Usuario.objects.filter(email=email)
        if self.initial:
            query = query.exclude(username=username)
        if query.exists():
             raise forms.ValidationError("Este correo electrÃ³nico ya estÃ¡ registrado por otro usuario.")
        return email
    

# Reemplaza la clase CheckoutForm en forms.py con esta versiÃ³n completa:

class CheckoutForm(forms.Form):
    """Formulario para el proceso de checkout (HU12)"""
    
    # Datos de contacto
    nombre_completo = forms.CharField(
        max_length=200,
        required=True,
        label='Nombre Completo',
        widget=forms.TextInput(attrs={
            'class': TAILWIND_INPUT_CLASSES,
            'placeholder': 'Juan PÃ©rez'
        })
    )
    
    telefono = forms.CharField(
        max_length=15,
        required=True,
        label='TelÃ©fono',
        widget=forms.TextInput(attrs={
            'class': TAILWIND_INPUT_CLASSES,
            'placeholder': '+56 9 1234 5678'
        })
    )
    
    # Tipo de orden
    TIPO_ORDEN_CHOICES = [
        ('delivery', 'Delivery a Domicilio'),
        ('retiro', 'Retiro en Local'),
    ]
    
    tipo_orden = forms.ChoiceField(
        choices=TIPO_ORDEN_CHOICES,
        widget=forms.RadioSelect,
        required=True,
        initial='delivery',
        label='Tipo de Entrega'
    )
    
    # DirecciÃ³n (solo para delivery)
    direccion_entrega = forms.CharField(
        required=False,
        label='DirecciÃ³n de Entrega',
        widget=forms.Textarea(attrs={
            'class': TAILWIND_TEXTAREA_CLASSES,
            'rows': 3,
            'placeholder': 'Calle, nÃºmero, departamento...'
        })
    )
    
    referencia_direccion = forms.CharField(
        max_length=200,
        required=False,
        label='Referencia de DirecciÃ³n',
        widget=forms.TextInput(attrs={
            'class': TAILWIND_INPUT_CLASSES,
            'placeholder': 'Casa amarilla, portÃ³n negro...'
        })
    )
    
    # MÃ©todo de pago
    metodo_pago = forms.ModelChoiceField(
        queryset=MetodoPago.objects.none(),  # Se carga dinÃ¡micamente
        required=True,
        label='MÃ©todo de Pago',
        widget=forms.RadioSelect
    )
    
    # Notas adicionales
    notas = forms.CharField(
        required=False,
        label='Notas Adicionales',
        widget=forms.Textarea(attrs={
            'class': TAILWIND_TEXTAREA_CLASSES,
            'rows': 3,
            'placeholder': 'Instrucciones especiales, alergias, etc.'
        })
    )
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Cargar mÃ©todos de pago activos
        self.fields['metodo_pago'].queryset = MetodoPago.objects.filter(activo=True)
        
        # Si hay usuario, prellenar datos
        if user:
            if not self.initial.get('nombre_completo'):
                self.initial['nombre_completo'] = user.get_full_name() or user.username
            if not self.initial.get('telefono'):
                self.initial['telefono'] = user.telefono or ''
            if not self.initial.get('direccion_entrega'):
                self.initial['direccion_entrega'] = user.direccion or ''
    
    def clean(self):
        cleaned_data = super().clean()
        tipo_orden = cleaned_data.get('tipo_orden')
        direccion_entrega = cleaned_data.get('direccion_entrega')
        
        # Validar que si es delivery, debe haber direcciÃ³n
        if tipo_orden == 'delivery' and not direccion_entrega:
            self.add_error('direccion_entrega', 'La direcciÃ³n es obligatoria para pedidos con delivery.')
        
        return cleaned_data
    
class ReclamoForm(forms.ModelForm):
    """Formulario para crear un reclamo"""
    class Meta:
        model = Reclamo
        fields = ['motivo', 'descripcion']
        widgets = {
            'motivo': forms.Select(attrs={
                'class': TAILWIND_SELECT_CLASSES
            }),
            'descripcion': forms.Textarea(attrs={
                'class': TAILWIND_TEXTAREA_CLASSES,
                'rows': 5,
                'placeholder': 'Describe detalladamente tu problema o inconformidad...'
            })
        }
        labels = {
            'motivo': 'Motivo del Reclamo',
            'descripcion': 'DescripciÃ³n Detallada'
        }

class CalificarPedidoForm(forms.Form):
    """Formulario para evaluar un pedido con opción de reclamo"""
    
    calificacion = forms.ChoiceField(
        choices=[(i, f'{i} estrella{"s" if i > 1 else ""}') for i in range(1, 6)],
        widget=forms.RadioSelect(attrs={
            'class': 'calificacion-radio'
        }),
        label='¿Cómo calificarías tu pedido?',
        required=True
    )
    
    comentario = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent transition',
            'rows': 4,
            'placeholder': '¿Qué te pareció el servicio y la comida? (Opcional)'
        }),
        label='Comentario (Opcional)'
    )
    
    # ✅ NUEVO: Campo para indicar si hay un problema
    tiene_reclamo = forms.BooleanField(
        required=False,
        label='¿Tienes algún problema o reclamo?',
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 text-red-600 border-gray-300 rounded focus:ring-red-500',
            'id': 'tiene_reclamo'
        })
    )


# ✅ NUEVO: Formulario específico para crear reclamo desde evaluación
class ReclamoRapidoForm(forms.ModelForm):
    """Formulario rápido para crear un reclamo desde la evaluación"""
    
    class Meta:
        model = Reclamo
        fields = ['motivo', 'descripcion']
        widgets = {
            'motivo': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent transition'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent transition',
                'rows': 5,
                'placeholder': 'Describe detalladamente el problema que tuviste con tu pedido...'
            })
        }
        labels = {
            'motivo': '¿Cuál es el motivo de tu reclamo?',
            'descripcion': 'Describe el problema en detalle'
        }
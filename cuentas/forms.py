from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    PasswordResetForm,
    SetPasswordForm,
    UserCreationForm,
)

from franchesco.forms_utils import BootstrapMixin

from .models import Usuario


class RegistroForm(BootstrapMixin, UserCreationForm):
    """CU-05: Registrarse."""

    acepta_terminos = forms.BooleanField(
        label='Acepto los términos y condiciones y la política de privacidad',
        required=True,
    )

    class Meta:
        model = Usuario
        fields = ('first_name', 'last_name', 'email', 'telefono')
        labels = {'first_name': 'Nombre', 'last_name': 'Apellido'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['email'].widget.attrs['placeholder'] = 'tu@email.com'
        self.fields['email'].widget.attrs['autocomplete'] = 'email'

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if Usuario.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Ya existe una cuenta registrada con este correo.')
        return email


class LoginForm(BootstrapMixin, AuthenticationForm):
    """CU-06: Iniciar sesión con correo y contraseña."""

    error_messages = {
        'invalid_login': 'Correo o contraseña incorrectos. Verificá los datos e intentá de nuevo.',
        'inactive': 'Esta cuenta está desactivada. Contactá a la tienda.',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Correo electrónico'
        self.fields['username'].widget.attrs['placeholder'] = 'tu@email.com'


class PerfilForm(BootstrapMixin, forms.ModelForm):
    """CU-08 / CU-09: Consultar y modificar información de la cuenta."""

    class Meta:
        model = Usuario
        fields = ('first_name', 'last_name', 'email', 'telefono',
                  'direccion', 'ciudad', 'codigo_postal')
        labels = {'first_name': 'Nombre', 'last_name': 'Apellido'}

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if Usuario.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Ese correo ya está en uso por otra cuenta.')
        return email


class CambiarPasswordForm(BootstrapMixin, PasswordChangeForm):
    pass


class RecuperarPasswordForm(BootstrapMixin, PasswordResetForm):
    """Pide el correo para enviar el enlace de recuperación."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].label = 'Correo electrónico'
        self.fields['email'].widget.attrs['placeholder'] = 'tu@email.com'


class NuevaPasswordForm(BootstrapMixin, SetPasswordForm):
    """Elegir la contraseña nueva desde el enlace del mail."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['new_password1'].label = 'Contraseña nueva'
        self.fields['new_password2'].label = 'Repetí la contraseña nueva'

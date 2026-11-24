import string

from django.core.exceptions import ValidationError


class MayusculaValidator:
    """La contraseña debe tener al menos una letra mayúscula."""

    def validate(self, password, user=None):
        if not any(c.isupper() for c in password):
            raise ValidationError('La contraseña debe contener al menos una letra mayúscula.', code='sin_mayuscula')

    def get_help_text(self):
        return 'Su contraseña debe contener al menos una letra mayúscula.'


class SimboloValidator:
    """La contraseña debe tener al menos un signo (punto, guion, @, !, #, etc.)."""

    def validate(self, password, user=None):
        if not any(c in string.punctuation or (not c.isalnum() and not c.isspace()) for c in password):
            raise ValidationError('La contraseña debe contener al menos un signo (por ejemplo . - _ @ ! # $).', code='sin_simbolo')

    def get_help_text(self):
        return 'Su contraseña debe contener al menos un signo (por ejemplo . - _ @ ! # $).'


class NumeroValidator:
    """La contraseña debe tener al menos un número."""

    def validate(self, password, user=None):
        if not any(c.isdigit() for c in password):
            raise ValidationError('La contraseña debe contener al menos un número.', code='sin_numero')

    def get_help_text(self):
        return 'Su contraseña debe contener al menos un número.'

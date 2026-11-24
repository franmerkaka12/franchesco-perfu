from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UsuarioManager(BaseUserManager):
    """Manager para un usuario que inicia sesión con su correo electrónico."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra):
        if not email:
            raise ValueError('El correo electrónico es obligatorio.')
        email = self.normalize_email(email).lower()
        usuario = self.model(email=email, **extra)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_user(self, email, password=None, **extra):
        extra.setdefault('is_staff', False)
        extra.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault('is_staff', True)
        extra.setdefault('is_superuser', True)
        extra.setdefault('rol', Usuario.Rol.ADMIN)
        return self._create_user(email, password, **extra)


class Usuario(AbstractUser):
    """Usuario del sistema (diagrama de clases: Usuario / Cliente / Administrador).

    Se usa un único modelo con un campo `rol` para diferenciar perfiles
    de acceso (RF-06, RNF-03, RNF-04).
    """

    class Rol(models.TextChoices):
        CLIENTE = 'cliente', 'Cliente'
        ADMIN = 'admin', 'Administrador'

    username = None
    email = models.EmailField('correo electrónico', unique=True)
    rol = models.CharField(max_length=10, choices=Rol.choices, default=Rol.CLIENTE)

    # Datos del cliente
    telefono = models.CharField('teléfono', max_length=30, blank=True)
    direccion = models.CharField('dirección', max_length=200, blank=True)
    ciudad = models.CharField(max_length=100, blank=True)
    codigo_postal = models.CharField('código postal', max_length=10, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = UsuarioManager()

    class Meta:
        verbose_name = 'usuario'
        verbose_name_plural = 'usuarios'
        ordering = ['-date_joined']

    def __str__(self):
        return self.get_full_name() or self.email

    @property
    def es_admin(self):
        return self.is_superuser or self.rol == self.Rol.ADMIN

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.lower()
        # Los administradores también pueden entrar al admin técnico de Django.
        if self.rol == self.Rol.ADMIN:
            self.is_staff = True
        elif not self.is_superuser:
            self.is_staff = False
        super().save(*args, **kwargs)

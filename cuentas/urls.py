from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LogoutView
from django.urls import path, reverse_lazy

from . import views
from .forms import NuevaPasswordForm, RecuperarPasswordForm

app_name = 'cuentas'

urlpatterns = [
    path('ingresar/', views.IngresarView.as_view(), name='login'),
    path('salir/', LogoutView.as_view(), name='logout'),  # CU-07 (requiere POST)
    path('registro/', views.registro, name='registro'),
    path('mi-cuenta/', views.perfil, name='perfil'),
    path('mi-cuenta/contrasena/', views.cambiar_password, name='cambiar_password'),

    # Recuperar contraseña por mail
    path('recuperar/', auth_views.PasswordResetView.as_view(
        template_name='cuentas/recuperar.html',
        form_class=RecuperarPasswordForm,
        subject_template_name='cuentas/emails/recuperar_asunto.txt',
        email_template_name='cuentas/emails/recuperar.txt',
        html_email_template_name='cuentas/emails/recuperar.html',
        success_url=reverse_lazy('cuentas:recuperar_enviado'),
    ), name='recuperar'),
    path('recuperar/enviado/', auth_views.PasswordResetDoneView.as_view(
        template_name='cuentas/recuperar_enviado.html',
    ), name='recuperar_enviado'),
    path('recuperar/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='cuentas/recuperar_nueva.html',
        form_class=NuevaPasswordForm,
        success_url=reverse_lazy('cuentas:recuperar_listo'),
    ), name='recuperar_confirmar'),
    path('recuperar/listo/', auth_views.PasswordResetCompleteView.as_view(
        template_name='cuentas/recuperar_listo.html',
    ), name='recuperar_listo'),
]

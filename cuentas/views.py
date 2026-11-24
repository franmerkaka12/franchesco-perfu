from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import CambiarPasswordForm, LoginForm, PerfilForm, RegistroForm


def _destino_seguro(request, por_defecto):
    destino = request.POST.get('next') or request.GET.get('next')
    if destino and url_has_allowed_host_and_scheme(destino, {request.get_host()}, request.is_secure()):
        return destino
    return por_defecto


class IngresarView(LoginView):
    """CU-06: Iniciar sesión."""

    template_name = 'cuentas/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def get_default_redirect_url(self):
        if self.request.user.es_admin:
            return reverse('panel:dashboard')
        return reverse('tienda:inicio')

    def form_valid(self, form):
        respuesta = super().form_valid(form)
        usuario = form.get_user()
        messages.success(self.request, f'¡Hola {usuario.first_name or usuario.email}! Iniciaste sesión correctamente.')
        return respuesta


def registro(request):
    """CU-05: Registrarse."""
    if request.user.is_authenticated:
        return redirect('tienda:inicio')

    form = RegistroForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        usuario = form.save()
        login(request, usuario)
        messages.success(request, f'¡Bienvenido/a a Franchesco, {usuario.first_name}! Tu cuenta fue creada.')
        return redirect(_destino_seguro(request, reverse('tienda:inicio')))

    return render(request, 'cuentas/registro.html', {
        'form': form,
        'next': request.GET.get('next', ''),
    })


@login_required
def perfil(request):
    """CU-08 / CU-09: Consultar y modificar la información de la cuenta."""
    form = PerfilForm(request.POST or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Tus datos se actualizaron correctamente.')
        return redirect('cuentas:perfil')

    ultimos_pedidos = request.user.pedidos.all()[:3]
    return render(request, 'cuentas/perfil.html', {
        'form': form,
        'ultimos_pedidos': ultimos_pedidos,
    })


@login_required
def cambiar_password(request):
    form = CambiarPasswordForm(request.user, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        usuario = form.save()
        update_session_auth_hash(request, usuario)
        messages.success(request, 'Tu contraseña se cambió correctamente.')
        return redirect('cuentas:perfil')
    return render(request, 'cuentas/cambiar_password.html', {'form': form})

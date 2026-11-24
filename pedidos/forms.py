from django import forms

from franchesco.forms_utils import BootstrapMixin

from .models import Pago


class CheckoutForm(BootstrapMixin, forms.Form):
    nombre = forms.CharField(max_length=80)
    apellido = forms.CharField(max_length=80)
    telefono = forms.CharField(label='Teléfono', max_length=30)
    direccion = forms.CharField(label='Dirección', max_length=200, widget=forms.TextInput(attrs={'placeholder': 'Calle, número, piso/depto'}))
    ciudad = forms.CharField(max_length=100)
    codigo_postal = forms.CharField(label='Código postal', max_length=10)
    notas = forms.CharField(label='Notas para la entrega (opcional)', required=False,
                            widget=forms.Textarea(attrs={'rows': 2}))
    metodo_pago = forms.ChoiceField(label='Medio de pago', choices=Pago.Metodo.choices,
                                    widget=forms.RadioSelect, initial=Pago.Metodo.CREDITO)
    guardar_datos = forms.BooleanField(label='Guardar estos datos en mi cuenta', required=False, initial=True)

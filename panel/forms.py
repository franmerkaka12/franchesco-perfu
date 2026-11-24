from django import forms

from cuentas.models import Usuario
from franchesco.forms_utils import BootstrapMixin
from pedidos.models import Pedido
from promociones.models import Cupon, Promocion
from tienda.models import Categoria, Producto


class FechaInput(forms.DateInput):
    input_type = 'date'

    def __init__(self, **kwargs):
        super().__init__(format='%Y-%m-%d', **kwargs)


class ProductoForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Producto
        fields = ('nombre', 'marca', 'categoria', 'genero', 'tipo', 'volumen_ml', 'precio',
                  'stock', 'imagen', 'notas', 'descripcion', 'activo', 'destacado', 'es_nuevo')
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 4}),
            'imagen': forms.ClearableFileInput(attrs={'accept': 'image/*'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['marca'].widget.attrs['autocomplete'] = 'off'


class PresentacionForm(BootstrapMixin, forms.ModelForm):
    """Otro tamaño del mismo perfume: solo cambia ml, precio y stock."""
    class Meta:
        model = Producto
        fields = ('volumen_ml', 'precio', 'stock')


class BasePresentacionFormSet(forms.BaseInlineFormSet):
    def __init__(self, *args, volumen_principal=None, **kwargs):
        self.volumen_principal = volumen_principal
        super().__init__(*args, **kwargs)

    def clean(self):
        super().clean()
        vistos = {self.volumen_principal} if self.volumen_principal else set()
        for form in self.forms:
            if not hasattr(form, 'cleaned_data') or not form.cleaned_data or form.cleaned_data.get('DELETE'):
                continue
            ml = form.cleaned_data.get('volumen_ml')
            if ml in vistos:
                raise forms.ValidationError(f'El tamaño de {ml} ml está repetido. Cada presentación debe tener un volumen distinto.')
            vistos.add(ml)


PresentacionFormSet = forms.inlineformset_factory(
    Producto, Producto, fk_name='principal', form=PresentacionForm,
    formset=BasePresentacionFormSet, extra=0, can_delete=True,
)


class CategoriaForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ('nombre', 'descripcion', 'orden')
        widgets = {'descripcion': forms.Textarea(attrs={'rows': 3})}


class PromocionForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Promocion
        fields = ('nombre', 'porcentaje_descuento', 'fecha_inicio', 'fecha_fin', 'descripcion', 'activa', 'productos')
        widgets = {
            'fecha_inicio': FechaInput(),
            'fecha_fin': FechaInput(),
            'productos': forms.SelectMultiple(attrs={'size': 12}),
        }
        help_texts = {'productos': 'Mantené presionada la tecla Ctrl para seleccionar varios productos.'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['productos'].queryset = Producto.objects.order_by('marca', 'nombre')


class CuponForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Cupon
        fields = ('codigo', 'tipo', 'valor', 'monto_minimo', 'fecha_vencimiento', 'usos_maximos', 'descripcion', 'activo')
        widgets = {'fecha_vencimiento': FechaInput()}


class UsuarioAdminForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ('first_name', 'last_name', 'email', 'telefono', 'direccion', 'ciudad', 'codigo_postal', 'rol', 'is_active')
        labels = {'first_name': 'Nombre', 'last_name': 'Apellido', 'is_active': 'Cuenta activa'}


class EstadoPedidoForm(BootstrapMixin, forms.Form):
    estado = forms.ChoiceField(choices=Pedido.Estado.choices)

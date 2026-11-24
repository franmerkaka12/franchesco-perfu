"""Utilidades compartidas para formularios (estilos de Bootstrap)."""
from django import forms


class BootstrapMixin:
    """Agrega automáticamente las clases de Bootstrap a los widgets del formulario
    y marca como inválidos los campos con errores (RNF-11: mensajes claros)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            w = field.widget
            if isinstance(w, (forms.CheckboxInput,)):
                clase = 'form-check-input'
            elif isinstance(w, (forms.RadioSelect, forms.CheckboxSelectMultiple)):
                continue
            elif isinstance(w, (forms.Select, forms.SelectMultiple)):
                clase = 'form-select'
            else:
                clase = 'form-control'
            w.attrs['class'] = (w.attrs.get('class', '') + ' ' + clase).strip()
            if field.required and not isinstance(w, forms.CheckboxInput):
                w.attrs.setdefault('required', 'required')

    def full_clean(self):
        super().full_clean()
        for nombre in self.errors:
            if nombre in self.fields:
                w = self.fields[nombre].widget
                w.attrs['class'] = (w.attrs.get('class', '') + ' is-invalid').strip()

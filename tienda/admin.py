from django.contrib import admin

from .models import Categoria, Producto


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'slug', 'orden')
    prepopulated_fields = {'slug': ('nombre',)}


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'marca', 'genero', 'precio', 'stock', 'activo', 'destacado')
    list_filter = ('genero', 'tipo', 'categoria', 'activo')
    list_editable = ('precio', 'stock', 'activo')
    search_fields = ('nombre', 'marca')

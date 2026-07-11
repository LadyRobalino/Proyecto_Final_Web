from django import template

register = template.Library()

INPUT_CSS = (
    "w-full rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm "
    "text-slate-800 shadow-sm transition focus:border-indigo-500 focus:ring-4 "
    "focus:ring-indigo-100 focus:outline-none placeholder:text-slate-400"
)

CHECK_CSS = "h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"


@register.filter(name="campo")
def campo(field):
    """Aplica el estilo Tailwind estándar a un campo de formulario Django."""
    widget = field.field.widget.__class__.__name__
    css = CHECK_CSS if widget == "CheckboxInput" else INPUT_CSS
    if field.errors:
        css += " border-rose-400 focus:border-rose-500 focus:ring-rose-100"
    return field.as_widget(attrs={"class": css})


@register.filter(name="add_class")
def add_class(field, css):
    return field.as_widget(attrs={"class": css})


@register.filter(name="es_textarea")
def es_textarea(field):
    return field.field.widget.__class__.__name__ == "Textarea"


@register.filter(name="es_checkbox")
def es_checkbox(field):
    return field.field.widget.__class__.__name__ == "CheckboxInput"


@register.filter(name="es_multiple")
def es_multiple(field):
    return field.field.widget.__class__.__name__ in ("SelectMultiple", "CheckboxSelectMultiple")

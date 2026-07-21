from django import template
from django.forms.widgets import CheckboxInput, Textarea, SelectMultiple, Select

register = template.Library()

@register.filter
def es_checkbox(field):
    if hasattr(field, 'field') and hasattr(field.field, 'widget'):
        return isinstance(field.field.widget, CheckboxInput)
    return False

@register.filter
def es_textarea(field):
    if hasattr(field, 'field') and hasattr(field.field, 'widget'):
        return isinstance(field.field.widget, Textarea)
    return False

@register.filter
def es_multiple(field):
    if hasattr(field, 'field') and hasattr(field.field, 'widget'):
        return isinstance(field.field.widget, SelectMultiple)
    return False

@register.filter
def es_select(field):
    if hasattr(field, 'field') and hasattr(field.field, 'widget'):
        return isinstance(field.field.widget, Select) and not isinstance(field.field.widget, SelectMultiple)
    return False

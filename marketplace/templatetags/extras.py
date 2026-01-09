from django import template

register = template.Library()

@register.filter
def calcular_gastos_operativos(value):
    try:
        precio = float(value)
        # 3.49% + IVA (16%) = 4.0484% aproximadamente
        comision_mp = precio * 0.0349 * 1.16
        cuota_fija = 4.64
        return comision_mp + cuota_fija
    except (ValueError, TypeError):
        return 0

@register.filter
def calcular_tu_comision(value):
    try:
        # Tu 5% libre
        return float(value) * 0.05
    except (ValueError, TypeError):
        return 0

@register.filter
def calcular_ganancia_neta(value):
    try:
        precio = float(value)
        gastos = (precio * 0.0349 * 1.16) + 4.64
        tu_comision = precio * 0.05
        return precio - gastos - tu_comision
    except (ValueError, TypeError):
        return 0
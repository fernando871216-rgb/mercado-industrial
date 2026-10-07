<<<<<<< HEAD
# marketplace/utils.py
from django.core.mail import send_mail
from django.conf import settings
from decimal import Decimal

def enviar_notificacion_venta(venta):
    # Obtenemos el monto neto usando la función que ya tienes en models.py
    monto_neto = venta.get_net_amount()
    
    # 1. NOTIFICACIÓN PARA EL VENDEDOR
    subject_vendedor = f"✅ ¡Venta confirmada!: {venta.product.title}"
    message_vendedor = (
        f"Hola {venta.product.user.username},\n\n"
        f"¡Excelentes noticias! Se ha confirmado el pago de tu producto.\n\n"
        f"DETALLES DE LA VENTA:\n"
        f"--------------------------\n"
        f"Producto: {venta.product.title}\n"
        f"Monto a recibir: ${monto_neto} (neto)\n"
        f"CP Destino: {venta.shipping_cp}\n"
        f"--------------------------\n\n"
        f"PRÓXIMOS PASOS:\n"
        f"1. El equipo de INITRE te contactará para coordinar la guía de envío.\n"
        f"2. Una vez enviado el equipo, se procesará tu pago a la CLABE registrada.\n\n"
        f"¡Gracias por vender en INITRE!"
    )
    
    # 2. NOTIFICACIÓN PARA TI (ADMINISTRADOR)
    subject_admin = f"💰 NUEVA VENTA - {venta.product.title}"
    # Usamos una dirección de respaldo si ADMIN_EMAIL no existe en settings
    admin_email = getattr(settings, 'ADMIN_EMAIL', settings.DEFAULT_FROM_EMAIL)
    
    message_admin = (
        f"Se ha registrado una nueva venta.\n\n"
        f"DETALLES OPERATIVOS:\n"
        f"--------------------------\n"
        f"ID Pago MP: {venta.payment_id}\n"
        f"Producto: {venta.product.title}\n"
        f"Vendedor: {venta.product.user.username} ({venta.product.user.email})\n"
        f"Comprador: {venta.buyer.username} ({venta.buyer.email})\n"
        f"Total cobrado (con flete): ${venta.price}\n"
        f"CP Destino: {venta.shipping_cp}\n"
        f"--------------------------\n\n"
        f"Acciones pendientes:\n"
        f"- Generar guía de envío.\n"
        f"- Notificar al vendedor.\n"
        f"- Revisar Panel de Administrador: https://mercado-industrial.onrender.com/panel-administrador/"
    )

    try:
        # Enviamos al Vendedor
        send_mail(
            subject_vendedor, 
            message_vendedor, 
            settings.DEFAULT_FROM_EMAIL, 
            [venta.product.user.email],
            fail_silently=False
        )
        
        # Enviamos al Administrador
        send_mail(
            subject_admin, 
            message_admin, 
            settings.DEFAULT_FROM_EMAIL, 
            [admin_email],
            fail_silently=False
        )
        
        print(f"DEBUG: Correos de venta {venta.id} enviados correctamente.")
        
    except Exception as e:
        print(f"Error crítico enviando notificaciones: {e}")
=======
# marketplace/utils.py
from django.core.mail import send_mail
from django.conf import settings
from decimal import Decimal

def enviar_notificacion_venta(venta):
    # Obtenemos el monto neto usando la función que ya tienes en models.py
    monto_neto = venta.get_net_amount()
    
    # 1. NOTIFICACIÓN PARA EL VENDEDOR
    subject_vendedor = f"✅ ¡Venta confirmada!: {venta.product.title}"
    message_vendedor = (
        f"Hola {venta.product.user.username},\n\n"
        f"¡Excelentes noticias! Se ha confirmado el pago de tu producto.\n\n"
        f"DETALLES DE LA VENTA:\n"
        f"--------------------------\n"
        f"Producto: {venta.product.title}\n"
        f"Monto a recibir: ${monto_neto} (neto)\n"
        f"CP Destino: {venta.shipping_cp}\n"
        f"--------------------------\n\n"
        f"PRÓXIMOS PASOS:\n"
        f"1. El equipo de INITRE te contactará para coordinar la guía de envío.\n"
        f"2. Una vez enviado el equipo, se procesará tu pago a la CLABE registrada.\n\n"
        f"¡Gracias por vender en INITRE!"
    )
    
    # 2. NOTIFICACIÓN PARA TI (ADMINISTRADOR)
    subject_admin = f"💰 NUEVA VENTA - {venta.product.title}"
    # Usamos una dirección de respaldo si ADMIN_EMAIL no existe en settings
    admin_email = getattr(settings, 'ADMIN_EMAIL', settings.DEFAULT_FROM_EMAIL)
    
    message_admin = (
        f"Se ha registrado una nueva venta.\n\n"
        f"DETALLES OPERATIVOS:\n"
        f"--------------------------\n"
        f"ID Pago MP: {venta.payment_id}\n"
        f"Producto: {venta.product.title}\n"
        f"Vendedor: {venta.product.user.username} ({venta.product.user.email})\n"
        f"Comprador: {venta.buyer.username} ({venta.buyer.email})\n"
        f"Total cobrado (con flete): ${venta.price}\n"
        f"CP Destino: {venta.shipping_cp}\n"
        f"--------------------------\n\n"
        f"Acciones pendientes:\n"
        f"- Generar guía de envío.\n"
        f"- Notificar al vendedor.\n"
        f"- Revisar Panel de Administrador: https://mercado-industrial.onrender.com/panel-administrador/"
    )

    try:
        # Enviamos al Vendedor
        send_mail(
            subject_vendedor, 
            message_vendedor, 
            settings.DEFAULT_FROM_EMAIL, 
            [venta.product.user.email],
            fail_silently=False
        )
        
        # Enviamos al Administrador
        send_mail(
            subject_admin, 
            message_admin, 
            settings.DEFAULT_FROM_EMAIL, 
            [admin_email],
            fail_silently=False
        )
        
        print(f"DEBUG: Correos de venta {venta.id} enviados correctamente.")
        
    except Exception as e:
        print(f"Error crítico enviando notificaciones: {e}")
>>>>>>> 1107540eac062862fea2ec2a7befbce2f83905be

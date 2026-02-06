# marketplace/utils.py
from django.core.mail import send_mail
from django.conf import settings

def enviar_notificacion_venta(venta):
    # 1. NOTIFICACIÓN PARA EL VENDEDOR
    subject_vendedor = f"✅ ¡Vendiste tu producto!: {venta.product.title}"
    message_vendedor = (
        f"Hola {venta.product.user.username},\n\n"
        f"¡Felicidades! Has realizado una venta.\n\n"
        f"Producto: {venta.product.title}\n"
        f"Precio: ${venta.product.price}\n\n"
        f"El administrador te enviará la guía de envío a la brevedad.\n"
        f"¡Gracias por vender en INITRE!"
    )
    
    # 2. NOTIFICACIÓN PARA TI (ADMINISTRADOR)
    subject_admin = f"💰 NUEVA VENTA REGISTRADA - ID: {venta.payment_id}"
    message_admin = (
        f"Se ha completado una venta en la plataforma.\n\n"
        f"DETALLES:\n"
        f"--------------------------\n"
        f"Producto: {venta.product.title}\n"
        f"Vendedor: {venta.product.user.username} ({venta.product.user.email})\n"
        f"Comprador: {venta.buyer.username} ({venta.buyer.email})\n"
        f"Monto Cobrado: ${venta.price}\n"
        f"CP Destino: {venta.shipping_cp}\n"
        f"--------------------------\n\n"
        f"Ya puedes generar la guía en SoloEnvíos y contactar al vendedor desde el panel."
    )

    try:
        # Enviamos al Vendedor
        send_mail(subject_vendedor, message_vendedor, settings.DEFAULT_FROM_EMAIL, [venta.product.user.email])
        
        # Enviamos al Administrador (A ti)
        send_mail(subject_admin, message_admin, settings.DEFAULT_FROM_EMAIL, [settings.ADMIN_EMAIL])
        
    except Exception as e:
        print(f"Error enviando notificaciones: {e}")

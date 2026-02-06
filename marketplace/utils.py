from django.core.mail import send_mail
from django.conf import settings

def enviar_notificacion_venta(venta):
    # Correo para el VENDEDOR
    asunto_vendedor = f"¡Felicidades! Vendiste {venta.product.title}"
    mensaje_vendedor = f"""
    Hola {venta.product.user.username},
    
    Has recibido una nueva venta en Mercado Industrial.
    
    Producto: {venta.product.title}
    Precio: ${venta.price}
    Comprador: {venta.buyer.username}
    
    Por favor, revisa tu panel para gestionar el envío.
    """
    
    # Correo para el COMPRADOR
    asunto_comprador = f"Tu compra de {venta.product.title} ha sido confirmada"
    mensaje_comprador = f"""
    Hola {venta.buyer.username},
    
    Tu pago por el producto {venta.product.title} ha sido procesado con éxito.
    
    Vendedor: {venta.product.user.username}
    Total pagado: ${venta.price}
    
    El vendedor se pondrá en contacto contigo para el envío. 
    Gracias por confiar en Mercado Industrial.
    """
    subject_admin = f"📢 NUEVA VENTA EN PLATAFORMA: {venta.product.title}"
    message_admin = (
        f"Se ha registrado una nueva venta.\n\n"
        f"Producto: {venta.product.title}\n"
        f"Vendedor: {venta.product.user.email}\n"
        f"Comprador: {venta.buyer.email}\n"
        f"Monto Total: ${venta.price}\n"
        f"CP Destino: {venta.shipping_cp}\n"
        f"Ganancia Neta Admin: ${venta.ganancia_neta}\n"
    )
    
    send_mail(
        subject_admin,
        message_admin,
        settings.DEFAULT_FROM_EMAIL,
        [settings.ADMIN_EMAIL], # Esto enviará el correo a fernando871216@gmail.com
        fail_silently=False,
    )

    try:
        # Enviar al vendedor
        send_mail(asunto_vendedor, mensaje_vendedor, settings.DEFAULT_FROM_EMAIL, [venta.product.user.email])
        # Enviar al comprador
        send_mail(asunto_comprador, mensaje_comprador, settings.DEFAULT_FROM_EMAIL, [venta.buyer.email])
    except Exception as e:

        print(f"Error enviando correo: {e}")

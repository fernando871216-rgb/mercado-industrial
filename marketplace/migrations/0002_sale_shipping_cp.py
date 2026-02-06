from django.db import migrations, models

class Migration(migrations.Migration): # <-- El error estaba aquí, faltaba el .Migration

    dependencies = [
        ('marketplace', '0001_initial'), 
    ]

    operations = [
        migrations.AddField(
            model_name='sale',
            name='shipping_cp',
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
    ]

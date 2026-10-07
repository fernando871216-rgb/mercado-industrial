from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0001_initial'), # Ahora sí encontrará a su padre
    ]

    operations = [
        migrations.AddField(
            model_name='sale',
            name='shipping_cp',
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
    ]

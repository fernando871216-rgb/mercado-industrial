from django.db import migrations, models

class Migration(migrations):

    dependencies = [
        ('marketplace', '0001_initial'), # Revisa que el nombre coincida con tu primer archivo de migración
    ]

    operations = [
        migrations.AddField(
            model_name='sale',
            name='shipping_cp',
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
    ]

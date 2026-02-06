from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        # Dejamos esto vacío para que no busque el archivo 0001
    ]

    operations = [
        migrations.AddField(
            model_name='sale',
            name='shipping_cp',
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
    ]

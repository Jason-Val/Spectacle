# Generated by Django 2.0.2 on 2018-05-17 21:53

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('schedule', '0002_meta'),
    ]

    operations = [
        migrations.AlterField(
            model_name='schedule',
            name='student',
            field=models.ForeignKey(help_text='The user this schedule belongs to', on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.DeleteModel(
            name='Student',
        ),
    ]

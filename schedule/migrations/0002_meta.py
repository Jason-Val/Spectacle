# Generated by Django 2.0.2 on 2018-05-16 20:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('schedule', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Meta',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('finished', models.BooleanField()),
                ('term', models.IntegerField()),
                ('dept', models.IntegerField()),
            ],
        ),
    ]

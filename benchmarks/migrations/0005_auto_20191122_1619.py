# Generated by Django 2.2.1 on 2019-11-22 21:19

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('benchmarks', '0004_auto_20191122_1437'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='datefield1',
            field=models.DateField(default=datetime.datetime(2019, 1, 1, 0, 0), verbose_name='Date'),
        ),
        migrations.AlterField(
            model_name='user',
            name='datefield2',
            field=models.DateField(default=datetime.datetime(2019, 1, 1, 0, 0), verbose_name='Date'),
        ),
        migrations.AlterField(
            model_name='user',
            name='datefield3',
            field=models.DateField(default=datetime.datetime(2019, 1, 1, 0, 0), verbose_name='Date'),
        ),
    ]

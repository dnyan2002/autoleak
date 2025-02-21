# Generated by Django 4.2 on 2025-02-18 10:08

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('leakapp', '0008_rename_data_leakappshowreport_date'),
    ]

    operations = [
        migrations.AlterField(
            model_name='leakappmasterdata',
            name='timer1',
            field=models.DurationField(blank=True, default=datetime.timedelta(seconds=5), null=True),
        ),
        migrations.AlterField(
            model_name='leakappmasterdata',
            name='timer2',
            field=models.DurationField(blank=True, default=datetime.timedelta(seconds=15), null=True),
        ),
    ]

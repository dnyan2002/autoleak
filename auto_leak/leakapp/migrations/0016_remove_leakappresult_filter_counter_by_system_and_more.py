# Generated by Django 4.2 on 2025-03-03 09:54

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('leakapp', '0015_alter_myplclog_table'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='leakappresult',
            name='filter_counter_by_system',
        ),
        migrations.RemoveField(
            model_name='leakappresult',
            name='iot_value',
        ),
        migrations.RemoveField(
            model_name='leakappresult',
            name='status',
        ),
        migrations.AlterField(
            model_name='leakappresult',
            name='shift',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='leakapp.shift'),
        ),
    ]

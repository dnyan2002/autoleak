# Generated by Django 4.2 on 2025-02-22 08:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('leakapp', '0011_rename_date_field_leakapptest_date_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='shift',
            name='end_time',
            field=models.TimeField(),
        ),
        migrations.AlterField(
            model_name='shift',
            name='start_time',
            field=models.TimeField(),
        ),
    ]

# Generated by Django 5.1.6 on 2025-02-17 11:53

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('leakapp', '0007_leakappresult'),
    ]

    operations = [
        migrations.RenameField(
            model_name='leakappshowreport',
            old_name='data',
            new_name='date',
        ),
    ]

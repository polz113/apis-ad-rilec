# Generated by Django 4.1.7 on 2023-03-19 21:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('apis_rilec', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='datasource',
            name='subsource',
            field=models.JSONField(default=dict),
        ),
    ]
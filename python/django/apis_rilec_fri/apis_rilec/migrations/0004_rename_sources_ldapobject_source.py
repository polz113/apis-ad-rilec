# Generated by Django 4.1.7 on 2023-08-08 10:55

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('apis_rilec', '0003_ldapfield_ldapobject_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='ldapobject',
            old_name='sources',
            new_name='source',
        ),
    ]

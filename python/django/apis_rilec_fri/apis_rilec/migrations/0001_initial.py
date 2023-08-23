# Generated by Django 4.1.7 on 2023-08-23 20:22

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='DataSet',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField()),
            ],
        ),
        migrations.CreateModel(
            name='DataSource',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('subsource', models.JSONField(blank=True, default=dict)),
                ('source', models.CharField(choices=[('apis', 'Apis'), ('studis', 'Studis')], max_length=32)),
                ('timestamp', models.DateTimeField()),
                ('data', models.BinaryField()),
            ],
        ),
        migrations.CreateModel(
            name='LDAPField',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('field', models.CharField(max_length=256)),
                ('value', models.BinaryField()),
            ],
        ),
        migrations.CreateModel(
            name='LDAPObject',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField()),
                ('source', models.CharField(choices=[('AD', 'Active Directory'), ('rilec', 'Apis rilec')], default='AD', max_length=64)),
                ('objectType', models.CharField(choices=[('user', 'User'), ('group', 'Group')], max_length=64, null=True)),
                ('dn', models.TextField(blank=True, null=True)),
                ('uid', models.CharField(blank=True, max_length=64, null=True)),
                ('upn', models.CharField(blank=True, max_length=256, null=True)),
                ('objectSid', models.BinaryField(blank=True, max_length=28, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='UserData',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uid', models.CharField(max_length=64)),
                ('sub_id', models.CharField(max_length=512)),
                ('dataset', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='apis_rilec.dataset')),
            ],
            options={
                'verbose_name_plural': 'UserData',
            },
        ),
        migrations.CreateModel(
            name='UserDataField',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('valid_from', models.DateTimeField(null=True)),
                ('valid_to', models.DateTimeField(null=True)),
                ('changed_t', models.DateTimeField(null=True)),
                ('fieldgroup', models.IntegerField(null=True)),
                ('field', models.CharField(max_length=256)),
                ('value', models.CharField(max_length=512)),
                ('userdata', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='fields', to='apis_rilec.userdata')),
            ],
        ),
        migrations.CreateModel(
            name='TranslationTable',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=256)),
                ('type', models.CharField(choices=[('dict', 'Dictionary'), ('defaultdict', 'Dictionary with default value'), ('substr', 'Replace pattern with replacement'), ('function', 'Function from TRANSLATOR_FUNCTIONS')], max_length=32)),
                ('flags', models.JSONField(blank=True, default=dict)),
                ('dataset', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='apis_rilec.dataset')),
            ],
        ),
        migrations.CreateModel(
            name='TranslationRule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order', models.IntegerField(default=0)),
                ('pattern', models.TextField(blank=True)),
                ('replacement', models.TextField()),
                ('table', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rules', to='apis_rilec.translationtable')),
            ],
        ),
        migrations.CreateModel(
            name='OURelation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('valid_from', models.DateTimeField()),
                ('valid_to', models.DateTimeField()),
                ('changed_t', models.DateTimeField(null=True)),
                ('relation', models.CharField(max_length=64)),
                ('ou1_id', models.CharField(max_length=32)),
                ('ou2_id', models.CharField(max_length=32)),
                ('dataset', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='apis_rilec.dataset')),
            ],
        ),
        migrations.CreateModel(
            name='OUData',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('valid_from', models.DateTimeField()),
                ('valid_to', models.DateTimeField()),
                ('changed_t', models.DateTimeField(null=True)),
                ('uid', models.CharField(max_length=64)),
                ('name', models.CharField(max_length=256)),
                ('shortname', models.CharField(max_length=32)),
                ('dataset', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='apis_rilec.dataset')),
            ],
            options={
                'verbose_name_plural': 'OUData',
            },
        ),
        migrations.CreateModel(
            name='MergedUserData',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uid', models.CharField(max_length=64)),
                ('data', models.ManyToManyField(to='apis_rilec.userdata')),
            ],
            options={
                'verbose_name_plural': 'MergedUserData',
            },
        ),
        migrations.CreateModel(
            name='LDAPObjectField',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ldapfield', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='apis_rilec.ldapfield')),
                ('ldapobject', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='apis_rilec.ldapobject')),
            ],
            options={
                'db_table': 'apis_rilec_ldapobject_fields',
            },
        ),
        migrations.CreateModel(
            name='LDAPObjectBatch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(auto_now=True)),
                ('name', models.TextField()),
                ('ldapobjects', models.ManyToManyField(to='apis_rilec.ldapobject')),
            ],
        ),
        migrations.AddField(
            model_name='ldapobject',
            name='fields',
            field=models.ManyToManyField(through='apis_rilec.LDAPObjectField', to='apis_rilec.ldapfield'),
        ),
        migrations.AddIndex(
            model_name='ldapfield',
            index=models.Index(fields=['field', 'value'], name='apis_rilec__field_b8424c_idx'),
        ),
        migrations.AddConstraint(
            model_name='ldapfield',
            constraint=models.UniqueConstraint(fields=('field', 'value'), name='field_value_unique'),
        ),
        migrations.AddField(
            model_name='dataset',
            name='source',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='apis_rilec.datasource'),
        ),
        migrations.AddIndex(
            model_name='userdatafield',
            index=models.Index(fields=['userdata'], name='apis_rilec__userdat_faf027_idx'),
        ),
        migrations.AddIndex(
            model_name='userdatafield',
            index=models.Index(fields=['field'], name='apis_rilec__field_ebf170_idx'),
        ),
        migrations.AddIndex(
            model_name='userdata',
            index=models.Index(fields=['uid', 'sub_id'], name='apis_rilec__uid_dee176_idx'),
        ),
        migrations.AddIndex(
            model_name='translationrule',
            index=models.Index(fields=['table'], name='apis_rilec__table_i_9222b2_idx'),
        ),
        migrations.AddIndex(
            model_name='translationrule',
            index=models.Index(fields=['pattern'], name='apis_rilec__pattern_848839_idx'),
        ),
        migrations.AddIndex(
            model_name='mergeduserdata',
            index=models.Index(fields=['uid'], name='apis_rilec__uid_831a7f_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='ldapobjectfield',
            unique_together={('ldapobject_id', 'ldapfield_id')},
        ),
        migrations.AddIndex(
            model_name='ldapobject',
            index=models.Index(fields=['timestamp', 'dn'], name='apis_rilec__timesta_98e050_idx'),
        ),
        migrations.AddIndex(
            model_name='ldapobject',
            index=models.Index(fields=['timestamp', 'objectSid'], name='apis_rilec__timesta_06055d_idx'),
        ),
        migrations.AddIndex(
            model_name='ldapobject',
            index=models.Index(fields=['timestamp', 'uid'], name='apis_rilec__timesta_596fce_idx'),
        ),
        migrations.AddIndex(
            model_name='ldapobject',
            index=models.Index(fields=['timestamp', 'upn'], name='apis_rilec__timesta_a0d172_idx'),
        ),
        migrations.AddIndex(
            model_name='ldapobject',
            index=models.Index(fields=['dn'], name='apis_rilec__dn_f1ce9e_idx'),
        ),
        migrations.AddIndex(
            model_name='ldapobject',
            index=models.Index(fields=['uid'], name='apis_rilec__uid_2d6ff4_idx'),
        ),
        migrations.AddIndex(
            model_name='ldapobject',
            index=models.Index(fields=['upn'], name='apis_rilec__upn_3187a9_idx'),
        ),
        migrations.AddIndex(
            model_name='ldapobject',
            index=models.Index(fields=['objectSid'], name='apis_rilec__objectS_8ec196_idx'),
        ),
        migrations.AddIndex(
            model_name='dataset',
            index=models.Index(fields=['timestamp'], name='apis_rilec__timesta_887506_idx'),
        ),
    ]

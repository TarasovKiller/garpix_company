# Generated by Django 3.2.16 on 2023-01-26 10:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0005_usercompanyrole'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='company',
            name='owner',
        ),
        migrations.AddField(
            model_name='usercompanyrole',
            name='role_type',
            field=models.CharField(choices=[('admin', 'Админ'), ('owner', 'Владелец'), ('employee', 'Сотрудник')], default='employee', max_length=128, verbose_name='Значение'),
        ),
    ]
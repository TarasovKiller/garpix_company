# Generated by Django 3.2.16 on 2022-12-02 11:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0003_company_owner'),
    ]

    operations = [
        migrations.AlterField(
            model_name='company',
            name='bank_title',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='Наименование банка'),
        ),
        migrations.AlterField(
            model_name='company',
            name='bic',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='БИК банка'),
        ),
        migrations.AlterField(
            model_name='company',
            name='korschet',
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name='Кор. счет'),
        ),
        migrations.AlterField(
            model_name='company',
            name='kpp',
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name='КПП'),
        ),
        migrations.AlterField(
            model_name='company',
            name='ogrn',
            field=models.CharField(blank=True, max_length=15, null=True, verbose_name='ОГРН'),
        ),
        migrations.AlterField(
            model_name='company',
            name='schet',
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name='Номер счета'),
        ),
    ]
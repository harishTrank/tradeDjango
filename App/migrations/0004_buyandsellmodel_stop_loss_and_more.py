# Generated by Django 4.1.1 on 2023-12-13 04:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('App', '0003_alter_buyandsellmodel_is_cancel_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='buyandsellmodel',
            name='stop_loss',
            field=models.IntegerField(blank=True, default=0, null=True, verbose_name='Quantity'),
        ),
        migrations.AlterField(
            model_name='buyandsellmodel',
            name='is_cancel',
            field=models.BooleanField(default=False, verbose_name='Is Cancel'),
        ),
    ]

# Generated by Django 5.1.7 on 2025-03-29 15:23

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('persons', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='customer',
            name='parent_company',
            field=models.ForeignKey(blank=True, help_text='Link to the parent company, if this is a subsidiary.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='child_customers', to='persons.customer', verbose_name='Parent Company'),
        ),
    ]

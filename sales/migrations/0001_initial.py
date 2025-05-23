# Generated by Django 5.1.7 on 2025-03-29 18:51

import django.core.validators
import django.db.models.deletion
import uuid
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('core', '0002_address'),
        ('inventory', '0001_initial'),
        ('persons', '0003_employee_daily_wage_rate_employee_monthly_salary_and_more'),
        ('projects', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SalesInvoice',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated At')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('invoice_number', models.CharField(help_text='Unique number for this invoice.', max_length=50, unique=True, verbose_name='Invoice Number')),
                ('invoice_date', models.DateField(db_index=True, verbose_name='Invoice Date')),
                ('due_date', models.DateField(blank=True, null=True, verbose_name='Due Date')),
                ('status', models.CharField(choices=[('DRAFT', 'Draft'), ('SENT', 'Sent'), ('PARTIAL', 'Partially Paid'), ('PAID', 'Paid'), ('VOID', 'Void')], db_index=True, default='DRAFT', max_length=10, verbose_name='Status')),
                ('subtotal', models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Total before taxes and discounts. Often calculated from lines.', max_digits=15, verbose_name='Subtotal')),
                ('tax_amount', models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Total tax amount. Often calculated.', max_digits=15, verbose_name='Tax Amount')),
                ('total_amount', models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Total amount due (subtotal + tax). Often calculated.', max_digits=15, verbose_name='Total Amount')),
                ('amount_paid', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=15, verbose_name='Amount Paid')),
                ('notes', models.TextField(blank=True, verbose_name='Notes')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created_by', to=settings.AUTH_USER_MODEL, verbose_name='Created By')),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='persons.customer', verbose_name='Customer')),
                ('project', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sales_invoices', to='projects.project', verbose_name='Project')),
                ('tags', models.ManyToManyField(blank=True, related_name='sales_invoices', to='core.tag', verbose_name='Tags')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_updated_by', to=settings.AUTH_USER_MODEL, verbose_name='Updated By')),
            ],
            options={
                'verbose_name': 'Sales Invoice',
                'verbose_name_plural': 'Sales Invoices',
                'ordering': ['-invoice_date', '-invoice_number'],
            },
        ),
        migrations.CreateModel(
            name='SalesInvoiceLine',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('description', models.TextField(help_text='Detailed description of item/service sold.', verbose_name='Description')),
                ('quantity', models.DecimalField(decimal_places=4, default=Decimal('1.0'), max_digits=15, verbose_name='Quantity')),
                ('unit_price', models.DecimalField(decimal_places=2, max_digits=15, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))], verbose_name='Unit Price')),
                ('line_total', models.DecimalField(blank=True, decimal_places=2, help_text='Calculated as Quantity * Unit Price (potentially less discounts).', max_digits=15, null=True, verbose_name='Line Total')),
                ('invoice', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lines', to='sales.salesinvoice', verbose_name='Sales Invoice')),
                ('product', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='invoice_lines', to='inventory.product', verbose_name='Product/Service')),
            ],
            options={
                'verbose_name': 'Sales Invoice Line',
                'verbose_name_plural': 'Sales Invoice Lines',
                'ordering': ['invoice', 'id'],
            },
        ),
    ]

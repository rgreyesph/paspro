# Generated by Django 5.1.7 on 2025-03-29 14:14

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0001_initial'),
        ('core', '0002_address'),
    ]

    operations = [
        migrations.CreateModel(
            name='Customer',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(help_text="Company name or individual's name.", max_length=255, verbose_name='Customer Name')),
                ('contact_person', models.CharField(blank=True, help_text='Primary contact at the customer company.', max_length=150, verbose_name='Contact Person')),
                ('email', models.EmailField(blank=True, max_length=254, null=True, verbose_name='Email Address')),
                ('phone_number', models.CharField(blank=True, max_length=30, verbose_name='Phone Number')),
                ('website', models.URLField(blank=True, verbose_name='Website')),
                ('tax_id', models.CharField(blank=True, help_text="Customer's Tax Identification Number, if applicable.", max_length=50, verbose_name='Tax ID / TIN')),
                ('is_active', models.BooleanField(default=True, help_text='Inactive customers cannot be used in new transactions.', verbose_name='Is Active')),
                ('notes', models.TextField(blank=True, verbose_name='Notes')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('billing_address', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='customer_billing_addresses', to='core.address', verbose_name='Billing Address')),
                ('default_revenue_account', models.ForeignKey(blank=True, help_text='Default account to use for invoices to this customer.', limit_choices_to={'account_type__in': ['REVENUE']}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='default_customers', to='accounts.chartofaccounts', verbose_name='Default Revenue Account')),
                ('shipping_address', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='customer_shipping_addresses', to='core.address', verbose_name='Shipping Address')),
                ('tags', models.ManyToManyField(blank=True, related_name='customers', to='core.tag', verbose_name='Tags')),
            ],
            options={
                'verbose_name': 'Customer',
                'verbose_name_plural': 'Customers',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Employee',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('employee_id', models.CharField(blank=True, help_text='Unique identifier for the employee.', max_length=20, null=True, unique=True, verbose_name='Employee ID')),
                ('first_name', models.CharField(max_length=100, verbose_name='First Name')),
                ('last_name', models.CharField(max_length=100, verbose_name='Last Name')),
                ('job_title', models.CharField(blank=True, max_length=150, verbose_name='Job Title')),
                ('email', models.EmailField(blank=True, max_length=254, null=True, verbose_name='Email Address')),
                ('phone_number', models.CharField(blank=True, max_length=30, verbose_name='Phone Number')),
                ('date_hired', models.DateField(blank=True, null=True, verbose_name='Date Hired')),
                ('date_terminated', models.DateField(blank=True, null=True, verbose_name='Date Terminated')),
                ('status', models.CharField(choices=[('ACTIVE', 'Active'), ('ON_LEAVE', 'On Leave'), ('TERMINATED', 'Terminated'), ('CONTRACTOR', 'Contractor')], default='ACTIVE', max_length=20, verbose_name='Employment Status')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('address', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.address', verbose_name='Primary Address')),
            ],
            options={
                'verbose_name': 'Employee',
                'verbose_name_plural': 'Employees',
                'ordering': ['last_name', 'first_name'],
            },
        ),
        migrations.CreateModel(
            name='Vendor',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(help_text="Company name or individual's name.", max_length=255, verbose_name='Vendor Name')),
                ('contact_person', models.CharField(blank=True, help_text='Primary contact at the vendor company.', max_length=150, verbose_name='Contact Person')),
                ('email', models.EmailField(blank=True, max_length=254, null=True, verbose_name='Email Address')),
                ('phone_number', models.CharField(blank=True, max_length=30, verbose_name='Phone Number')),
                ('website', models.URLField(blank=True, verbose_name='Website')),
                ('tax_id', models.CharField(blank=True, help_text="Vendor's Tax Identification Number, if applicable.", max_length=50, verbose_name='Tax ID / TIN')),
                ('is_active', models.BooleanField(default=True, help_text='Inactive vendors cannot be used in new transactions.', verbose_name='Is Active')),
                ('notes', models.TextField(blank=True, verbose_name='Notes')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('billing_address', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.address', verbose_name='Billing Address')),
                ('default_expense_account', models.ForeignKey(blank=True, help_text='Default account to use for bills from this vendor.', limit_choices_to={'account_type__in': ['EXPENSE']}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='default_vendors', to='accounts.chartofaccounts', verbose_name='Default Expense Account')),
                ('tags', models.ManyToManyField(blank=True, related_name='vendors', to='core.tag', verbose_name='Tags')),
            ],
            options={
                'verbose_name': 'Vendor',
                'verbose_name_plural': 'Vendors',
                'ordering': ['name'],
            },
        ),
    ]

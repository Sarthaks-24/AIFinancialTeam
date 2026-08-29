# Generated manually for Phase 2 core specialist data.

from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("agents", "0010_remove_unused_agent_budget"),
    ]

    operations = [
        migrations.CreateModel(
            name="ComplianceRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("jurisdiction", models.CharField(blank=True, max_length=100)),
                ("status", models.CharField(choices=[("Compliant", "Compliant"), ("Attention", "Attention required"), ("Overdue", "Overdue")], default="Attention", max_length=20)),
                ("due_date", models.DateField(blank=True, null=True)),
                ("evidence_reference", models.CharField(blank=True, max_length=500)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["due_date", "name"]},
        ),
        migrations.CreateModel(
            name="Vendor",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255, unique=True)),
                ("category", models.CharField(blank=True, max_length=100)),
                ("annual_spend", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=15)),
                ("risk_level", models.CharField(choices=[("Low", "Low"), ("Medium", "Medium"), ("High", "High")], default="Medium", max_length=20)),
                ("contract_renewal_date", models.DateField(blank=True, null=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
    ]

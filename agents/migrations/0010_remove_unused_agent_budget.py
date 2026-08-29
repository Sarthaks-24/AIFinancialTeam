# Generated manually for Phase 0 dead-model cleanup

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("agents", "0009_alter_financialmetric_month"),
    ]

    operations = [
        migrations.DeleteModel(name="Agent"),
        migrations.DeleteModel(name="Budget"),
    ]

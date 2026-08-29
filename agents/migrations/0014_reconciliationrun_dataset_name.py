from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("agents", "0013_reconciliationrun_reconciliationexception"),
    ]

    operations = [
        migrations.AddField(
            model_name="reconciliationrun",
            name="dataset_name",
            field=models.CharField(default="canonical_60", max_length=100),
        ),
    ]
# Generated migration for classification_source field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('agents', '0014_reconciliationrun_dataset_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='reconciliationexception',
            name='classification_source',
            field=models.CharField(blank=True, choices=[('deterministic', 'Deterministic Rule'), ('ai', 'AI Classification')], default='ai', max_length=20),
        ),
    ]

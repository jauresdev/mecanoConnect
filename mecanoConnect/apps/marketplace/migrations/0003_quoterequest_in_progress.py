from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("marketplace", "0002_seed_catalogue")]

    operations = [
        migrations.AlterField(
            model_name="quoterequest",
            name="status",
            field=models.CharField(
                choices=[
                    ("new", "Nouvelle"),
                    ("answered", "Répondue"),
                    ("accepted", "Acceptée"),
                    ("in_progress", "En cours"),
                    ("declined", "Refusée"),
                    ("completed", "Terminée"),
                    ("cancelled", "Annulée"),
                ],
                default="new",
                max_length=16,
            ),
        ),
    ]

from django.db import migrations


SERVICES = (
    ("Vidange", "vidange"),
    ("Freins", "freins"),
    ("Moteur", "moteur"),
    ("Électricité", "electricite"),
    ("Pneus", "pneus"),
    ("Diagnostic", "diagnostic"),
)
VEHICLES = (("Moto", "moto"), ("Voiture", "voiture"))


def create_catalogue(apps, schema_editor):
    Service = apps.get_model("marketplace", "Service")
    VehicleType = apps.get_model("marketplace", "VehicleType")
    Service.objects.using(schema_editor.connection.alias).bulk_create(
        [Service(name=name, slug=slug) for name, slug in SERVICES],
        ignore_conflicts=True,
    )
    VehicleType.objects.using(schema_editor.connection.alias).bulk_create(
        [VehicleType(name=name, slug=slug) for name, slug in VEHICLES],
        ignore_conflicts=True,
    )


class Migration(migrations.Migration):
    dependencies = [("marketplace", "0001_initial")]

    operations = [migrations.RunPython(create_catalogue, migrations.RunPython.noop)]

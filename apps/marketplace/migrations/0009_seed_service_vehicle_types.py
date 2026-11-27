from django.db import migrations


AUTO_SERVICES = (
    ("Carrosserie", "carrosserie"),
    ("Climatisation automobile", "climatisation-auto"),
    ("Boîte de vitesses", "boite-vitesses"),
)
MOTO_SERVICES = (
    ("Chaîne et transmission", "chaine-transmission"),
    ("Carburateur", "carburateur"),
    ("Suspension moto", "suspension-moto"),
)
SPECIALTIES = {
    "voiture": (
        ("Mécanique générale", "mecanique-generale"),
        ("Électricité automobile", "electricite-auto"),
        ("Diagnostic électronique", "diagnostic-electronique"),
        ("Climatisation automobile", "climatisation-auto"),
        ("Carrosserie", "carrosserie"),
        ("Moteur et transmission", "moteur-transmission-auto"),
    ),
    "moto": (
        ("Mécanique générale", "mecanique-generale"),
        ("Réparation moteur moto", "moteur-moto"),
        ("Électricité moto", "electricite-moto"),
        ("Transmission moto", "transmission-moto"),
        ("Entretien et vidange moto", "entretien-vidange-moto"),
        ("Pneumatiques moto", "pneumatiques-moto"),
    ),
}


def seed_vehicle_specific_services(apps, schema_editor):
    Service = apps.get_model("marketplace", "Service")
    VehicleType = apps.get_model("marketplace", "VehicleType")
    database = schema_editor.connection.alias

    vehicles = {
        vehicle.slug: vehicle
        for vehicle in VehicleType.objects.using(database).all()
    }
    auto = vehicles["voiture"]
    moto = vehicles["moto"]

    # Les services historiques du catalogue sont communs aux deux véhicules.
    general_services = Service.objects.using(database).filter(
        vehicle_types__isnull=True
    )
    for service in general_services:
        service.vehicle_types.add(auto, moto)

    # Ajoute les services spécifiques qui n'existaient pas dans le catalogue initial.
    for name, slug in AUTO_SERVICES:
        service, _ = Service.objects.using(database).get_or_create(
            slug=slug,
            defaults={"name": name},
        )
        service.vehicle_types.add(auto)

    for name, slug in MOTO_SERVICES:
        service, _ = Service.objects.using(database).get_or_create(
            slug=slug,
            defaults={"name": name},
        )
        service.vehicle_types.add(moto)

    for vehicle_slug, specialties in SPECIALTIES.items():
        vehicle = vehicles[vehicle_slug]
        for name, slug in specialties:
            service, _ = Service.objects.using(database).get_or_create(
                slug=slug,
                defaults={"name": name},
            )
            service.vehicle_types.add(vehicle)


class Migration(migrations.Migration):
    dependencies = [
        ("marketplace", "0008_repairshop_years_experience_service_vehicle_types_and_more"),
    ]

    operations = [
        migrations.RunPython(
            seed_vehicle_specific_services,
            migrations.RunPython.noop,
        ),
    ]

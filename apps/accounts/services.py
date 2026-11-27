from apps.marketplace.models import RepairShop

from .models import ProfessionalVerification


def sync_professional_verification_badges(user):
    latest = ProfessionalVerification.objects.filter(user=user).first()
    is_verified = (
        user.is_active
        and latest is not None
        and latest.status == ProfessionalVerification.Status.VERIFIED
    )
    RepairShop.objects.filter(owner=user).update(is_verified=is_verified)

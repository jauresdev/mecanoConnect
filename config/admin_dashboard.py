from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.shortcuts import render
from django.urls import reverse

from apps.accounts.models import ProfessionalVerification
from apps.marketplace.models import QuoteReport, QuoteRequest, RepairShop, Review


@staff_member_required
def admin_dashboard(request):
    user_model = get_user_model()
    can_view_users = request.user.has_perm("accounts.view_user")
    can_view_verifications = request.user.has_perm(
        "accounts.view_professionalverification"
    )
    can_view_shops = request.user.has_perm("marketplace.view_repairshop")
    can_view_quotes = request.user.has_perm("marketplace.view_quoterequest")
    can_view_reports = request.user.has_perm("marketplace.view_quotereport")
    can_view_reviews = request.user.has_perm("marketplace.view_review")

    pending_verifications = 0
    verifications_in_review = 0
    shops_pending_review = 0
    open_reports = 0
    reviews_pending = 0
    verification_items = []
    shop_items = []
    metrics = []
    quick_links = []

    if can_view_verifications:
        pending_verifications = ProfessionalVerification.objects.filter(
            status=ProfessionalVerification.Status.PENDING
        ).count()
        verifications_in_review = ProfessionalVerification.objects.filter(
            status=ProfessionalVerification.Status.IN_REVIEW
        ).count()
        for verification in ProfessionalVerification.objects.select_related(
            "user"
        ).filter(
            status__in=(
                ProfessionalVerification.Status.PENDING,
                ProfessionalVerification.Status.IN_REVIEW,
            )
        )[:5]:
            verification_items.append(
                {
                    "title": verification.user.get_full_name()
                    or verification.user.username,
                    "status": verification.get_status_display(),
                    "date": verification.submitted_at,
                    "url": reverse(
                        "admin:accounts_professionalverification_change",
                        args=(verification.pk,),
                    ),
                }
            )
        metrics.extend(
            (
                {
                    "label": "Vérifications à examiner",
                    "value": pending_verifications,
                    "detail": "Nouvelles demandes",
                    "icon": "✓",
                    "url": reverse(
                        "admin:accounts_professionalverification_changelist"
                    )
                    + "?status__exact=pending",
                    "tone": "gold",
                },
                {
                    "label": "Vérifications en cours",
                    "value": verifications_in_review,
                    "detail": "Dossiers en analyse",
                    "icon": "◷",
                    "url": reverse(
                        "admin:accounts_professionalverification_changelist"
                    )
                    + "?status__exact=in_review",
                    "tone": "blue",
                },
            )
        )
        quick_links.append(
            {
                "title": "Vérifications professionnelles",
                "detail": "Consulter les dossiers et les justificatifs",
                "url": reverse(
                    "admin:accounts_professionalverification_changelist"
                ),
            }
        )

    if can_view_shops:
        shops_pending_review = RepairShop.objects.filter(
            publication_status=RepairShop.PublicationStatus.PENDING
        ).count()
        for shop in RepairShop.objects.select_related("owner").filter(
            publication_status=RepairShop.PublicationStatus.PENDING
        )[:5]:
            shop_items.append(
                {
                    "title": shop.name,
                    "detail": f"{shop.district}, {shop.city}",
                    "date": shop.updated_at,
                    "url": reverse(
                        "admin:marketplace_repairshop_change",
                        args=(shop.pk,),
                    ),
                }
            )
        published_shops = RepairShop.objects.filter(
            is_active=True,
            publication_status=RepairShop.PublicationStatus.APPROVED,
        ).count()
        metrics.extend(
            (
                {
                    "label": "Ateliers à examiner",
                    "value": shops_pending_review,
                    "detail": "À approuver ou à corriger",
                    "icon": "⌂",
                    "url": reverse("admin:marketplace_repairshop_changelist")
                    + "?publication_status__exact=pending",
                    "tone": "red",
                },
                {
                    "label": "Ateliers publiés",
                    "value": published_shops,
                    "detail": "Ateliers visibles dans l’annuaire",
                    "icon": "↗",
                    "url": reverse("admin:marketplace_repairshop_changelist")
                    + "?publication_status__exact=approved",
                    "tone": "green",
                },
            )
        )
        quick_links.append(
            {
                "title": "Ateliers",
                "detail": "Examiner les fiches et gérer les publications",
                "url": reverse("admin:marketplace_repairshop_changelist"),
            }
        )

    if can_view_reports:
        open_reports = QuoteReport.objects.filter(
            status=QuoteReport.Status.OPEN
        ).count()
        metrics.append(
            {
                "label": "Signalements ouverts",
                "value": open_reports,
                "detail": "Demandes de modération",
                "icon": "!",
                "url": reverse("admin:marketplace_quotereport_changelist")
                + "?status__exact=open",
                "tone": "red",
            }
        )
        quick_links.append(
            {
                "title": "Signalements",
                "detail": "Consulter les problèmes signalés",
                "url": reverse("admin:marketplace_quotereport_changelist"),
            }
        )

    if can_view_reviews:
        reviews_pending = Review.objects.filter(is_approved=False).count()
        metrics.append(
            {
                "label": "Avis à modérer",
                "value": reviews_pending,
                "detail": "En attente de publication",
                "icon": "★",
                "url": reverse("admin:marketplace_review_changelist")
                + "?is_approved__exact=0",
                "tone": "gold",
            }
        )
        quick_links.append(
            {
                "title": "Avis clients",
                "detail": "Approuver ou masquer les avis",
                "url": reverse("admin:marketplace_review_changelist"),
            }
        )

    if can_view_users:
        metrics.insert(
            0,
            {
                "label": "Mécaniciens inscrits",
                "value": user_model.objects.filter(
                    role=user_model.Role.MECHANIC
                ).count(),
                "detail": "Comptes professionnels",
                "icon": "M",
                "url": reverse("admin:accounts_user_changelist")
                + "?role__exact=mechanic",
                "tone": "green",
            },
        )
        quick_links.append(
            {
                "title": "Comptes utilisateurs",
                "detail": "Rechercher et gérer les comptes",
                "url": reverse("admin:accounts_user_changelist"),
            }
        )

    if can_view_quotes:
        metrics.append(
            {
                "label": "Demandes d’intervention",
                "value": QuoteRequest.objects.count(),
                "detail": "Demandes enregistrées",
                "icon": "↗",
                "url": reverse("admin:marketplace_quoterequest_changelist"),
                "tone": "blue",
            }
        )

    context = {
        **admin.site.each_context(request),
        "admin_metrics": metrics,
        "can_view_verifications": can_view_verifications,
        "can_view_shops": can_view_shops,
        "pending_verifications": pending_verifications,
        "verifications_in_review": verifications_in_review,
        "shops_pending_review": shops_pending_review,
        "open_reports": open_reports,
        "reviews_pending": reviews_pending,
        "verification_items": verification_items,
        "shop_items": shop_items,
        "quick_links": quick_links,
    }
    return render(request, "admin/mecanoconnect_dashboard.html", context)

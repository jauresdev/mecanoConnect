from .models import Notification, QuoteEvent


def record_quote_event(quote, actor, action, details, recipient=None):
    QuoteEvent.objects.create(
        quote=quote,
        actor=actor,
        action=action,
        details=details,
    )
    if recipient is not None and recipient.pk != getattr(actor, "pk", None):
        Notification.objects.create(
            recipient=recipient,
            quote=quote,
            event=action,
            message=details,
        )

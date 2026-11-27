from pathlib import PurePath
import warnings

from PIL import Image, UnidentifiedImageError
from rest_framework import serializers


MAX_IMAGE_SIZE = 5 * 1024 * 1024
MAX_DOCUMENT_SIZE = 10 * 1024 * 1024

IMAGE_SIGNATURES = {
    ".jpg": lambda content: content.startswith(b"\xff\xd8\xff"),
    ".jpeg": lambda content: content.startswith(b"\xff\xd8\xff"),
    ".png": lambda content: content.startswith(b"\x89PNG\r\n\x1a\n"),
    ".webp": lambda content: (
        content.startswith(b"RIFF") and content[8:12] == b"WEBP"
    ),
}

DOCUMENT_SIGNATURES = {
    **IMAGE_SIGNATURES,
    ".pdf": lambda content: content.startswith(b"%PDF-"),
}


def _validate_signature(upload, signatures, size_limit, message):
    if upload.size > size_limit:
        raise serializers.ValidationError(message)

    extension = PurePath(upload.name).suffix.lower()
    signature = signatures.get(extension)

    content = upload.read(12)
    upload.seek(0)

    if signature is None or not signature(content):
        raise serializers.ValidationError(
            "Le format du fichier ne correspond pas à son contenu."
        )

    return extension


def validate_image_upload(upload):
    _validate_signature(
        upload,
        IMAGE_SIGNATURES,
        MAX_IMAGE_SIZE,
        "L’image ne peut pas dépasser 5 Mo.",
    )

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)

            image = Image.open(upload)

            if image.width * image.height > 40_000_000:
                raise serializers.ValidationError(
                    "Les dimensions de l’image sont trop grandes."
                )

            image.verify()

    except (
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        UnidentifiedImageError,
        OSError,
    ) as error:
        raise serializers.ValidationError(
            "Le fichier image est invalide."
        ) from error

    finally:
        upload.seek(0)

    return upload


def validate_verification_document(upload):
    extension = _validate_signature(
        upload,
        DOCUMENT_SIGNATURES,
        MAX_DOCUMENT_SIZE,
        "Un document ne peut pas dépasser 10 Mo.",
    )

    if extension in IMAGE_SIGNATURES:
        validate_image_upload(upload)

    return upload
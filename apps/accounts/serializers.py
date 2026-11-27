from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from config.file_validation import validate_image_upload
from .models import ProfessionalVerification, VerificationDocument


User = get_user_model()


class RegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, min_length=10, style={"input_type": "password"}
    )
    role = serializers.ChoiceField(choices=User.Role.choices, default=User.Role.CUSTOMER)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "password",
            "first_name",
            "last_name",
            "phone",
            "role",
            "vehicle_scope",
        )
        read_only_fields = ("id",)

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate(self, attrs):
        role = attrs.get("role", User.Role.CUSTOMER)
        if role == User.Role.MECHANIC and not attrs.get("vehicle_scope"):
            raise serializers.ValidationError(
                {"vehicle_scope": "Choisissez l’automobile, la moto ou les deux."}
            )
        if role != User.Role.MECHANIC and attrs.get("vehicle_scope"):
            raise serializers.ValidationError(
                {"vehicle_scope": "Ce choix est réservé aux comptes réparateur."}
            )
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.full_clean()
        user.save()
        return user


class UserSerializer(serializers.ModelSerializer):
    profile_photo = serializers.ImageField(
        required=False,
        validators=[validate_image_upload],
    )

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "phone",
            "role",
            "vehicle_scope",
            "profile_photo",
        )
        read_only_fields = ("id", "username", "email", "role", "vehicle_scope")


class VerificationDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = VerificationDocument
        fields = ("id", "document_type", "original_filename", "uploaded_at")
        read_only_fields = fields


class ProfessionalVerificationSerializer(serializers.ModelSerializer):
    documents = VerificationDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = ProfessionalVerification
        fields = (
            "id",
            "status",
            "rejection_reason",
            "submitted_at",
            "reviewed_at",
            "documents",
        )
        read_only_fields = fields

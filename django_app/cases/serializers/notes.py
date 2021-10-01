from django_synergy.cases.models import Case, User, ParentNote, ParentNoteFileUpload
from django_synergy.cases.models.notes import ProviderNote
from django_synergy.cases.serializers import SimpleCaseSerializer
from django_synergy.users.serializers import SimpleUserSerializer
from django_synergy.utils.serializers import BaseSerializer, serializers


class ProviderNoteReadOnlySerializer(BaseSerializer):
    user = SimpleUserSerializer()
    case = SimpleCaseSerializer()

    class Meta:
        model = ProviderNote
        exclude = ('id', 'created_by', 'updated_by')


class ProviderNoteWritableSerializer(BaseSerializer):
    case = serializers.SlugRelatedField(
        slug_field='slug', queryset=Case.objects.all())

    user = serializers.SlugRelatedField(
        slug_field='slug', queryset=User.objects.all())

    class Meta:
        model = ProviderNote
        exclude = ('id', 'slug', 'created_on', 'created_by', 'updated_on', 'updated_by')


class ParentNoteReadOnlySerializer(BaseSerializer):
    user = SimpleUserSerializer()
    case = SimpleCaseSerializer()

    url = serializers.SerializerMethodField()

    def get_url(self, obj):
        parent_note_upload = ParentNoteFileUpload.objects.filter(parent_note_id=obj.id).last()
        if parent_note_upload and parent_note_upload.presigned_url_for_get:
            return parent_note_upload.presigned_url_for_get
        else:
            return None

    presigned_url = serializers.SerializerMethodField()

    def get_presigned_url(self, obj):
        parent_note_upload = ParentNoteFileUpload.objects.filter(parent_note_id=obj.id).last()
        if parent_note_upload and parent_note_upload.presigned_url:
            return parent_note_upload.presigned_url
        else:
            return None

    uuid = serializers.SerializerMethodField()

    def get_uuid(self, obj):
        parent_note_upload = ParentNoteFileUpload.objects.filter(parent_note_id=obj.id).last()
        if parent_note_upload and parent_note_upload.uuid:
            return parent_note_upload.uuid
        else:
            return None

    filename = serializers.SerializerMethodField()

    def get_filename(self, obj):
        parent_note_upload = ParentNoteFileUpload.objects.filter(parent_note_id=obj.id).last()
        if parent_note_upload and parent_note_upload.filename:
            return parent_note_upload.filename
        else:
            return None

    class Meta:
        model = ParentNote
        exclude = ('id', 'created_by', 'updated_by')


class ParentNoteWritableSerializer(BaseSerializer):
    case = serializers.SlugRelatedField(
        slug_field='slug', queryset=Case.objects.all())

    user = serializers.SlugRelatedField(
        slug_field='slug', queryset=User.objects.all())

    class Meta:
        model = ParentNote
        exclude = ('id', 'slug', 'created_on', 'created_by', 'updated_on', 'updated_by')


class ParentNoteFileUploadSerializer(BaseSerializer):
    parent_note = serializers.SlugRelatedField(slug_field="slug",
                                               queryset=ParentNote.objects.filter())

    class Meta:
        model = ParentNoteFileUpload
        fields = (
            "uuid", "url", "filename", "presigned_url",
            "url_expiry", "url_created_on", "uploaded",
            "presigned_url_for_get", "parent_note", "created_on",
        )
        read_only_fields = ("presigned_url", "presigned_url_for_get", "url", "created_on")


class ParentNoteFileUploadWritableSerializer(BaseSerializer):
    parent_note = serializers.SlugRelatedField(slug_field="slug",
                                               queryset=ParentNote.objects.filter())

    def __init__(self, *args, **kwargs):
        kwargs["partial"] = True
        super().__init__(*args, **kwargs)

    class Meta:
        model = ParentNoteFileUpload
        fields = (
            "filename", "url_expiry", "get_url_expiry",
            "uploaded", "presigned_url", "uuid",
            "presigned_url_for_get", "parent_note", "created_on",
        )
        read_only_fields = ("presigned_url", "presigned_url_for_get", "created_on",)

from django.db import models
from django_extensions.db.fields import AutoSlugField, slugify
from django.contrib.postgres.fields import JSONField
from config.settings.base import PARENTNOTE_S3_KEY_PREFIX
from django_synergy.cases.models import Case, User
from django_synergy.utils.models import AbstractBaseModel, S3AbstractModel

NOTE_CHOICES = [('Feeding', 'Feeding'), ('Alarm', 'Alarm'), ('Medication', 'Medication'), ('Others', 'Others')]


class ProviderNote(AbstractBaseModel):
    slug = AutoSlugField(max_length=255, db_index=True, allow_unicode=True, unique=True, populate_from=[
        'created_by__name', 'case__patient__first_name', 'case__patient__last_name'], slugify_function=slugify)
    case = models.ForeignKey(
        Case, related_name='provider_note_case', on_delete=models.PROTECT)
    user = models.ForeignKey(
        User, related_name='provider_note_user', on_delete=models.PROTECT)
    subject = models.TextField()
    content = models.TextField()
    default_case_roles = JSONField()

    class Meta:
        default_permissions = ()
        permissions = []


class ParentNote(AbstractBaseModel):
    slug = AutoSlugField(max_length=255, db_index=True, allow_unicode=True, unique=True, populate_from=[
        'created_by__name', 'note_type'], slugify_function=slugify)
    case = models.ForeignKey(
        Case, related_name='parent_note_case', on_delete=models.PROTECT)
    user = models.ForeignKey(
        User, related_name='parent_note_user', on_delete=models.PROTECT)
    note_type = models.CharField(max_length=255, choices=NOTE_CHOICES)
    content = models.TextField()
    default_case_roles = JSONField()

    class Meta:
        default_permissions = ()


class ParentNoteFileUpload(S3AbstractModel):
    _key_prefix = PARENTNOTE_S3_KEY_PREFIX
    parent_note = models.ForeignKey(ParentNote, on_delete=models.PROTECT)
    slug = None



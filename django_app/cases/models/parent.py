from django.db import models

from django_synergy.utils.models import AbstractBaseModel
from django_extensions.db.fields import AutoSlugField, slugify
from django.core.validators import EmailValidator
from django.utils.translation import ugettext_lazy as _
from pytz import common_timezones
from config.settings.base import LANGUAGES, LANGUAGE_CODE, TIME_ZONE

TITLE_CHOICES = [('Mr.', 'Mr.'), ('Mrs.', 'Mrs.'), ('Ms.', 'Ms.')]
RELATIONSHIP_CHOICES = [('Mother', 'Mother'), ('Father', 'Father'), ('Guardian', 'Guardian')]
COMMUNICATION_CHOICES = [('Email', 'Email'), ('Phone', 'Phone')]


class Parent(AbstractBaseModel):
    slug = AutoSlugField(max_length=255, db_index=True, allow_unicode=True, unique=True, populate_from=[
        'created_by__name', 'created_on'], slugify_function=slugify)
    first_name = models.CharField(max_length=255, null=True, blank=True)
    last_name = models.CharField(max_length=255, null=True, blank=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    title = models.CharField(max_length=255, choices=TITLE_CHOICES,
                             null=True, blank=True)
    national_no = models.CharField(max_length=255, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    relationship_to_patient = models.CharField(max_length=255, choices=RELATIONSHIP_CHOICES,
                                               null=True, blank=True)
    address1 = models.CharField(max_length=512, blank=True, null=True)
    address2 = models.CharField(max_length=512, blank=True, null=True)
    address3 = models.CharField(max_length=512, blank=True, null=True)
    city = models.CharField(max_length=255, blank=True, null=True)
    state = models.CharField(max_length=255, blank=True, null=True)
    country = models.CharField(max_length=255, blank=True, null=True)
    zipcode = models.CharField(max_length=11, blank=True, null=True)
    email = models.CharField(
        _('email address'),
        max_length=150,
        null=True,
        blank=True,
        help_text=_('Required. 150 characters or fewer.'),
        validators=[EmailValidator],
    )
    phone1 = models.CharField(max_length=15, null=True, blank=True)
    phone2 = models.CharField(max_length=15, null=True, blank=True)
    pref_comm = models.CharField(
        max_length=10, choices=COMMUNICATION_CHOICES, default='Email', blank=True, null=True)
    language = models.CharField(
        max_length=10, choices=LANGUAGES, default=LANGUAGE_CODE, blank=True, null=True)

    timezone = models.CharField(max_length=100, choices=[
        (t, t) for t in common_timezones], default=TIME_ZONE, blank=True, null=True)

    class Meta:
        default_permissions = ()
        permissions = []

from django.db import models

from config.settings.base import FIELD_ENCRYPTION_KEYS
from django_synergy.synergy_libraries.models import Ethnicity, Race, Diagnosis
from django_synergy.utils.models import AbstractBaseModel
from django_extensions.db.fields import AutoSlugField, slugify
from django.core.validators import EmailValidator
from django.utils.translation import ugettext_lazy as _
from encrypted_fields import fields

GENDERS = [
    ('Male', 'Male'),
    ('Female', 'Female'),
    ('Undeclared', 'Undeclared'),
]


class Patient(AbstractBaseModel):
    slug = AutoSlugField(max_length=255, db_index=True, allow_unicode=True, unique=True, populate_from=[
        'first_name', 'last_name'], slugify_function=slugify)
    _first_name = fields.EncryptedCharField(max_length=255, editable=False)
    first_name = fields.SearchField(hash_key=FIELD_ENCRYPTION_KEYS[0],
                                    encrypted_field_name="_first_name")
    _last_name = fields.EncryptedCharField(max_length=255, editable=False)
    last_name = fields.SearchField(hash_key=FIELD_ENCRYPTION_KEYS[0],
                                   encrypted_field_name="_last_name")
    middle_name = fields.EncryptedCharField(max_length=255, blank=True, null=True)
    patient_aka = fields.EncryptedCharField(max_length=255, blank=True, null=True)
    national_no = fields.EncryptedCharField(max_length=255, blank=True, null=True)
    _gender = fields.EncryptedCharField(choices=GENDERS, max_length=50, editable=False)
    gender = fields.SearchField(hash_key=FIELD_ENCRYPTION_KEYS[0],
                                encrypted_field_name="_gender")
    ethnicity = models.ManyToManyField(
        Ethnicity, through='PatientEthnicity', related_name='patient_ethnicity', blank=True, symmetrical=False)
    race = models.ManyToManyField(
        Race, through='PatientRace', related_name='patient_race', blank=True, symmetrical=False)
    _date_of_birth = fields.EncryptedDateField(editable=False)
    date_of_birth = fields.SearchField(hash_key=FIELD_ENCRYPTION_KEYS[0],
                                       encrypted_field_name="_date_of_birth")
    address1 = fields.EncryptedCharField(max_length=512)
    address2 = fields.EncryptedCharField(max_length=512, blank=True, null=True)
    address3 = fields.EncryptedCharField(max_length=512, blank=True, null=True)
    _city_name = fields.EncryptedCharField(max_length=255, editable=False)
    city_name = fields.SearchField(hash_key=FIELD_ENCRYPTION_KEYS[0],
                                   encrypted_field_name="_city_name")
    _state_name = fields.EncryptedCharField(max_length=255, editable=False)
    state_name = fields.SearchField(hash_key=FIELD_ENCRYPTION_KEYS[0],
                                    encrypted_field_name="_state_name")
    _country_name = fields.EncryptedCharField(max_length=255, editable=False)
    country_name = fields.SearchField(hash_key=FIELD_ENCRYPTION_KEYS[0],
                                      encrypted_field_name="_country_name")
    zipcode = fields.EncryptedCharField(max_length=11)
    carrier = fields.EncryptedCharField(max_length=255, blank=True, null=True)
    policy_number = fields.EncryptedCharField(max_length=255, blank=True, null=True)
    group_number = fields.EncryptedCharField(max_length=255, blank=True, null=True)
    contact_person = fields.EncryptedCharField(max_length=255, blank=True, null=True)
    contact_email = fields.EncryptedCharField(
        _('email address'),
        max_length=150,
        help_text=_('Required. 150 characters or fewer.'),
        validators=[EmailValidator],
        blank=True,
        null=True
    )
    contact_phone = fields.EncryptedCharField(max_length=15, null=True, blank=True)
    diagnosis = models.ManyToManyField(
        Diagnosis, through='PatientDiagnosis', blank=True, symmetrical=False)

    class Meta:
        default_permissions = ()
        permissions = []


class PatientEthnicity(AbstractBaseModel):
    slug = AutoSlugField(max_length=255, db_index=True, allow_unicode=True, unique=True, populate_from=[
        'patient__first_name', 'patient__last_name', 'ethnicity__name'], slugify_function=slugify)
    patient = models.ForeignKey(Patient, related_name="PatientEthnicity_patient", on_delete=models.PROTECT)
    ethnicity = models.ForeignKey(Ethnicity, related_name="PatientEthnicity_ethnicity", on_delete=models.PROTECT)

    class Meta:
        default_permissions = ()
        permissions = []


class PatientRace(AbstractBaseModel):
    slug = AutoSlugField(max_length=255, db_index=True, allow_unicode=True, unique=True, populate_from=[
        'patient__first_name', 'patient__last_name', 'race__name'], slugify_function=slugify)
    patient = models.ForeignKey(Patient, related_name="PatientRace_patient", on_delete=models.PROTECT)
    race = models.ForeignKey(Race, related_name="PatientRace_race", on_delete=models.PROTECT)

    class Meta:
        default_permissions = ()
        permissions = []


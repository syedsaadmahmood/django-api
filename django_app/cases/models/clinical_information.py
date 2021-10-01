from django.db import models
from django.utils import timezone
from django_extensions.db.fields import AutoSlugField, slugify
from config.settings.base import PRESCRIPTION_S3_KEY_PREFIX
from django_synergy.users.models import User
from django_synergy.utils.models import S3AbstractModel, AbstractBaseModel
from . import Case
from .patient import Patient
from ...synergy_libraries.models import Diagnosis
from datetime import date
import math


class Prescription(AbstractBaseModel):
    slug = AutoSlugField(max_length=255, db_index=True, allow_unicode=True, unique=True, populate_from=[
        'patient__first_name', 'patient__last_name', 'id'], slugify_function=slugify)
    patient = models.ForeignKey(
        Patient, related_name='prescription_patient', on_delete=models.PROTECT)
    referring_physician = models.ForeignKey(
        User, related_name='prescription_referring', on_delete=models.PROTECT, blank=True, null=True)
    referring_physician_name = models.CharField(max_length=15, blank=True, null=True)
    note = models.TextField(blank=True, null=True)

    class Meta:
        default_permissions = ()
        permissions = []


class PrescriptionUpload(S3AbstractModel):
    _key_prefix = PRESCRIPTION_S3_KEY_PREFIX
    prescription = models.ForeignKey(Prescription, on_delete=models.PROTECT)
    slug = None


class PatientDiagnosis(AbstractBaseModel):
    slug = AutoSlugField(max_length=255, db_index=True, allow_unicode=True, unique=True, populate_from=[
        'patient__first_name', 'patient__last_name', 'diagnosis__code'], slugify_function=slugify)
    patient = models.ForeignKey(Patient, related_name="PatientDiagnosis_patient", on_delete=models.PROTECT)
    diagnosis = models.ForeignKey(Diagnosis, related_name="PatientDiagnosis_diagnosis", on_delete=models.PROTECT)

    class Meta:
        default_permissions = ()
        unique_together = ('patient', 'diagnosis')


class History(AbstractBaseModel):
    slug = AutoSlugField(max_length=255, db_index=True, allow_unicode=True, unique=True, populate_from=[
        'patient__first_name', 'patient__last_name', 'id'], slugify_function=slugify)
    patient = models.ForeignKey(
        Patient, related_name='history_patient', on_delete=models.PROTECT)
    note = models.TextField()
    date = models.DateField(default=timezone.now)

    class Meta:
        default_permissions = ()


class Vitals(AbstractBaseModel):
    slug = AutoSlugField(max_length=255, db_index=True, allow_unicode=True, unique=True, populate_from=[
        'case__patient__first_name', 'case__patient__last_name', 'case__case_no'], slugify_function=slugify)
    case = models.OneToOneField(
        Case, related_name='vitals_case', on_delete=models.PROTECT)
    gestational_age_weeks = models.CharField(max_length=15, blank=True, null=True)
    gestational_age_days = models.CharField(max_length=15, blank=True, null=True)
    discharge_date = models.DateField(blank=True, null=True)
    referring_hospital = models.CharField(max_length=15, blank=True, null=True)
    gestational_age_at_birth_weeks = models.CharField(max_length=15, blank=True, null=True)
    gestational_age_at_birth_days = models.CharField(max_length=15, blank=True, null=True)
    discharge_weight = models.CharField(max_length=15, blank=True, null=True)
    birth_weight = models.CharField(max_length=15, blank=True, null=True)
    birth_height = models.CharField(max_length=15, blank=True, null=True)
    discharge_height = models.CharField(max_length=15, blank=True, null=True)

    class Meta:
        default_permissions = ()

    @property
    def gestational_age(self):
        if self.gestational_age_at_birth_days is not None and self.gestational_age_at_birth_weeks is not None:
            date_of_birth = self.case.patient.date_of_birth
            current_date = date.today()
            diff_in_days = current_date - date_of_birth
            diff_in_days = diff_in_days.days
            total_days = int(self.gestational_age_at_birth_days.split(' ')[0]) + diff_in_days
            weeks = math.floor(total_days / 7 + int(self.gestational_age_at_birth_weeks.split(' ')[0]))
            days = total_days % 7
            return days, weeks
        else:
            return None, None

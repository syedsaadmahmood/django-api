from django.db import models

from django_synergy.utils.models import AbstractBaseModel
from django_synergy.devices.models import Device
from django_synergy.users.models import User
from .parent import Parent
from .patient import Patient
from django_extensions.db.fields import AutoSlugField, slugify
from config.settings.base import TIME_ZONE
from pytz import common_timezones
from ...accounts.models import Account


def increment_case_number():
    last_case = Case.objects.all().order_by('id').last()
    if not last_case:
        return '0000001'
    case_no = last_case.case_no
    case_int = int(case_no)
    new_case_int = case_int + 1
    new_case_no = str(new_case_int)
    new_case_no = new_case_no.zfill(7)
    return new_case_no


class Case(AbstractBaseModel):

    def __str__(self):
        return str(self.case_no)

    slug = AutoSlugField(max_length=255, db_index=True, allow_unicode=True, unique=True, populate_from=[
        'case_no', 'patient__first_name', 'patient__last_name'], slugify_function=slugify)
    case_no = models.CharField(max_length=15, default=increment_case_number)
    device = models.ManyToManyField(Device, through='CaseDevice', related_name='case_device', blank=True,
                                    symmetrical=False)
    patient = models.ForeignKey(
        Patient, related_name='case_patient', on_delete=models.PROTECT)
    parent = models.ForeignKey(
        Parent, related_name='case_parent', on_delete=models.PROTECT, blank=True, null=True)
    parent_user = models.ForeignKey(
        User, related_name='case_parent_user', on_delete=models.PROTECT, blank=True, null=True)
    account = models.ForeignKey(
        Account, related_name='case_account', on_delete=models.PROTECT)
    is_consent = models.BooleanField(default=False, null=False)
    is_active = models.BooleanField(default=False, null=False)
    timezone = models.CharField(max_length=100, choices=[
        (t, t) for t in common_timezones], default=TIME_ZONE, blank=True, null=True)
    is_archived = models.BooleanField(default=False, null=False)
    is_closed = models.BooleanField(default=False)

    class Meta:
        default_permissions = ()
        permissions = [
            ("case-create", "Can create case"),

            ("case-list-account", "Can view list of all account cases"),
            ("case-detail-account", "Can view detail of all account cases"),
            ("case-edit-account", "Can edit all account cases"),
            ("case-role-account", "Can view case roles of all account cases"),
            ("case-role-edit-account", "Can edit case roles of all account cases"),
            ("case-notification-matrix-account", "Can view notification matrix of all account cases"),
            ("case-notification-matrix-edit-account", "Can edit notification matrix of all account cases"),
            ("case-patient-account", "Can view patient detail of all account cases"),
            ("case-patient-edit-account", "Can edit patient detail of all account cases"),
            ("case-parent-account", "Can view parent detail of all account cases"),
            ("case-parent-edit-account", "Can edit parent detail of all account cases"),
            ("case-note-create-account", "Can create parent and provider notes of all account cases"),
            ("case-note-account", "Can view parent and provider notes of all account cases"),
            ("case-note-detail-account", "Can view detail of parent and provider notes of all account cases"),
            ("case-note-edit-account", "Can edit parent and provider notes of all account cases"),
            ("case-interpretation-create-account", "Can create interpretation of all account cases"),
            ("case-interpretation-account", "Can view interpretation of all account cases"),
            ("case-interpretation-detail-account", "Can view detail of all account case interpretations"),
            ("case-interpretation-edit-account", "Can edit all account case interpretations"),
            ("case-clinical-information-account", "Can view clinical information of all account cases"),
            ("case-clinical-information-edit-account", "Can edit clinical information of all account cases"),

            ("case-list-subsidiary", "Can view list of all subsidiary cases"),
            ("case-detail-subsidiary", "Can view detail of all subsidiary cases"),
            ("case-edit-subsidiary", "Can edit all subsidiary cases"),
            ("case-role-subsidiary", "Can view case roles of all subsidiary cases"),
            ("case-role-edit-subsidiary", "Can edit case roles of all subsidiary cases"),
            ("case-notification-matrix-subsidiary", "Can view notification matrix of all subsidiary cases"),
            ("case-notification-matrix-edit-subsidiary", "Can edit notification matrix of all subsidiary cases"),
            ("case-patient-subsidiary", "Can view patient detail of all subsidiary cases"),
            ("case-patient-edit-subsidiary", "Can edit patient detail of all subsidiary cases"),
            ("case-parent-subsidiary", "Can view parent detail of all subsidiary cases"),
            ("case-parent-edit-subsidiary", "Can edit parent detail of all subsidiary cases"),
            ("case-note-create-subsidiary", "Can create parent and provider notes of all subsidiary cases"),
            ("case-note-subsidiary", "Can view parent and provider notes of all subsidiary cases"),
            ("case-note-detail-subsidiary", "Can view detail of parent and provider notes of all subsidiary cases"),
            ("case-note-edit-subsidiary", "Can edit parent and provider notes of all subsidiary cases"),
            ("case-interpretation-create-subsidiary", "Can create interpretation of all subsidiary cases"),
            ("case-interpretation-subsidiary", "Can view interpretation of all subsidiary cases"),
            ("case-interpretation-detail-subsidiary", "Can view detail of all subsidiary case interpretations"),
            ("case-interpretation-edit-subsidiary", "Can edit all account subsidiary interpretations"),
            ("case-clinical-information-subsidiary", "Can view clinical information of all subsidiary cases"),
            ("case-clinical-information-edit-subsidiary", "Can edit clinical information of all subsidiary cases"),

            ("case-list-assigned-to-users", "Can view list of cases assigned to account users"),
            ("case-detail-assigned-to-users", "Can view detail of cases assigned to account users"),
            ("case-role-assigned-to-users", "Can view case roles of cases assigned to account users"),
            ("case-notification-matrix-assigned-to-users",
             "Can view notification matrix of cases assigned to account users"),
            ("case-patient-assigned-to-users", "Can view patient detail of cases assigned to account users"),
            ("case-parent-assigned-to-users", "Can view parent detail of cases assigned to account users"),
            ("case-note-assigned-to-users", "Can view parent and provider notes of cases assigned to account users"),
            ("case-note-detail-assigned-to-users",
             "Can view detail of parent and provider notes of cases assigned to account users"),
            ("case-interpretation-assigned-to-users", "Can view interpretation of cases assigned to account users"),
            ("case-interpretation-detail-assigned-to-users",
             "Can view detail of case interpretations assigned to account users"),
            ("case-clinical-information-assigned-to-users",
             "Can view clinical information of cases assigned to account users"),

            ("case-list-assigned", "Can view list of assigned cases"),
            ("case-detail-assigned", "Can view detail of assigned cases"),
            ("case-edit-assigned", "Can edit assigned cases"),
            ("case-role-assigned", "Can view case roles of assigned cases"),
            ("case-role-edit-assigned", "Can edit case roles of assigned cases"),
            ("case-notification-matrix-assigned", "Can view notification matrix of assigned cases"),
            ("case-notification-matrix-edit-assigned", "Can edit notification matrix of assigned cases"),
            ("case-patient-assigned", "Can view patient detail of assigned cases"),
            ("case-patient-edit-assigned", "Can edit patient detail of assigned cases"),
            ("case-parent-assigned", "Can view parent detail of assigned cases"),
            ("case-parent-edit-assigned", "Can edit parent detail of assigned cases"),
            ("case-note-create-assigned", "Can create parent and provider notes of assigned cases"),
            ("case-note-assigned", "Can view parent and provider notes of assigned cases"),
            ("case-note-detail-assigned", "Can view detail of parent and provider notes of assigned cases"),
            ("case-note-edit-assigned", "Can edit parent and provider notes of assigned cases"),
            ("case-interpretation-create-assigned", "Can create interpretation of assigned cases"),
            ("case-interpretation-assigned", "Can view interpretation of assigned cases"),
            ("case-interpretation-detail-assigned", "Can view detail of assigned case interpretations"),
            ("case-interpretation-edit-assigned", "Can edit assigned case interpretations"),
            ("case-clinical-information-assigned", "Can view clinical information of assigned cases"),
            ("case-clinical-information-edit-assigned", "Can edit clinical information of assigned cases"),
        ]


class CaseDevice(AbstractBaseModel):
    slug = AutoSlugField(max_length=255, db_index=True, allow_unicode=True, unique=True, populate_from=[
        'case__case_no', 'device__serial_number'], slugify_function=slugify)
    case = models.ForeignKey(Case, related_name="CaseDevice_case", on_delete=models.PROTECT)
    device = models.ForeignKey(Device, related_name="CaseDevice_device", on_delete=models.PROTECT)
    is_active = models.BooleanField(default=False, null=False)

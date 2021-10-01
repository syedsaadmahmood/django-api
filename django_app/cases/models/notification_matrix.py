from django.db import models
from django_extensions.db.fields import AutoSlugField, slugify
from django_synergy.cases.models import CaseDefaultRole, Case
from django_synergy.notifications.models import NotificationType
from django_synergy.utils.models import AbstractBaseModel
from django_synergy.users.models import User

SUPER_ADMIN_USER_ID = 1


class DefaultNotificationMatrix(AbstractBaseModel):
    slug = AutoSlugField(max_length=255, db_index=True, allow_unicode=True, unique=True, populate_from=[
        'case_default_role__name', 'notification_type__name'], slugify_function=slugify)
    case_default_role = models.ForeignKey(
        CaseDefaultRole, related_name='default_notification_role', on_delete=models.PROTECT)
    notification_type = models.ForeignKey(
        NotificationType, related_name='default_notification_type', on_delete=models.PROTECT)
    is_notified = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='+', default=SUPER_ADMIN_USER_ID,
                                   null=True, blank=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='+', default=SUPER_ADMIN_USER_ID,
                                   null=True, blank=True)

    unique_together = ('case_default_role', 'notification_type')

    class Meta:
        default_permissions = ()
        permissions = [
            ("default-notification-matrix-list", "Can view default notification matrix list"),
            ("default-notification-matrix-edit", "Can edit default notification matrix"),
            ("default-notification-matrix-create", "Can create default notification matrix")
        ]


class CaseNotificationMatrix(AbstractBaseModel):
    slug = AutoSlugField(max_length=255, db_index=True, allow_unicode=True, unique=True, populate_from=[
        'case__case_no', 'case_default_role__name', 'notification_type__name'], slugify_function=slugify)
    case = models.ForeignKey(
        Case, related_name='notification_matrix_case', on_delete=models.PROTECT)
    case_default_role = models.ForeignKey(
        CaseDefaultRole, related_name='notification_matrix_role', on_delete=models.PROTECT)
    notification_type = models.ForeignKey(
        NotificationType, related_name='notification_matrix_type', on_delete=models.PROTECT)
    is_notified = models.BooleanField(default=False)

    class Meta:
        default_permissions = ()
        permissions = []

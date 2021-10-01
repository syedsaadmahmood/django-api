from django.db import models

from django_synergy.cases.models import Case
from django_synergy.utils.models import AbstractBaseModel
from django_extensions.db.fields import AutoSlugField, slugify
from django_synergy.users.models import User

SUPER_ADMIN_USER_ID = 1


class CaseDefaultRole(AbstractBaseModel):
    slug = AutoSlugField(max_length=255, db_index=True, allow_unicode=True, unique=True, populate_from=[
        'name'], slugify_function=slugify)
    name = models.CharField(max_length=255)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='+', default=SUPER_ADMIN_USER_ID,
                                   null=True, blank=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='+', default=SUPER_ADMIN_USER_ID,
                                   null=True, blank=True)

    class Meta:
        default_permissions = ()
        permissions = []


class CaseRole(AbstractBaseModel):

    def __str__(self):
        return self.user.name

    slug = AutoSlugField(max_length=255, db_index=True, allow_unicode=True, unique=True, populate_from=[
        'case__patient__first_name', 'case__patient__last_name', 'case_default_role__name'], slugify_function=slugify)
    case = models.ForeignKey(
        Case, related_name='role_case', on_delete=models.PROTECT)
    case_default_role = models.ForeignKey(
        CaseDefaultRole, related_name='default_role', on_delete=models.PROTECT)
    user = models.ForeignKey(
        User, related_name='case_role_user', on_delete=models.PROTECT, blank=True, null=True)

    class Meta:
        default_permissions = ()
        permissions = []

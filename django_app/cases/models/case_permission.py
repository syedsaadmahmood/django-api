from django.db import models
from django.db.models import Model

from django_synergy.cases.models import CaseDefaultRole


class CasePermission(Model):
    name = models.CharField(max_length=255)
    codename = models.CharField(max_length=255)


class CaseRolePermission(Model):
    case_default_role = models.ForeignKey(CaseDefaultRole, related_name="role_permissions", on_delete=models.PROTECT)
    case_permission = models.ForeignKey(CasePermission, related_name="case_permissions", on_delete=models.PROTECT)

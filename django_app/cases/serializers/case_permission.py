from rest_framework.serializers import ModelSerializer

from django_synergy.cases.models import CasePermission, CaseRolePermission


class CasePermissionSerializer(ModelSerializer):
    class Meta:
        model = CasePermission
        fields = ('id', 'codename', 'name')


class CaseRolePermissionSerializer(ModelSerializer):
    class Meta:
        model = CaseRolePermission
        fields = ('case_default_role', 'case_permission')

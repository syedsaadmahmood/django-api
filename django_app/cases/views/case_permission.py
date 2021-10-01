from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.pagination import PageNumberPagination
from django_synergy.cases.models import CasePermission, CaseRolePermission, CaseDefaultRole
from django_synergy.cases.serializers.case_permission import CasePermissionSerializer, CaseRolePermissionSerializer


class CasePermissionViewSet(ModelViewSet):
    queryset = CasePermission.objects.all()
    pagination_class = PageNumberPagination
    lookup_field = 'id'
    serializer_class = CasePermissionSerializer


class CaseRolePermissionViewSet(ModelViewSet):
    queryset = CaseRolePermission.objects.all()
    pagination_class = PageNumberPagination
    lookup_field = 'id'
    serializer_class = CaseRolePermissionSerializer

    def retrieve(self, request, *args, **kwargs):
        case_default_role = CaseDefaultRole.objects.get(id=kwargs["id"])
        case_role_permissions = case_default_role.role_permissions.all()
        permissionIds = []
        for case_role_permission in case_role_permissions:
            permissionIds.append(case_role_permission.case_permission.id)
        case_permissions = CasePermission.objects.filter(id__in=permissionIds)

        return Response(status=status.HTTP_200_OK,
                        data={"success": True,
                              "data": CasePermissionSerializer(case_permissions, many=True).data})

    def create(self, request, *args, **kwargs):
        data = request.data
        case_default_role = CaseDefaultRole.objects.get(id=data['role'])

        CaseRolePermission.objects.filter(case_default_role=case_default_role).delete()
        for permission in data['permissions']:
            send_data = {
                'case_default_role': data['role'],
                'case_permission': permission
            }
            case_role_permission_serializer = CaseRolePermissionSerializer(data=send_data,
                                                                           context=self.get_serializer_context())

            if case_role_permission_serializer.is_valid(raise_exception=True):
                case_role_permission_serializer_data = case_role_permission_serializer.validated_data
                case_role_permission_serializer.save()

        return Response(status=status.HTTP_200_OK,
                        data={"success": True,
                              "data": None})

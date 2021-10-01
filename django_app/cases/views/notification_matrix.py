from rest_framework.exceptions import PermissionDenied
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from django_synergy.cases.models import CaseDefaultRole, DefaultNotificationMatrix, Case, CaseNotificationMatrix
from django_synergy.cases.serializers.notification_matrix import NotificationMatrixSerializer, \
    NotificationMatrixWritableSerializer, CaseNotificationMatrixWritableSerializer, CaseNotificationMatrixSerializer
from django_synergy.cases.utils import fetchChildAccounts, fetchCasesAssigned, fetchCasesAssignedToUser
from django_synergy.utils.views import BaseViewset
from rest_framework.permissions import IsAuthenticated
from django_synergy.cases.permissions import user_has_permission, get_user_permission_list, \
    CanViewCaseNotificationMatrix, CanEditCaseNotificationMatrix, IsSuperUser


class NotificationMatrixViewSet(BaseViewset):
    queryset = CaseDefaultRole.objects.all()
    lookup_field = 'slug'
    action_serializers = {
        'default': NotificationMatrixSerializer,
        'update': NotificationMatrixWritableSerializer,
    }

    def get_permissions(self):
        if self.action == "edit":
            self.permission_classes = [IsSuperUser]
        else:
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    @action(["post"], detail=False)
    def edit(self, request, *args, **kwargs):
        try:
            for data in request.data:
                notification_matrix = DefaultNotificationMatrix.objects.get(case_default_role__slug=data['role'],
                                                                            notification_type__slug=data[
                                                                                'notification_type'])
                if data["is_notified"] is True or data["is_notified"] == "true":
                    notification_matrix.is_notified = True
                else:
                    notification_matrix.is_notified = False
                notification_matrix.save()
            return Response({"status": "success", "message": 'Notification Matrix Updated'}
                            , status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"status": "failed", "message": e}
                            , status=status.HTTP_400_BAD_REQUEST)


class CaseNotificationMatrixViewSet(BaseViewset):
    queryset = CaseNotificationMatrix.objects.all()
    lookup_field = 'slug'
    action_serializers = {
        'default': CaseNotificationMatrixSerializer,
        'update': CaseNotificationMatrixWritableSerializer,
    }

    def get_queryset(self):
        if hasattr(self.request.user, 'is_superuser'):
            if self.request.user.is_superuser:
                return CaseNotificationMatrix.objects.all()
        if hasattr(self.request.user, 'account'):
            if self.request.user.account:
                permission_list = get_user_permission_list(self.request.user)
                account_instance = CaseNotificationMatrix.objects.none()
                if user_has_permission('case-notification-matrix-account', user_permissions=permission_list):
                    account_instance = CaseNotificationMatrix.objects.filter(
                        case__account__id=self.request.user.account.id)

                subsidiary_account_instance = CaseNotificationMatrix.objects.none()
                if user_has_permission('case-notification-matrix-subsidiary', user_permissions=permission_list):
                    account_slugs_list = []
                    fetchChildAccounts(account_slugs_list, self.request.user.account)
                    subsidiary_account_instance = CaseNotificationMatrix.objects.filter(
                        case__slug__in=account_slugs_list)

                cases_assigned_instance = CaseNotificationMatrix.objects.none()
                if user_has_permission('case-notification-matrix-assigned', user_permissions=permission_list):
                    cases_assigned_slug_list = []
                    fetchCasesAssigned(cases_assigned_slug_list, self.request.user)
                    cases_assigned_instance = CaseNotificationMatrix.objects.filter(
                        case__slug__in=cases_assigned_slug_list)

                case_list_assigned_to_users = CaseNotificationMatrix.objects.none()
                if user_has_permission('case-notification-matrix-assigned-to-users', user_permissions=permission_list):
                    cases_assigned_slug_list = []
                    fetchCasesAssignedToUser(cases_assigned_slug_list, self.request.user.account)
                    case_list_assigned_to_users = CaseNotificationMatrix.objects.filter(
                        case__slug__in=cases_assigned_slug_list)

                return account_instance | subsidiary_account_instance | cases_assigned_instance | case_list_assigned_to_users

        else:
            return CaseNotificationMatrix.objects.none()

    def get_permissions(self):
        if self.action == "retrieve":
            self.permission_classes = [CanViewCaseNotificationMatrix]
        elif self.action == "create":
            self.permission_classes = [CanEditCaseNotificationMatrix]
        elif self.action == "update":
            self.permission_classes = [CanEditCaseNotificationMatrix]
        elif self.action == "partial_update":
            self.permission_classes = [CanEditCaseNotificationMatrix]
        else:
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    def retrieve(self, request, *args, **kwargs):
        try:
            case = Case.objects.get(slug=kwargs['slug'])
            case_default_roles = CaseDefaultRole.objects.all().order_by('-created_on')
            case_notification_serializer = CaseNotificationMatrixSerializer(case_default_roles, many=True,
                                                                            context={"case": case}).data
            return Response(status=status.HTTP_200_OK,
                            data={"success": True, "data": case_notification_serializer})

        except Exception as e:
            return Response({"status": "failed", "message": e}
                            , status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        try:

            for data in request.data:
                notification_matrix = CaseNotificationMatrix.objects.get(case_default_role__slug=data['role'],
                                                                         notification_type__slug=data[
                                                                             'notification_type'],
                                                                         case__slug=kwargs['slug'])

                self.check_object_permissions(self.request, notification_matrix)
                notification_matrix.is_notified = data["is_notified"]
                notification_matrix.save()

            return Response({"status": "success", "message": 'Notification Matrix Updated'}
                            , status=status.HTTP_200_OK)

        except PermissionDenied as pd:
            raise PermissionDenied

        except Exception as e:
            return Response({"status": "failed", "message": e}
                            , status=status.HTTP_400_BAD_REQUEST)

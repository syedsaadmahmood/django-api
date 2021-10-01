from datetime import datetime
import logging

from django.db import transaction
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from django_synergy.cases.models.case import Case, CaseDevice
from django_synergy.cases.utils import fetchChildAccounts, fetchCasesAssigned, fetchCasesAssignedToUser
from django_synergy.cases.views.utils import create_patient, create_parent, create_patient_ethnicity, \
    create_patient_race, create_prescription, create_history, create_patient_diagnosis, create_vitals, create_roles, \
    create_notification_matrix
from django_synergy.cases.serializers import CaseSerializer, CaseWritableSerializer, CaseListSerializer, \
    CaseDetailSerializer, SimpleCaseSerializer, CaseDeviceSerializer, CaseStatusSerializer
from django_synergy.devices.models import Device, DeviceSettings
from django_synergy.devices.serializers import DeviceSettingsSerializer
from django_synergy.notifications.utils import generate_case_notification, \
    generate_case_user_notification
from django_synergy.utils.permissions import get_user_permission_list

from django_synergy.utils.views import BaseViewset
from django_synergy.cases.permissions import CanViewCaseList, user_has_permission, \
    CanViewCaseDetail, CanCreateCase, CanEditCase, IsSuperUser

logger = logging.getLogger(__name__)


class CaseViewSet(BaseViewset):
    queryset = Case.objects.all()
    lookup_field = 'slug'
    action_serializers = {
        'default': CaseSerializer,
        'create': CaseWritableSerializer,
        'list': CaseListSerializer,
        'retrieve': CaseDetailSerializer,
        'status': CaseStatusSerializer
    }

    def get_queryset(self):
        if hasattr(self.request.user, 'is_superuser'):
            if self.request.user.is_superuser:
                return Case.objects.all()
        if hasattr(self.request.user, 'account'):
            if self.request.user.account:
                permission_list = get_user_permission_list(self.request.user)
                queryset = Case.objects.filter(is_archived=False)
                account_cases = Case.objects.none()
                if user_has_permission('case-list-account', user_permissions=permission_list):
                    account_cases = queryset.filter(account=self.request.user.account)

                subsidiary_account_cases = Case.objects.none()
                if user_has_permission('case-list-subsidiary', user_permissions=permission_list):
                    account_slugs_list = []
                    fetchChildAccounts(account_slugs_list, self.request.user.account)
                    subsidiary_account_cases = queryset.filter(account__slug__in=account_slugs_list)

                cases_assigned = Case.objects.none()
                if user_has_permission('case-list-assigned', user_permissions=permission_list):
                    cases_assigned_slug_list = []
                    fetchCasesAssigned(cases_assigned_slug_list, self.request.user)
                    cases_assigned = queryset.filter(slug__in=cases_assigned_slug_list)

                case_list_assigned_to_users = Case.objects.none()
                if user_has_permission('case-list-assigned-to-users', user_permissions=permission_list):
                    cases_assigned_slug_list = []
                    fetchCasesAssignedToUser(cases_assigned_slug_list, self.request.user.account)
                    case_list_assigned_to_users = queryset.filter(slug__in=cases_assigned_slug_list)

                return account_cases | subsidiary_account_cases | cases_assigned | case_list_assigned_to_users

        else:
            return Case.objects.none()

    def get_permissions(self):
        if self.action == "list":
            self.permission_classes = [CanViewCaseList]
        elif self.action == "retrieve":
            self.permission_classes = [CanViewCaseDetail]
        elif self.action == "create":
            self.permission_classes = [CanCreateCase]
        elif self.action == "update":
            self.permission_classes = [CanEditCase]
        elif self.action == "partial_update":
            self.permission_classes = [CanEditCase]
        elif self.action == "close":
            self.permission_classes = [CanEditCase]
        elif self.action == "device_change":
            self.permission_classes = [CanEditCase]
        elif self.action == "archive":
            self.permission_classes = [IsSuperUser]
        elif self.action == "case_list_to_archive":
            self.permission_classes = [IsSuperUser]
        elif self.action == "unarchive":
            self.permission_classes = [IsSuperUser]
        elif self.action == "edit":
            self.permission_classes = [CanEditCase]
        elif self.action == "status":
            self.permission_classes = [CanEditCase]
        else:
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    def get_serializer_context(self):
        context = super(CaseViewSet, self).get_serializer_context()
        context.update({"request": self.request})
        return context

    def create(self, request, *args, **kwargs):
        try:
            data = request.data
            if "date_of_birth" in data["patient"]:
                date_of_birth = datetime.strptime(data["patient"]["date_of_birth"], "%d-%m-%Y").date()
                data["patient"]["date_of_birth"] = str(date_of_birth)

            with transaction.atomic():
                # Device
                device = Device.objects.get(slug=data['device']['slug'])
                if device.status == 'Available':
                    device.status = 'Assigned'
                    device.save()
                else:
                    return Response({"status": "failed", "message": 'Device status should be Available'}
                                    , status=status.HTTP_400_BAD_REQUEST)

                # Patient
                patient = create_patient(data, self)

                # Parent
                parent, parent_user = create_parent(data, self)

                # Ethnicity
                create_patient_ethnicity(data, self, patient)

                # Race
                create_patient_race(data, self, patient)

                # Prescription
                create_prescription(data, self, patient)

                # History
                create_history(data, self, patient)

                # Diagnosis
                create_patient_diagnosis(data, self, patient)

                # Case
                case_data = {
                    "patient": patient.id,
                    "parent_user": parent_user.id if parent_user is not None else parent_user,
                    "parent": parent.id if parent is not None else parent,
                    "account": data['account']
                }
                case_serializer = CaseWritableSerializer(data=case_data,
                                                         context=self.get_serializer_context())
                if case_serializer.is_valid(raise_exception=True):
                    case_serializer_data = case_serializer.validated_data
                    case = case_serializer.save()

                    device_data = {"case": case.id, "device": device.id, "is_active": True}
                    case_device_serializer = CaseDeviceSerializer(data=device_data,
                                                                  context=self.get_serializer_context())
                    if case_device_serializer.is_valid(raise_exception=True):
                        case_serializer_data = case_device_serializer.validated_data
                        case_device_serializer.save()

                # Vitals
                create_vitals(data, self, case)

                # Roles
                role_users = create_roles(data, self, case)

                # Notification Matrix
                case_notification_matrices = create_notification_matrix(data, self, case)

                case_data = CaseSerializer(case, many=False, context=self.get_serializer_context()).data

                # send_notifications(case_notification_matrices, role_users, case, request)

                return Response(case_data, status.HTTP_200_OK)

        except Exception as e:
            logger.exception(e)
            return Response({"status": "failed", "message": e}
                            , status=status.HTTP_400_BAD_REQUEST)

    @action(["get"], detail=False, permission_classes=[CanViewCaseList])
    def case_list_interpretation(self, request, *args, **kwargs):
        cases = self.filter_queryset(self.get_queryset())
        return Response(status=status.HTTP_200_OK,
                        data={"success": True,
                              "data": SimpleCaseSerializer(cases, many=True).data})

    @action(["post"], detail=True)
    def device_change(self, request, *args, **kwargs):
        try:
            self.check_object_permissions(request, self.get_object())
            data = request.data
            case = Case.objects.get(slug=kwargs["slug"])
            with transaction.atomic():
                old_device = Device.objects.get(serial_number=data["old_device"]["serial_number"])
                if CaseDevice.objects.filter(is_active=True,
                                             case=case).first().device.serial_number == old_device.serial_number:
                    old_device.status = data["old_device"]["status"]
                    old_device.save()
                else:
                    return Response(status=status.HTTP_200_OK,
                                    data={"success": False, "status_code": 200,
                                          "message": "This device don't belong to this case"})

                new_device = Device.objects.get(slug=data["new_device"]["serial_number"])

                # if case.account.slug != new_device.slug:
                #     return Response(status=status.HTTP_200_OK,
                #                     data={"success": False, "status_code": 200,
                #                           "message": "This device don't belong to case account"})

                if new_device.status == "Available":
                    new_device.status = 'Assigned'
                    new_device.save()

                    case_device = CaseDevice.objects.get(case=case, is_active=True)
                    case_device.is_active = False
                    case_device.save()

                    device_data = {"case": case.id, "device": new_device.id, "is_active": True}
                    case_device_serializer = CaseDeviceSerializer(data=device_data,
                                                                  context=self.get_serializer_context())
                    if case_device_serializer.is_valid(raise_exception=True):
                        case_serializer_data = case_device_serializer.validated_data
                        case_device_serializer.save()

                    if data["new_settings"] is not None and bool(data["new_settings"]):
                        del data["new_settings"]["created_by_id"]
                        del data["new_settings"]["slug"]
                        data["new_settings"]["device"] = new_device.id
                        if DeviceSettings.objects.filter(device__id=data["new_settings"]["device"]).exists:
                            device_settings = DeviceSettings.objects.get(device__id=data["new_settings"]["device"])
                            settings_serializer = DeviceSettingsSerializer(device_settings, data=data["new_settings"],
                                                                           context=self.get_serializer_context())
                        else:
                            settings_serializer = DeviceSettingsSerializer(data=data["new_settings"],
                                                                           context=self.get_serializer_context())

                        if settings_serializer.is_valid(raise_exception=True):
                            settings_serializer_data = settings_serializer.validated_data
                            settings_serializer.save()

                    return Response(status=status.HTTP_200_OK,
                                    data={"success": True, "status_code": 200,
                                          "message": "Device changed successfully"})

                else:
                    return Response(status=status.HTTP_200_OK,
                                    data={"success": False, "status_code": 200,
                                          "message": "Device status should be Available"})

        except Exception as e:
            return Response({"status": "failed", "message": e}
                            , status=status.HTTP_400_BAD_REQUEST)

    @action(["post"], detail=False)
    def archive(self, request, *args, **kwargs):
        try:
            data = request.data
            for slug in data["cases"]:
                case = Case.objects.get(slug=slug)
                if case.is_active is False:
                    case.is_archived = True
                    case.save()

                    generate_case_user_notification.delay(
                        action='Case Archived', to_user_id=case.account.account_admin_id, from_user_id=request.user.id,
                        case_number=case.case_no, from_user_name=request.user.first_name + " " + request.user.last_name
                    )

            return Response({"status": "success", "message": "Cases are archived successfully"}
                            , status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"status": "failed", "message": e}
                            , status=status.HTTP_400_BAD_REQUEST)

    @action(["patch"], detail=True)
    def edit(self, request, *args, **kwargs):
        try:
            self.check_object_permissions(request, self.get_object())
            data = request.data
            case = Case.objects.get(slug=kwargs["slug"])
            if data["is_active"] is True or data["is_active"] == "true":
                case.is_active = True

                context_data = {'link_name': case.case_no, 'case_slug': case.slug}

                generate_case_notification.delay(
                    action='Case Opened', from_user_id=request.user.id, case_slug=case.slug,
                    case_number=case.case_no, case_manager=request.user.name,
                    case_manager_phone_number=request.user.phone1,
                    link=case.slug, context_data=context_data
                )

            elif data["is_active"] is False or data["is_active"] == "false":
                case.is_active = False
                case.is_closed = True

                generate_case_notification.delay(
                    action='Case Closed', from_user_id=request.user.id, case_slug=case.slug,
                    case_number=case.case_no, case_manager=request.user.name,
                    case_manager_phone_number=request.user.phone1
                )

            case.updated_on = datetime.now()
            case.save()

            return Response(status=status.HTTP_200_OK,
                            data={"success": True,
                                  "message": "Case is updated successfully",
                                  "data": CaseSerializer(case, many=False).data})

        except Exception as e:
            return Response({"status": "failed", "message": e}
                            , status=status.HTTP_400_BAD_REQUEST)

    @action(["patch"], detail=True)
    def close(self, request, *args, **kwargs):
        self.check_object_permissions(request, self.get_object())
        data = request.data
        case = Case.objects.get(slug=kwargs["slug"])
        case.is_active = False
        case.is_closed = True
        case.save()
        device = CaseDevice.objects.get(case=case, is_active=True).device
        device.status = "In Checkout"
        device.save()

        generate_case_notification.delay(
            action='Case Closed', from_user_id=request.user.id, case_slug=case.slug,
            case_number=case.case_no, case_manager=request.user.name,
            case_manager_phone_number=request.user.phone1
        )

        return super().partial_update(request, args, kwargs)

    @action(["get"], detail=True)
    def status(self, request, *args, **kwargs):
        self.check_object_permissions(request, self.get_object())
        case = Case.objects.get(slug=kwargs["slug"])

        return Response(status=status.HTTP_200_OK,
                        data={"success": True,
                              "data": CaseStatusSerializer(case, many=False).data})

    @action(["get"], detail=False)
    def case_list_to_archive(self, request, *args, **kwargs):
        date = request.query_params.get('date')
        date_time_obj = datetime.strptime(date, '%d-%m-%Y')
        cases = self.filter_queryset(
            Case.objects.filter(is_active=False, updated_on__lt=date_time_obj, is_archived=False))

        return Response(status=status.HTTP_200_OK,
                        data={"success": True,
                              "data": CaseListSerializer(cases, many=True).data})

    @action(["post"], detail=False)
    def unarchive(self, request, *args, **kwargs):
        try:
            data = request.data
            # to_account_admin = User.objects.get(id=self.request.user.account_admin_id)
            for slug in data["cases"]:
                case = Case.objects.get(slug=slug)
                case.is_archived = False
                case.save()
                # generate_user_notification(
                #     action="case_unarchived", to_user=to_account_admin, from_user=request.user,
                #     from_user_name=request.user.first_name + " " + request.user.last_name,
                #     case_number=case.case_no)

            return Response({"status": "success", "message": "Cases are unarchived successfully"}
                            , status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"status": "failed", "message": e}
                            , status=status.HTTP_400_BAD_REQUEST)

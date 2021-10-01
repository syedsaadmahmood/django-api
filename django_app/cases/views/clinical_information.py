from rest_framework import status
from rest_framework.response import Response

from django_synergy.cases.models import Prescription, PrescriptionUpload, PatientDiagnosis, Patient, Vitals, \
    Case, History
from django_synergy.cases.permissions import CanViewClinicalInformation, CanEditClinicalInformation
from django_synergy.cases.serializers import VitalsSerializer, HistorySerializer
from django_synergy.cases.serializers.clinical_information import PrescriptionSerializer, \
    PrescriptionUploadWritableSerializer, PrescriptionUploadSerializer, PrescriptionWritableSerializer, \
    VitalsWritableSerializer, HistoryWritableSerializer, PatientDiagnosisReadOnlySerializer, \
    PatientDiagnosisWritableSerializer, VitalsReadOnlySerializer, PatientDiagnosisWritableCreateSerializer, \
    PrescriptionReadOnlySerializer
from django_synergy.cases.utils import fetchChildAccounts, fetchCasesAssigned, fetchCasesAssignedToUser
from django_synergy.utils.views import BaseViewset
from rest_framework.permissions import IsAuthenticated
from django_synergy.cases.permissions import user_has_permission, get_user_permission_list


class PrescriptionViewSet(BaseViewset):
    queryset = Prescription.objects.all()
    lookup_field = 'slug'
    action_serializers = {
        'default': PrescriptionSerializer,
        'update': PrescriptionWritableSerializer,
        'partial_update': PrescriptionWritableSerializer,
        'create': PrescriptionWritableSerializer
    }

    def get_queryset(self):
        if hasattr(self.request.user, 'is_superuser'):
            if self.request.user.is_superuser:
                return Prescription.objects.all()
        if hasattr(self.request.user, 'account'):
            if self.request.user.account:
                permission_list = get_user_permission_list(self.request.user)
                account_instance = Prescription.objects.none()
                if user_has_permission('case-clinical-information-account', user_permissions=permission_list):
                    account_instance = Prescription.objects.filter(
                        patient__case_patient__account__id=self.request.user.account.id)

                subsidiary_account_instance = Prescription.objects.none()
                if user_has_permission('case-clinical-information-subsidiary', user_permissions=permission_list):
                    account_slugs_list = []
                    fetchChildAccounts(account_slugs_list, self.request.user.account)
                    subsidiary_account_instance = Prescription.objects.filter(
                        patient__case_patient__account__slug__in=account_slugs_list)

                cases_assigned_instance = Prescription.objects.none()
                if user_has_permission('case-clinical-information-assigned', user_permissions=permission_list):
                    cases_assigned_slug_list = []
                    fetchCasesAssigned(cases_assigned_slug_list, self.request.user)
                    cases_assigned_instance = Prescription.objects.filter(
                        patient__case_patient__slug__in=cases_assigned_slug_list)

                case_list_assigned_to_users = Prescription.objects.none()
                if user_has_permission('case-clinical-information-assigned-to-users', user_permissions=permission_list):
                    cases_assigned_slug_list = []
                    fetchCasesAssignedToUser(cases_assigned_slug_list, self.request.user.account)
                    case_list_assigned_to_users = Prescription.objects.filter(
                        patient__case_patient__slug__in=cases_assigned_slug_list)

                return account_instance | subsidiary_account_instance | cases_assigned_instance | case_list_assigned_to_users

        else:
            return Prescription.objects.none()

    def get_permissions(self):
        if self.action == "list":
            self.permission_classes = [CanViewClinicalInformation]
        elif self.action == "retrieve":
            self.permission_classes = [CanViewClinicalInformation]
        elif self.action == "create":
            self.permission_classes = [CanEditClinicalInformation]
        elif self.action == "update":
            self.permission_classes = [CanEditClinicalInformation]
        elif self.action == "partial_update":
            self.permission_classes = [CanEditClinicalInformation]
        elif self.action == "destroy":
            self.permission_classes = [CanEditClinicalInformation]
        else:
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    def retrieve(self, request, *args, **kwargs):
        try:
            all_prescriptions = self.get_queryset().all()
            prescription = all_prescriptions.filter(patient__slug=kwargs['slug'])
            prescription_serializer = PrescriptionReadOnlySerializer(prescription, many=True).data
            return Response(status=status.HTTP_200_OK,
                            data={"success": True, "data": prescription_serializer})
        except Exception as e:
            return Response({"status": "failed", "message": e}
                            , status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        try:
            self.check_object_permissions(request, self.get_object())

            PrescriptionUpload.objects.filter(prescription__slug=kwargs['slug']).delete()
            Prescription.objects.filter(slug=kwargs['slug']).delete()
            return Response({"status": "success", "message": 'prescription deleted successfully'}
                            , status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"status": "failed", "message": e}
                            , status=status.HTTP_400_BAD_REQUEST)


class PrescriptionUploadViewSet(BaseViewset):
    queryset = PrescriptionUpload.objects.all()
    action_serializers = {
        'default': PrescriptionUploadSerializer,
        'create': PrescriptionUploadWritableSerializer,
        'update': PrescriptionUploadWritableSerializer,
    }

    def partial_update(self, request, *args, **kwargs):
        try:
            data = request.data
            prescription_upload = PrescriptionUpload.objects.get(uuid=kwargs['slug'])
            if data['uploaded'] is True or data['uploaded'] == "true":
                prescription_upload.uploaded = True
            elif data['uploaded'] is False or data['uploaded'] == "false":
                prescription_upload.uploaded = False
            prescription_upload.save()
            return Response({"status": "success", "message": 'prescription upload updated'}
                            , status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"status": "failed", "message": e}
                            , status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        try:
            data = request.data
            if not PrescriptionUpload.objects.filter(prescription__slug=kwargs['slug']).exists():
                body = {
                    "filename": data["filename"],
                    "url_expiry": "60000",
                    "prescription": kwargs['slug']
                }
                prescription_upload_serializer = PrescriptionUploadWritableSerializer(data=body,
                                                                                      context=self.get_serializer_context())

                if prescription_upload_serializer.is_valid(raise_exception=True):
                    prescription_upload_serializer_data = prescription_upload_serializer.validated_data
                    upload = prescription_upload_serializer.save()

                    return Response(status=status.HTTP_200_OK,
                                    data={"success": True,
                                          "data": PrescriptionUploadWritableSerializer(upload,
                                                                                       many=False).data})
            else:
                prescription_upload = PrescriptionUpload.objects.get(prescription__slug=kwargs['slug'])
                prescription_upload.filename = data["filename"]
                prescription_upload.save()
                return Response(status=status.HTTP_200_OK,
                                data={"success": True,
                                      "data": PrescriptionUploadWritableSerializer(prescription_upload, many=False).data})

        except Exception as e:
            return Response({"status": "failed", "message": e}
                            , status=status.HTTP_400_BAD_REQUEST)


class DiagnosisViewSet(BaseViewset):
    queryset = PatientDiagnosis.objects.all()
    lookup_field = 'slug'
    action_serializers = {
        'default': PatientDiagnosisReadOnlySerializer,
        'update': PatientDiagnosisWritableSerializer,
        'partial_update': PatientDiagnosisWritableSerializer,
        'create': PatientDiagnosisWritableCreateSerializer
    }

    def get_queryset(self):
        if hasattr(self.request.user, 'is_superuser'):
            if self.request.user.is_superuser:
                return PatientDiagnosis.objects.all()
        if hasattr(self.request.user, 'account'):
            if self.request.user.account:
                permission_list = get_user_permission_list(self.request.user)
                account_instance = PatientDiagnosis.objects.none()
                if user_has_permission('case-clinical-information-account', user_permissions=permission_list):
                    account_instance = PatientDiagnosis.objects.filter(
                        patient__case_patient__account__id=self.request.user.account.id)

                subsidiary_account_instance = PatientDiagnosis.objects.none()
                if user_has_permission('case-clinical-information-subsidiary', user_permissions=permission_list):
                    account_slugs_list = []
                    fetchChildAccounts(account_slugs_list, self.request.user.account)
                    subsidiary_account_instance = PatientDiagnosis.objects.filter(
                        patient__case_patient__account__slug__in=account_slugs_list)

                cases_assigned_instance = PatientDiagnosis.objects.none()
                if user_has_permission('case-clinical-information-assigned', user_permissions=permission_list):
                    cases_assigned_slug_list = []
                    fetchCasesAssigned(cases_assigned_slug_list, self.request.user)
                    cases_assigned_instance = PatientDiagnosis.objects.filter(
                        patient__case_patient__slug__in=cases_assigned_slug_list)

                case_list_assigned_to_users = PatientDiagnosis.objects.none()
                if user_has_permission('case-clinical-information-assigned-to-users', user_permissions=permission_list):
                    cases_assigned_slug_list = []
                    fetchCasesAssignedToUser(cases_assigned_slug_list, self.request.user.account)
                    case_list_assigned_to_users = PatientDiagnosis.objects.filter(
                        patient__case_patient__slug__in=cases_assigned_slug_list)

                return account_instance | subsidiary_account_instance | cases_assigned_instance | case_list_assigned_to_users

        else:
            return PatientDiagnosis.objects.none()

    def get_permissions(self):
        if self.action == "list":
            self.permission_classes = [CanViewClinicalInformation]
        elif self.action == "retrieve":
            self.permission_classes = [CanViewClinicalInformation]
        elif self.action == "create":
            self.permission_classes = [CanEditClinicalInformation]
        elif self.action == "update":
            self.permission_classes = [CanEditClinicalInformation]
        elif self.action == "partial_update":
            self.permission_classes = [CanEditClinicalInformation]
        elif self.action == "destroy":
            self.permission_classes = [CanEditClinicalInformation]
        else:
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    def retrieve(self, request, *args, **kwargs):
        try:
            all_diagnosis = self.get_queryset().all()
            patient_diagnosis = all_diagnosis.filter(patient__slug=kwargs['slug'])
            diagnosis_serializer = PatientDiagnosisReadOnlySerializer(patient_diagnosis, many=True).data
            return Response(status=status.HTTP_200_OK,
                            data={"success": True, "data": diagnosis_serializer})
        except Exception as e:
            return Response({"status": "failed", "message": e}
                            , status=status.HTTP_400_BAD_REQUEST)


class VitalsViewSet(BaseViewset):
    queryset = Vitals.objects.all()
    lookup_field = 'slug'
    action_serializers = {
        'default': VitalsSerializer,
        'list': VitalsReadOnlySerializer,
    }

    def get_queryset(self):
        if hasattr(self.request.user, 'is_superuser'):
            if self.request.user.is_superuser:
                return Vitals.objects.all()
        if hasattr(self.request.user, 'account'):
            if self.request.user.account:
                permission_list = get_user_permission_list(self.request.user)
                account_instance = Vitals.objects.none()
                if user_has_permission('case-clinical-information-account', user_permissions=permission_list):
                    account_instance = Vitals.objects.filter(
                        case__account__id=self.request.user.account.id)

                subsidiary_account_instance = Vitals.objects.none()
                if user_has_permission('case-clinical-information-subsidiary', user_permissions=permission_list):
                    account_slugs_list = []
                    fetchChildAccounts(account_slugs_list, self.request.user.account)
                    subsidiary_account_instance = Vitals.objects.filter(
                        case__account__slug__in=account_slugs_list)

                cases_assigned_instance = Vitals.objects.none()
                if user_has_permission('case-clinical-information-assigned', user_permissions=permission_list):
                    cases_assigned_slug_list = []
                    fetchCasesAssigned(cases_assigned_slug_list, self.request.user)
                    cases_assigned_instance = Vitals.objects.filter(
                        case__slug__in=cases_assigned_slug_list)

                case_list_assigned_to_users = Vitals.objects.none()
                if user_has_permission('case-clinical-information-assigned-to-users', user_permissions=permission_list):
                    cases_assigned_slug_list = []
                    fetchCasesAssignedToUser(cases_assigned_slug_list, self.request.user.account)
                    case_list_assigned_to_users = Vitals.objects.filter(
                        case__slug__in=cases_assigned_slug_list)

                return account_instance | subsidiary_account_instance | cases_assigned_instance | case_list_assigned_to_users

        else:
            return Vitals.objects.none()

    def get_permissions(self):
        if self.action == "list":
            self.permission_classes = [CanViewClinicalInformation]
        elif self.action == "retrieve":
            self.permission_classes = [CanViewClinicalInformation]
        elif self.action == "create":
            self.permission_classes = [CanEditClinicalInformation]
        elif self.action == "update":
            self.permission_classes = [CanEditClinicalInformation]
        elif self.action == "partial_update":
            self.permission_classes = [CanEditClinicalInformation]
        elif self.action == "destroy":
            self.permission_classes = [CanEditClinicalInformation]
        else:
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    def update(self, request, *args, **kwargs):
        try:
            self.check_object_permissions(request, self.get_object())
            data = request.data
            vitals = Vitals.objects.get(slug=kwargs['slug'])
            data["case"] = vitals.case.id
            vitals_serializer = VitalsWritableSerializer(vitals, data=data,
                                                         context=self.get_serializer_context())

            if vitals_serializer.is_valid(raise_exception=True):
                vitals_serializer_data = vitals_serializer.validated_data
                vitals_serializer.save()
                return Response(status=status.HTTP_200_OK,
                                data={"success": True,
                                      "data": VitalsSerializer(vitals_serializer_data,
                                                               many=False).data})

        except Exception as e:
            return Response({"status": "failed", "message": e}
                            , status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        try:
            all_vitals = self.get_queryset().all()
            case_vitals = all_vitals.filter(case__patient__slug=kwargs['slug'])

            if len(case_vitals) > 0:
                case_vitals = case_vitals[0]
            else:
                case_vitals = Vitals.objects.none()
            return Response(status=status.HTTP_200_OK,
                            data={"success": True,
                                  "data": VitalsReadOnlySerializer(case_vitals,
                                                                   many=False).data})

        except Exception as e:
            return Response({"status": "failed", "message": e}
                            , status=status.HTTP_400_BAD_REQUEST)


class HistoryViewSet(BaseViewset):
    queryset = History.objects.all()
    lookup_field = 'slug'
    action_serializers = {
        'default': HistorySerializer,
        'update': HistoryWritableSerializer,
        'partial_update': HistoryWritableSerializer,
        'create': HistoryWritableSerializer
    }

    def get_queryset(self):
        if hasattr(self.request.user, 'is_superuser'):
            if self.request.user.is_superuser:
                return History.objects.all()
        if hasattr(self.request.user, 'account'):
            if self.request.user.account:
                permission_list = get_user_permission_list(self.request.user)
                account_instance = History.objects.none()
                if user_has_permission('case-clinical-information-account', user_permissions=permission_list):
                    account_instance = History.objects.filter(
                        patient__case_patient__account__id=self.request.user.account.id)

                subsidiary_account_instance = History.objects.none()
                if user_has_permission('case-clinical-information-subsidiary', user_permissions=permission_list):
                    account_slugs_list = []
                    fetchChildAccounts(account_slugs_list, self.request.user.account)
                    subsidiary_account_instance = History.objects.filter(
                        patient__case_patient__account__slug__in=account_slugs_list)

                cases_assigned_instance = History.objects.none()
                if user_has_permission('case-clinical-information-assigned', user_permissions=permission_list):
                    cases_assigned_slug_list = []
                    fetchCasesAssigned(cases_assigned_slug_list, self.request.user)
                    cases_assigned_instance = History.objects.filter(
                        patient__case_patient__slug__in=cases_assigned_slug_list)

                case_list_assigned_to_users = History.objects.none()
                if user_has_permission('case-clinical-information-assigned-to-users', user_permissions=permission_list):
                    cases_assigned_slug_list = []
                    fetchCasesAssignedToUser(cases_assigned_slug_list, self.request.user.account)
                    case_list_assigned_to_users = History.objects.filter(
                        patient__case_patient__slug__in=cases_assigned_slug_list)

                return account_instance | subsidiary_account_instance | cases_assigned_instance | case_list_assigned_to_users

        else:
            return History.objects.none()

    def get_permissions(self):
        if self.action == "list":
            self.permission_classes = [CanViewClinicalInformation]
        elif self.action == "retrieve":
            self.permission_classes = [CanViewClinicalInformation]
        elif self.action == "create":
            self.permission_classes = [CanEditClinicalInformation]
        elif self.action == "update":
            self.permission_classes = [CanEditClinicalInformation]
        elif self.action == "partial_update":
            self.permission_classes = [CanEditClinicalInformation]
        elif self.action == "destroy":
            self.permission_classes = [CanEditClinicalInformation]
        else:
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    def retrieve(self, request, *args, **kwargs):
        try:
            all_history = self.get_queryset().all()
            history = all_history.filter(patient__slug=kwargs['slug'])
            history_serializer = HistorySerializer(history, many=True).data
            return Response(status=status.HTTP_200_OK,
                            data={"success": True, "data": history_serializer})

        except Exception as e:
            return Response({"status": "failed", "message": e}
                            , status=status.HTTP_400_BAD_REQUEST)

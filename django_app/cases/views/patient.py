from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from datetime import datetime

from django_synergy.cases.models import Patient, PatientEthnicity, PatientRace
from django_synergy.cases.serializers import PatientDetailSerializer, PatientWritableSerializer, \
    PatientEthnicityWritableSerializer, PatientRaceWritableSerializer
from django_synergy.cases.utils import fetchChildAccounts, fetchCasesAssigned, fetchCasesAssignedToUser
from django_synergy.utils.views import BaseViewset
from django_synergy.cases.permissions import user_has_permission, get_user_permission_list, CanViewPatient, \
    CanEditPatient


class PatientViewSet(BaseViewset):
    queryset = Patient.objects.all()
    lookup_field = 'slug'
    action_serializers = {
        'default': PatientDetailSerializer,
    }

    def get_queryset(self):
        if hasattr(self.request.user, 'is_superuser'):
            if self.request.user.is_superuser:
                return Patient.objects.all()
        if hasattr(self.request.user, 'account'):
            if self.request.user.account:
                permission_list = get_user_permission_list(self.request.user)
                account_instance = Patient.objects.none()
                if user_has_permission('case-patient-account', user_permissions=permission_list):
                    account_instance = Patient.objects.filter(
                        case_patient__account__id=self.request.user.account.id)

                subsidiary_account_instance = Patient.objects.none()
                if user_has_permission('case-patient-subsidiary', user_permissions=permission_list):
                    account_slugs_list = []
                    fetchChildAccounts(account_slugs_list, self.request.user.account)
                    subsidiary_account_instance = Patient.objects.filter(
                        case_patient__account__slug__in=account_slugs_list)

                cases_assigned_instance = Patient.objects.none()
                if user_has_permission('case-patient-assigned', user_permissions=permission_list):
                    cases_assigned_slug_list = []
                    fetchCasesAssigned(cases_assigned_slug_list, self.request.user)
                    cases_assigned_instance = Patient.objects.filter(
                        case_patient__slug__in=cases_assigned_slug_list)

                case_list_assigned_to_users = Patient.objects.none()
                if user_has_permission('case-patient-assigned-to-users', user_permissions=permission_list):
                    cases_assigned_slug_list = []
                    fetchCasesAssignedToUser(cases_assigned_slug_list, self.request.user.account)
                    case_list_assigned_to_users = Patient.objects.filter(
                        case_patient__slug__in=cases_assigned_slug_list)

                return account_instance | subsidiary_account_instance | cases_assigned_instance | case_list_assigned_to_users

        else:
            return Patient.objects.none()

    def get_permissions(self):
        if self.action == "list":
            self.permission_classes = [CanViewPatient]
        elif self.action == "retrieve":
            self.permission_classes = [CanViewPatient]
        elif self.action == "create":
            self.permission_classes = [CanEditPatient]
        elif self.action == "update":
            self.permission_classes = [CanEditPatient]
        elif self.action == "partial_update":
            self.permission_classes = [CanEditPatient]
        else:
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    def partial_update(self, request, *args, **kwargs):
        try:
            self.check_object_permissions(request, self.get_object())
            data = request.data
            patient = Patient.objects.get(slug=kwargs['slug'])
            if "date_of_birth" in data:
                date_of_birth = datetime.strptime(data["date_of_birth"], "%d-%m-%Y").date()
                data["date_of_birth"] = str(date_of_birth)

            if "address1" not in data:
                data["address1"] = patient.address1

            if "zipcode" not in data:
                data["zipcode"] = patient.zipcode

            if "ethnicity" in data:
                PatientEthnicity.objects.filter(patient__slug=kwargs["slug"]).delete()
                for index, ethnicity_obj in enumerate(data["ethnicity"]):
                    patient_ethnicity = {
                        'patient': patient.id,
                        'ethnicity': ethnicity_obj
                    }
                    patient_ethnicity_serializer = PatientEthnicityWritableSerializer(data=patient_ethnicity,
                                                                                      context=self.get_serializer_context())
                    if patient_ethnicity_serializer.is_valid(raise_exception=True):
                        patient_ethnicity_serializer_data = patient_ethnicity_serializer.validated_data
                        patient_ethnicity_serializer.save()

            if "race" in data:
                PatientRace.objects.filter(patient__slug=kwargs["slug"]).delete()
                for index, race_obj in enumerate(data["race"]):
                    patient_race = {
                        'patient': patient.id,
                        'race': race_obj
                    }
                    patient_race_serializer = PatientRaceWritableSerializer(data=patient_race,
                                                                            context=self.get_serializer_context())
                    if patient_race_serializer.is_valid(raise_exception=True):
                        patient_race_serializer_data = patient_race_serializer.validated_data
                        patient_race_serializer.save()

            patient_serializer = PatientWritableSerializer(patient, data=data,
                                                           context=self.get_serializer_context())
            if patient_serializer.is_valid(raise_exception=True):
                patient_serializer_data = patient_serializer.validated_data
                patient_serializer.save()

                return Response(status=status.HTTP_200_OK,
                                data={"success": True,
                                      "data": {}})

        except Exception as e:
            return Response({"status": "failed", "message": e}
                            , status=status.HTTP_400_BAD_REQUEST)

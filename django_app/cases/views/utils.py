import json

from django.contrib.auth.models import Group
from django.contrib.sites.models import Site
from rest_framework.exceptions import ValidationError
from django.conf import settings
from websocket import create_connection
from config import celery_app
from django_synergy.accounts.serializers import AssociatedContactsWritableSerializer
from django_synergy.cases.models import CaseDefaultRole, User, NotificationType, \
    DefaultNotificationMatrix, Diagnosis, CaseRole
from django_synergy.cases.serializers.clinical_information import PrescriptionWritableSerializer, \
    HistoryWritableSerializer, \
    PatientDiagnosisSerializer, VitalsWritableSerializer
from django_synergy.cases.serializers import PatientWritableSerializer, ParentWritableSerializer, \
    PatientEthnicityWritableSerializer, PatientRaceWritableSerializer
from django_synergy.cases.serializers.notification_matrix import CaseNotificationMatrixWritableSerializer
from django_synergy.cases.serializers.roles import CaseRoleWritableSerializer
from django_synergy.notifications.serializers import NotificationSerializer
from django_synergy.notifications.utils import save_notification_db
from django_synergy.users.serializers import UserCreateSerializer


def create_patient(data, self):
    patient_serializer = PatientWritableSerializer(data=data["patient"],
                                                   context=self.get_serializer_context())
    if patient_serializer.is_valid(raise_exception=True):
        patient_serializer_data = patient_serializer.validated_data
        patient = patient_serializer.save()
        return patient


def create_parent(data, self):
    parent = None
    parent_user = None
    if "parent" in data:
        if data["create_system_contact"] is True or data["create_system_contact"] == "true":
            data['parent']["groups"] = ['Contact']
            user_serializer = UserCreateSerializer(data=data['parent'],
                                                   context=self.get_serializer_context())
            if user_serializer.is_valid(raise_exception=True):
                user_serializer_data = user_serializer.validated_data
                parent_user = user_serializer.save()

                # Associated contact
                contact_body = {
                    "from_user": parent_user.slug,
                    "to_account": data['account'],
                    "accepted": True
                }
                associated_contact = AssociatedContactsWritableSerializer(data=contact_body,
                                                                          context=self.get_serializer_context())
                if associated_contact.is_valid(raise_exception=True):
                    associated_contact_data = associated_contact.validated_data
                    associated_contact.save()
        else:
            parent_serializer = ParentWritableSerializer(data=data["parent"],
                                                         context=self.get_serializer_context())
            if parent_serializer.is_valid(raise_exception=True):
                parent_serializer_data = parent_serializer.validated_data
                parent = parent_serializer.save()
                if parent.first_name is not None and parent.last_name is None:
                    parent.name = parent.first_name
                elif parent.first_name is None and parent.last_name is not None:
                    parent.name = parent.last_name
                elif parent.first_name is not None and parent.last_name is not None:
                    parent.name = parent.first_name + ' ' + parent.last_name
                parent.save()

    return parent, parent_user


def create_patient_ethnicity(data, self, patient):
    if "ethnicity" in data["patient"] and data["patient"]["ethnicity"]:
        for index, ethnicity_obj in enumerate(data["patient"]["ethnicity"]):
            patient_ethnicity = {
                'patient': patient.id,
                'ethnicity': ethnicity_obj
            }
            patient_ethnicity_serializer = PatientEthnicityWritableSerializer(data=patient_ethnicity,
                                                                              context=self.get_serializer_context())
            if patient_ethnicity_serializer.is_valid(raise_exception=True):
                patient_ethnicity_serializer_data = patient_ethnicity_serializer.validated_data
                patient_ethnicity_serializer.save()


def create_patient_race(data, self, patient):
    if "race" in data["patient"] and data["patient"]["race"]:
        for index, race_obj in enumerate(data["patient"]["race"]):
            patient_race = {
                'patient': patient.id,
                'race': race_obj
            }
            patient_race_serializer = PatientRaceWritableSerializer(data=patient_race,
                                                                    context=self.get_serializer_context())
            if patient_race_serializer.is_valid(raise_exception=True):
                patient_race_serializer_data = patient_race_serializer.validated_data
                patient_race_serializer.save()


def create_prescription(data, self, patient):
    if "prescription" in data:
        for index, prescriptions in enumerate(data["prescription"]):
            data["prescription"][index]["patient"] = patient.slug
            prescription_serializer = PrescriptionWritableSerializer(data=prescriptions,
                                                                     context=self.get_serializer_context())

            if prescription_serializer.is_valid(raise_exception=True):
                prescription_serializer_data = prescription_serializer.validated_data
                prescription_serializer.save()


def create_history(data, self, patient):
    if "history" in data:
        for index, histories in enumerate(data["history"]):
            data["history"][index]["patient"] = patient.slug
            history_serializer = HistoryWritableSerializer(data=histories,
                                                           context=self.get_serializer_context())

            if history_serializer.is_valid(raise_exception=True):
                history_serializer_data = history_serializer.validated_data
                history_serializer.save()


def create_patient_diagnosis(data, self, patient):
    if "diagnosis" in data:
        for index, diagnoses in enumerate(data["diagnosis"]):
            diagnosis = Diagnosis.objects.get(slug=data["diagnosis"][index]['code'])
            patient_diagnoses = {
                'patient': patient.id,
                'diagnosis': diagnosis.id
            }

            patient_diagnosis_serializer = PatientDiagnosisSerializer(data=patient_diagnoses,
                                                                      context=self.get_serializer_context())

            if patient_diagnosis_serializer.is_valid(raise_exception=True):
                patient_diagnosis_serializer_data = patient_diagnosis_serializer.validated_data
                patient_diagnosis_serializer.save()


def create_vitals(data, self, case):
    data["vitals"]["case"] = case.id
    vitals_serializer = VitalsWritableSerializer(data=data["vitals"],
                                                 context=self.get_serializer_context())

    if vitals_serializer.is_valid(raise_exception=True):
        vitals_serializer_data = vitals_serializer.validated_data
        vitals_serializer.save()


def create_notification_matrix(data, self, case):
    case_notification_matrices = []
    default_notification_matrix = DefaultNotificationMatrix.objects.all()
    for default_notification in default_notification_matrix:
        case_default_role = CaseDefaultRole.objects.get(id=default_notification.case_default_role.id)
        notification_type = NotificationType.objects.get(id=default_notification.notification_type.id)
        matrix_data = {
            "case_default_role": case_default_role.slug,
            "notification_type": notification_type.slug,
            "case": case.slug,
            "is_notified": default_notification.is_notified
        }
        if "notification_matrix" in data:
            for matrix in data['notification_matrix']:
                if case_default_role.slug == matrix['role'] and notification_type.slug == matrix['notification_type']:
                    if matrix["is_notified"] is True or matrix["is_notified"] == "true":
                        matrix_data["is_notified"] = True
                        break
                    else:
                        matrix_data["is_notified"] = False
                        break

        case_notification_matrices.append(matrix_data)
        case_notification_serializer = CaseNotificationMatrixWritableSerializer(data=matrix_data,
                                                                                context=self.get_serializer_context())

        if case_notification_serializer.is_valid(raise_exception=True):
            case_notification_serializer_data = case_notification_serializer.validated_data
            case_notification_serializer.save()

    return case_notification_matrices


def create_roles(data, self, case):
    if "roles" in data:
        role_users = []
        if "Case Manager" in data["roles"] and data["roles"]["Case Manager"]:
            default_role = CaseDefaultRole.objects.get(name='Case Manager')
            for user_slug in data["roles"]["Case Manager"]:
                user = User.objects.get(slug=user_slug)
                user_groups = user.groups.all()
                if not hasattr(user, 'account'):
                    raise ValidationError("account is required")
                elif not user.account:
                    raise ValidationError("account is required")
                elif user.account != case.account:
                    raise ValidationError("User's and case account must be same")
                if user.user_type == "User" and "Biomedical User" not in user_groups:
                    save_roles(self, case, default_role, user)
                    role_users.append({
                        "default_role": default_role,
                        "user": user
                    })

        if "Scorer" in data["roles"] and data["roles"]["Scorer"]:
            default_role = CaseDefaultRole.objects.get(name='Scorer')
            for user_slug in data["roles"]["Scorer"]:
                user = User.objects.get(slug=user_slug)
                user_groups = user.groups.all()
                if user.user_type == "User" and "Biomedical User" not in user_groups:
                    save_roles(self, case, default_role, user)
                    role_users.append({
                        "default_role": default_role,
                        "user": user
                    })

        if "Interpreting Physician" in data["roles"] and data["roles"]["Interpreting Physician"]:
            default_role = CaseDefaultRole.objects.get(name='Interpreting Physician')
            for user_slug in data["roles"]["Interpreting Physician"]:
                user = User.objects.get(slug=user_slug)
                user_groups = user.groups.all()
                if user.user_type == "User" and "Biomedical User" not in user_groups:
                    save_roles(self, case, default_role, user)
                    role_users.append({
                        "default_role": default_role,
                        "user": user
                    })

        if "Referring Physician" in data["roles"] and data["roles"]["Referring Physician"]:
            default_role = CaseDefaultRole.objects.get(name='Referring Physician')
            for user_slug in data["roles"]["Referring Physician"]:
                user = User.objects.get(slug=user_slug)
                user_groups = user.groups.all()
                if "Biomedical User" not in user_groups:
                    save_roles(self, case, default_role, user)
                    role_users.append({
                        "default_role": default_role,
                        "user": user
                    })

        if "Specialist" in data["roles"] and data["roles"]["Specialist"]:
            default_role = CaseDefaultRole.objects.get(name='Specialist')
            for user_slug in data["roles"]["Specialist"]:
                user = User.objects.get(slug=user_slug)
                user_groups = user.groups.all()
                if "Biomedical User" not in user_groups:
                    save_roles(self, case, default_role, user)
                    role_users.append({
                        "default_role": default_role,
                        "user": user
                    })

        if "Pediatrician / Family Doctor" in data["roles"] and data["roles"]["Pediatrician / Family Doctor"]:
            default_role = CaseDefaultRole.objects.get(name='Pediatrician / Family Doctor')
            for user_slug in data["roles"]["Pediatrician / Family Doctor"]:
                user = User.objects.get(slug=user_slug)
                user_groups = user.groups.all()
                if "Biomedical User" not in user_groups:
                    save_roles(self, case, default_role, user)
                    role_users.append({
                        "default_role": default_role,
                        "user": user
                    })

        if data["create_system_contact"] is True or data["create_system_contact"] == "true":
            if case.parent_user is not None:
                default_role = CaseDefaultRole.objects.get(name='Parent')
                save_roles(self, case, default_role, case.parent_user)
                role_users.append({
                    "default_role": default_role,
                    "user": case.parent_user
                })
        else:
            if "Parent" in data["roles"] and data["roles"]["Parent"] and len(data["roles"]["Parent"]) > 0:
                default_role = CaseDefaultRole.objects.get(name='Parent')
                if type(data["roles"]["Parent"]) == str:
                    user = User.objects.get(slug=data["roles"]["Parent"])
                else:
                    user = User.objects.get(slug=data["roles"]["Parent"][0])
                groups = []
                parent_group = Group.objects.get(name='Parent')
                user_groups = user.groups.all()
                if user.user_type == "Contact" and "Biomedical User" not in user_groups:
                    groups.append(parent_group)
                    for user_group in user_groups:
                        groups.append(Group.objects.get(name=user_group.name))
                    user.groups.set(groups)
                    user.save()
                    save_roles(self, case, default_role, user)

                    # Assign parent to case
                    case.parent_user = user
                    case.save()

                    role_users.append({
                        "default_role": default_role,
                        "user": user
                    })

        return role_users


def save_roles(self, case, default_role, user):
    role_data = {
        "case": case.slug,
        "case_default_role": default_role.slug,
        "user": user.slug
    }
    roles_serializer = CaseRoleWritableSerializer(data=role_data,
                                                  context=self.get_serializer_context())

    if roles_serializer.is_valid(raise_exception=True):
        roles_serializer_data = roles_serializer.validated_data
        roles_serializer.save()

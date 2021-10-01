from rest_framework import permissions
from django.contrib.auth.models import Group

from django_synergy.cases.models import CaseRole, Vitals, Parent, Case
from django_synergy.utils.permissions import get_user_permission_list, user_has_permission


class IsSuperUser(permissions.IsAuthenticated):
    message = 'Super User Access permission required'

    def has_permission(self, request, view):
        return request.user.is_superuser


class CanViewCaseList(permissions.IsAuthenticated):
    message = 'This API is only accessible to an super user or user that has permission.'

    def has_permission(self, request, view):
        user = request.user
        if request.user.is_superuser:
            return True

        user_permissions = get_user_permission_list(user)
        if user_has_permission('case-list-account', user_permissions) or \
            user_has_permission('case-list-subsidiary', user_permissions) or \
            user_has_permission('case-list-assigned', user_permissions) or \
            user_has_permission('case-list-assigned-to-users', user_permissions):
            return True
        else:
            return False


class CanViewCaseDetail(permissions.IsAuthenticated):
    message = 'This API is only accessible to an super user or user that has permission.'

    # def has_permission(self, request, view):
    #     user = request.user
    #     if request.user.is_superuser:
    #         return True
    #
    #     user_permissions = get_user_permission_list(user)
    #     if user_has_permission('case-detail-account', user_permissions) or \
    #         user_has_permission('case-detail-subsidiary', user_permissions) or \
    #         user_has_permission('case-detail-assigned', user_permissions) or \
    #         user_has_permission('case-detail-assigned-to-users', user_permissions):
    #         return True
    #     else:
    #         return False

    def has_object_permission(self, request, view, obj):
        user = request.user
        if request.user.is_superuser:
            return True

        user_permissions = get_user_permission_list(user, obj)
        if user_has_permission('case-detail-account', user_permissions) and user.account == obj.account:
            return True
        if user_has_permission('case-detail-subsidiary',
                               user_permissions) and obj.account.parent_account == user.account:
            return True
        if user_has_permission('case-detail-assigned', user_permissions) and \
            CaseRole.objects.filter(user=user, case=obj).exists():
            return True
        if user_has_permission('case-detail-assigned-to-users', user_permissions):
            account_users = set(user.account.users.all())
            case_role_users = set(obj.role_case.all().values_list('user', flat=True))
            users = account_users & case_role_users
            if len(users) > 0:
                return True
        return False


class CanCreateCase(permissions.IsAuthenticated):
    message = 'This API is only accessible to an super user or user that has permission.'

    def has_permission(self, request, view):
        user = request.user

        user_permissions = get_user_permission_list(user)
        if user_has_permission('case-create', user_permissions):
            return True
        else:
            return False


class CanEditCase(permissions.IsAuthenticated):
    message = 'This API is only accessible to an super user or user that has permission.'

    # def has_permission(self, request, view):
    #     user = request.user
    #     if request.user.is_superuser:
    #         return True
    #     import pdb;
    #     pdb.set_trace()
    #     user_permissions = get_user_permission_list(user)
    #     if user_has_permission('case-edit-account', user_permissions) or \
    #         user_has_permission('case-edit-subsidiary', user_permissions) or \
    #         user_has_permission('case-edit-assigned', user_permissions):
    #         return True
    #     else:
    #         return False

    def has_object_permission(self, request, view, obj):
        user = request.user
        if request.user.is_superuser:
            return True

        user_permissions = get_user_permission_list(user, obj)
        if user_has_permission('case-edit-account', user_permissions) and user.account == obj.account:
            return True
        if user_has_permission('case-edit-subsidiary',
                               user_permissions) and obj.account.parent_account == user.account:
            return True
        if user_has_permission('case-edit-assigned', user_permissions) and \
            CaseRole.objects.filter(user=user, case=obj).exists():
            return True
        return False


class CanViewClinicalInformation(permissions.IsAuthenticated):
    message = 'This API is only accessible to an super user or user that has permission.'

    def has_permission(self, request, view):
        user = request.user
        if request.user.is_superuser:
            return True
        user_permissions = get_user_permission_list(user)
        if user_has_permission('case-clinical-information-account', user_permissions) or \
            user_has_permission('case-clinical-information-subsidiary', user_permissions) or \
            user_has_permission('case-clinical-information-assigned-to-users', user_permissions) or \
            user_has_permission('case-clinical-information-assigned', user_permissions):
            return True
        else:
            return False


class CanEditClinicalInformation(permissions.IsAuthenticated):
    message = 'This API is only accessible to an super user or user that has permission.'

    # def has_permission(self, request, view):
    #     user = request.user
    #     if request.user.is_superuser:
    #         return True
    #
    #     user_permissions = get_user_permission_list(user)
    #     if user_has_permission('case-clinical-information-edit-account', user_permissions) or \
    #         user_has_permission('case-clinical-information-edit-subsidiary', user_permissions) or \
    #         user_has_permission('case-clinical-information-edit-assigned', user_permissions):
    #         return True
    #     else:
    #         return False

    def has_object_permission(self, request, view, obj):
        user = request.user
        if request.user.is_superuser:
            return True

        user_permissions = get_user_permission_list(user, obj.patient.case_patient.all().first())
        if type(obj) != Vitals:
            if user_has_permission('case-clinical-information-edit-account',
                                   user_permissions) and user.account == obj.patient.case_patient.all().first().account:
                return True
            if user_has_permission('case-clinical-information-edit-subsidiary',
                                   user_permissions) and obj.patient.case_patient.all().first().account.parent_account == user.account:
                return True
            if user_has_permission('case-clinical-information-edit-assigned', user_permissions) and \
                CaseRole.objects.filter(user=user, case=obj.patient.case_patient.all().first()).exists():
                return True
            return False
        else:
            if user_has_permission('case-clinical-information-edit-account',
                                   user_permissions) and user.account == obj.case.account:
                return True
            if user_has_permission('case-clinical-information-edit-subsidiary',
                                   user_permissions) and obj.case.account.parent_account == user.account:
                return True
            if user_has_permission('case-clinical-information-edit-assigned', user_permissions) and \
                CaseRole.objects.filter(user=user, case=obj.case).exists():
                return True
            return False


class CanViewCaseNotificationMatrix(permissions.IsAuthenticated):
    message = 'This API is only accessible to an super user or user that has permission.'

    def has_permission(self, request, view):
        user = request.user
        if request.user.is_superuser:
            return True

        user_permissions = get_user_permission_list(user)
        if user_has_permission('case-notification-matrix-account', user_permissions) or \
            user_has_permission('case-notification-matrix-subsidiary', user_permissions) or \
            user_has_permission('case-notification-matrix-assigned-to-users', user_permissions) or \
            user_has_permission('case-notification-matrix-assigned', user_permissions):
            return True
        else:
            return False


class CanEditCaseNotificationMatrix(permissions.IsAuthenticated):
    message = 'This API is only accessible to an super user or user that has permission.'

    # def has_permission(self, request, view):
    #     user = request.user
    #     if request.user.is_superuser:
    #         return True
    #
    #     user_permissions = get_user_permission_list(user)
    #     if user_has_permission('case-notification-matrix-edit-account', user_permissions) or \
    #         user_has_permission('case-notification-matrix-edit-subsidiary', user_permissions) or \
    #         user_has_permission('case-notification-matrix-edit-assigned', user_permissions):
    #         return True
    #     else:
    #         return False

    def has_object_permission(self, request, view, obj):
        user = request.user
        if request.user.is_superuser:
            return True

        user_permissions = get_user_permission_list(user, obj.case)
        if user_has_permission('case-notification-matrix-edit-account',
                               user_permissions) and user.account == obj.case.account:
            return True
        if user_has_permission('case-notification-matrix-edit-subsidiary',
                               user_permissions) and obj.case.account.parent_account == user.account:
            return True
        if user_has_permission('case-notification-matrix-edit-assigned', user_permissions) and \
            CaseRole.objects.filter(user=user, case=obj.case).exists():
            return True
        return False


class CanViewParent(permissions.IsAuthenticated):
    message = 'This API is only accessible to an super user or user that has permission.'

    def has_permission(self, request, view):
        user = request.user
        if request.user.is_superuser:
            return True

        user_permissions = get_user_permission_list(user)
        if user_has_permission('case-parent-account', user_permissions) or \
            user_has_permission('case-parent-subsidiary', user_permissions) or \
            user_has_permission('case-parent-assigned-to-users', user_permissions) or \
            user_has_permission('case-parent-assigned', user_permissions):
            return True
        else:
            return False


class CanEditParent(permissions.IsAuthenticated):
    message = 'This API is only accessible to an super user or user that has permission.'

    # def has_permission(self, request, view):
    #     user = request.user
    #     if request.user.is_superuser:
    #         return True
    #
    #     user_permissions = get_user_permission_list(user)
    #     if user_has_permission('case-parent-edit-account', user_permissions) or \
    #         user_has_permission('case-parent-edit-subsidiary', user_permissions) or \
    #         user_has_permission('case-parent-edit-assigned', user_permissions):
    #         return True
    #     else:
    #         return False

    def has_object_permission(self, request, view, obj):
        user = request.user
        if request.user.is_superuser:
            return True

        user_permissions = get_user_permission_list(user, obj.case_parent.all().first())
        if type(obj) == Parent:
            if user_has_permission('case-parent-edit-account',
                                   user_permissions) and user.account == obj.case_parent.all().first().account:
                return True
            if user_has_permission('case-parent-edit-subsidiary',
                                   user_permissions) and obj.case_parent.all().first().account.parent_account == user.account:
                return True
            if user_has_permission('case-parent-edit-assigned', user_permissions) and \
                CaseRole.objects.filter(user=user, case=obj.case_parent.all().first()).exists():
                return True
            return False
        else:
            if user_has_permission('case-parent-edit-account',
                                   user_permissions) and user.account == obj.case_parent_user.all().first().account:
                return True
            if user_has_permission('case-parent-edit-subsidiary',
                                   user_permissions) and obj.case_parent_user.all().first().account.parent_account == user.account:
                return True
            if user_has_permission('case-parent-edit-assigned', user_permissions) and \
                CaseRole.objects.filter(user=user, case=obj.case_parent_user.all().first()).exists():
                return True
            return False


class CanViewPatient(permissions.IsAuthenticated):
    message = 'This API is only accessible to an super user or user that has permission.'

    def has_permission(self, request, view):
        user = request.user
        if request.user.is_superuser:
            return True

        user_permissions = get_user_permission_list(user)
        if user_has_permission('case-patient-account', user_permissions) or \
            user_has_permission('case-patient-subsidiary', user_permissions) or \
            user_has_permission('case-patient-assigned-to-users', user_permissions) or \
            user_has_permission('case-patient-assigned', user_permissions):
            return True
        else:
            return False


class CanEditPatient(permissions.IsAuthenticated):
    message = 'This API is only accessible to an super user or user that has permission.'

    # def has_permission(self, request, view):
    #     user = request.user
    #     if request.user.is_superuser:
    #         return True
    #
    #     user_permissions = get_user_permission_list(user)
    #     if user_has_permission('case-patient-edit-account', user_permissions) or \
    #         user_has_permission('case-patient-edit-subsidiary', user_permissions) or \
    #         user_has_permission('case-patient-edit-assigned', user_permissions):
    #         return True
    #     else:
    #         return False

    def has_object_permission(self, request, view, obj):
        user = request.user
        if request.user.is_superuser:
            return True

        user_permissions = get_user_permission_list(user, obj.case_patient.all().first())
        if user_has_permission('case-patient-edit-account',
                               user_permissions) and user.account == obj.case_patient.all().first().account:
            return True
        if user_has_permission('case-patient-edit-subsidiary',
                               user_permissions) and obj.case_patient.all().first().account.parent_account == user.account:
            return True
        if user_has_permission('case-patient-edit-assigned', user_permissions) and \
            CaseRole.objects.filter(user=user, case=obj.case_patient.all().first()).exists():
            return True
        return False


class CanViewCaseRole(permissions.BasePermission):
    message = 'This API is only accessible to an super user or user that has permission.'

    def has_permission(self, request, view):
        user = request.user
        if request.user.is_superuser:
            return True

        user_permissions = get_user_permission_list(user)
        if user_has_permission('case-role-account', user_permissions) or \
            user_has_permission('case-role-subsidiary', user_permissions) or \
            user_has_permission('case-role-assigned-to-users', user_permissions) or \
            user_has_permission('case-role-assigned', user_permissions):
            return True
        else:
            return False


class CanEditCaseRole(permissions.IsAuthenticated):
    message = 'This API is only accessible to an super user or user that has permission.'

    # def has_permission(self, request, view):
    #     user = request.user
    #     if request.user.is_superuser:
    #         return True
    #
    #     user_permissions = get_user_permission_list(user)
    #     if user_has_permission('case-role-edit-account', user_permissions) or \
    #         user_has_permission('case-role-edit-subsidiary', user_permissions) or \
    #         user_has_permission('case-role-edit-assigned', user_permissions):
    #         return True
    #     else:
    #         return False

    def has_object_permission(self, request, view, obj):
        user = request.user
        if request.user.is_superuser:
            return True

        user_permissions = get_user_permission_list(user, obj.case)

        if user_has_permission('case-role-edit-account',
                               user_permissions) and user.account == obj.case.account:
            return True
        if user_has_permission('case-role-edit-subsidiary',
                               user_permissions) and obj.case.account.parent_account == user.account:
            return True
        if user_has_permission('case-role-edit-assigned', user_permissions) and \
            CaseRole.objects.filter(user=user, case=obj.case).exists():
            return True
        return False


class CanViewNote(permissions.IsAuthenticated):
    message = 'This API is only accessible to an super user or user that has permission.'

    def has_permission(self, request, view):
        user = request.user
        if request.user.is_superuser:
            return True
        user_permissions = get_user_permission_list(user)
        if user_has_permission('case-note-account', user_permissions) or \
            user_has_permission('case-note-subsidiary', user_permissions) or \
            user_has_permission('case-note-assigned-to-users', user_permissions) or \
            user_has_permission('case-note-assigned', user_permissions):
            return True
        else:
            return False


class CanViewDetailNote(permissions.IsAuthenticated):
    message = 'This API is only accessible to an super user or user that has permission.'

    # def has_permission(self, request, view):
    #     user = request.user
    #     if request.user.is_superuser:
    #         return True
    #     user_permissions = get_user_permission_list(user)
    #     if user_has_permission('case-note-detail-account', user_permissions) or \
    #         user_has_permission('case-note-detail-subsidiary', user_permissions) or \
    #         user_has_permission('case-note-detail-assigned-to-users', user_permissions) or \
    #         user_has_permission('case-note-detail-assigned', user_permissions):
    #         return True
    #     else:
    #         return False

    def has_object_permission(self, request, view, obj):
        user = request.user
        if request.user.is_superuser:
            return True

        user_permissions = get_user_permission_list(user, obj.case)

        if user_has_permission('case-note-detail-account', user_permissions) and user.account == obj.case.account:
            return True
        if user_has_permission('case-note-detail-subsidiary',
                               user_permissions) and obj.case.account.parent_account == user.account:
            return True
        if user_has_permission('case-note-detail-assigned', user_permissions) and \
            CaseRole.objects.filter(user=user, case=obj.case).exists():
            return True
        if user_has_permission('case-note-detail-assigned-to-users', user_permissions):
            account_users = set(user.account.users.all())
            case_role_users = set(obj.case.role_case.all().values_list('user', flat=True))
            users = account_users & case_role_users
            if len(users) > 0:
                return True
        return False


class CanEditNote(permissions.IsAuthenticated):
    message = 'This API is only accessible to an super user or user that has permission.'

    # def has_permission(self, request, view):
    #     user = request.user
    #     if request.user.is_superuser:
    #         return True
    #
    #     user_permissions = get_user_permission_list(user)
    #     if user_has_permission('case-note-edit-account', user_permissions) or \
    #         user_has_permission('case-note-edit-subsidiary', user_permissions) or \
    #         user_has_permission('case-note-edit-assigned', user_permissions):
    #         return True
    #     else:
    #         return False

    def has_object_permission(self, request, view, obj):
        user = request.user
        if request.user.is_superuser:
            return True

        user_permissions = get_user_permission_list(user, obj.case)

        if user_has_permission('case-note-edit-account', user_permissions) and user.account == obj.case.account:
            return True
        if user_has_permission('case-note-edit-subsidiary',
                               user_permissions) and obj.case.account.parent_account == user.account:
            return True
        if user_has_permission('case-note-edit-assigned', user_permissions) and \
            CaseRole.objects.filter(user=user, case=obj.case).exists():
            return True
        return False


class CanViewInterpretationList(permissions.IsAuthenticated):
    message = 'This API is only accessible to an super user or user that has permission.'

    def has_permission(self, request, view):
        user = request.user
        if request.user.is_superuser:
            return True
        user_permissions = get_user_permission_list(user)
        if user_has_permission('case-interpretation-account', user_permissions) or \
            user_has_permission('case-interpretation-subsidiary', user_permissions) or \
            user_has_permission('case-interpretation-assigned-to-users', user_permissions) or \
            user_has_permission('case-interpretation-assigned', user_permissions):
            return True
        else:
            return False


class CanViewInterpretationDetail(permissions.IsAuthenticated):
    message = 'This API is only accessible to an super user or user that has permission.'

    # def has_permission(self, request, view):
    #     user = request.user
    #     if request.user.is_superuser:
    #         return True
    #
    #     user_permissions = get_user_permission_list(user)
    #     if user_has_permission('case-interpretation-detail-account', user_permissions) or \
    #         user_has_permission('case-interpretation-detail-subsidiary', user_permissions) or \
    #         user_has_permission('case-interpretation-detail-assigned-to-users', user_permissions) or \
    #         user_has_permission('case-interpretation-detail-assigned', user_permissions):
    #         return True
    #     else:
    #         return False

    def has_object_permission(self, request, view, obj):
        user = request.user
        if request.user.is_superuser:
            return True

        user_permissions = get_user_permission_list(user, obj.case)

        if user_has_permission('case-interpretation-detail-account',
                               user_permissions) and user.account == obj.case.account:
            return True
        if user_has_permission('case-interpretation-detail-subsidiary',
                               user_permissions) and obj.case.account.parent_account == user.account:
            return True
        if user_has_permission('case-interpretation-detail-assigned', user_permissions) and \
            CaseRole.objects.filter(user=user, case=obj.case).exists():
            return True
        if user_has_permission('case-interpretation-detail-assigned-to-users', user_permissions):
            account_users = set(user.account.users.all())
            case_role_users = set(obj.case.role_case.all().values_list('user', flat=True))
            users = account_users & case_role_users
            if len(users) > 0:
                return True
        return False


class CanEditInterpretation(permissions.IsAuthenticated):
    message = 'This API is only accessible to an super user or user that has permission.'

    # def has_permission(self, request, view):
    #     user = request.user
    #     if request.user.is_superuser:
    #         return True
    #
    #     user_permissions = get_user_permission_list(user)
    #     if user_has_permission('case-interpretation-edit-account', user_permissions) or \
    #         user_has_permission('case-interpretation-edit-subsidiary', user_permissions) or \
    #         user_has_permission('case-interpretation-edit-assigned', user_permissions):
    #         return True
    #     else:
    #         return False

    def has_object_permission(self, request, view, obj):
        user = request.user
        if request.user.is_superuser:
            return True

        user_permissions = get_user_permission_list(user, obj.case)

        if user_has_permission('case-interpretation-edit-account',
                               user_permissions) and user.account == obj.case.account:
            return True
        if user_has_permission('case-interpretation-edit-subsidiary',
                               user_permissions) and obj.case.account.parent_account == user.account:
            return True
        if user_has_permission('case-interpretation-edit-assigned', user_permissions) and \
            CaseRole.objects.filter(user=user, case=obj.case).exists():
            return True
        return False


class CanCreateInterpretation(permissions.IsAuthenticated):
    message = 'This API is only accessible to an super user or user that has permission.'

    def has_permission(self, request, view):
        user = request.user
        if request.user.is_superuser:
            return True

        case_slug = request.query_params.get('case', None)
        if case_slug is None:
            case_slug = request.data['case']
        obj = Case.objects.get(slug=case_slug)

        user_permissions = get_user_permission_list(user, obj)

        if user_has_permission('case-interpretation-create-account',
                               user_permissions) and user.account == obj.account:
            return True
        if user_has_permission('case-interpretation-create-subsidiary',
                               user_permissions) and obj.account.parent_account == user.account:
            return True
        if user_has_permission('case-interpretation-create-assigned', user_permissions) and \
            CaseRole.objects.filter(user=user, case=obj).exists():
            return True
        return False

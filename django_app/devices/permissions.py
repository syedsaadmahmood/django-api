from django.utils.translation import ugettext_lazy as _

from rest_framework import permissions

from django_synergy.utils.permissions import get_user_permission_list, user_has_permission


class CanViewDeviceList(permissions.IsAuthenticated):
    message = _('You do not have permission to access this data.')

    def has_permission(self, request, view):
        user = request.user
        if user.is_superuser:
            return True

        user_permissions = get_user_permission_list(user)
        if user_has_permission('device-list-account', user_permissions) or \
            user_has_permission('device-list-subsidiary', user_permissions) or \
            user_has_permission('device-list-hq', user_permissions) or \
            user_has_permission('device-list-assc', user_permissions) or \
            user_has_permission('device-list-assigned', user_permissions):
            return True
        else:
            return False


class CanViewDeviceDetail(permissions.IsAuthenticated):
    message = _('You do not have permission to access this data.')

    # def has_permission(self, request, view):
    #     user = request.user
    #     if user.is_superuser:
    #         return True
    #
    #     user_permissions = get_user_permission_list(user)
    #     if user_has_permission('device-view-detail-account', user_permissions) or \
    #         user_has_permission('device-view-detail-subsidiary', user_permissions) or \
    #         user_has_permission('device-view-detail-hq', user_permissions) or \
    #         user_has_permission('device-view-detail-assc', user_permissions) or \
    #         user_has_permission('device-view-detail-assigned', user_permissions):
    #         return True
    #     else:
    #         return False

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_superuser:
            return True
        user_permissions = get_user_permission_list(user)

        if obj.account == user.account and user_has_permission('device-view-detail-account', user_permissions):
            return True
        elif obj.account.parent_account == user.account and user_has_permission('device-view-detail-subsidiary', user_permissions):
            return True
        elif obj.account == user.account.parent_account and user_has_permission('device-view-detail-hq', user_permissions):
            return True

        elif user_has_permission('device-view-detail-assc', user_permissions):

            associated_to_accounts = [ass_acc.to_account for ass_acc in user.account.from_account.filter(accepted=True)]
            associated_from_accounts = [ass_acc.from_account for ass_acc in
                                        user.account.to_account.filter(accepted=True)]
            associated_accounts = associated_to_accounts + associated_from_accounts
            associated_accounts_ids = [asc.id for asc in associated_accounts]

            if obj.account.id in associated_accounts_ids:
                return True
        elif user_has_permission('device-view-detail-assigned', user_permissions):
            user_cases = [cr.case for cr in user.case_role_user.all() if (cr.case.is_active is True and cr.case.is_archived is False)]
            case_devices = [cs.CaseDevice_case.all() for cs in user_cases]
            devices = [cd.device for cd in case_devices]
            if obj in devices:
                return True
        return False


class CanEditDevice(permissions.IsAuthenticated):
    message = _('You do not have permission to access this data.')

    # def has_permission(self, request, view):
    #     user = request.user
    #     if user.is_superuser:
    #         return True
    #
    #     user_permissions = get_user_permission_list(user)
    #     if user_has_permission('device-edit-account', user_permissions) or \
    #         user_has_permission('device-edit-subsidiary', user_permissions):
    #         return True
    #     else:
    #         return False

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_superuser:
            return True
        user_permissions = get_user_permission_list(user)
        if obj.account == user.account and user_has_permission('device-edit-account', user_permissions):
            return True
        elif obj.account.parent_account == user.account and user_has_permission('device-edit-subsidiary', user_permissions):
            return True
        return False



class CanViewDeviceSetting(permissions.IsAuthenticated):
    message = _('You do not have permission to access this data.')

    def has_permission(self, request, view):
        user = request.user
        if user.is_superuser:
            return True

        user_permissions = get_user_permission_list(user)
        if user_has_permission('device-view-settings-account', user_permissions) or \
            user_has_permission('device-view-settings-subsidiary', user_permissions) or \
            user_has_permission('device-view-settings-hq', user_permissions) or \
            user_has_permission('device-view-settings-assc', user_permissions) or \
            user_has_permission('device-view-settings-assigned', user_permissions):
            return True
        else:
            return False

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_superuser:
            return True
        user_permissions = get_user_permission_list(user)
        if obj.device.account == user.account and user_has_permission('device-view-settings-account', user_permissions):
            return True
        elif obj.device.account.parent_account == user.account and user_has_permission('device-view-settings-subsidiary', user_permissions):
            return True
        elif obj.device.account == user.account.parent_account and user_has_permission('device-view-settings-hq', user_permissions):
            return True
        elif user_has_permission('device-view-settings-assc', user_permissions):
            associated_to_accounts = [ass_acc.to_account for ass_acc in user.account.from_account.filter(accepted=True)]
            associated_from_accounts = [ass_acc.from_account for ass_acc in
                                        user.account.to_account.filter(accepted=True)]
            associated_accounts = associated_to_accounts + associated_from_accounts
            associated_accounts_ids = [asc.id for asc in associated_accounts]
            if obj.device.account.id in associated_accounts_ids:
                return True
        elif user_has_permission('device-view-settings-assigned', user_permissions):
            user_cases = [cr.case for cr in user.case_role_user.all() if (cr.case.is_active is True and cr.case.is_archived is False)]
            case_devices = [cs.CaseDevice_case.all() for cs in user_cases]
            devices = [cd.device for cd in case_devices]
            if obj.device in devices:
                return True
        return False


class CanViewDeviceSettingHistory(permissions.IsAuthenticated):
    message = _('You do not have permission to access this data.')

    def has_permission(self, request, view):
        user = request.user
        if user.is_superuser:
            return True

        user_permissions = get_user_permission_list(user)
        if user_has_permission('device-view-settings-history-account', user_permissions) or \
            user_has_permission('device-view-settings-history-subsidiary', user_permissions) or \
            user_has_permission('device-view-settings-history-hq', user_permissions) or \
            user_has_permission('device-view-settings-history-assc', user_permissions) or \
            user_has_permission('device-view-settings-history-assigned', user_permissions):
            return True
        else:
            return False

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_superuser:
            return True
        user_permissions = get_user_permission_list(user)
        if obj.device.account == user.account and user_has_permission('device-view-settings-history-account', user_permissions):
            return True
        elif obj.device.account.parent_account == user.account and user_has_permission('device-view-settings-history-subsidiary', user_permissions):
            return True
        elif obj.device.account == user.account.parent_account and user_has_permission('device-view-settings-history-hq', user_permissions):
            return True
        elif user_has_permission('device-view-settings-history-assc', user_permissions):
            associated_to_accounts = [ass_acc.to_account for ass_acc in user.account.from_account.filter(accepted=True)]
            associated_from_accounts = [ass_acc.from_account for ass_acc in
                                        user.account.to_account.filter(accepted=True)]
            associated_accounts = associated_to_accounts + associated_from_accounts
            associated_accounts_ids = [asc.id for asc in associated_accounts]
            if obj.device.account.id in associated_accounts_ids:
                return True
        elif user_has_permission('device-view-settings-history-assigned', user_permissions):
            user_cases = [cr.case for cr in user.case_role_user.all() if (cr.case.is_active is True and cr.case.is_archived is False)]
            case_devices = [cs.CaseDevice_case.all() for cs in user_cases]
            devices = [cd.device for cd in case_devices]
            if obj.device in devices:
                return True
        return False


class CanViewEquipmentRecord(permissions.IsAuthenticated):
    message = _('You do not have permission to access this data.')

    def has_permission(self, request, view):
        user = request.user
        if user.is_superuser:
            return True

        user_permissions = get_user_permission_list(user)
        if user_has_permission('device-view-eqp-record-account', user_permissions) or \
            user_has_permission('device-view-eqp-record-subsidiary', user_permissions) or \
            user_has_permission('device-view-eqp-record-hq', user_permissions) or \
            user_has_permission('device-view-settings-history-assc', user_permissions) or \
            user_has_permission('device-view-settings-history-assigned', user_permissions):
            return True
        else:
            return False

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_superuser:
            return True
        user_permissions = get_user_permission_list(user)
        if obj.device.account == user.account and user_has_permission('device-view-eqp-record-account', user_permissions):
            return True
        elif obj.device.account.parent_account == user.account and user_has_permission('device-view-eqp-record-subsidiary', user_permissions):
            return True
        elif obj.device.account == user.account.parent_account and user_has_permission('device-view-eqp-record-hq', user_permissions):
            return True
        elif user_has_permission('device-view-settings-history-assc', user_permissions):
            associated_to_accounts = [ass_acc.to_account for ass_acc in user.account.from_account.filter(accepted=True)]
            associated_from_accounts = [ass_acc.from_account for ass_acc in
                                        user.account.to_account.filter(accepted=True)]
            associated_accounts = associated_to_accounts + associated_from_accounts
            associated_accounts_ids = [asc.id for asc in associated_accounts]
            if obj.device.account.id in associated_accounts_ids:
                return True
        elif user_has_permission('device-view-settings-history-assigned', user_permissions):
            user_cases = [cr.case for cr in user.case_role_user.all() if (cr.case.is_active is True and cr.case.is_archived is False)]
            case_devices = [cs.CaseDevice_case.all() for cs in user_cases]
            devices = [cd.device for cd in case_devices]
            if obj.device in devices:
                return True
        return False


class CanEditEquipmentRecord(permissions.IsAuthenticated):
    message = _('You do not have permission to access this data.')

    # def has_permission(self, request, view):
    #     user = request.user
    #     if user.is_superuser:
    #         return True
    #
    #     user_permissions = get_user_permission_list(user)
    #     if user_has_permission('device-edit-eqp-record-account', user_permissions) or \
    #         user_has_permission('device-edit-eqp-record-subsidiary', user_permissions):
    #         return True
    #     else:
    #         return False

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_superuser:
            return True
        user_permissions = get_user_permission_list(user)
        if obj.device.account == user.account and user_has_permission('device-edit-eqp-record-account', user_permissions):
            return True
        elif obj.device.account.parent_account == user.account and user_has_permission('device-edit-eqp-record-subsidiary', user_permissions):
            return True
        return False

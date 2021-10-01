from rest_framework import permissions

from django_synergy.accounts.models import Account
from django_synergy.utils.permissions import get_user_permission_list, user_has_permission


class CanViewAccountList(permissions.IsAuthenticated):
    def has_permission(self, request, view):
        user = request.user
        if user.is_superuser:
            return True

        user_permissions = get_user_permission_list(user)
        if user_has_permission('account-view-own', user_permissions) or \
            user_has_permission('account-list-all', user_permissions) or \
            user_has_permission('account-list-subsidiary', user_permissions) or \
            user_has_permission('account-list-hq', user_permissions) or \
            user_has_permission('account-list-associated', user_permissions):
            return True
        else:
            return False


class CanViewAccountDetail(permissions.IsAuthenticated):
    message = 'This API is only accessible to an super user or user that has permission.'

    # def has_permission(self, request, view):
    #     user = request.user
    #     if request.user.is_superuser:
    #         return True
    #
    #     user_permissions = get_user_permission_list(user)
    #     if user_has_permission('account-view-detail-own', user_permissions) or \
    #         user_has_permission('account-view-all-detail', user_permissions) or \
    #         user_has_permission('account-view-detail-subsidiary', user_permissions) or \
    #         user_has_permission('account-view-detail-hq', user_permissions) or \
    #         user_has_permission('account-view-detail-associated', user_permissions):
    #         return True
    #     else:
    #         return False

    def has_object_permission(self, request, view, obj):
        user = request.user
        if request.user.is_superuser:
            return True

        user_permissions = get_user_permission_list(user)
        if user_has_permission('account-view-detail-own', user_permissions) and user.account == obj:
            return True
        if user_has_permission('account-view-all-detail', user_permissions):
            return True
        if user_has_permission('account-view-detail-subsidiary',
                               user_permissions) and obj.parent_account == user.account:
            return True
        if user_has_permission('account-view-detail-associated', user_permissions):
            to_account_association = user.account.to_account.filter(
                accepted=True).all()
            from_account_association = user.account.from_account.filter(
                accepted=True).all()
            for acc in to_account_association:
                if obj == acc.from_account:
                    return True
            for acc in from_account_association:
                if obj == acc.to_account:
                    return True
        if user_has_permission('account-view-detail-hq',
                               user_permissions) and obj == user.account.parent_account:
            return True
        return False


class CanEditAccount(permissions.IsAuthenticated):
    def has_permission(self, request, view):
        user = request.user
        if user.is_superuser:
            return True

        user_permissions = get_user_permission_list(user)
        if user_has_permission('account-edit-own', user_permissions):
            return True
        else:
            return False


class CanViewSubscription(permissions.IsAuthenticated):
    message = 'This API is only accessible to an super user or user that has permission.'

    # def has_permission(self, request, view):
    #     user = request.user
    #     if request.user.is_superuser:
    #         return True
    #     user_permissions = get_user_permission_list(user)
    #
    #     if user_has_permission('account-view-detail-own-sub', user_permissions) or \
    #         user_has_permission('account-view-detail-subsidiary-sub', user_permissions):
    #         return True
    #     else:
    #         return False

    def has_object_permission(self, request, view, obj):
        user = request.user
        if request.user.is_superuser:
            return True

        user_permissions = get_user_permission_list(user)
        if user_has_permission('account-view-detail-own-sub', user_permissions) and user.account == obj:
            return True
        if user_has_permission('account-view-detail-subsidiary-sub',
                               user_permissions) and obj.parent_account == user.account:
            return True
        return False


class CanAssociateToAccounts(permissions.IsAuthenticated):
    def has_permission(self, request, view):
        user = request.user

        user_permissions = get_user_permission_list(user)
        if user_has_permission('account-associate', user_permissions):
            return True
        else:
            return False


class CanRequestAdminToAssociate(permissions.IsAuthenticated):
    def has_permission(self, request, view):
        user = request.user

        user_permissions = get_user_permission_list(user)
        if user_has_permission('account-request-associate', user_permissions):
            return True
        else:
            return False


class CanInviteContact(permissions.IsAuthenticated):
    def has_permission(self, request, view):
        user = request.user

        user_permissions = get_user_permission_list(user)
        if user_has_permission('account-invite-associate', user_permissions):
            return True
        else:
            return False

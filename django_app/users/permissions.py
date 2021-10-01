from rest_framework import permissions
from rest_framework.permissions import SAFE_METHODS
from django.contrib.auth.models import Group

from django_synergy.utils.permissions import get_user_permission_list, user_has_permission


def get_user_groups(user):
    return user.groups.all().values_list('name', flat=True)


class CurrentUserOrAdmin(permissions.IsAuthenticated):

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_superuser:
            return True
        elif hasattr(user, 'account'):

            account = request.user.account
            user_permissions = get_user_permission_list(user)
            return obj.account.slug == user.account.slug and 'user-list' in user_permissions
        else:
            return False


class isAdmin(permissions.IsAuthenticated):
    message = 'This API is only accessible to an account admin.'

    def has_permission(self, request, view):
        user = request.user
        if hasattr(user, 'account') and user.account is not None:
            return True
        else:
            return False


class isSuperUser(permissions.IsAuthenticated):
    message = 'Super User Access permission required'

    def has_permission(self, request, view):
        return request.user.is_superuser


class CurrentUserOrAdminOrReadOnly(permissions.IsAuthenticated):
    def has_object_permission(self, request, view, obj):
        user = request.user
        if type(obj) == type(user) and obj == user:
            return True
        return request.method in SAFE_METHODS or user.is_staff


class CurrentUserOrAdminOrDebugging(permissions.IsAuthenticated):
    def has_object_permission(self, request, view, obj):
        if settings.DEBUG:
            return True
        return request.session and "user_id" in request.session


class CreateUserPermission(permissions.IsAuthenticated):
    message = 'User does not have permission to create this account'

    def has_permission(self, request, view):
        creating_user = request.user
        user_permissions = get_user_permission_list(creating_user)

        if creating_user.is_circadianceadmin:
            return True
        if request.data.get('groups'):
            user_to_create_groups = request.data['groups']
            if creating_user.is_superuser and not request.data['is_superuser']:
                return True

            elif "user-create" in user_permissions and not request.data['is_superuser'] and not (
                'Account Admin' in user_to_create_groups):
                return True

            else:
                return False
        else:
            return False


class CanViewUserList(permissions.IsAuthenticated):
    def has_permission(self, request, view):
        user = request.user
        if user.is_superuser:
            return True

        user_permissions = get_user_permission_list(user)
        if user_has_permission('user-view-own-user', user_permissions) or \
            user_has_permission('user-list-account', user_permissions) or \
            user_has_permission('user-list-subsidiary', user_permissions) or \
            user_has_permission('user-list-associated', user_permissions) or \
            user_has_permission('user-list-hq', user_permissions) or \
            user_has_permission("user-list-contacts", user_permissions) or \
            user_has_permission("user-list-associated-contacts", user_permissions):
            return True
        else:
            return False


class IsCurrentUserSuperAdminAccountAdmin(permissions.IsAuthenticated):
    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.slug == obj.slug:
            return True
        if user.is_superuser:
            return True
        elif hasattr(user, 'account'):
            account = request.user.account
            user_permissions = get_user_permission_list(user)
            if obj.account.account_id == user.account.account_id and 'user-edit-account' in user_permissions:
                return True
            elif user.account.account_id in obj.account.parents and 'user-edit-subsidiary' in user_permissions:
                return True
        else:
            return False


class CanViewUserDetail(permissions.IsAuthenticated):
    message = 'This API is only accessible to an super user or user that has permission.'

    def has_permission(self, request, view):
        user = request.user
        if request.user.is_superuser:
            return True

        user_permissions = get_user_permission_list(user)
        if user_has_permission('user-view-own-user', user_permissions) or \
            user_has_permission('user-view-detail-account', user_permissions) or \
            user_has_permission('user-view-detail-subsidiary', user_permissions) or \
            user_has_permission('user-view-detail-associated', user_permissions) or \
            user_has_permission('user-view-detail-hq', user_permissions) or \
            user_has_permission('user-view-detail-contact', user_permissions) or \
            user_has_permission("user-view-detail-associated-contact", user_permissions):
            return True
        else:
            return False

    def has_object_permission(self, request, view, obj):
        user = request.user
        if request.user.is_superuser:
            return True

        user_permissions = get_user_permission_list(user)
        if user_has_permission('user-view-own-user', user_permissions) and user == obj:
            return True
        if user_has_permission('user-view-detail-account', user_permissions) and user.account == obj.account:
            return True
        if user_has_permission('user-view-detail-subsidiary', user_permissions) and obj.account:
            if obj.account.parent_account == user.account:
                return True
        if user_has_permission('user-view-detail-associated', user_permissions):
            to_account_association = user.account.to_account.filter(
                accepted=True).all()
            from_account_association = user.account.from_account.filter(
                accepted=True).all()
            for acc in to_account_association:
                if obj.account == acc.from_account:
                    return True
            for acc in from_account_association:
                if obj.account == acc.to_account:
                    return True
        if user_has_permission('user-view-detail-hq',
                                 user_permissions) and user.account:
            if obj.account == user.account.parent_account:
                return True
        if user_has_permission('user-view-detail-contact', user_permissions):
            return True
        if user_has_permission('user-view-detail-associated-contact', user_permissions):
            contact_association = user.account.account_associated_contact.filter(accepted=True).all()
            for contact in contact_association:
                if obj.account == contact.from_user.account:
                    return True

        return False


class CanEditUser(permissions.IsAuthenticated):
    message = 'This API is only accessible to an super user or user that has permission.'

    def has_permission(self, request, view):
        user = request.user
        if request.user.is_superuser:
            return True

        user_permissions = get_user_permission_list(user)
        if user_has_permission('user-edit-account', user_permissions) or \
            user_has_permission('user-edit-subsidiary', user_permissions):
            return True
        else:
            return False

    def has_object_permission(self, request, view, obj):
        user = request.user
        if request.user.is_superuser:
            return True

        user_permissions = get_user_permission_list(user)
        if user == obj:
            return True
        if user_has_permission('user-edit-account', user_permissions) and user.account == obj.account:
            return True
        if user_has_permission('user-edit-subsidiary',
                                 user_permissions) and obj.account:
            if obj.account.parent_account == user.account:
                return True
        return False


class CanDeleteUser(permissions.IsAuthenticated):
    message = 'This API is only accessible to an super user or user that has permission.'

    def has_permission(self, request, view):
        user = request.user
        if request.user.is_superuser:
            return True

        user_permissions = get_user_permission_list(user)
        if user_has_permission('user-delete-account', user_permissions) or \
            user_has_permission('user-delete-subsidiary', user_permissions):
            return True
        else:
            return False

    def has_object_permission(self, request, view, obj):
        user = request.user
        if request.user.is_superuser:
            return True

        user_permissions = get_user_permission_list(user)
        if user == obj:
            return True
        if user_has_permission('user-delete-account', user_permissions) and user.account == obj.account:
            return True
        if user_has_permission('user-delete-subsidiary',
                                 user_permissions) and obj.account:
            if obj.account.parent_account == user.account:
                return True
        return False


class CanResetPassword(permissions.IsAuthenticated):
    message = 'This API is only accessible to an super user or user that has permission.'

    def has_permission(self, request, view):
        user = request.user

        if request.user.is_anonymous:
            return True

        if request.user.is_superuser:
            return True

        user_permissions = get_user_permission_list(user)
        if user_has_permission('user-edit-account', user_permissions) or \
            user_has_permission('user-edit-subsidiary', user_permissions):
            return True
        else:
            return False

    def has_object_permission(self, request, view, obj):
        user = request.user
        if request.user.is_superuser:
            return True

        user_permissions = get_user_permission_list(user)
        if user == obj:
            return True
        if user_has_permission('user-edit-account', user_permissions) and user.account == obj.account:
            return True
        if user_has_permission('user-edit-subsidiary',
                                 user_permissions) and obj.account:
            if obj.account.parent_account == user.account:
                return True
        return False


class CanInviteContact(permissions.IsAuthenticated):
    def has_permission(self, request, view):
        user = request.user
        if user.is_superuser:
            return True

        user_permissions = get_user_permission_list(user)
        if user_has_permission('user-invite', user_permissions):
            return True
        else:
            return False

from django.contrib.auth.models import Group
from rest_framework import status
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django_synergy.cases.models import CaseDefaultRole, CaseRole, Case, User
from django_synergy.cases.serializers.roles import CaseDefaultRoleSerializer, CaseRoleWritableSerializer
from django_synergy.cases.utils import fetchCasesAssignedToUser, fetchCasesAssigned, fetchChildAccounts
from django_synergy.cases.views.utils import save_roles
from django_synergy.utils.views import BaseViewset
from django_synergy.cases.permissions import user_has_permission, get_user_permission_list, CanViewCaseRole, \
    CanEditCaseRole
from django_synergy.notifications.utils import generate_case_user_notification


class CaseDefaultRoleViewSet(BaseViewset):
    queryset = CaseDefaultRole.objects.all()
    lookup_field = 'slug'
    action_serializers = {
        'default': CaseDefaultRoleSerializer
    }


def get_match(roles, user):
    for index, role in enumerate(roles):
        if role["user"].slug == user:
            return True, index

    return False, 0


def get_is_removed(case, default_role, users):
    roles = []
    case_roles = CaseRole.objects.filter(case=case, case_default_role=default_role)
    for case_role in case_roles:
        if len(users) == 0:
            flag, index = get_match(roles, case_role.user.slug)
            if flag is True:
                if roles[index]["is_removed"] is True:
                    roles[index]["is_removed"] = True
            else:
                roles.append({
                    "user": case_role.user,
                    "is_removed": True
                })

        for user in users:
            if case_role.user.slug == user:
                flag, index = get_match(roles, case_role.user.slug)
                if flag is True:
                    roles[index]["is_removed"] = False
                else:
                    roles.append({
                        "user": case_role.user,
                        "is_removed": False
                    })
            else:
                flag, index = get_match(roles, case_role.user.slug)
                if flag is True:
                    if roles[index]["is_removed"] is True:
                        roles[index]["is_removed"] = True
                else:
                    roles.append({
                        "user": case_role.user,
                        "is_removed": True
                    })
    return roles


def check_role(case, default_role, user):
    if CaseRole.objects.filter(case=case, case_default_role=default_role).exists():
        if CaseRole.objects.filter(case=case, case_default_role=default_role, user=user).exists():
            return True
        else:
            return False


def remove_users(self, removed_users, case, default_role, request):
    for removed_user in removed_users:
        if removed_user["is_removed"] is True:
            obj = CaseRole.objects.get(case=case, case_default_role=default_role, user=removed_user["user"])
            self.check_object_permissions(self.request, obj)
            CaseRole.objects.filter(case=case, case_default_role=default_role, user=removed_user["user"]).delete()

            # unassigned notification
            to_user = removed_user["user"]
            role_name = default_role.name
            generate_case_user_notification.delay(
                action='Case Role Unassigned', to_user_id=to_user.id, from_user_id=request.user.id,
                case_number=case.case_no, case_manager=request.user.name, case_manager_phone_number=request.user.phone1,
                role_name=role_name
            )


def send_assigned_notification(user, default_role, case, request):
    to_user = user
    role_name = default_role.name
    context_data = {'link_name': case.case_no, 'case_slug': case.slug}
    generate_case_user_notification.delay(
        action='Case Role Assigned', to_user_id=to_user.id, from_user_id=request.user.id,
        case_number=case.case_no, case_manager=request.user.name, case_manager_phone_number=request.user.phone1,
        role_name=role_name, link=case.slug, context_data=context_data
    )


class CaseRoleViewSet(BaseViewset):
    queryset = CaseRole.objects.all()
    lookup_field = 'slug'
    action_serializers = {
        'default': CaseRoleWritableSerializer
    }

    def get_queryset(self):
        if hasattr(self.request.user, 'is_superuser'):
            if self.request.user.is_superuser:
                return CaseRole.objects.all()
        if hasattr(self.request.user, 'account'):
            if self.request.user.account:
                permission_list = get_user_permission_list(self.request.user)
                account_instance = CaseRole.objects.none()
                if user_has_permission('case-role-account', user_permissions=permission_list):
                    account_instance = CaseRole.objects.filter(
                        case__account__id=self.request.user.account.id)

                subsidiary_account_instance = CaseRole.objects.none()
                if user_has_permission('case-role-subsidiary', user_permissions=permission_list):
                    account_slugs_list = []
                    fetchChildAccounts(account_slugs_list, self.request.user.account)
                    subsidiary_account_instance = CaseRole.objects.filter(
                        case__account__slug__in=account_slugs_list)

                cases_assigned_instance = CaseRole.objects.none()
                if user_has_permission('case-role-assigned', user_permissions=permission_list):
                    cases_assigned_slug_list = []
                    fetchCasesAssigned(cases_assigned_slug_list, self.request.user)
                    cases_assigned_instance = CaseRole.objects.filter(
                        case__slug__in=cases_assigned_slug_list)

                case_list_assigned_to_users = CaseRole.objects.none()
                if user_has_permission('case-role-assigned-to-users', user_permissions=permission_list):
                    cases_assigned_slug_list = []
                    fetchCasesAssignedToUser(cases_assigned_slug_list, self.request.user.account)
                    case_list_assigned_to_users = CaseRole.objects.filter(
                        case__slug__in=cases_assigned_slug_list)

                return account_instance | subsidiary_account_instance | cases_assigned_instance | case_list_assigned_to_users

        else:
            return CaseRole.objects.none()

    def get_permissions(self):
        if self.action == "list":
            self.permission_classes = [CanViewCaseRole]
        if self.action == "retrieve":
            self.permission_classes = [CanViewCaseRole]
        if self.action == "create":
            self.permission_classes = [CanEditCaseRole]
        if self.action == "update":
            self.permission_classes = [CanEditCaseRole]
        if self.action == "partial_update":
            self.permission_classes = [CanEditCaseRole]
        else:
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    def retrieve(self, request, *args, **kwargs):
        try:
            all_case_roles = self.get_queryset().all()
            case_role_filter = all_case_roles.filter(case__slug=kwargs['slug'])
            if not case_role_filter:
                return Response({"status": "failed", "message": 'Permission Denied'}
                                , status=status.HTTP_403_FORBIDDEN)
            roles = {
                "Case Manager": [],
                "Scorer": [],
                "Interpreting Physician": [],
                "Referring Physician": [],
                "Specialist": [],
                "Pediatrician / Family Doctor": [],
                "Parent": {}
            }
            for role in roles:
                case_roles = all_case_roles.filter(case__slug=kwargs['slug'], case_default_role__name=role)
                for case_role in case_roles:
                    if role == "Parent":
                        roles[role] = {"slug": case_role.user.slug,
                                       "name": case_role.user.name}
                    else:
                        roles[role].append({"slug": case_role.user.slug,
                                            "name": case_role.user.name})

            return Response({"status": "success", "data": roles}
                            , status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"status": "failed", "message": e}
                            , status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        try:
            data = request.data
            all_case_roles = self.get_queryset().all()
            case_role_filter = all_case_roles.filter(case__slug=kwargs['slug'])
            case = Case.objects.get(slug=kwargs['slug'])
            if not case_role_filter:
                return Response({"status": "failed", "message": 'Permission Denied'}
                                , status=status.HTTP_403_FORBIDDEN)

            if "Case Manager" in data:
                default_role = CaseDefaultRole.objects.get(name='Case Manager')
                removed_array = get_is_removed(case, default_role, data["Case Manager"])
                remove_users(self, removed_array, case, default_role, request)
                for user_slug in data["Case Manager"]:
                    user = User.objects.get(slug=user_slug)
                    if not check_role(case, default_role, user):
                        user_groups = user.groups.all()
                        if not hasattr(user, 'account'):
                            raise ValidationError("account is required")
                        elif not user.account:
                            raise ValidationError("account is required")
                        elif user.account != case.account:
                            raise ValidationError("User's and case account must be same")
                        if user.user_type == "User" and "Biomedical User" not in user_groups:
                            save_roles(self, case, default_role, user)
                            send_assigned_notification(user, default_role, case, request)

            if "Scorer" in data:
                default_role = CaseDefaultRole.objects.get(name='Scorer')
                removed_array = get_is_removed(case, default_role, data["Scorer"])
                remove_users(self, removed_array, case, default_role, request)
                for user_slug in data["Scorer"]:
                    user = User.objects.get(slug=user_slug)
                    if not check_role(case, default_role, user):
                        user_groups = user.groups.all()
                        if user.user_type == "User" and "Biomedical User" not in user_groups:
                            save_roles(self, case, default_role, user)
                            send_assigned_notification(user, default_role, case, request)

            if "Interpreting Physician" in data:
                default_role = CaseDefaultRole.objects.get(name='Interpreting Physician')
                removed_array = get_is_removed(case, default_role, data["Interpreting Physician"])
                remove_users(self, removed_array, case, default_role, request)
                for user_slug in data["Interpreting Physician"]:
                    user = User.objects.get(slug=user_slug)
                    if not check_role(case, default_role, user):
                        user_groups = user.groups.all()
                        if user.user_type == "User" and "Biomedical User" not in user_groups:
                            save_roles(self, case, default_role, user)
                            send_assigned_notification(user, default_role, case, request)

            if "Referring Physician" in data:
                default_role = CaseDefaultRole.objects.get(name='Referring Physician')
                removed_array = get_is_removed(case, default_role, data["Referring Physician"])
                remove_users(self, removed_array, case, default_role, request)
                for user_slug in data["Referring Physician"]:
                    user = User.objects.get(slug=user_slug)
                    if not check_role(case, default_role, user):
                        user_groups = user.groups.all()
                        if "Biomedical User" not in user_groups:
                            save_roles(self, case, default_role, user)
                            send_assigned_notification(user, default_role, case, request)

            if "Specialist" in data:
                default_role = CaseDefaultRole.objects.get(name='Specialist')
                removed_array = get_is_removed(case, default_role, data["Specialist"])
                remove_users(self, removed_array, case, default_role, request)
                for user_slug in data["Specialist"]:
                    user = User.objects.get(slug=user_slug)
                    if not check_role(case, default_role, user):
                        user_groups = user.groups.all()
                        if "Biomedical User" not in user_groups:
                            save_roles(self, case, default_role, user)
                            send_assigned_notification(user, default_role, case, request)

            if "Pediatrician / Family Doctor" in data:
                default_role = CaseDefaultRole.objects.get(name='Pediatrician / Family Doctor')
                removed_array = get_is_removed(case, default_role, data["Pediatrician / Family Doctor"])
                remove_users(self, removed_array, case, default_role, request)
                for user_slug in data["Pediatrician / Family Doctor"]:
                    user = User.objects.get(slug=user_slug)
                    if not check_role(case, default_role, user):
                        user_groups = user.groups.all()
                        if "Biomedical User" not in user_groups:
                            save_roles(self, case, default_role, user)
                            send_assigned_notification(user, default_role, case, request)

            if "Parent" in data:
                default_role = CaseDefaultRole.objects.get(name='Parent')
                removed_array = get_is_removed(case, default_role, data["Parent"])
                remove_users(self, removed_array, case, default_role, request)
                for user_slug in data["Parent"]:
                    user = User.objects.get(slug=user_slug)
                    if not check_role(case, default_role, user):
                        groups = []
                        parent_group = Group.objects.get(name='Parent')
                        user_groups = user.groups.all()
                        if (user.user_type == "Contact") and ("Biomedical User" not in user_groups):
                            groups.append(parent_group)
                            for user_group in user_groups:
                                groups.append(Group.objects.get(name=user_group.name))
                            user.groups.set(groups)
                            user.save()
                            save_roles(self, case, default_role, user)

                            # Assign parent to case
                            case = Case.objects.get(slug=kwargs["slug"])
                            case.parent_user = user
                            case.save()

                            send_assigned_notification(user, default_role, case, request)

            return Response({"status": "success", "message": 'Case Roles Updated'}
                            , status=status.HTTP_200_OK)

        except PermissionDenied as pd:
            raise PermissionDenied

        except Exception as e:
            return Response({"status": "failed", "message": e}
                            , status=status.HTTP_400_BAD_REQUEST)

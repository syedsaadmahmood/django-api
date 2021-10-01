from rest_framework import status
from rest_framework.decorators import action, authentication_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django_synergy.accounts.serializers import AssociatedContactsWritableSerializer
from django_synergy.cases.models import Parent, User, Case, CaseDefaultRole
from django_synergy.cases.serializers import ParentSerializer, ParentWritableSerializer
from django_synergy.cases.utils import fetchChildAccounts, fetchCasesAssigned, fetchCasesAssignedToUser
from django_synergy.cases.views.utils import save_roles
from django_synergy.users.serializers import UserWritableSerializer, ParentUserSerializer, UserCreateSerializer
from django_synergy.utils.views import BaseViewset
from django_synergy.cases.permissions import user_has_permission, get_user_permission_list, CanViewParent, \
    CanEditParent


class ParentViewSet(BaseViewset):
    queryset = Parent.objects.all()
    lookup_field = 'slug'
    action_serializers = {
        'default': ParentSerializer,
    }

    def get_queryset(self):
        if hasattr(self.request.user, 'is_superuser'):
            if self.request.user.is_superuser:
                parent = Parent.objects.all()
                parent_user = User.objects.filter(groups__name='Parent').all()
                all_parent = list(parent) + list(parent_user)
                sorted_parent = sorted(all_parent, key=lambda x: x.created_on)
                return sorted_parent
        if hasattr(self.request.user, 'account'):
            if self.request.user.account:
                permission_list = get_user_permission_list(self.request.user)
                sorted_all_account = []
                if user_has_permission('case-parent-account', user_permissions=permission_list):
                    account_instance_parent = Parent.objects.filter(
                        case_parent__account__id=self.request.user.account.id)
                    account_instance_parent_user = User.objects.filter(
                        case_parent_user__account__id=self.request.user.account.id)
                    all_account = list(account_instance_parent) + list(account_instance_parent_user)
                    sorted_all_account = sorted(all_account, key=lambda x: x.created_on)

                sorted_all_subsidiary_account = []
                if user_has_permission('case-parent-subsidiary', user_permissions=permission_list):
                    account_slugs_list = []
                    fetchChildAccounts(account_slugs_list, self.request.user.account)
                    subsidiary_account_instance = Parent.objects.filter(
                        case_parent__account__slug__in=account_slugs_list)
                    subsidiary_account_instance_parent_user = User.objects.filter(
                        case_parent_user__account__slug__in=account_slugs_list)
                    all_account = list(subsidiary_account_instance) + list(subsidiary_account_instance_parent_user)
                    sorted_all_subsidiary_account = sorted(all_account, key=lambda x: x.created_on)

                sorted_all_assigned = []
                if user_has_permission('case-parent-assigned', user_permissions=permission_list):
                    cases_assigned_slug_list = []
                    fetchCasesAssigned(cases_assigned_slug_list, self.request.user)
                    cases_assigned_instance = Parent.objects.filter(
                        case_parent__slug__in=cases_assigned_slug_list)
                    cases_assigned_instance_parent_user = User.objects.filter(
                        case_parent_user__slug__in=cases_assigned_slug_list)
                    all_account = list(cases_assigned_instance) + list(cases_assigned_instance_parent_user)
                    sorted_all_assigned = sorted(all_account, key=lambda x: x.created_on)

                sorted_all_assigned_to_users = []
                if user_has_permission('case-parent-assigned-to-users', user_permissions=permission_list):
                    cases_assigned_slug_list = []
                    fetchCasesAssignedToUser(cases_assigned_slug_list, self.request.user.account)
                    case_list_assigned_to_users = Parent.objects.filter(
                        case_parent__slug__in=cases_assigned_slug_list)
                    case_list_assigned_to_parent_users = User.objects.filter(
                        case_parent_user__slug__in=cases_assigned_slug_list)
                    all_account = list(case_list_assigned_to_users) + list(case_list_assigned_to_parent_users)
                    sorted_all_assigned_to_users = sorted(all_account, key=lambda x: x.created_on)

                return sorted_all_account + sorted_all_subsidiary_account + sorted_all_assigned + sorted_all_assigned_to_users

        else:
            return Parent.objects.none()

    def get_permissions(self):
        if self.action == "list":
            self.permission_classes = [CanViewParent]
        elif self.action == "retrieve":
            self.permission_classes = [CanViewParent]
        elif self.action == "create":
            self.permission_classes = [CanEditParent]
        elif self.action == "update":
            self.permission_classes = [CanEditParent]
        elif self.action == "partial_update":
            self.permission_classes = [CanEditParent]
        elif self.action == "system_contact":
            self.permission_classes = [CanEditParent]
        else:
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    def list(self, request, *args, **kwargs):
        return Response(status=status.HTTP_200_OK,
                        data={"success": True, "data": []})

    def retrieve(self, request, *args, **kwargs):
        all_parents = self.get_queryset()
        flag = False
        for parent in all_parents:
            if parent.slug == kwargs['slug']:
                flag = True

        if not flag:
            return Response({"status": "failed", "message": 'Permission Denied'}
                            , status=status.HTTP_403_FORBIDDEN)
        slug = kwargs['slug']
        parent = Parent.objects.filter(slug=slug).first()
        user = User.objects.filter(slug=slug, user_type="Contact").first()
        if user is not None and user.case_parent_user is not None:
            return Response(status=status.HTTP_200_OK,
                            data={"success": True, "data": ParentUserSerializer(user, many=False).data})
        if parent is not None and parent.case_parent is not None:
            return Response(status=status.HTTP_200_OK,
                            data={"success": True, "data": ParentSerializer(parent, many=False).data})
        if parent is None and user is None:
            return Response(status=status.HTTP_200_OK,
                            data={"success": True, "data": {}})

    def update(self, request, *args, **kwargs):
        all_parents = self.get_queryset()
        flag = False
        for parent in all_parents:
            if parent.slug == kwargs['slug']:
                flag = True

        if not flag:
            return Response({"status": "failed", "message": 'Permission Denied'}
                            , status=status.HTTP_403_FORBIDDEN)

        slug = kwargs['slug']
        data = request.data
        parent = Parent.objects.filter(slug=slug).first()
        user = User.objects.filter(slug=slug, user_type="Contact").first()
        if parent is None and user is None:
            return Response(status=status.HTTP_200_OK,
                            data={"success": False, "data": {}})

        elif user:
            self.check_object_permissions(self.request, user)
            user_serializer = UserWritableSerializer(user, data=data,
                                                     context=self.get_serializer_context())
            if user_serializer.is_valid(raise_exception=True):
                user_serializer_data = user_serializer.validated_data
                user = user_serializer.save()
            return Response(status=status.HTTP_200_OK,
                            data={"success": True, "data": ParentUserSerializer(user, many=False).data})

        elif parent:
            self.check_object_permissions(self.request, parent)
            parent_serializer = ParentWritableSerializer(parent, data=data,
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
            return Response(status=status.HTTP_200_OK,
                            data={"success": True, "data": ParentSerializer(parent, many=False).data})

    @action(["post"], detail=False)
    def system_contact(self, request, *args, **kwargs):
        try:
            data = request.data
            data["groups"] = ['Contact']

            user_serializer = UserCreateSerializer(data=data,
                                                   context=self.get_serializer_context())
            if user_serializer.is_valid(raise_exception=True):
                user_serializer_data = user_serializer.validated_data
                parent_user = user_serializer.save()

                case = Case.objects.get(slug=data["case"])
                case.parent_user = parent_user
                case.save()

                default_role = CaseDefaultRole.objects.get(name='Parent')
                save_roles(self, case, default_role, case.parent_user)

                # Associated contact
                contact_body = {
                    "from_user": parent_user.slug,
                    "to_account": case.account.slug,
                    "accepted": True
                }
                associated_contact = AssociatedContactsWritableSerializer(data=contact_body,
                                                                          context=self.get_serializer_context())
                if associated_contact.is_valid(raise_exception=True):
                    associated_contact_data = associated_contact.validated_data
                    associated_contact.save()

                return Response(status=status.HTTP_200_OK,
                                data={"success": True, "data": ParentUserSerializer(parent_user, many=False).data})

        except Exception as e:
            return Response({"status": "failed", "message": e}
                            , status=status.HTTP_400_BAD_REQUEST)

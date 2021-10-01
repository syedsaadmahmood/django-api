from pytz import common_timezones

from django.contrib.auth import get_user_model, user_logged_in, user_logged_out
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.utils.timezone import now
from django.conf import settings as django_settings
from django.db.models import ProtectedError
from django.utils.translation import gettext as _

from rest_framework import generics, status, views, viewsets
from rest_framework.decorators import action, api_view, authentication_classes, permission_classes
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
# from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework.permissions import AllowAny, IsAuthenticated
# from rest_framework_simplejwt.views import TokenViewBase
# from rest_framework_simplejwt.authentication import AUTH_HEADER_TYPES
from rest_framework_jwt import views as jwt_views
from drf_jwt_2fa import serializers as drf_jwt_2fa_serializers
from drf_jwt_2fa.throttling import AuthTokenThrottler, CodeTokenThrottler
from drf_jwt_2fa.authentication import Jwt2faAuthentication
from rest_framework_jwt.settings import api_settings

from django_synergy.cases.models import Case, CaseRole
from django_synergy.users import signals, utils
from django_synergy.users.compat import get_user_email
from django_synergy.users.conf import settings
from django_synergy.users.manager import super_user_widgets, account_admin_widgets, \
    case_manager_widgets, user_widgets, bio_medical_user_widgets, \
    contact_widgets
from django_synergy.utils.models import WidgetConfiguration
from django_synergy.utils.permissions import get_user_permission_list, user_has_permission
from django_synergy.utils.serializers import GetUserConfigSerializer
from django_synergy.utils.views.base import BaseViewset
from django_synergy.users import serializers
from django_synergy.users.serializers import TimezoneLookupSerializer, SystemUserCreateSerializer, UserSerializer
from django_synergy.accounts.models import Account
from django.http import JsonResponse
from django.contrib.auth.models import Group, Permission
from django.conf import settings as s
from django_synergy.users.permissions import CreateUserPermission, isSuperUser, CanInviteContact
from datetime import datetime, timedelta
from django.db import transaction

User = get_user_model()
LANGUAGES = s.LANGUAGES


def fetchChildAccounts(account_list, current_account):
    if current_account not in account_list:
        account_list.append(current_account.slug)
        # for account in current_account.subsidiaries.all():
        #     fetchChildAccounts(account_list, account)
    if current_account not in account_list:
        account_list.append(current_account.slug)
    subsidiaries = Account.objects.filter(parents__contains=current_account.account_id)
    subsidiaries_slugs = [s.slug for s in subsidiaries]
    account_list += subsidiaries_slugs


def updateWidgets(user_configs, user):
    widget_configurations = WidgetConfiguration.objects.filter(user=user)
    for widget_configuration in widget_configurations:
        for user_config in user_configs:
            if widget_configuration.title == user_config["title"]:
                widget_configuration.cols = user_config["cols"]
                widget_configuration.rows = user_config["rows"]
                widget_configuration.x = user_config["x"]
                widget_configuration.y = user_config["y"]
                widget_configuration.widget_type = user_config["widget_type"]
                widget_configuration.save()


class UserViewSet(BaseViewset):
    # serializer_class = settings.SERIALIZERS.user
    queryset = User.objects.select_related('account').all()
    # permission_classes = settings.PERMISSIONS.user
    token_generator = default_token_generator
    lookup_field = 'slug'

    action_serializers = {
        'default': serializers.UserSerializer,
        'list': serializers.UserSerializer,
        'create': serializers.UserCreateSerializer,
        'update': serializers.UserWritableSerializer,
        'destroy': serializers.UserDeleteSerializer,
        'me': serializers.UserSerializer,
        'activation': serializers.ActivationSerializer,
        'resend_activation': serializers.SendEmailResetSerializer,
        'reset_password_confirm': serializers.PasswordResetConfirmRetypeSerializer,
        'set_password': serializers.SetPasswordRetypeSerializer,
        'signup': serializers.UserCreatePasswordRetypeSerializer,
        'logout': serializers.LogoutSerializer,
        'reset_password': serializers.SendEmailResetSerializer,
        'widget': GetUserConfigSerializer,
        'create_system_user': SystemUserCreateSerializer,
        'resend_activation_set_password': serializers.ResendActivationSetPassword,
        'resend_activation_auto': serializers.ResendActivationAuto,
    }

    def get_queryset(self):
        user = self.request.user
        user_groups = self.request.user.groups.all()

        if user.is_superuser:
            return super().get_queryset()

        elif hasattr(user, 'account') and user.account:
            account = user.account
            permission_list = get_user_permission_list(user)

            own_user = User.objects.none()
            if user_has_permission('user-view-own-user', user_permissions=permission_list):
                own_user = User.objects.filter(slug=user.slug)

            account_user_list = User.objects.none()
            if user_has_permission('user-list-account', user_permissions=permission_list):
                account_user_list = User.objects.filter(account_id=user.account.id).exclude(slug=user.slug)

            subsidiary_user_list = User.objects.none()
            if user_has_permission('user-list-subsidiary', user_permissions=permission_list):
                subsidiary_user_list = User.objects.filter(account__parents__contains=user.account.account_id)

            hq_user_list = User.objects.none()
            if user_has_permission('user-list-hq', user_permissions=permission_list):
                if user.account.parent_account:
                    hq_user_list = User.objects.filter(account_id=user.account.parent_account.id)

            associated_user_list = User.objects.none()
            if user_has_permission('user-list-associated', user_permissions=permission_list):
                to_account_association = user.account.to_account.filter(
                    accepted=True).all()
                from_account_association = user.account.from_account.filter(
                    accepted=True).all()

                for account in to_account_association:
                    associated_user_list = associated_user_list | account.from_account.users.all()

                for account in from_account_association:
                    associated_user_list = associated_user_list | account.to_account.users.all()

            contact_user_list = User.objects.none()
            if user_has_permission('user-list-contacts', user_permissions=permission_list):
                contact_user_list = User.objects.filter(user_type='Contact')

            associated_contact_user_list = User.objects.none()
            associated_contact_list_of_slugs = []
            if user_has_permission('user-list-associated-contacts', user_permissions=permission_list):
                contact_association = user.account.account_associated_contact.filter(accepted=True).all()
                for contact in contact_association:
                    associated_contact_list_of_slugs.append(contact.from_user.slug)

                associated_contact_user_list = User.objects.filter(slug__in=associated_contact_list_of_slugs)

            return own_user | account_user_list | subsidiary_user_list | hq_user_list | associated_user_list | contact_user_list | associated_contact_user_list
        else:
            return User.objects.none()

    def get_permissions(self):

        if self.action == "create":
            self.permission_classes = settings.PERMISSIONS.user_create
        elif self.action == "retrieve":
            self.permission_classes = settings.PERMISSIONS.user_detail
        elif self.action == "update":
            self.permission_classes = settings.PERMISSIONS.user_edit
        elif self.action == "partial_update":
            self.permission_classes = settings.PERMISSIONS.user_edit
        elif self.action == "activation":
            self.permission_classes = settings.PERMISSIONS.activation
        elif self.action == "resend_activation":
            self.permission_classes = settings.PERMISSIONS.password_reset
        elif self.action == "list":
            self.permission_classes = settings.PERMISSIONS.user_list
        elif self.action == "reset_password":
            self.permission_classes = settings.PERMISSIONS.password_reset
        elif self.action == "activate":
            self.permission_classes = settings.PERMISSIONS.user_edit
        elif self.action == "deactivate":
            self.permission_classes = settings.PERMISSIONS.user_edit
        elif self.action == "reset_password_confirm":
            self.permission_classes = settings.PERMISSIONS.password_reset_confirm
        elif self.action == "set_password":
            self.permission_classes = settings.PERMISSIONS.set_password
        elif self.action == "set_username":
            self.permission_classes = settings.PERMISSIONS.set_username
        elif self.action == "reset_username":
            self.permission_classes = settings.PERMISSIONS.username_reset
        elif self.action == "reset_username_confirm":
            self.permission_classes = settings.PERMISSIONS.username_reset_confirm
        elif self.action == "destroy" or (
            self.action == "me" and self.request and self.request.method == "DELETE"
        ):
            self.permission_classes = settings.PERMISSIONS.user_delete
        elif self.action == "signup":
            self.permission_classes = settings.PERMISSIONS.signup
        elif self.action == 'logout':
            self.permission_classes = settings.PERMISSIONS.logout
        elif self.action == "create_system_user":
            self.permission_classes = settings.PERMISSIONS.create_system_user

        return super().get_permissions()

    def get_instance(self):
        return self.request.user

    def perform_create(self, serializer):
        user = serializer.save()
        signals.user_registered.send(
            sender=self.__class__, user=user, request=self.request
        )
        context = {"user": user}
        to = [get_user_email(user)]
        if settings.SEND_ACTIVATION_EMAIL:
            settings.EMAIL.activation_set_password(
                self.request, context).send(to)

    # This is the function that maps to signup functionality on the front-end
    def create(self, request):
        return super().create(request)

    def partial_update(self, request, *args, **kwargs):
        user = User.objects.get(slug=kwargs['slug'])
        data = request.data
        if "tandc_policy_agreed" in data:
            user.tandc_policy_agreed = data["tandc_policy_agreed"]

        if "subscription_policy_agreed" in data:
            user.subscription_policy_agreed = data["subscription_policy_agreed"]

        user.save()

        user_serializer = UserSerializer(user, many=False).data
        return Response(status=status.HTTP_200_OK,
                        data={"success": True, "data": user_serializer})

    def perform_update(self, serializer):
        super().perform_update(serializer)
        user = serializer.instance
        # should we send activation email after update?
        if settings.SEND_ACTIVATION_EMAIL and not user.is_active:
            context = {"user": user}
            to = [get_user_email(user)]
            settings.EMAIL.activation(self.request, context).send(to)

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data)
            serializer.is_valid(raise_exception=True)

            if instance == request.user:
                utils.logout_user(self.request)

            with transaction.atomic():
                if WidgetConfiguration.objects.filter(user=instance).exists():
                    widget_configurations = WidgetConfiguration.objects.filter(user=instance)
                    for widget_conf in widget_configurations:
                        WidgetConfiguration.objects.get(slug=widget_conf.slug).delete()

                User.objects.get(slug=kwargs["slug"]).delete()
                # self.perform_destroy(instance)

                return Response(status=status.HTTP_200_OK,
                                data={"success": True,
                                      "message": "User deleted successfully", })

        except ProtectedError as e:
            return Response(status=status.HTTP_400_BAD_REQUEST,
                            data={"success": False, "status_code": 400,
                                  "message": _("User can not be deleted because one or more ") + str(
                                      e.protected_objects.model.updated_by.field.opts.verbose_name_plural) + _(
                                      " exist.")})

    @action(["get"], detail=False)
    def me(self, request, *args, **kwargs):
        self.get_object = self.get_instance
        if request.method == "GET":
            return self.retrieve(request, *args, **kwargs)
        elif request.method == "PUT":
            return self.update(request, *args, **kwargs)

    @action(["get", "put"], detail=False)
    def widget(self, request, *args, **kwargs):
        self.get_object = self.get_instance
        if request.method == "GET":
            return self.retrieve(request, *args, **kwargs)
        elif request.method == "PUT":
            return self.update(request, *args, **kwargs)

    @action(["post"], detail=False)
    def activation(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.user
        user.is_active = True
        user.save()

        signals.user_activated.send(
            sender=self.__class__, user=user, request=self.request
        )

        if settings.SEND_CONFIRMATION_EMAIL:
            context = {"user": user}
            to = [get_user_email(user)]
            settings.EMAIL.confirmation(self.request, context).send(to)

        return Response(status=status.HTTP_201_CREATED,
                        data={
                            "success": True,
                            "status_code": 200,
                            "message": "activated",
                        }
                        )

    @action(["put"], detail=True)
    def activate(self, request, *args, **kwargs):
        self.check_object_permissions(request, self.get_object())
        user = User.objects.get(slug=kwargs['slug'])

        # if user has subscriptions left
        if user.account:
            if user.account.num_user_subscriptions < user.account.max_user_subscriptions:
                user.is_active = True
                user.save()

                context = {"user": user}
                to = [get_user_email(user)]
                settings.EMAIL.user_activate(self.request, context).send(to)

                signals.user_activated.send(
                    sender=self.__class__, user=user, request=self.request
                )

                return Response(status=status.HTTP_200_OK,
                                data={"success": True,
                                      "status_code": 200,
                                      "message": "User Activated", })
            else:
                return Response(status=status.HTTP_400_BAD_REQUEST,
                                data={"success": False,
                                      "status_code": 400,
                                      "message": {"User Subscriptions limit reached", }})

        else:
            user.is_active = True
            user.save()

            signals.user_activated.send(
                sender=self.__class__, user=user, request=self.request
            )

            context = {"user": user}
            to = [get_user_email(user)]
            settings.EMAIL.user_activate(self.request, context).send(to)

            return Response(status=status.HTTP_200_OK,
                            data={"success": True,
                                  "status_code": 200,
                                  "message": "User Activated", })

    @action(["put"], detail=True)
    def deactivate(self, request, *args, **kwargs):
        self.check_object_permissions(request, self.get_object())
        user = User.objects.get(slug=kwargs['slug'])
        user.is_active = False
        user.save()

        context = {"user": user}
        to = [get_user_email(user)]
        settings.EMAIL.user_deactivate(self.request, context).send(to)

        signals.user_deactivated.send(
            sender=self.__class__, user=user, request=self.request
        )

        return Response(status=status.HTTP_200_OK,
                        data={"success": True,
                              "status_code": 200,
                              "message": "User Deactivated", })

    @action(["post"], detail=False)
    def resend_activation(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.get_user(is_active=False)

        if not settings.SEND_ACTIVATION_EMAIL or not user:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        context = {"user": user}
        to = [get_user_email(user)]
        settings.EMAIL.activation(self.request, context).send(to)

        signals.user_resend_activation.send(
            sender=self.__class__, user=user, request=self.request
        )

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(["post"], detail=False)
    def set_password(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        self.request.user.set_password(serializer.data["new_password"])
        self.request.user.save()

        if settings.LOGOUT_ON_PASSWORD_CHANGE:
            utils.logout_user(self.request)

        if settings.PASSWORD_CHANGED_EMAIL_CONFIRMATION:
            context = {"user": self.request.user}
            to = [get_user_email(self.request.user)]
            settings.EMAIL.password_changed_confirmation(
                self.request, context).send(to)

        signals.set_password.send(
            sender=self.__class__, user=user, request=self.request
        )

        return Response(status=status.HTTP_200_OK, data={"success": True, "status_code": 200,
                                                         "message": "Password changed for {0}".format(
                                                             request.user.email)})

    @action(["post"], detail=False)
    def reset_password(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.get_user()

        if user:
            context = {"user": user}
            to = [get_user_email(user)]
            settings.EMAIL.password_reset(self.request, context).send(to)

        signals.reset_password.send(
            sender=self.__class__, user=user, request=self.request
        )

        return Response(status=status.HTTP_200_OK, data={"success": True, "status_code": 200, "message": "Success"})

    @action(["post"], detail=False)
    def reset_password_confirm(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        serializer.user.set_password(serializer.data["new_password"])
        serializer.user.is_active = True
        if hasattr(serializer.user, "last_login"):
            serializer.user.last_login = now()
        serializer.user.save()

        if settings.PASSWORD_CHANGED_EMAIL_CONFIRMATION:
            context = {"user": serializer.user}
            to = [get_user_email(serializer.user)]
            settings.EMAIL.password_changed_confirmation(
                self.request, context).send(to)

        signals.reset_password_confirm.send(
            sender=self.__class__, user=serializer.user, request=self.request
        )
        return Response(status=status.HTTP_200_OK,
                        data={"success": True, "status_code": 200, "message": "Password reset"})

    # This function is used for user signup
    @action(["post"], detail=False, permission_classes=[AllowAny], authentication_classes=[])
    def signup(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save()
        signals.user_registered.send(
            sender=self.__class__, user=user, request=self.request
        )
        context = {"user": user}
        to = [get_user_email(user)]
        if settings.SEND_ACTIVATION_EMAIL:
            settings.EMAIL.activation(self.request, context).send(to)
        elif settings.SEND_CONFIRMATION_EMAIL:
            settings.EMAIL.confirmation(self.request, context).send(to)

        return Response(status=status.HTTP_201_CREATED,
                        data={"success": True,
                              "status_code": 201,
                              "message": "User Created", })

    @action(["post"], detail=False, permission_classes=[], authentication_classes=[Jwt2faAuthentication])
    def create_system_user(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_to_create = serializer.save()

        # Sending Email
        context = {"user": user_to_create}
        to = [get_user_email(user_to_create)]

        if settings.SEND_ACTIVATION_EMAIL:
            user_to_create.is_active = False
            user_to_create.save(update_fields=["is_active"])
            settings.EMAIL.activation_set_password(
                self.request, context).send(to)
        # if settings.SEND_ACTIVATION_EMAIL:
        #     settings.EMAIL.activation(self.request, context).send(to)
        # elif settings.SEND_CONFIRMATION_EMAIL:
        #     settings.EMAIL.confirmation(self.request, context).send(to)

        return Response(status=status.HTTP_201_CREATED,
                        data={
                            "success": True,
                            "status_code": 201,
                            "message": "User Created",
                        }
                        )

    @action(["post"], detail=False, permission_classes=[], authentication_classes=[])
    def resend_activation_set_password(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.user
        # Sending Email
        context = {"user": user}
        to = [get_user_email(user)]

        if settings.SEND_ACTIVATION_EMAIL:
            settings.EMAIL.activation_set_password(
                self.request, context).send(to)

        return Response(status=status.HTTP_201_CREATED,
                        data={
                            "success": True,
                            "status_code": 200,
                            "message": "resent set password link",
                        }
                        )

    @action(["post"], detail=False, permission_classes=[], authentication_classes=[])
    def resend_activation_auto(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.user

        if not settings.SEND_ACTIVATION_EMAIL or not user:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        context = {"user": user}
        to = [get_user_email(user)]
        settings.EMAIL.activation(self.request, context).send(to)

        return Response(status=status.HTTP_201_CREATED,
                        data={
                            "success": True,
                            "status_code": 200,
                            "message": "resent set password link",
                        }
                        )

    @action(["post"], detail=False)
    def logout(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_id = serializer.context.get('request').user.id
        cache.expire(user_id, timeout=0)

        response = Response(status=status.HTTP_200_OK,
                            data={"success": True,
                                  "status_code": 200,
                                  "message": "User Logged Out", })
        response.delete_cookie(api_settings.JWT_AUTH_COOKIE)
        user_logged_out.send(
            sender=self.__class__, user=self.request.user, request=self.request
        )
        return response

    @action(["get"], detail=True)
    def reset_widget_config(self, request, *args, **kwargs):
        user_instance = self.get_object()
        if user_instance.is_superuser:
            updateWidgets(super_user_widgets, user_instance)

        elif user_instance.groups.filter(name='Account Admin').count() > 0:
            updateWidgets(account_admin_widgets, user_instance)

        elif user_instance.groups.filter(name='Case Manager').count() > 0:
            updateWidgets(case_manager_widgets, user_instance)

        elif user_instance.groups.filter(name='User').count() > 0:
            updateWidgets(user_widgets, user_instance)

        elif user_instance.groups.filter(name='Biomedical User').count() > 0:
            updateWidgets(bio_medical_user_widgets, user_instance)

        elif user_instance.groups.filter(name='Contact').count() > 0:
            updateWidgets(contact_widgets, user_instance)

        return Response(status=status.HTTP_200_OK,
                        data={
                            "success": True,
                            "status_code": 200,
                            "message": "Widgets reset to default successfully",
                            "data": GetUserConfigSerializer(user_instance, many=False).data
                        }
                        )

    @action(["post"], detail=False)
    def check_email(self, request, *args, **kwargs):
        data = request.data
        if User.objects.filter(email=data["email"]).exists():
            return Response(status=status.HTTP_200_OK,
                            data={"success": False, "status_code": 200, "message": "Email already exists"})
        else:
            return Response(status=status.HTTP_200_OK,
                            data={"success": True, "status_code": 200, "message": "New email"})


@api_view()
@authentication_classes([])
@permission_classes([AllowAny])
def getTimezones(request):
    timezones = [t for t in common_timezones]
    return JsonResponse({
        "success": True,
        "status_code": 200,
        "message": "List of timezones",
        "data": timezones
    }, safe=False)


@api_view(['GET'])
@authentication_classes([Jwt2faAuthentication])
@permission_classes([IsAuthenticated])
def getGroups(request):
    groups = list(Group.objects.all().values("id", "name"))
    return JsonResponse({
        "success": True,
        "status_code": 200,
        "message": "List of groups",
        "data": groups
    })


@api_view(['GET'])
@authentication_classes([Jwt2faAuthentication])
@permission_classes([IsAuthenticated])
def getPermissions(request):
    content_type_name = request.query_params.get('content_type', None)
    permissions = []
    if content_type_name:
        permissions = Permission.objects.select_related('content_type') \
            .filter(content_type__app_label=content_type_name) \
            .values("id", "name", "codename", "content_type__model")
    else:
        all_permissions = Permission.objects.select_related('content_type').order_by('id')
        permissions = all_permissions.exclude(codename__contains='_').all().values(
            "id", "name", "codename", "content_type__model")
    permissions = [{'id': p['id'], 'name': p['name'], 'codename': p['codename'],
                    'content_type': p['content_type__model']} for p in permissions]

    return JsonResponse({
        "success": True,
        "status_code": 200,
        "message": "List of permissions",
        "data": permissions
    })


@api_view(['POST'])
@authentication_classes([Jwt2faAuthentication])
@permission_classes([IsAuthenticated])
def savePermissionGroups(request):
    group = Group.objects.get(id=request.data.get('role'))
    permissionList = request.data.get('permissions')
    group.permissions.set(permissionList)
    return JsonResponse({
        "success": True,
        "status_code": 200,
        "message": "Permissions saved",
        "data": None
    })


@api_view()
@authentication_classes([Jwt2faAuthentication])
@permission_classes([IsAuthenticated])
def getGroupPermissions(request):
    group_id = request.query_params.get('GroupId')
    group = Group.objects.get(id=group_id)
    permissions = group.permissions.all()
    permissions = [{
        'id': p.id,
        'name': p.name,
        'codename': p.codename,
    } for p in permissions]
    return JsonResponse({
        "success": True,
        "status_code": 200,
        "message": "List of Group Permissions",
        "data": permissions
    })


@api_view()
@authentication_classes([])
@permission_classes([AllowAny])
def getLanguages(request):
    languages = []
    for language in LANGUAGES:
        langDict = {
            "code": language[0],
            "name": language[1]
        }
        languages.append(langDict)

    return JsonResponse({
        "success": True,
        "status_code": 200,
        "message": "List of languages",
        "data": languages
    })


@api_view(['POST'])
@authentication_classes([Jwt2faAuthentication])
@permission_classes([CanInviteContact])
def inviteContact(request):
    email = request.data.get('email')
    email_exists = User.objects.filter(email=email).count()
    if email_exists == 0:
        context = {}
        to = [email]
        settings.EMAIL.invite_contact(request, context).send(to)
        return Response(status=status.HTTP_200_OK,
                        data={"success": True,
                              "status_code": 200,
                              "message": "Invitation send", })
    else:
        return Response(status=status.HTTP_403_FORBIDDEN,
                        data={"success": True,
                              "status_code": 403,
                              "message": "Email exist", })


@api_view()
@authentication_classes([Jwt2faAuthentication])
@permission_classes([IsAuthenticated])
def getUserListSummaries(request):
    last_month = datetime.utcnow() - timedelta(days=30)
    contacts = User.objects.filter(user_type="Contact").count()
    new_contacts = User.objects.filter(
        user_type="Contact", created_on__gte=last_month).count()
    active_users = User.objects.filter(is_active=True).count()
    new_users = User.objects.filter(created_on__gte=last_month).count()

    summaries = {
        "contacts": contacts,
        "new_contacts": new_contacts,
        "active_users": active_users,
        "new_users": new_users
    }

    return JsonResponse({
        "success": True,
        "status_code": 200,
        "message": "List of User List Summaries",
        "data": summaries
    })

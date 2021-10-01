import os
import csv
import datetime
import logging
from re import compile
from io import TextIOWrapper
from tempfile import mkstemp
from collections import defaultdict
from django.utils.translation import gettext as _
from rest_framework.permissions import IsAuthenticated
from xlrd import open_workbook, xldate_as_tuple
from django.db.models import ProtectedError

from django.conf import settings as django_settings
from django.contrib.auth.models import Group
from django.db import transaction
from django.core.exceptions import ValidationError
from django.db.models import Q, F

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ParseError

from django_synergy.utils.views.base import BaseViewset
from django_synergy.utils.mappings import abbrev_us_state, abbrev_country
from django_synergy.users.models import User
from django_synergy.notifications.utils import generate_user_notification, generate_account_notification

from .models import Account, AccountUpload, AccountUploadItems, AssociatedAccounts, AssociatedContacts, UserSubscription
from .permissions import CanViewAccountList, CanViewAccountDetail, CanEditAccount, CanViewSubscription, \
    CanAssociateToAccounts, CanRequestAdminToAssociate, CanInviteContact
from .serializers import AccountSerializer, AccountCreateSerializer, AccountWritableSerializer, \
    AssociatedAccountsSerializer, AssociatedAccountsWritableSerializer, AccountUploadSerializer, \
    AccountUploadItemSerializer, AccountUploadWritableSerializer, AssociatedSerializer, UserSubscriptionSerializer, \
    AssociatedContactsSerializer, AssociatedContactsWritableSerializer, AccountReadOnlySerializer, \
    DropDownAccountSerializer, AccountSimpleSerializer, UserSubscriptionReadOnlySerializer

# from config.settings.base import MEDIA_URL, MEDIA_ROOT
# from ..notifications.data import default_types
from ..cases.models import Case
from ..cases.permissions import CanCreateCase
from ..notifications.models import NotificationType
from ..users.permissions import isSuperUser
from ..users.serializers import UserSummarySerializer
from ..utils.permissions import get_user_permission_list, user_has_permission

logger = logging.getLogger(__name__)

ACCOUNT_IMPORT_DICTIONARY = {
    "account_number": "account_number",
    "account_name": "account_name",
    "city": "city",
    "state": "state",
    "country": "country",
    "zipcode": "zipcode",
    "phone1": "phone1",
    "phone2": "phone2",
    "address1": "address1",
    "address2": "address2",
    "address3": "address3",
    "domain": "domain",
    "hq_account_number": "hq_account_number",
    "no_of_usr_subs": "no_of_usr_subs",
    "sub_start_date": "sub_end_date",
    "sub_end_date": "sub_end_date",
    "language": "language"
}


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


def get_parent_accounts(account, parents):
    if account.parent_account:
        if account.parent_account.account_id == account.account_id:
            return
        parents.append(account.parent_account.account_id)
        get_parent_accounts(account.parent_account, parents)
    else:
        return


def get_queryset_for_list(user):
    user_groups = user.groups.all()
    user_account = user.account

    if user.is_superuser or user.is_circadianceadmin:
        queryset = Account.objects.select_related('parent_account').all()

    elif Group.objects.get(name='Account Admin') in user_groups:
        account_list = []
        fetchChildAccounts(account_list, user_account)
        queryset = Account.objects.select_related(
            'parent_account').filter(slug__in=account_list)

    else:
        queryset = Account.objects.select_related(
            'parent_account').filter(slug=user_account.slug)

    return queryset


def try_parsing_date(text):
    for fmt in ('%m/%d/%Y', '%d-%b-%y', '%m-%d-%Y'):
        try:
            return datetime.datetime.strptime(text, fmt)
        except ValueError:
            pass
    raise ValueError('no valid date format found')


class AccountsViewSet(BaseViewset):
    queryset = Account.objects.select_related('parent_account').all()
    lookup_field = 'slug'
    action_serializers = {
        'default': AccountSerializer,
        'create': AccountCreateSerializer,
        'update': AccountWritableSerializer,
        'list_of_hqs': AccountReadOnlySerializer,
        'list_accounts': DropDownAccountSerializer
    }

    def get_permissions(self):
        if self.action == "list":
            self.permission_classes = [CanViewAccountList]
        elif self.action == "retrieve":
            self.permission_classes = [CanViewAccountDetail]
        elif self.action == "create":
            self.permission_classes = [isSuperUser]
        elif self.action == "update":
            self.permission_classes = [CanEditAccount]
        elif self.action == "partial_update":
            self.permission_classes = [CanEditAccount]
        elif self.action == "get_subscription":
            self.permission_classes = [CanViewSubscription]
        else:
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    def get_queryset(self):
        user = self.request.user
        user_groups = self.request.user.groups.all()
        if user.is_superuser:
            return super().get_queryset()

        if hasattr(user, 'account') and user.account:
            account = user.account
            permission_list = get_user_permission_list(user)

            own_account = Account.objects.none()
            if user_has_permission('account-view-own', user_permissions=permission_list):
                own_account = Account.objects.filter(slug=account.slug)

            account_list_all = Account.objects.none()
            if user_has_permission('account-list-all', user_permissions=permission_list):
                account_list_all = Account.objects.all()

            subsidiary_account_list = Account.objects.none()
            if user_has_permission('account-list-subsidiary', user_permissions=permission_list):
                subsidiary_account_list = Account.objects.filter(parents__contains=user.account.account_id)

            hq_account_list = Account.objects.none()
            if user_has_permission('account-list-hq', user_permissions=permission_list):
                if user.account.parent_account:
                    hq_account_list = Account.objects.filter(
                        parent_account__account_id=user.account.parent_account.account_id)

            associated_account_list = Account.objects.none()
            if user_has_permission('account-list-associated', user_permissions=permission_list):
                to_account_association = user.account.to_account.filter(
                    accepted=True).all()
                from_account_association = user.account.from_account.filter(
                    accepted=True).all()

                for account in to_account_association:
                    associated_account_list = associated_account_list | Account.objects.filter(
                        id=account.from_account.id)

                for account in from_account_association:
                    associated_account_list = associated_account_list | Account.objects.filter(
                        id=account.to_account.id)

            return own_account | account_list_all | subsidiary_account_list | hq_account_list | associated_account_list
        elif hasattr(user, 'account') and not user.account:
            permission_list = get_user_permission_list(user)
            account_list_all = Account.objects.none()
            if user_has_permission('account-list-all', user_permissions=permission_list):
                account_list_all = Account.objects.all()

            return account_list_all
        else:
            return Account.objects.none()

    def create(self, request, *args, **kwargs):
        # default_types_objs = [NotificationType(**notif_type) for notif_type in default_types]
        # NotificationType.objects.bulk_create(default_types_objs)
        return super().create(request, args, kwargs)

    def partial_update(self, request, *args, **kwargs):
        try:
            data = request.data
            account = Account.objects.get(slug=kwargs["slug"])
            to_account_admin = User.objects.get(id=account.account_admin_id)

            if (data["is_active"] == "true" or data["is_active"] is True) and account.is_active is False:
                current_subscription = account.current_active_subscription
                if current_subscription is None:
                    return Response(status=status.HTTP_400_BAD_REQUEST,
                                    data={"success": False, "status_code": 400,
                                          "message": _("Subscription does not exist")})

                if to_account_admin is None:
                    return Response(status=status.HTTP_400_BAD_REQUEST,
                                    data={"success": False, "status_code": 400,
                                          "message": _("Account admin of this account does not exist")})

                with transaction.atomic():
                    if data["is_hq"] == "true" or data["is_hq"] is True:
                        account.is_active = True
                        account.save()

                    if data["is_subsidiaries"] == "true" or data["is_subsidiaries"] is True:
                        subsidiaries = Account.objects.filter(parents__contains=account.account_id)
                        no_subscription_subsidiary = []
                        for subsidiary in subsidiaries:
                            current_subsidiary_subscription = subsidiary.current_active_subscription
                            if current_subsidiary_subscription is None:
                                no_subscription_subsidiary.append(str(subsidiary.account_id))
                            else:
                                subsidiary.is_active = True
                                subsidiary.save()
                        if len(no_subscription_subsidiary) > 0:
                            concatenate_message = ', '.join(no_subscription_subsidiary)
                            raise ValueError

                        if to_account_admin is not None:
                            generate_user_notification(
                                action="Account Activation", to_user=to_account_admin, from_user=request.user,
                                number_of_users=account.max_user_subscriptions,
                                subscription_end_date=current_subscription.user_end_date)

            elif (data["is_active"] == "false" or data["is_active"] is False) and account.is_active is True:
                if data["is_hq"] == "true" or data["is_hq"] is True:
                    account.is_active = False
                    account.save()

                if data["is_subsidiaries"] == "true" or data["is_subsidiaries"] is True:
                    subsidiaries = Account.objects.filter(parents__contains=account.account_id)
                    for subsidiary in subsidiaries:
                        subsidiary.is_active = False
                        subsidiary.save()

                if to_account_admin is not None:
                    generate_user_notification(
                        action="Account Deactivation", to_user=to_account_admin, from_user=request.user,
                        phone_number="+145623409123")

            return Response(status=status.HTTP_200_OK,
                            data={"success": True,
                                  "data": AccountWritableSerializer(account,
                                                                    many=False).data})

        except ValueError as e:
            return Response({"success": False,
                             "message": _(
                                 "One or more subsidiary does not have subscriptions and cannot be activated. </br> Following accounts are '") + concatenate_message + "'."}
                            , status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"success": False, "message": e}
                            , status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                if not UserSubscription.objects.filter(account__slug=kwargs["slug"], is_active=True).exists():
                    UserSubscription.objects.filter(account__slug=kwargs["slug"]).delete()
                response = super().destroy(request, *args, **kwargs)
                return response

        except ProtectedError as e:
            return Response(status=status.HTTP_400_BAD_REQUEST,
                            data={"success": False, "status_code": 400,
                                  "message": _("Account can not be deleted because one or more ") + str(
                                      e.protected_objects.model.updated_by.field.opts.verbose_name_plural) + _(
                                      " exist.")})

    def get_serializer_context(self):
        context = super(AccountsViewSet, self).get_serializer_context()
        # context.update({
        #     "exclude_email_list": ['test@test.com', 'test1@test.com']
        #     # extra data
        # })
        return context

    @action(methods=['get'], detail=False)
    def list_accounts(self, request, *args, **kwargs):
        queryset = get_queryset_for_list(request.user)
        serializer = self.get_serializer(queryset, many=True)
        return Response(status=status.HTTP_200_OK,
                        data={"success": True, "results": serializer.data, "status_code": 200,
                              "message": "List of Accounts"})

    @action(methods=['get'], detail=False)
    def list_of_hqs(self, request, *args, **kwargs):
        accounts_hq = self.get_queryset().filter(account_type="hq")
        accounts_hq_subsidiary = self.get_queryset().filter(account_id__in=F('parent_account__account_id'))

        queryset = accounts_hq | accounts_hq_subsidiary
        queryset = self.filter_queryset(queryset)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(methods=['get'], detail=False)
    def list_of_subsidiaries(self, request, *args, **kwargs):
        account_id = request.query_params.get('account_id', None)
        queryset = self.filter_queryset(self.get_queryset())
        queryset_subsidiaries = queryset.filter(parent_account__account_id=account_id)
        return Response(status=status.HTTP_200_OK,
                        data={"success": True,
                              "data": AccountReadOnlySerializer(queryset_subsidiaries, many=True,
                                                                context={"is_hq": False}).data})

    @action(methods=['get'], detail=False)
    def acquiring_accounts(self, request, *args, **kwargs):
        account_slug = request.query_params.get('account', None)
        account = Account.objects.get(slug=account_slug)
        accounts = Account.objects.exclude(parents__contains=account.account_id).exclude(
            account_id__in=account.parents).exclude(slug=account_slug)

        return Response(status=status.HTTP_200_OK,
                        data={"success": True,
                              "data": AccountSimpleSerializer(accounts, many=True).data})

    @action(methods=['post'], detail=False)
    def account_acquisition(self, request, *args, **kwargs):
        data = request.data
        account_acquired = Account.objects.get(slug=data["account_acquired"])
        account_acquiring = Account.objects.get(slug=data["account_acquiring"])

        if account_acquiring.account_type == "sub":
            account_acquiring.account_type = "hq_sub"
        elif account_acquiring.account_type == "hq_sub":
            account_acquiring.account_type = "hq"

        subsidiaries = Account.objects.filter(parents__contains=account_acquired.account_id)
        if account_acquired.account_type == "hq" and len(subsidiaries) > 0:
            account_acquired.account_type = "hq_sub"
        elif account_acquired.account_type == "hq_sub" and len(subsidiaries) == 0:
            account_acquired.account_type = "sub"
        elif account_acquired.account_type == "hq" and len(subsidiaries) == 0:
            account_acquired.account_type = "sub"

        account_acquired.parent_account = account_acquiring

        parents = list()
        get_parent_accounts(account_acquired, parents)
        account_acquired.parents = parents

        account_acquired.save()
        account_acquiring.save()

        account_acquired_admin = User.objects.get(id=account_acquired.account_admin_id)
        account_acquiring_admin = User.objects.get(id=account_acquiring.account_admin_id)

        if account_acquired_admin is not None:
            generate_user_notification(
                action="Account Acquisition - Acquirer", to_user=account_acquired_admin, from_user=request.user,
                acquired_account=account_acquired.account_name, acquiring_account=account_acquiring.account_name)

        if account_acquiring_admin is not None:
            generate_user_notification(
                action="Account Acquisition - Acquiring", to_user=account_acquiring_admin, from_user=request.user,
                acquired_account=account_acquired.account_name, acquiring_account=account_acquiring.account_name)

        return Response(status=status.HTTP_200_OK,
                        data={"success": True,
                              "message": "Account acquired successfully"})

    @action(methods=['post'], detail=True)
    def create_subscription(self, request, *args, **kwargs):
        account = self.get_object()

        user_start_date = request.data.get('user_start_date')
        user_end_date = request.data.get('user_end_date')
        num_of_users = request.data.get('num_of_users')
        if num_of_users is None:
            num_of_users = 0
        # account = account.id
        user_sub = {'user_start_date': user_start_date, 'user_end_date': user_end_date, 'num_of_users': num_of_users,
                    'account': account.id, 'is_cancelled': False,
                    'is_active': True}
        serializer = UserSubscriptionSerializer(data=user_sub, context=self.get_serializer_context())
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            device_sub_start_date = datetime.datetime.strptime(user_start_date, '%d-%m-%Y').strftime('%Y-%m-%d')
            account.devices.all().update(sub_start_date=device_sub_start_date)

        return Response(status=status.HTTP_200_OK,
                        data={"success": True, "results": [], "status_code": 200,
                              "message": "Subscription Created"})

    @action(methods=['put'], detail=True)
    def update_subscription(self, request, *args, **kwargs):
        account = self.get_object()
        user_start_date = None
        user_end_date = None

        current_active_sub = account.current_active_subscription
        if current_active_sub is not None:
            user_start_date = current_active_sub.user_start_date
            user_end_date = current_active_sub.user_end_date
        else:
            raise ValidationError("Current subscription does not exist")

        num_of_users = request.data.get('num_of_users')
        if num_of_users is None:
            num_of_users = 0
        # account = account.id

        subscription = UserSubscription.objects.filter(account__id=account.id, is_active=True)
        if len(subscription) > 0:
            subscription[0].is_active = False
            subscription[0].save()

        user_sub = {'user_start_date': user_start_date, 'user_end_date': user_end_date, 'num_of_users': num_of_users,
                    'account': account.id, 'is_cancelled': False,
                    'is_active': True}
        serializer = UserSubscriptionSerializer(data=user_sub, context=self.get_serializer_context())
        if serializer.is_valid(raise_exception=True):
            serializer.save()

        return Response(status=status.HTTP_200_OK,
                        data={"success": True, "results": [], "status_code": 200,
                              "message": "Subscription Updated"})

    @action(methods=['post'], detail=True)
    def renew_subscription(self, request, *args, **kwargs):
        account = self.get_object()

        current_sub = None
        user_subscriptions = account.user_subscriptions.order_by('-created_on')
        current_date = datetime.date.today()
        for user_subscription in user_subscriptions:
            if user_subscription.user_start_date <= current_date <= user_subscription.user_end_date:
                current_sub = user_subscription

        user_start_date = current_sub.user_end_date + datetime.timedelta(days=1)
        user_end_date = request.data.get('user_end_date')
        num_of_users = request.data.get('num_of_users')
        if num_of_users is None:
            num_of_users = 0
        # account = account.id

        subscription = UserSubscription.objects.filter(account__id=account.id, is_active=True)
        if len(subscription) > 0:
            subscription[0].is_active = False
            subscription[0].save()

        user_sub = {'user_start_date': user_start_date, 'user_end_date': user_end_date, 'num_of_users': num_of_users,
                    'account': account.id, 'is_cancelled': False,
                    'is_active': True}
        serializer = UserSubscriptionSerializer(data=user_sub, context=self.get_serializer_context())
        if serializer.is_valid(raise_exception=True):
            serializer.save()

        return Response(status=status.HTTP_200_OK,
                        data={"success": True, "results": [], "status_code": 200,
                              "message": "Subscription Renewed"})

    @action(methods=['post'], detail=True)
    def cancel_subscription(self, request, *args, **kwargs):
        account = self.get_object()

        current_subscription = account.current_active_subscription
        if current_subscription is not None:
            current_subscription.is_cancelled = True
            current_subscription.is_active = False
            current_subscription.save()

            account = Account.objects.get(id=account.id)
            account.is_active = False
            account.save()

        return Response(status=status.HTTP_200_OK,
                        data={"success": True, "results": [], "status_code": 200,
                              "message": "Subscription Cancelled"})

    @action(["post"], detail=False)
    def bulk_create(self, request, *args, **kwargs):
        data = request.data
        hq_accounts = []
        hq_sub_accounts = []
        sub_accounts = []
        already_existing_accounts = []

        for account in data:
            if account['language'] == "English":
                account['language'] = "en"
            elif account['language'] == "Spanish":
                account['language'] = "es"
            elif account['language'] == "French":
                account['language'] = "fr"

        def already_exists(acc):
            return Account.objects.filter(account_id=acc['account_id']).count() > 0

        already_existing_accounts = [acc for acc in data if already_exists(acc)]
        new_accounts = [acc for acc in data if not already_exists(acc)]
        current_account = None
        for account in new_accounts:
            if account['account_type'] == 'Head Quarter':
                account['account_type'] = 'hq'
                hq_accounts.append(account)
            elif account['account_type'] == 'Subsidiary':
                account['account_type'] = 'sub'

                sub_accounts.append(account)
            elif account['account_type'] == 'Head Quarter / Subsidiary':
                account['account_type'] = 'hq_sub'
                hq_sub_accounts.append(account)
        try:
            with transaction.atomic():
                # serializer = AccountCreateSerializer(data=hq_accounts, many=True, context=self.get_serializer_context())
                # if serializer.is_valid(raise_exception=True):
                #     serializer.save()
                for hq_account in hq_accounts:
                    current_account = hq_account
                    logger.info("Account processed: " + str(hq_account['account_id']))
                    logger.info("Parent account processed: " + str(hq_account['parent_account']))
                    serializer = AccountCreateSerializer(data=hq_account, many=False,
                                                         context=self.get_serializer_context())
                    if serializer.is_valid(raise_exception=True):
                        serializer.save()

                for hq_sub_account in hq_sub_accounts:
                    current_account = hq_sub_account
                    if hq_sub_account['account_id'] == hq_sub_account['parent_account']:
                        logger.info("Account processed: " + str(hq_sub_account['account_id']))
                        logger.info("Parent account processed: " + str(hq_sub_account['parent_account']))
                        hq_sub_account['parent_account'] = None
                        serializer = AccountCreateSerializer(data=hq_sub_account, many=False,
                                                             context=self.get_serializer_context())
                        if serializer.is_valid(raise_exception=True):
                            serializer.save()
                    else:
                        logger.info("Account processed: " + str(hq_sub_account['account_id']))
                        logger.info("Parent account processed: " + str(hq_sub_account['parent_account']))
                        hq_sub_account['parent_account'] = Account.objects.get(
                            account_id=hq_sub_account['parent_account']).slug

                        serializer = AccountCreateSerializer(data=hq_sub_account, many=False,
                                                             context=self.get_serializer_context())
                        if serializer.is_valid(raise_exception=True):
                            serializer.save()

                for sub_account in sub_accounts:
                    current_account = sub_account
                    logger.info("Account processed: " + str(sub_account['account_id']))
                    logger.info("Parent account processed: " + str(sub_account['parent_account']))
                    sub_account['parent_account'] = Account.objects.get(account_id=sub_account['parent_account']).slug

                    serializer = AccountCreateSerializer(data=sub_account, many=False,
                                                         context=self.get_serializer_context())
                    if serializer.is_valid(raise_exception=True):
                        serializer.save()

            return Response(status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(e)
            raise ParseError(detail="Error importing account with account number " + current_account["account_id"])

    @action(methods=['patch'], detail=True)
    def set_domain(self, request, *args, **kwargs):
        account = Account.objects.get(slug=kwargs['slug'])
        data = request.data
        if data['domain'] is None or data['domain'] == '':
            pass
        else:
            regex = compile('(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]')
            domain = regex.match(data['domain'])
            if not domain:
                return Response(status=status.HTTP_400_BAD_REQUEST,
                                data={"success": False,
                                      "message": "Unable to parse domain, might not be valid", })
            else:
                if not account.domain:
                    account.domain = data['domain']
                    account.save()
                    message = "Domain updated successfully"
                else:
                    message = "Domain already exists"
                return Response(status=status.HTTP_200_OK,
                                data={"success": True,
                                      "message": message})

    @action(["get"], detail=True)
    def case_user_list(self, request, *args, **kwargs):

        if Account.objects.filter(slug=kwargs["slug"]).exists():
            account = Account.objects.get(slug=kwargs["slug"])
        else:
            case = Case.objects.get(patient__slug=kwargs["slug"])
            account = case.account

        # Account users
        account_users = account.users.all()

        # Subsidiary accounts users
        subsidiary_account_users = User.objects.none()
        subsidiary_account_list = Account.objects.filter(parents__contains=account.account_id)
        for subsidiary_account in subsidiary_account_list:
            subsidiary_account_users = subsidiary_account_users | subsidiary_account.users.all()

        # HQ accounts users
        hq_account_users = User.objects.none()
        if account.parent_account:
            hq_account_users = account.parent_account.users.all()

        # Associated accounts users
        associated_account_list = Account.objects.none()
        associated_account_users = User.objects.none()
        to_account_association = account.to_account.filter(accepted=True).all()
        from_account_association = account.from_account.filter(accepted=True).all()

        for acc in to_account_association:
            associated_account_list = associated_account_list | Account.objects.filter(id=acc.from_account.id)

        for acc in from_account_association:
            associated_account_list = associated_account_list | Account.objects.filter(id=acc.to_account.id)

        for associated_account in associated_account_list:
            associated_account_users = associated_account_users | associated_account.users.all()

        # Associated contact users
        associated_contact_list_of_slugs = []
        contact_association = account.account_associated_contact.filter(accepted=True).all()
        for contact in contact_association:
            associated_contact_list_of_slugs.append(contact.from_user.slug)

        associated_contact_users = User.objects.filter(slug__in=associated_contact_list_of_slugs)

        # return all users
        all_users = account_users | subsidiary_account_users | hq_account_users | associated_account_users | associated_contact_users

        return Response(status=status.HTTP_200_OK,
                        data={"success": True,
                              "data": UserSummarySerializer(all_users, many=True).data})

    @action(["get"], detail=True)
    def get_subscription(self, request, *args, **kwargs):
        self.check_object_permissions(request, self.get_object())
        account = Account.objects.get(slug=kwargs["slug"])
        current_active_subscription = account.current_active_subscription
        serializer = UserSubscriptionReadOnlySerializer(current_active_subscription)

        return Response(status=status.HTTP_200_OK, data={"success": True, "data": serializer.data})


class AccountAssociationViewSet(BaseViewset):
    queryset = AssociatedAccounts.objects.prefetch_related(
        'from_account').prefetch_related('to_account').all()

    lookup_field = 'slug'
    action_serializers = {
        'default': AssociatedAccountsSerializer,
        'create': AssociatedAccountsWritableSerializer,
        'associated': AssociatedSerializer,
    }

    def get_permissions(self):
        if self.action == "account_associate_request":
            self.permission_classes = [CanRequestAdminToAssociate]
        else:
            self.permission_classes = [CanAssociateToAccounts]
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        association = serializer.create(serializer.validated_data)
        to_account = Account.objects.get(slug=request.data['to_account'])
        if to_account.account_admin_id is None:
            raise ValidationError('Account Admin of {0} does not exist'.format(to_account.account_name))

        to_account_admin = User.objects.get(id=to_account.account_admin_id)
        from_account = Account.objects.get(slug=request.data['from_account'])
        from_account_admin = User.objects.get(id=from_account.account_admin_id)

        context_data = {'association': association.slug, 'link_name': from_account.account_name,
                        'account_slug': from_account.slug}

        generate_user_notification(
            action='Account Association Request', to_user=to_account_admin, from_user=request.user,
            from_user_name=request.user.name, from_account_name=from_account.account_name,
            to_account_name=to_account.account_name, link=from_account.slug, context_data=context_data
        )

        return Response(status=status.HTTP_200_OK,
                        data={"success": True, "status_code": 200, "message": "Account Associated"})

    def destroy(self, request, *args, **kwargs):
        requesting_user_account_id = request.user.account.account_id
        association = self.get_object()
        association_action = None

        if association.from_account.account_id == requesting_user_account_id:
            to_account = association.to_account
            to_account_admin = User.objects.get(id=to_account.account_admin_id)
            from_account = association.from_account
            from_account_admin = User.objects.get(id=from_account.account_admin_id)

            if not association.accepted:
                association_action = 'Account Association Revoked'

            else:
                association_action = 'Account Dissociated'
                generate_account_notification.delay(
                    action='Account Dissociated', to_account_id=request.user.account.id, from_user_id=request.user.id,
                    from_account_name=to_account.account_name, to_account_name=from_account.account_name,
                    from_user_name=request.user.name
                )

                generate_account_notification.delay(
                    action='Account Dissociated', to_account_id=association.to_account.id,
                    from_user_id=request.user.id,
                    from_account_name=from_account.account_name, to_account_name=to_account.account_name,
                    from_user_name=request.user.name
                )

        elif association.to_account.account_id == requesting_user_account_id:
            to_account = association.from_account
            to_account_admin = User.objects.get(id=to_account.account_admin_id)
            from_account = association.to_account
            from_account_admin = User.objects.get(id=from_account.account_admin_id)

            if not association.accepted:
                association_action = 'Account Association Rejected'
            else:
                association_action = 'Account Dissociated'
                generate_account_notification.delay(
                    action='Account Dissociated', to_account_id=request.user.account.id, from_user_id=request.user.id,
                    from_account_name=from_account.account_name, to_account_name=to_account.account_name,
                    from_user_name=request.user.name
                )

                generate_account_notification.delay(
                    action='Account Dissociated', to_account_id=association.from_account.id,
                    from_user_id=request.user.id,
                    from_account_name=from_account.account_name, to_account_name=to_account.account_name,
                    from_user_name=request.user.name
                )

        if association_action == 'Account Association Rejected':
            generate_user_notification(
                action=association_action, to_user=to_account_admin, from_user=request.user,
                to_account_name=from_account.account_name, to_user_name=from_account.account_admin
            )
        elif association_action == 'Account Association Revoked':
            generate_user_notification(
                action=association_action, to_user=to_account_admin, from_user=request.user,
                from_account_name=from_account.account_name, from_user_name=from_account.account_admin
            )

        return super().destroy(request, args, kwargs)

    def partial_update(self, request, *args, **kwargs):
        association = self.get_object()
        # Association request was from this account, so send notification that it has been accepted
        to_account = association.from_account
        # This account accepted the association, this will be the one sending the acceptance
        from_account = association.to_account

        to_account_admin = User.objects.get(id=to_account.account_admin_id)
        from_account_admin = User.objects.get(id=from_account.account_admin_id)

        context_data = {'association': association.slug, 'link_name': from_account.account_name,
                        'account_slug': from_account.slug}

        generate_user_notification(
            action='Account Association Accepted', to_user=to_account_admin, from_user=request.user,
            to_user_name=from_account.account_admin, to_account_name=from_account.account_name,
            link=from_account.slug, context_data=context_data
        )

        context_data = {'association': association.slug, 'link_name': to_account.account_name,
                        'account_slug': to_account.slug}

        generate_account_notification.delay(
            action='Account Associated', to_account_id=request.user.account.id, from_user_id=request.user.id,
            from_account_name=from_account.account_name, to_account_name=to_account.account_name,
            link=to_account.slug, context_data=context_data
        )

        context_data = {'association': association.slug, 'link_name': from_account.account_name,
                        'account_slug': from_account.slug}

        generate_account_notification.delay(
            action='Account Associated', to_account_id=association.from_account.id,
            from_user_id=to_account.account_admin_id,
            from_account_name=to_account.account_name, to_account_name=from_account.account_name,
            link=from_account.slug, context_data=context_data
        )

        return super().partial_update(request, args, kwargs)

    @action(methods=['post'], detail=False)
    def account_associate_request(self, request, *args, **kwargs):
        data = request.data
        user = request.user
        from_account = Account.objects.get(slug=data["from_account"])

        account_admin = User.objects.get(id=user.account.account_admin_id)

        if account_admin is not None:
            context_data = {'link_name': from_account.account_name, 'account_slug': from_account.slug}
            generate_user_notification(
                action="Account Association Request to Admin", to_user=account_admin, from_user=user,
                from_user_name=user.name, from_account_name=from_account.account_name,
                to_account_name=user.account.account_name, link=from_account.slug, context_data=context_data)

        return Response(status=status.HTTP_200_OK,
                        data={"success": True,
                              "message": "Account association request to admin send successfully"})

    # @action(methods=['GET'], detail=False)
    # def associated(self, request, *args, **kwargs):
    #     account_slug = kwargs.get('slug', None)
    #     if not account_slug:
    #         account_slug = request.user.account.slug
    #         # raise ValidationError("Request missing kwargs")
    #     associated_accounts = self.queryset.filter(
    #         Q(to_account__slug=account_slug) | Q(from_account__slug=account_slug))
    #     accounts = []
    #     for associated_account in associated_accounts:
    #         association = {}
    #         if associated_account.from_account.slug == account_slug:
    #             association['account'] = associated_account.to_account
    #             association["type"] = "sent"
    #         else:
    #             association['account'] = associated_account.from_account
    #             association["type"] = "received"
    #         association["accepted"] = associated_account.accepted
    #         association["slug"] = associated_account.slug
    #         accounts.append(association)
    #
    #     serializer = AssociatedSerializer(accounts, many=True)
    #     data = {'result': serializer.data}
    #     return Response(status=status.HTTP_200_OK,
    #                     data={"success": True, "data": data, "status_code": 200,
    #                           "message": "List of Accounts"})


class AssociatedAccountsViewset(BaseViewset):
    queryset = Account.objects.all()
    lookup_field = 'slug'
    action_serializers = {
        'default': AccountSerializer,
    }

    def get_queryset(self):
        account_slug = self.request.user.account.slug
        if not account_slug:
            raise ValidationError("Request missing account")
        current_account = Account.objects.get(slug=account_slug)
        associated_accounts = current_account.associated_accounts.all()

        associated_accounts_from = AssociatedAccounts.objects.filter(to_account_id=current_account.id).all()
        for acc in associated_accounts_from:
            associated_accounts |= Account.objects.filter(slug=acc.from_account.slug)
        # associated_accounts = Account.object.filter()
        accounts = []
        # for associated_account in associated_accounts:
        #     association = {}
        #     if associated_account.from_account.slug == account_slug:
        #         association['account'] = associated_account.to_account
        #         association["type"] = "sent"
        #     else:
        #         association['account'] = associated_account.from_account
        #         association["type"] = "received"
        #     association["accepted"] = associated_account.accepted
        #     association["slug"] = associated_account.slug
        #     accounts.append(association)
        #
        # serializer = AssociatedSerializer(accounts, many=True)
        # data = {'result': serializer.data}
        return associated_accounts


class SubsidiaryAccountsViewset(BaseViewset):
    queryset = Account.objects.all()
    lookup_field = 'slug'
    action_serializers = {
        'default': AccountSerializer,
    }

    def get_queryset(self):
        account_slug = self.request.user.account.slug
        if not account_slug:
            raise ValidationError("Request missing account")
        current_account = Account.objects.get(slug=account_slug)
        return Account.objects.filter(parents__contains=current_account.account_id)

    # def list(self, request, *args, **kwargs):
    #     user = request.user
    #     if hasattr(user, 'account'):


class AccountUploadViewSet(BaseViewset):
    queryset = AccountUpload.objects.order_by('created_on').all()
    lookup_field = 'id'
    action_serializers = {
        'default': AccountUploadSerializer,
        'create': AccountUploadWritableSerializer,

    }

    def get_serializer_context(self):
        context = super(AccountUploadViewSet, self).get_serializer_context()
        # context.update({
        #     "exclude_email_list": ['test@test.com', 'test1@test.com']
        #     # extra data
        # })
        return context

    def create(self, request, *args, **kwargs):
        file = request.FILES['upload']
        temp_file, temp_path = mkstemp()
        with open(temp_path, 'wb') as f:
            f.write(file.read())
        filename = file.name
        response = super().create(request, args, kwargs)
        account_upload_id = response.data['data']['id']
        AccountUploadItems.objects.filter(is_imported=False).delete()
        self.parse_file(temp_file, filename, account_upload_id, temp_path)
        os.close(temp_file)
        return response

    def parse_data(self, row, account_ids, account_upload_id, duplicate_account_ids, hq_account_ids, current_column):
        row_errors = {'error_detail': list()}
        current_column = "account_number"
        if row['account_number'] is None or row['account_number'] == '':
            row_errors['data_missing'] = True
            row_errors['error_detail'].append("Account number missing")
        else:
            if Account.objects.filter(account_id=row['account_number']).count() > 0:
                row_errors['account_already_exists'] = True
                row_errors['error_detail'].append("Account with this account number already exists")
                # row["slug"] = Account.objects.filter(account_id=row['account_number']).values('slug')
            if row['account_number'] in duplicate_account_ids:
                row_errors['dublicate_entry'] = True
                row_errors['error_detail'].append("Duplicate entry")
            else:
                duplicate_account_ids.append(row['account_number'])

            if len(row["account_number"]) > 12:
                row_errors['error_detail'].append("Account Number cannot be more than 12 characters")

        # account_name
        current_column = "account_name"
        if row['account_name'] is None or row['account_name'] == '':
            row_errors['data_missing'] = True
            row_errors['error_detail'].append("Account name missing")
        else:
            if len(row['account_name']) > 255:
                row_errors['error_detail'].append("Account name length greater than 255")

        # country
        current_column = "country"
        if row['country'] is None or row['country'] == '':
            pass
        else:
            row['country'] = abbrev_country[row['country']].title()
        # state
        current_column = "state"
        if row['state'] is None or row['state'] == '':
            pass
        else:
            if row['country'] == 'United States':
                try:
                    row['state'] = abbrev_us_state[row['state']]
                except Exception as e:
                    row_errors['data_missing'] = True
                    row_errors['error_detail'].append("Unable to parse state data")

        # city
        current_column = "city"
        if row['city'] is None or row['city'] == '':
            pass

        # zipcode
        current_column = "zipcode"
        if row['zipcode'] is None or row['zipcode'] == '':
            pass

        # phone1
        current_column = "phone1"
        if row['phone1'] is None or row['phone1'] == '':
            pass
        else:
            if len(row['phone1']) > 23:
                row_errors['phone_number_error'] = True
                row_errors['error_detail'].append("Could not parse phone1")
                row['phone1'] = row['phone1'][0:23]
            else:
                try:
                    regex = compile(
                        '(?P<country>[0-9]{0,3})\s{0,1}\((?P<city>[0-9]{3})\)\s{1}(?P<first>[0-9]{3})[-]{1}(?P<second>[0-9]{4})\s{0,1}[x]{0,1}\s{0,1}(?P<ext>[0-9]{0,6})')
                    phone1 = regex.fullmatch(row['phone1'])
                    if not phone1:
                        row_errors['phone_number_error'] = True
                        row_errors['error_detail'].append("Could not parse phone2")
                    country_code = phone1.group('country')
                    city_code = phone1.group('city')
                    first_part = phone1.group('first')
                    second_part = phone1.group('second')
                    ext = phone1.group('ext')
                    row["phone1_ext"] = ext

                    if country_code == "" and row['country'] == "United States":
                        country_code = '+1'
                        row['phone1'] = country_code + city_code + first_part + second_part
                    elif country_code == "" and row['country'] != "United States":
                        row_errors['phone_number_error'] = True
                        row_errors['error_detail'].append("Country code not provided in Phone1")
                    elif country_code != "":
                        row['phone1'] = country_code + city_code + first_part + second_part

                except Exception as e:
                    row_errors['phone_number_error'] = True
                    row_errors['error_detail'].append("Unable to parse phone1")

        # phone2
        current_column = "phone2"
        if row['phone2'] is None or row['phone2'] == '':
            pass
        elif row['phone2'] is not None and row['phone2'] != '':
            if len(row['phone2']) > 23:
                row_errors['phone_number_error'] = True
                row_errors['error_detail'].append("Could not parse phone2")
                row['phone2'] = row['phone2'][0:23]
            try:
                regex = compile(
                    '(?P<country>[0-9]{0,3})\s{0,1}\((?P<city>[0-9]{3})\)\s{1}(?P<first>[0-9]{3})[-]{1}(?P<second>[0-9]{4})\s{0,1}[x]{0,1}\s{0,1}(?P<ext>[0-9]{0,6})')
                phone2 = regex.fullmatch(row['phone2'])
                if not phone2:
                    row_errors['phone_number_error'] = True
                    row_errors['error_detail'].append("Could not parse phone2")
                country_code = phone2.group('country')
                city_code = phone2.group('city')
                first_part = phone2.group('first')
                second_part = phone2.group('second')
                ext = phone2.group('ext')
                row["phone2_ext"] = ext

                if country_code == "" and row['country'] == "United States":
                    country_code = '+1'
                    row['phone2'] = country_code + city_code + first_part + second_part
                elif country_code == "" and row['country'] != "United States":
                    row_errors['phone_number_error'] = True
                    row_errors['error_detail'].append("Country code not provided in Phone2")
                elif country_code != "":
                    row['phone2'] = country_code + city_code + first_part + second_part

            except Exception as e:
                row_errors['phone_number_error'] = True
                row_errors['error_detail'].append("Unable to parse phone2")

        # address1
        current_column = "address1"
        if row['address1'] is None or row['address1'] == '':
            pass

        # domain
        current_column = "address2"
        if row['domain'] is None or row['domain'] == '':
            pass
            # Domain is longer required when importing accounts or creating it manually
            # row_errors['data_missing'] = True
            # row_errors['error_detail'].append("Domain missing")

        else:
            regex = compile('(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]')
            domain = regex.match(row['domain'])
            if not domain:
                row_errors['domain_error'] = True
                row_errors['error_detail'].append("Unable to parse domain, might not be valid")

        # hq_account_id
        current_column = "hq_account_number"
        if row['hq_account_number'] is None or row['hq_account_number'] == '':
            row['account_type'] = 'Head Quarter'
        else:
            p_acc = Account.objects.filter(parent_account__account_id=row['account_number']).count() > 0
            p_acc_in_file = [x for x in hq_account_ids if row['account_number'] == x]
            if p_acc or p_acc_in_file:
                row['account_type'] = 'Head Quarter / Subsidiary'
            else:
                row['account_type'] = 'Subsidiary'

        # hq_account_id
        if (row['hq_account_number'] is None or row['hq_account_number'] == '') \
            and (row['account_type'] == "Subsidiary" or row["account_type"] == "Head Quarter / Subsidiary"):
            row_errors['data_missing'] = True
            row_errors['error_detail'].append("Headquarter account number missing")
        else:
            if row['account_type'] == "Subsidiary" or row["account_type"] == "Head Quarter / Subsidiary":
                parent_account = Account.objects.filter(parent_account__account_id=row['hq_account_number'])
                parent_account_in_file = [x for x in account_ids if row['hq_account_number'] == x]
                if not parent_account and not parent_account_in_file:
                    row_errors["hq_account_does_not_exist"] = True
                    row_errors['error_detail'].append("Headquarter account does not exist in database or file")

        # no_of_usr_subs
        current_column = "no_of_usr_subs"
        if row['no_of_usr_subs'] is None or row['no_of_usr_subs'] == '':
            row_errors['data_missing'] = True
            row_errors['error_detail'].append("User subscription missing, enter 0 if there are none")

        # user_sub_start_date
        current_column = "sub_start_date"
        if row['sub_start_date'] is None or row['sub_start_date'] == '':
            row['sub_start_date'] = None
        else:
            if not type(row['sub_start_date']) == datetime.date:
                try:
                    row['sub_start_date'] = try_parsing_date(row['sub_start_date']).date()
                except Exception:
                    row_errors["data_missing"] = True
                    row_errors['error_detail'].append("Unable to parse subscription start date")

        # user_sub_end_date
        current_column = "sub_end_date"
        if row['sub_end_date'] is None or row['sub_end_date'] == '':
            row['sub_end_date'] = None
        else:
            try:
                if not type(row['sub_end_date']) == datetime.date:
                    row['sub_end_date'] = try_parsing_date(row['sub_end_date']).date()
                if row['sub_start_date'] > row['sub_end_date']:
                    row_errors['data_missing'] = True
                    row_errors['error_detail'].append("Subscription end date cannot be less than start date")
            except Exception:
                row_errors['data_missing'] = True
                row_errors['error_detail'].append("Unable to parse subscription end date")

        if (row['sub_start_date'] is None) and (row['sub_end_date'] is not None):
            row_errors["data_missing"] = True
            row_errors['error_detail'].append("Subscription end date is missing")

        if (row['sub_start_date'] is not None) and (row['sub_end_date'] is None):
            row_errors["data_missing"] = True
            row_errors['error_detail'].append("Subscription start date is missing")

        # language
        current_column = "language"
        if row['language'] is None or row['language'] == '':
            row_errors['data_missing'] = True
            row_errors['error_detail'].append("Language missing")
        else:
            if row['language'] == "English":
                row['language_code'] = "en"
            elif row['language'] == "Spanish":
                row['language_code'] = "es"
            elif row['language'] == "French":
                row['language_code'] = "fr"
            else:
                row_errors['data_missing'] = True
                row_errors['error_detail'].append("Unable to parse language")

        row["account_upload"] = account_upload_id
        row["errors"] = row_errors
        return row, current_column

    def parse_file(self, file, filename, account_upload_id, temp_path):
        ext = filename.split('.')[-1]
        imported_rows = []
        account_ids = []
        hq_account_ids = []
        duplicate_account_ids = []
        current_column = None
        try:
            if (ext == 'csv'):
                fields = [field for field in ACCOUNT_IMPORT_DICTIONARY.keys()]
                with open(temp_path, encoding='utf-8') as file_data:
                    reader = csv.DictReader(
                        file_data, fieldnames=fields, delimiter=',')
                    next(reader)
                    for row in reader:
                        account_ids.append(row['account_number'])
                        if row['hq_account_number'] is not None or row['hq_account_number'] != '':
                            hq_account_ids.append(row['hq_account_number'])

                with open(temp_path, encoding='utf-8') as file_data:
                    reader = csv.DictReader(
                        file_data, fieldnames=fields, delimiter=',')
                    next(reader)
                    for row in reader:
                        parsed_data, current_column = self.parse_data(
                            row, account_ids, account_upload_id, duplicate_account_ids, hq_account_ids, current_column)
                        imported_rows.append(parsed_data)

            elif (ext in ('xlsx',)):
                book = open_workbook(temp_path)
                sheet = book.sheet_by_index(0)
                keys = [sheet.cell(
                    0, col_index).value for col_index in range(sheet.ncols)]
                for row_index in range(1, sheet.nrows):
                    d = {keys[col_index]: sheet.cell(row_index, col_index).value
                         for col_index in range(sheet.ncols)}
                    for col_index in range(sheet.ncols):
                        cell = sheet.cell(row_index, col_index)
                        val = cell.value
                        if cell.ctype in (2,) and int(val) == val:
                            val = int(val)
                        elif cell.ctype in (3,):
                            val = datetime.datetime(*xldate_as_tuple(val, book.datemode)).date()
                        elif cell.ctype in (4,) and repr(val) == val:
                            val = repr(val)
                        d[keys[col_index]] = val
                    d = self.parse_data(d, serial_numbers, device_upload_id, duplicate_account_ids, [])
                    imported_rows.append(d)

            account_upload_items = AccountUploadItemSerializer(
                data=imported_rows, many=True, context=self.get_serializer_context())
            if account_upload_items.is_valid(raise_exception=True):
                account_upload_items.save()
        except KeyError as key_error:
            raise ParseError(
                detail="Error in row with account number " + row["account_number"] + ", unable to parse " + str(
                    key_error))
        except Exception as e:
            raise ParseError(
                detail="Error in row with account number " + row["account_number"] + ", unable to parse key " + str(
                    current_column))


class AccountUploadItemsViewSet(BaseViewset):
    queryset = AccountUploadItems.objects.all()
    lookup_field = 'slug'
    action_serializers = {
        'default': AccountUploadItemSerializer,

    }


class ContactAssociationViewSet(BaseViewset):
    queryset = AssociatedContacts.objects.prefetch_related(
        'from_user').prefetch_related('to_account').all()

    lookup_field = 'slug'
    action_serializers = {
        'default': AssociatedContactsSerializer,
        'create': AssociatedContactsWritableSerializer
    }

    def get_permissions(self):
        if self.action == "contact_associate_request":
            self.permission_classes = [CanRequestAdminToAssociate]
        elif self.action == "contact_associate_invite":
            self.permission_classes = [CanInviteContact]
        else:
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        data = request.data
        to_account = Account.objects.get(slug=request.data['to_account'])
        if to_account.account_admin_id is None:
            raise ValidationError('Account Admin of {0} does not exist'.format(to_account.account_name))

        to_account_admin = User.objects.get(id=to_account.account_admin_id)
        from_user = User.objects.get(slug=request.data['from_user'])

        if from_user.user_type != "Contact":
            raise ValidationError('User type is not contact')

        with transaction.atomic():
            contact_serializer = AssociatedContactsWritableSerializer(data=data,
                                                                      context=self.get_serializer_context())
            if contact_serializer.is_valid(raise_exception=True):
                contact_serializer_data = contact_serializer.validated_data
                contact_serializer.save()

        context_data = {'link_name': from_user.name, 'user_slug': from_user.slug}

        generate_user_notification(
            action='Contact Association Request', to_user=to_account_admin, from_user=request.user,
            from_user_name=from_user.name,
            to_account_name=to_account.account_name, link=from_user.slug, context_data=context_data
        )

        return Response(status=status.HTTP_200_OK,
                        data={"success": True, "status_code": 200, "message": "Account Associated"})

    def destroy(self, request, *args, **kwargs):
        association = self.get_object()
        from_user = association.from_user
        to_account = association.to_account
        to_account_admin = User.objects.get(id=to_account.account_admin_id)

        if not association.accepted:
            if self.request.user.id == to_account.account_admin_id:
                generate_user_notification(
                    action='Contact Association Rejected', to_user=from_user, from_user=request.user,
                    to_account_name=to_account.account_name, to_user_name=from_user.name
                )
            elif self.request.user.id == from_user.id:
                generate_user_notification(
                    action='Contact Association Revoked', to_user=to_account_admin, from_user=request.user,
                    from_user_name=from_user.name
                )
        else:
            generate_account_notification.delay(
                action='Contact Dissociated', to_account_id=to_account.id, from_user_id=request.user.id,
                to_account_name=to_account.account_name,
                from_user_name=from_user.name
            )

            generate_user_notification(
                action='Contact Dissociated', to_user=from_user, from_user=request.user,
                to_account_name=to_account.account_name
            )

        return super().destroy(request, args, kwargs)

    def partial_update(self, request, *args, **kwargs):
        association = self.get_object()
        to_account = association.to_account
        from_user = association.from_user

        to_account_admin = User.objects.get(id=to_account.account_admin_id)

        generate_user_notification(
            action='Contact Association Accepted', to_user=from_user, from_user=request.user,
            to_user_name=from_user.name, to_account_name=to_account.account_name
        )

        generate_account_notification.delay(
            action='Contact Associated', to_account_id=to_account_admin.id, from_user_id=request.user.id,
            from_user_name=from_user.name, to_account_name=to_account.account_name
        )

        return super().partial_update(request, args, kwargs)

    @action(methods=['post'], detail=False)
    def contact_associate_request(self, request, *args, **kwargs):
        data = request.data
        user = request.user
        to_user = User.objects.get(slug=data["to_user"])

        account_admin = User.objects.get(id=user.account.account_admin_id)

        if account_admin is not None:
            context_data = {'link_name': to_user.name, 'user_slug': to_user.slug}
            generate_user_notification(
                action="Contact Association Request to Admin", to_user=account_admin, from_user=user,
                from_user_name=user.name, to_user_name=to_user.name,
                to_account_name=user.account.account_name, link=to_user.slug, context_data=context_data)

        return Response(status=status.HTTP_200_OK,
                        data={"success": True,
                              "message": "Contact association request to admin send successfully"})

    @action(methods=['post'], detail=False)
    def contact_associate_invite(self, request, *args, **kwargs):
        data = request.data
        user = request.user
        to_user = User.objects.get(slug=data["to_user"])

        account_admin = User.objects.get(id=user.account.account_admin_id)

        if account_admin is not None:
            context_data = {'link_name': to_user.name, 'user_slug': to_user.slug}
            generate_user_notification(
                action="Contact Association Invite", to_user=to_user, from_user=user,
                from_user_name=user.name, to_account_name=user.account.account_name, link=to_user.slug,
                context_data=context_data)

        return Response(status=status.HTTP_200_OK,
                        data={"success": True,
                              "message": "Contact association invite send successfully"})

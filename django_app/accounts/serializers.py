from django.db import transaction
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from .models import Account, AssociatedAccounts, AccountUpload, AccountUploadItems, AssociatedContacts
from .models import DeviceSubscription, UserSubscription
from django_synergy.utils.serializers.base import BaseSerializer
from django_synergy.users.serializers import UserCreateSerializer, UserSerializer
from django_synergy.users.models import User
from django_synergy.devices.serializers import DeviceCreateSerializer
from datetime import date
from django.db.models import Q, F


class DropDownAccountSerializer(BaseSerializer):
    class Meta:
        model = Account
        fields = ('account_id', 'account_name', 'slug', 'domain', 'account_type', 'language', 'is_active')


# used for relationships
class MinifiedAccountSerializer(BaseSerializer):
    parent_account = serializers.SlugRelatedField(
        slug_field='account_id', read_only=True)
    account_admin = serializers.CharField()
    account_type = serializers.SerializerMethodField()
    parent_account_number = serializers.SerializerMethodField()

    def get_account_type(self, obj):
        return obj.get_account_type_display()

    def get_parent_account_number(self, obj):
        if obj.parent_account:
            return obj.parent_account.account_id
        else:
            return None

    class Meta:
        model = Account
        fields = (
            "account_id",
            "slug",
            "parent_account",
            "account_name",
            "account_admin",
            "parent_account_number",
            "account_type"
        )


# default serilizer


class DeviceSubscriptionSerializer(BaseSerializer):
    device_start_date = serializers.DateField(required=False)

    class Meta:
        model = DeviceSubscription
        fields = (
            'device_end_date',
            'device_start_date',
            'account',
        )
        lookup_field = 'slug'


class UserSubscriptionSerializer(BaseSerializer):
    user_start_date = serializers.DateField(required=False, allow_null=True)
    user_end_date = serializers.DateField(required=False, allow_null=True)
    num_of_users = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = UserSubscription
        fields = (
            'user_start_date',
            'user_end_date',
            'num_of_users',
            'account',
            'is_cancelled',
            'is_active'
        )
        lookup_field = 'slug'


class UserSubscriptionReadOnlySerializer(BaseSerializer):
    user_start_date = serializers.DateField(required=False, allow_null=True)
    user_end_date = serializers.DateField(required=False, allow_null=True)
    num_of_users = serializers.IntegerField(required=False, allow_null=True)
    num_device_subscriptions = serializers.SerializerMethodField()
    num_user_subscriptions = serializers.SerializerMethodField()
    max_user_subscriptions = serializers.SerializerMethodField()

    def get_num_device_subscriptions(self, obj):
        return obj.account.num_device_subscriptions

    def get_num_user_subscriptions(self, obj):
        return obj.account.num_user_subscriptions

    def get_max_user_subscriptions(self, obj):
        return obj.account.max_user_subscriptions

    class Meta:
        model = UserSubscription
        exclude = ['created_on', 'updated_on', 'created_by', 'updated_by', 'id', 'slug']


class AssociatedContactsSerializer(BaseSerializer):
    from_user = serializers.SlugRelatedField(
        slug_field="slug", read_only=True)
    to_account = serializers.SlugRelatedField(
        slug_field="slug", read_only=True)

    class Meta:
        model = AssociatedContacts
        fields = ('from_user', 'to_account', 'accepted', 'slug')


class AccountSerializer(BaseSerializer):
    parent_account = MinifiedAccountSerializer()
    account_admin = serializers.CharField()
    account_type = serializers.SerializerMethodField()
    subsidiaries = serializers.SerializerMethodField()
    user_subscriptions = serializers.SerializerMethodField()
    associated_accounts = serializers.SerializerMethodField()
    device_subscriptions = DeviceSubscriptionSerializer(
        many=True, read_only=True)
    account_associated_contact = AssociatedContactsSerializer(many=True, read_only=True)

    def get_account_type(self, obj):
        return obj.get_account_type_display()

    def get_subsidiaries(self, obj):
        queryset = Account.objects.filter(parents__contains=obj.account_id)
        return AccountWritableSerializer(queryset, many=True).data

    def get_user_subscriptions(self, obj):
        if self.context["request"].user.is_superuser:
            current_active_subscription = obj.current_active_subscription
            serializer = UserSubscriptionReadOnlySerializer(current_active_subscription)
            return serializer.data
        else:
            return None

    def get_associated_accounts(self, obj):
        list_of_associated_accounts = []
        association_requests_sent = list(obj.to_account.all())
        association_request_recieved = list(obj.from_account.all())

        for account in association_requests_sent:
            list_of_associated_accounts.append({
                "account_id": account.from_account.account_id,
                "account_name": account.from_account.account_name,
                "slug": account.slug,
                "accepted": account.accepted,
                "type": "sent"

            })
        for account in association_request_recieved:
            list_of_associated_accounts.append({
                "account_id": account.to_account.account_id,
                "account_name": account.to_account.account_name,
                "slug": account.slug,
                "accepted": account.accepted,
                "type": "received"
            })

        return list_of_associated_accounts

    class Meta:
        model = Account
        fields = (
            "parent_account",
            "account_admin",
            "account_type",
            "account_id",
            "slug",
            "account_name",
            "city",
            "state",
            "country",
            "zipcode",
            "phone1",
            "phone2",
            "address1",
            "address2",
            "address3",
            "domain",
            "user_subscriptions",
            "device_subscriptions",
            "associated_accounts",
            "parents",
            "is_active",
            "subsidiaries",
            "account_associated_contact"
        )
        lookup_field = 'slug'


class AccountSimpleSerializer(BaseSerializer):
    class Meta:
        model = Account
        fields = ('account_id', 'slug', 'account_name', 'account_type', 'parents')
        lookup_field = 'slug'


class AccountReadOnlySerializer(BaseSerializer):
    parent_account = MinifiedAccountSerializer()
    account_admin = serializers.CharField()
    account_type = serializers.SerializerMethodField()
    associated_accounts = serializers.SerializerMethodField()
    device_subscriptions = DeviceSubscriptionSerializer(
        many=True, read_only=True)
    user_subscriptions = serializers.SerializerMethodField()
    treeStatus = serializers.SerializerMethodField()

    def get_account_type(self, obj):
        return obj.get_account_type_display()

    def get_user_subscriptions(self, obj):
        current_active_subscription = obj.current_active_subscription
        serializer = UserSubscriptionSerializer(current_active_subscription)
        return serializer.data
        # user_subscriptions = UserSubscription.objects.filter(account=obj)
        # current_date = date.today()
        # for user_subscription in user_subscriptions:
        #     if user_subscription.user_start_date <= current_date <= user_subscription.user_end_date:
        #         return {'user_start_date': user_subscription.user_start_date.strftime("%m-%b-%Y"),
        #                 'user_end_date': user_subscription.user_end_date.strftime("%m-%b-%Y")}

    def get_associated_accounts(self, obj):
        list_of_associated_accounts = []
        association_requests_sent = list(obj.from_account.all())
        association_request_recieved = list(obj.to_account.all())

        for account in association_requests_sent:
            list_of_associated_accounts.append({
                "account_id": account.to_account.account_id,
                "account_name": account.to_account.account_name,
                "slug": account.slug,
                "accepted": account.accepted,
                "type": "sent"

            })
        for account in association_request_recieved:
            list_of_associated_accounts.append({
                "account_id": account.from_account.account_id,
                "account_name": account.from_account.account_name,
                "slug": account.slug,
                "accepted": account.accepted,
                "type": "received"
            })

        return list_of_associated_accounts

    def get_treeStatus(self, obj):

        is_hq = self.context.get('is_hq')

        if is_hq is not False:
            if (
                (obj.account_type == 'hq' or obj.account_type == 'hq_sub') and Account.objects.filter(
                parents__contains=obj.account_id).exists()):
                if obj.account_type == 'hq':
                    return "collapsed"
                if obj.account_type == 'hq_sub' and not obj.account_id == obj.parent_account.account_id:
                    return "collapsed"
                else:
                    return "disabled"
            else:
                return "disabled"

        elif is_hq is False:
            if obj.account_type == 'sub':
                return "disabled"
            elif obj.account_type == 'hq_sub':
                return "collapsed"

    class Meta:
        model = Account
        exclude = ['created_on', 'updated_on', 'created_by', 'updated_by', 'id']
        lookup_field = 'slug'


# updating account
class AccountWritableSerializer(BaseSerializer):
    class Meta:
        model = Account
        exclude = [
            'created_on',
            'updated_on',
            'created_by',
            'updated_by',
            'id',
            'account_type',
            'domain',
            'slug',
            'parent_account',
        ]
        lookup_field = 'slug'


class AccountCreateSerializer(BaseSerializer):
    parent_account = serializers.SlugRelatedField(
        slug_field='slug', queryset=Account.objects.all(), required=False, allow_null=True)
    devices = DeviceCreateSerializer(many=True, required=False)
    users = UserCreateSerializer(many=True, required=False)
    user_subscriptions = UserSubscriptionSerializer(many=True, required=False, allow_null=True)

    class Meta:
        model = Account
        fields = (
            "account_id",
            "slug",
            "parent_account",
            "account_name",
            "account_type",
            "city",
            "state",
            "country",
            "zipcode",
            "phone1",
            "phone2",
            "address1",
            "address2",
            "address3",
            "domain",
            "devices",
            "users",
            "user_subscriptions",
            "language",
            "parents",
            "is_active"
        )

    def create(self, validated_data):
        devices = validated_data.get('devices', None)
        if devices:
            validated_data.pop('devices')
        elif type(devices) == list and len(devices) >= 0:
            validated_data.pop('devices')
        else:
            devices = []
        users = validated_data.get('users', None)
        if users:
            validated_data.pop('users')
        elif type(users) == list and len(users) >= 0:
            validated_data.pop('users')
        else:
            users = []
        user_subscriptions = validated_data.get('user_subscriptions', [])
        validated_data.pop('user_subscriptions')
        language = validated_data["language"]

        user_subscriptions_available = False
        device_subscriptions_available = False
        with transaction.atomic():
            if user_subscriptions:
                if user_subscriptions[0]['num_of_users'] < len(users):
                    raise ValueError("User count is more than user subscriptions.")

                if user_subscriptions[0]['user_start_date'] >= user_subscriptions[0]['user_end_date']:
                    raise ValueError("End date should be greater than start date.")

                if user_subscriptions[0]['num_of_users'] is not None and user_subscriptions[0]['num_of_users'] > 0 and \
                    user_subscriptions[0]['user_end_date'] >= user_subscriptions[0]['user_start_date']:
                    user_subscriptions_available = True

                if user_subscriptions[0]['user_end_date'] >= user_subscriptions[0]['user_start_date']:
                    device_subscriptions_available = True

            account = super().create(validated_data)
            if account.account_type == 'hq_sub' and account.parent_account is None:
                account.parent_account = account
                account.save()

            if account.parent_account:
                if account.parent_account.parents:
                    account.parents = account.parent_account.parents
                account.parents += [account.parent_account.account_id, ]
                if account.parent_account.account_type == 'sub':
                    account.parent_account.account_type = 'hq_sub'
                    account.parent_account.save()
                account.save()

            if not device_subscriptions_available and len(devices) > 0:
                raise ValueError("Subscription start date and end date are not set ")
            elif device_subscriptions_available and len(devices) > 0:

                for d in devices:
                    d.update({'account': account.slug})
                    d.update(
                        {'sub_start_date': user_subscriptions[0]['user_start_date']})
                    d['item'] = d['item'].slug
                d = DeviceCreateSerializer(
                    data=devices, many=True, context=self.context)

                if d.is_valid():
                    d.save()

            if not user_subscriptions_available and len(users) > 0:
                raise ValueError("Subscription start date, end date or number of users are not set ")
            elif user_subscriptions_available and len(users) > 0:

                is_account_admin = False

                for user in users:
                    user.update({'account': account.id})
                    user.update({'language': language})
                    for group in user["groups"]:
                        if group.name == 'Account Admin' and not is_account_admin:
                            is_account_admin = True
                        elif group.name == 'Account Admin' and is_account_admin:
                            raise serializers.ValidationError(
                                {"groups": "The account can not have more then one account admin"})

                user = UserCreateSerializer(
                    data=users, many=True, context=self.context)

                if user.is_valid():
                    user.save()

            # device_subscriptions[0].update({'account': account.id})
            # device_subscriptions[0].pop('device_start_date')
            # device_sub = DeviceSubscriptionSerializer(
            #     data=device_subscriptions, many=True, context=self.context)
            if user_subscriptions_available or device_subscriptions_available:
                user_subscriptions[0].update({'account': account.id, 'is_active': True})
                user_sub = UserSubscriptionSerializer(
                    data=user_subscriptions, many=True, context=self.context)
                if user_sub.is_valid():
                    user_sub.save()
                    account.is_active = True
            else:
                account.is_active = False

            return account


class AssociatedAccountsSerializer(BaseSerializer):
    from_account = serializers.SlugRelatedField(
        slug_field="slug", read_only=True)
    to_account = serializers.SlugRelatedField(
        slug_field="slug", read_only=True)

    class Meta:
        model = AssociatedAccounts
        fields = ('from_account', 'to_account', 'accepted', 'slug')


class AssociatedSerializer(serializers.Serializer):
    account = MinifiedAccountSerializer()
    accepted = serializers.BooleanField()
    slug = serializers.CharField()
    type = serializers.CharField()


class AssociatedAccountsWritableSerializer(BaseSerializer):
    from_account = serializers.SlugRelatedField(
        slug_field="slug", queryset=Account.objects.all())
    to_account = serializers.SlugRelatedField(
        slug_field="slug", queryset=Account.objects.all())
    accepted = serializers.BooleanField(required=False)

    class Meta:
        model = AssociatedAccounts
        fields = ('from_account', 'to_account', 'accepted')

    def create(self, validated_data):
        with transaction.atomic():
            return super().create(validated_data)

    def partial_update(self, validated_data):
        from_account = Account.objects.get(
            slug=validated_data.get('from_account'))
        to_account = Account.objects.get(slug=validated_data.get('to_account'))
        # to_account.associated_accounts.filter()
        from_account.save()
        return from_account

    def destroy(self, validated_data):
        from_account = Account.objects.get(
            slug=validated_data.get('from_account'))
        to_account = Account.objects.get(slug=validated_data.get('to_account'))
        from_account.associated_accounts.remove(to_account)
        from_account.save()
        return from_account


class AccountSummarySerializer(BaseSerializer):
    class Meta:
        model = Account
        fields = (
            "account_type",
            "account_name",
            "num_user_subscriptions",
            "num_device_subscriptions",
            'slug'
        )


class AccountUploadItemSerializer(BaseSerializer):
    class Meta:
        model = AccountUploadItems
        lookup_field = 'slug'
        fields = (
            "account_upload",
            "account_number",
            "hq_account_number",
            "account_name",
            "slug",
            "account_type",
            "city",
            "state",
            "country",
            "zipcode",
            "phone1",
            "phone1_ext",
            "phone2",
            "phone2_ext",
            "address1",
            "address2",
            "address3",
            "domain",
            "sub_start_date",
            "sub_end_date",
            "no_of_usr_subs",
            "language",
            "is_imported",
            "errors",
        )


class AccountUploadSerializer(BaseSerializer):
    items = AccountUploadItemSerializer(many=True)

    class Meta:
        model = AccountUpload
        lookup_field = 'slug'
        fields = (
            "upload",
            "slug",
            'id',
            "items"
        )


class AccountUploadWritableSerializer(BaseSerializer):
    class Meta:
        model = AccountUpload
        lookup_field = 'slug'
        fields = (
            "upload",
            'id'
        )


class AssociatedContactsWritableSerializer(BaseSerializer):
    from_user = serializers.SlugRelatedField(
        slug_field="slug", queryset=User.objects.filter(user_type="Contact"))
    to_account = serializers.SlugRelatedField(
        slug_field="slug", queryset=Account.objects.all())
    accepted = serializers.BooleanField(required=False)

    class Meta:
        model = AssociatedContacts
        fields = ('from_user', 'to_account', 'accepted')

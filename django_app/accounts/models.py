from uuid import uuid4
from django.utils.translation import ugettext_lazy as _
from datetime import date
from django.db import models
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.exceptions import ValidationError
from django.contrib.postgres.fields import JSONField

from django_extensions.db.fields import AutoSlugField

from django_synergy.utils.models.base import AbstractBaseModel


# User = get_user_model()


def slugify(content):
    return content.replace('_', '-').lower()


def slugify_user_sub(content):
    return 'user-sub-' + slugify(content)


def slugify_device_sub(content):
    return 'device-sub-' + slugify(content)


def slugify_upload(content):
    return str(uuid4())


def user_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    name = filename.split('.')[0]
    ext = filename.split('.')[-1]
    return '{0}/account_import/{1}'.format(settings.S3_ENVIRON, '{0}_{1}.{2}'.format(name, uuid4(), ext))


ACCOUNT_TYPES = [
    ('hq', 'Head Quarter'),
    ('sub', 'Subsidiary'),
    ('hq_sub', 'Head Quarter / Subsidiary'),
]


class Account(AbstractBaseModel):

    def __str__(self):
        return self.account_name

    account_id = models.CharField(max_length=12, unique=True)
    slug = AutoSlugField(max_length=255, db_index=True, allow_unicode=True, unique=True, populate_from=[
                         'account_name', 'city'], slugify_function=slugify)
    parent_account = models.ForeignKey(
        'self', related_name='subsidiaries', on_delete=models.PROTECT, blank=True, null=True)
    account_name = models.CharField(max_length=255)
    account_type = models.CharField(
        choices=ACCOUNT_TYPES, max_length=50, default='hq')
    city = models.CharField(max_length=255, null=True, blank=True)
    state = models.CharField(max_length=255, null=True, blank=True)
    country = models.CharField(max_length=255, null=True, blank=True)
    zipcode = models.CharField(max_length=11, null=True, blank=True)
    phone1 = models.CharField(max_length=15, null=True, blank=True)
    phone1_ext = models.CharField(max_length=6, null=True, blank=True)
    phone2 = models.CharField(max_length=15, blank=True, null=True)
    phone2_ext = models.CharField(max_length=6, null=True, blank=True)
    address1 = models.CharField(max_length=512, null=True, blank=True)
    address2 = models.CharField(max_length=512, blank=True, null=True)
    address3 = models.CharField(max_length=512, blank=True, null=True)
    domain = models.CharField(max_length=255, null=True, blank=True)
    language = models.CharField(max_length=10, choices=settings.LANGUAGES, default=settings.LANGUAGE_CODE)
    associated_accounts = models.ManyToManyField(
        "self", through='AssociatedAccounts', blank=True, symmetrical=False)
    associated_contacts = models.ManyToManyField(
        "users.User", through='AssociatedContacts', blank=True, symmetrical=False,
        through_fields=('to_account', 'from_user'), related_name="associated_contacts")
    # JSON Field to hold a list of all parent accounts
    parents = JSONField(default=list())
    is_active = models.BooleanField(default=False)

    @property
    def account_admin(self):
        account_admin = self.users.filter(
            groups__name__contains="Account Admin").all()
        if account_admin:
            return account_admin[0].first_name + ' ' + account_admin[0].last_name
        else:
            None

    @property
    def account_admin_id(self):
        account_admin = self.users.filter(
            groups__name__contains="Account Admin").all()
        if account_admin:
            return account_admin[0].id
        else:
            None

    @property
    def num_device_subscriptions(self):
        return self.devices.filter(is_active=True,).exclude(status='Lost or Broken').count()

    @property
    def num_user_subscriptions(self):
        return self.users.filter(is_active=True).count()

    @property
    def current_active_subscription(self):
        user_subscriptions = self.user_subscriptions.order_by('-created_on').all()
        current_date = date.today()
        current_active_sub = user_subscriptions.filter(is_active=True, is_cancelled=False)
        # current_active_sub = [x for x in user_subscriptions if x.user_start_date <= current_date <= x.user_end_date and x.is_active is True]
        if len(current_active_sub) == 0:
            return None
        elif len(current_active_sub) > 0:
            return current_active_sub[0]

    @property
    def max_user_subscriptions(self):
        current_active_sub = self.current_active_subscription
        if current_active_sub is not None:
            return current_active_sub.num_of_users
        else:
            return None
        # user_subscriptions = self.user_subscriptions.order_by('-created_on').all()
        # current_date = date.today()
        # current_active_sub = [x for x in user_subscriptions if x.user_start_date <= current_date <= x.user_end_date]
        # if len(current_active_sub) == 0:
        #     return None
        # elif len(current_active_sub) > 0:
        #     return current_active_sub[0].num_of_users

    class Meta:
        default_permissions = ()
        permissions = [
            ("account-view-own", _("Can view their own account")),
            ("account-view-detail-own", "Can view detail of their own account"),
            ("account-edit-own", "Can request admin to update their own account details"),
            ("account-view-detail-own-sub", "Can view subscription detail of their own account"),

            ("account-list-all", "Can view list of all accounts"),
            ("account-view-all-detail", "Can view detail of all accounts"),

            ("account-list-subsidiary", "Can view list of subsidiary accounts"),
            ("account-view-detail-subsidiary", "Can view detail of subsidiary accounts"),
            ("account-view-detail-subsidiary-sub", "Can view subscription detail of subsidiary accounts"),

            ("account-list-hq", "Can view list of hq accounts"),
            ("account-view-detail-hq", "Can view detail of hq accounts"),

            ("account-list-associated", "Can view list of associated accounts"),
            ("account-view-detail-associated", "Can view detail of associated accounts"),

            ("account-associate", "Can associate to other accounts"),
            ("account-request-associate", "Can request admin to associate to other accounts or contacts"),
            ("account-invite-associate", "Can invite contacts to associate"),
        ]


class AssociatedAccounts(AbstractBaseModel):
    from_account = models.ForeignKey(
        'Account', on_delete=models.PROTECT, related_name="from_account")
    to_account = models.ForeignKey(
        'Account', on_delete=models.PROTECT, related_name="to_account")
    accepted = models.BooleanField(default=False)
    slug = AutoSlugField(max_length=255, db_index=True, allow_unicode=True, unique=True, populate_from=[
                         'from_account__account_name', 'to_account__account_name'], slugify_function=slugify)

    class Meta:
        unique_together = ('from_account', 'to_account')


class UserSubscription(AbstractBaseModel):
    account = models.ForeignKey(
        "accounts.Account", on_delete=models.PROTECT, related_name="user_subscriptions", blank=True)
    user_start_date = models.DateField()
    user_end_date = models.DateField()
    num_of_users = models.PositiveIntegerField(default=0, blank=True)
    slug = AutoSlugField(max_length=255, db_index=True, allow_unicode=True, unique=True, populate_from=[
                         'account__account_name'], slugify_function=slugify_user_sub)
    is_cancelled = models.BooleanField(default=False, null=True)
    is_active = models.BooleanField(default=False, null=True)


class DeviceSubscription(AbstractBaseModel):
    account = models.ForeignKey("accounts.Account", on_delete=models.PROTECT,
                                related_name="device_subscriptions", blank=True)
    device_end_date = models.DateField()
    slug = AutoSlugField(max_length=255, db_index=True, allow_unicode=True, unique=True, populate_from=[
                         'account__account_name'], slugify_function=slugify_device_sub)


def validate_upload(value):
    # Probably worth doing this check first anyway
    if not value.name.endswith(('.csv', '.xlsx')):
        raise ValidationError('Invalid file type')


class AccountUpload(AbstractBaseModel):
    _key_prefix = settings.DEVICE_IMPORT_KEY_PREFIX

    upload = models.FileField(
        upload_to=user_directory_path, validators=[validate_upload])
    slug = models.CharField(max_length=1, null=True, blank=True)


class AccountUploadItems(AbstractBaseModel):
    account_upload = models.ForeignKey(AccountUpload, on_delete=models.CASCADE, related_name="items")
    account_number = models.CharField(max_length=12, null=True, blank=True)
    hq_account_number = models.CharField(max_length=12, null=True, blank=True)
    account_name = models.CharField(max_length=255, null=True, blank=True)
    slug = models.CharField(max_length=1, null=True, blank=True)
    account_type = models.CharField(max_length=50, null=True, blank=True)
    city = models.CharField(max_length=255, null=True, blank=True)
    state = models.CharField(max_length=255, null=True, blank=True)
    country = models.CharField(max_length=255, null=True, blank=True)
    zipcode = models.CharField(max_length=11, null=True, blank=True)
    phone1 = models.CharField(max_length=23, null=True, blank=True)
    phone1_ext = models.CharField(max_length=6, null=True, blank=True)
    phone2 = models.CharField(max_length=23, blank=True, null=True)
    phone2_ext = models.CharField(max_length=6, null=True, blank=True)
    address1 = models.CharField(max_length=512, null=True, blank=True)
    address2 = models.CharField(max_length=512, blank=True, null=True)
    address3 = models.CharField(max_length=512, blank=True, null=True)
    domain = models.CharField(max_length=255, null=True, blank=True)
    sub_start_date = models.DateField(null=True, blank=True)
    sub_end_date = models.DateField(null=True, blank=True)
    no_of_usr_subs = models.IntegerField(null=True, blank=True)
    device_sub_end_date = models.DateField(null=True, blank=True)
    language = models.CharField(max_length=10, default=settings.LANGUAGE_CODE)
    is_imported = models.BooleanField(default=False)
    errors = JSONField()


class AssociatedContacts(AbstractBaseModel):
    from_user = models.ForeignKey(
        'users.User', on_delete=models.PROTECT, related_name="contact_associated_account")
    to_account = models.ForeignKey(
        'Account', on_delete=models.PROTECT, related_name="account_associated_contact")
    accepted = models.BooleanField(default=False)
    slug = AutoSlugField(max_length=255, db_index=True, allow_unicode=True, unique=True, populate_from=[
                         'from_user__name', 'to_account__account_name'], slugify_function=slugify)

    class Meta:
        unique_together = ('from_user', 'to_account')

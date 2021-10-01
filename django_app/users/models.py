from django.db.models import CASCADE
from django.utils import timezone
from pytz import common_timezones

from django.conf import settings
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import AbstractUser, Group
from django.core.validators import EmailValidator
from django_extensions.db.fields import AutoSlugField
from django.db.models import CharField, DateTimeField, ForeignKey, TextField, BooleanField, PROTECT, DateField

from django_synergy.users.manager import UserManager
from django_synergy.accounts.models import Account

SUPER_ADMIN_USER_ID = 1

COMMUNICATION_CHOICES = [('Email', _('Email')), ('Phone', _('Phone'))]
USER_TYPES = [('Contact', _('Contact')),
              ('User', _('User'))]
TITLE_CHOICES = [('Mr.', _('Mr.')), ('Mrs.', _('Mrs.')), ('Ms.', _('Ms.'))]
RELATIONSHIP_CHOICES = [('Mother', _('Mother')), ('Father', _('Father')), ('Guardian', _('Guardian'))]
ACTIVE_CHOICES = [(False, _('Inactive')), (True, _('Active'))]


def slugify(content):
    return content.replace('_', '-').lower()


class User(AbstractUser):
    # First Name and Last Name do not cover name patterns
    # around the globe.
    name = CharField(_("Name of User"), max_length=255, null=True, blank=True)
    first_name = CharField(max_length=255)
    last_name = CharField(max_length=255)
    title = CharField(max_length=255, choices=TITLE_CHOICES,
                      null=True, blank=True)
    credentials = CharField(max_length=255, null=True, blank=True)
    # not the account, field specific to contact
    company = CharField(max_length=255, null=True, blank=True)
    email = CharField(
        _('email address'),
        max_length=150,
        unique=True,
        help_text=_('Required. 150 characters or fewer.'),
        validators=[EmailValidator],
        error_messages={
            'unique': _("A user with that email already exists."),
        },
    )
    account = ForeignKey(Account, on_delete=PROTECT, related_name="users", default=None, null=True, blank=True)
    country = CharField(max_length=255, null=True, blank=True)
    city = CharField(max_length=255, null=True, blank=True)
    state = CharField(max_length=255, null=True, blank=True)
    zipcode = CharField(max_length=11, null=True, blank=True)
    address1 = TextField(max_length=512, null=True, blank=True)
    address2 = TextField(max_length=512, null=True, blank=True)
    address3 = TextField(max_length=512, null=True, blank=True)
    phone1 = CharField(max_length=15)
    phone2 = CharField(max_length=15, null=True, blank=True)
    pref_comm = CharField(
        max_length=10, choices=COMMUNICATION_CHOICES, default='Email')
    user_type = CharField(
        max_length=15, choices=USER_TYPES, default='Contact')

    slug = AutoSlugField(max_length=255, db_index=True, allow_unicode=True, unique=True, populate_from=[
        'first_name', 'last_name'], slugify_function=slugify)
    created_by = ForeignKey('self', on_delete=CASCADE,
                            related_name="+", default=SUPER_ADMIN_USER_ID, null=True, blank=True)
    created_on = DateTimeField(default=timezone.now)
    updated_by = ForeignKey('self', on_delete=CASCADE,
                            related_name="+", default=SUPER_ADMIN_USER_ID, null=True, blank=True)
    updated_on = DateTimeField(default=timezone.now)

    language = CharField(
        max_length=10, choices=settings.LANGUAGES, default=settings.LANGUAGE_CODE)

    timezone = CharField(max_length=100, choices=[
        (t, t) for t in common_timezones], default=settings.TIME_ZONE)

    is_circadianceadmin = BooleanField(default=False, null=False)
    tandc_policy_agreed = BooleanField(default=False, null=False)
    subscription_policy_agreed = BooleanField(default=False, null=False)
    is_phone1_primary = BooleanField(default=True)
    disable_notification = BooleanField(default=False)
    relationship_to_patient = CharField(max_length=255, choices=RELATIONSHIP_CHOICES,
                                        null=True, blank=True)
    national_no = CharField(max_length=255, null=True, blank=True)
    date_of_birth = DateField(null=True, blank=True)

    is_active = BooleanField(choices=ACTIVE_CHOICES, default=False)

    REQUIRED_FIELDS = ['first_name', 'last_name',
                       'phone1', 'pref_comm', 'language', 'timezone']

    USERNAME_FIELD = 'email'

    EMAIL_FIELD = 'email'

    objects = UserManager()

    def get_absolute_url(self):
        return reverse("users:user-detail", kwargs={"slug": self.slug})

    @property
    def account_name(self):
        if self.account:
            return self.account.account_name
        else:
            return None

    @property
    def account_number(self):
        if self.account:
            return self.account.account_id
        else:
            return None

    @property
    def hq_account_number(self):
        if self.account:
            if self.account.parent_account:
                return self.account.parent_account.account_id
        else:
            return None

    @property
    def user_groups(self):
        if self.is_superuser:
            return _("Super User")
        else:
            return [g.name for g in self.groups.all()]

    class Meta:
        # default permissions are "view", "add", "change", "delete"
        default_permissions = ()
        permissions = [
            ("user-view-own-user", _("Can view their own user")),

            ("user-create", _("Can create account & subsidiary users")),

            ("user-list-account", _("Can view list of account users")),
            ("user-view-detail-account", _("Can view detail of account users")),
            ("user-edit-account", _("Can edit account users")),
            ("user-delete-account", _("Can delete account users")),

            ("user-list-subsidiary", _("Can view list of subsidiary account users")),
            ("user-view-detail-subsidiary", _("Can view detail of subsidiary account users")),
            ("user-edit-subsidiary", _("Can edit subsidiary users")),
            ("user-delete-subsidiary", _("Can delete subsidiary users")),

            ("user-list-associated", _("Can view list of associated account users")),
            ("user-view-detail-associated", _("Can view detail of associated account users")),

            ("user-list-hq", _("Can view list of hq account users")),
            ("user-view-detail-hq", _("Can view detail of hq account users")),

            ("user-list-contacts", _("Can view list of all contacts")),
            ("user-view-detail-contact", _("Can view detail of all contacts")),

            ("user-list-associated-contacts", _("Can view list of associated contacts")),
            ("user-view-detail-associated-contact", _("Can view detail of associated contacts")),

            ("user-invite", _("Can invite contact via email")),
        ]

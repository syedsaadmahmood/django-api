from django_synergy.devices.serializers import DeviceSerializer
from django_synergy.users.serializers import ParentUserSerializer
from django_synergy.utils.serializers import BaseSerializer, serializers
from django_synergy.cases.models import Case, User, Parent, Account, CaseRole, CaseDevice, ProviderNote, ParentNote
from .parent import ParentSerializer
from .patient import PatientSerializer
from .roles import CaseRoleSerializer


class CaseSerializer(BaseSerializer):
    device = serializers.SerializerMethodField()
    patient = PatientSerializer(many=False)
    parent = serializers.SerializerMethodField()
    is_active = serializers.BooleanField()

    def get_device(self, obj):
        case_device = CaseDevice.objects.get(case=obj, is_active=True)
        return DeviceSerializer(case_device.device, many=False).data

    def get_parent(self, obj):
        if obj.parent is None and obj.parent_user is None:
            return None
        elif obj.parent is None:
            case_parent = User.objects.get(id=obj.parent_user_id)
            return ParentUserSerializer(case_parent, many=False).data
        else:
            case_parent = Parent.objects.get(id=obj.parent_id)
            return ParentSerializer(case_parent, many=False).data

    class Meta:
        model = Case
        fields = ('slug', 'is_consent', 'is_active', 'device', 'patient', 'parent')


class CaseWritableSerializer(BaseSerializer):
    account = serializers.SlugRelatedField(slug_field='slug', queryset=Account.objects.all(), required=False,
                                           allow_null=True)

    class Meta:
        model = Case
        fields = ('patient', 'parent', 'parent_user', 'account', 'is_consent', 'is_active', 'timezone')


class CaseListSerializer(BaseSerializer):
    parent_name = serializers.SerializerMethodField()
    device_serial_number = serializers.SerializerMethodField()
    account_no = serializers.SerializerMethodField()
    account_name = serializers.SerializerMethodField()
    case_manager_name = serializers.SerializerMethodField()
    scorer_name = serializers.SerializerMethodField()
    interpreting_physician_name = serializers.SerializerMethodField()

    @staticmethod
    def get_parent_name(obj):
        if obj.parent is None and obj.parent_user is None:
            return None
        elif obj.parent_user:
            case_parent = obj.parent_user.name
            return case_parent
        elif obj.parent:
            case_parent = obj.parent.name
            return case_parent

    @staticmethod
    def get_device_serial_number(obj):
        return CaseDevice.objects.filter(is_active=True, case=obj).first().device.serial_number

    @staticmethod
    def get_account_no(obj):
        return obj.account.account_id

    @staticmethod
    def get_account_name(obj):
        return obj.account.account_name

    @staticmethod
    def get_case_manager_name(obj):
        case_roles = CaseRole.objects.filter(case=obj, case_default_role__slug='case-manager')
        names = []
        for case_role in case_roles:
            names.append(case_role.user.first_name + ' ' + case_role.user.last_name)
        return names

    @staticmethod
    def get_scorer_name(obj):
        case_roles = CaseRole.objects.filter(case=obj, case_default_role__slug='scorer')
        names = []
        for case_role in case_roles:
            names.append(case_role.user.first_name + ' ' + case_role.user.last_name)
        return names

    @staticmethod
    def get_interpreting_physician_name(obj):
        case_roles = CaseRole.objects.filter(case=obj, case_default_role__slug='interpreting-physician')
        names = []
        for case_role in case_roles:
            names.append(case_role.user.first_name + ' ' + case_role.user.last_name)
        return names

    class Meta:
        model = Case
        fields = ('slug', 'case_no', 'is_active', 'is_archived', 'parent_name', 'device_serial_number', 'account_no',
                  'account_name', 'case_manager_name', 'scorer_name', 'interpreting_physician_name')


class CaseDetailSerializer(BaseSerializer):
    patient = serializers.SerializerMethodField()
    parent = serializers.SerializerMethodField()
    device = serializers.SerializerMethodField()
    event_count = serializers.SerializerMethodField()
    interpretation_count = serializers.SerializerMethodField()
    provider_note_count = serializers.SerializerMethodField()
    parent_note_count = serializers.SerializerMethodField()
    account = serializers.SerializerMethodField()

    def get_account(self, obj):
        return {
            "slug": obj.account.slug,
            "name": obj.account.account_name
        }

    def get_event_count(self, obj):
        return obj.events.count()

    def get_interpretation_count(self, obj):
        return obj.data_interpretation_case.count()

    def get_provider_note_count(self, obj):
        provider_note_count = ProviderNote.objects.filter(case=obj).count()
        return provider_note_count

    def get_parent_note_count(self, obj):
        parent_note_count = ParentNote.objects.filter(case=obj).count()
        return parent_note_count

    @staticmethod
    def get_parent(obj):
        if obj.parent is None and obj.parent_user is None:
            return None
        elif obj.parent_user:
            return {"name": obj.parent_user.name, "slug": obj.parent_user.slug, "create_system_contact": True}
        elif obj.parent:
            return {"name": obj.parent.name, "slug": obj.parent.slug, "create_system_contact": False}

    @staticmethod
    def get_patient(obj):
        return {"name": obj.patient.first_name + ' ' + obj.patient.last_name, "slug": obj.patient.slug}

    @staticmethod
    def get_device(obj):
        return {"serial_number": CaseDevice.objects.filter(is_active=True, case=obj).first().device.serial_number,
                "slug": CaseDevice.objects.filter(is_active=True, case=obj).first().device.slug,
                'item_number': CaseDevice.objects.filter(is_active=True, case=obj).first().device.item.item_number,
                'configuration': CaseDevice.objects.filter(is_active=True, case=obj).first().device.item.configuration}

    class Meta:
        model = Case
        fields = (
            'patient', 'parent', 'device', 'is_consent', 'is_archived', 'is_active', 'event_count', 'account',
            'interpretation_count', 'is_closed', 'case_no', 'provider_note_count', 'parent_note_count')


class SimpleCaseSerializer(BaseSerializer):
    class Meta:
        model = Case
        fields = ('slug', 'case_no')


class CaseSummarySerializer(BaseSerializer):
    account = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()
    device_serial_number = serializers.SerializerMethodField()

    def get_account(self, obj):
        return obj.account.account_name

    def get_roles(self, obj):
        case_managers = CaseRole.objects.filter(case__slug=obj.slug, case_default_role__name="Case Manager")
        display_count = 5 - case_managers.count()
        roles = CaseRole.objects.filter(case__slug=obj.slug).exclude(case_default_role__name__contains="Case Manager")[
                :display_count]
        all_roles = case_managers | roles
        all_roles = all_roles.order_by('user__slug').distinct('user__slug')
        return CaseRoleSerializer(all_roles, many=True, context={"case": obj}).data

    @staticmethod
    def get_device_serial_number(obj):
        return CaseDevice.objects.filter(is_active=True, case=obj).first().device.serial_number

    class Meta:
        model = Case
        fields = (
            'slug',
            'case_no',
            'account',
            'is_active',
            'roles',
            'device_serial_number'
        )


class CaseDeviceSerializer(BaseSerializer):
    class Meta:
        model = CaseDevice
        exclude = ('id', 'slug', 'created_on', 'created_by', 'updated_on', 'updated_by')


class CaseStatusSerializer(BaseSerializer):
    class Meta:
        model = Case
        fields = ('slug', 'is_closed', 'is_active')

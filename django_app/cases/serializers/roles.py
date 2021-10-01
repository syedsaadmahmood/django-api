from django_synergy.cases.models import CaseDefaultRole, CaseRole, Case, User
from django_synergy.utils.serializers import BaseSerializer, serializers


class CaseDefaultRoleSerializer(BaseSerializer):
    class Meta:
        model = CaseDefaultRole
        fields = ('id', 'name',)


class CaseRoleWritableSerializer(BaseSerializer):
    case = serializers.SlugRelatedField(slug_field='slug', queryset=Case.objects.all())
    case_default_role = serializers.SlugRelatedField(slug_field='slug', queryset=CaseDefaultRole.objects.all())
    user = serializers.SlugRelatedField(slug_field='slug', queryset=User.objects.all())

    class Meta:
        model = CaseRole
        exclude = ('id', 'slug', 'created_on', 'created_by', 'updated_on', 'updated_by')


class CaseRoleSerializer(BaseSerializer):
    name = serializers.SerializerMethodField()
    slug = serializers.SerializerMethodField()
    account_name = serializers.SerializerMethodField()
    role_name = serializers.SerializerMethodField()

    def get_name(self, obj):
        return obj.user.name

    def get_slug(self, obj):
        return obj.user.slug

    def get_account_name(self, obj):
        if obj.user.account:
            return obj.user.account.account_name
        else:
            return ''

    def get_role_name(self, obj):
        case = self.context.get('case')
        case_role = CaseRole.objects.filter(case=case, user=obj.user).first()
        return case_role.case_default_role.name

    class Meta:
        model = CaseRole
        fields = ('name', 'slug', 'account_name', 'role_name')

from django_synergy.utils.serializers import BaseSerializer, serializers
from django_synergy.cases.models import Parent
from datetime import datetime


class ParentSerializer(BaseSerializer):
    is_system_contact = serializers.SerializerMethodField()

    @staticmethod
    def get_is_system_contact(obj):
        return False

    date_of_birth = serializers.SerializerMethodField()

    @staticmethod
    def get_date_of_birth(obj):
        if obj.date_of_birth:
            date = datetime.strftime(obj.date_of_birth, "%d-%m-%Y")
            return date
        else:
            return None

    class Meta:
        model = Parent
        exclude = ('id', 'created_on', 'created_by', 'updated_on', 'updated_by')


class ParentWritableSerializer(BaseSerializer):
    class Meta:
        model = Parent
        exclude = ('id', 'slug', 'created_on', 'created_by', 'updated_on', 'updated_by')

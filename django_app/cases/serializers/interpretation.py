from django_synergy.cases.models.interpretation import InterpretationData
from django_synergy.cases.serializers import SimpleCaseSerializer
from django_synergy.devices.serializers import DeviceSettingsSerializer
from django_synergy.events.models import Event
from django_synergy.interpretation_libraries.models import InterpretationDiagnosis, Utilization, EventRecording, \
    Interpretation, InterpretationNotes1, InterpretationNotes2, InterpretationNotes3, InterpretationNotes4, \
    Recommendation, RecommendationNotes1, RecommendationNotes2
from django_synergy.cases.models import Case, CaseDevice
from django_synergy.interpretation_libraries.serializers import InterpretationDiagnosisSerializer, \
    UtilizationSerializer, EventRecordingSerializer, InterpretationSerializer, InterpretationNotes2Serializer, \
    InterpretationNotes1Serializer, InterpretationNotes3Serializer, InterpretationNotes4Serializer, \
    RecommendationSerializer, RecommendationNotes1Serializer, RecommendationNotes2Serializer
from django_synergy.utils.serializers import BaseSerializer, serializers

from datetime import datetime
from datetime import date


def YMD_format1(date):
    dt = datetime.strptime(date, '%d-%b-%Y')
    return dt.year, dt.month, dt.day


def YMD_format2(date):
    dt = datetime.strptime(date, '%d-%m-%Y')
    return dt.year, dt.month, dt.day


class InterpretationDataWritableSerializer(BaseSerializer):
    case = serializers.SlugRelatedField(
        slug_field='slug', queryset=Case.objects.all(), allow_null=True, allow_empty=True)

    diagnosis = serializers.SlugRelatedField(
        slug_field='slug', queryset=InterpretationDiagnosis.objects.all(), allow_null=True, allow_empty=True)

    utilization = serializers.SlugRelatedField(
        slug_field='slug', queryset=Utilization.objects.all(), allow_null=True, allow_empty=True)

    event_recording = serializers.SlugRelatedField(
        slug_field='slug', queryset=EventRecording.objects.all(), allow_null=True, allow_empty=True)

    interpretation = serializers.SlugRelatedField(
        slug_field='slug', queryset=Interpretation.objects.all(), allow_null=True, allow_empty=True)

    interpretation_notes1 = serializers.SlugRelatedField(
        slug_field='slug', queryset=InterpretationNotes1.objects.all(), allow_null=True, allow_empty=True)

    interpretation_notes2 = serializers.SlugRelatedField(
        slug_field='slug', queryset=InterpretationNotes2.objects.all(), allow_null=True, allow_empty=True)

    interpretation_notes3 = serializers.SlugRelatedField(
        slug_field='slug', queryset=InterpretationNotes3.objects.all(), allow_null=True, allow_empty=True)

    interpretation_notes4 = serializers.SlugRelatedField(
        slug_field='slug', queryset=InterpretationNotes4.objects.all(), allow_null=True, allow_empty=True)

    recommendation = serializers.SlugRelatedField(
        slug_field='slug', queryset=Recommendation.objects.all(), allow_null=True, allow_empty=True)

    recommendation_notes1 = serializers.SlugRelatedField(
        slug_field='slug', queryset=RecommendationNotes1.objects.all(), allow_null=True, allow_empty=True)

    recommendation_notes2 = serializers.SlugRelatedField(
        slug_field='slug', queryset=RecommendationNotes2.objects.all(), allow_null=True, allow_empty=True)

    class Meta:
        model = InterpretationData
        exclude = ('id', 'created_on', 'created_by', 'updated_on', 'updated_by')


class InterpretationDataReadOnlySerializer(BaseSerializer):
    case = SimpleCaseSerializer()
    diagnosis = InterpretationDiagnosisSerializer()
    utilization = UtilizationSerializer()
    event_recording = EventRecordingSerializer()
    interpretation = InterpretationSerializer()
    interpretation_notes1 = InterpretationNotes1Serializer()
    interpretation_notes2 = InterpretationNotes2Serializer()
    interpretation_notes3 = InterpretationNotes3Serializer()
    interpretation_notes4 = InterpretationNotes4Serializer()
    recommendation = RecommendationSerializer()
    recommendation_notes1 = RecommendationNotes1Serializer()
    recommendation_notes2 = RecommendationNotes2Serializer()
    device_settings = DeviceSettingsSerializer()

    updated_by = serializers.SerializerMethodField()

    def get_updated_by(self, obj):
        return obj.updated_by.name

    class Meta:
        model = InterpretationData
        exclude = ('id',)


class InterpretationDataRetrieveSerializer(BaseSerializer):
    interpretation = serializers.SerializerMethodField()
    created_date = serializers.SerializerMethodField()
    patient = serializers.SerializerMethodField()
    user = serializers.SerializerMethodField()
    account = serializers.SerializerMethodField()
    num_of_provider_notes = serializers.SerializerMethodField()
    num_of_parent_notes = serializers.SerializerMethodField()
    num_of_events = serializers.SerializerMethodField()
    account_slug = serializers.SerializerMethodField()

    def get_interpretation(self, obj):
        return InterpretationDataReadOnlySerializer(obj, many=False).data

    def get_account_slug(self, obj):
        return obj.case.account.slug

    def get_created_date(self, obj):
        return datetime.today().strftime('%d-%b-%Y')

    def get_patient(self, obj):
        gestational_age_days, gestational_age_weeks = obj.case.vitals_case.gestational_age
        if gestational_age_days is not None:
            gestational_age_days = str(gestational_age_days) + ' days'

        if gestational_age_weeks is not None:
            gestational_age_weeks = str(gestational_age_weeks) + ' weeks'
        return {
            'name': obj.case.patient.first_name + ' ' + obj.case.patient.last_name,
            'date_of_birth': obj.case.patient.date_of_birth.strftime('%d-%b-%Y'),
            'gestational_age_at_birth_days': obj.case.vitals_case.gestational_age_at_birth_days,
            'gestational_age_at_birth_weeks': obj.case.vitals_case.gestational_age_at_birth_weeks,
            'gestational_age_now_days': gestational_age_days,
            'gestational_age_now_weeks': gestational_age_weeks
        }

    def get_user(self, obj):
        return {
            'name': obj.created_by.name,
            'account': obj.created_by.account.account_id + ' ' + obj.created_by.account.account_name,
        }

    def get_account(self, obj):
        device = CaseDevice.objects.filter(is_active=True, case=obj.case).first().device
        return {
            'monitor_config': device.item.item_number + ' ' + device.item.configuration,
            'monitor_serial_number': device.serial_number,
            'monitor_slug': device.slug,
            'device_account': device.account.account_id + ' ' + device.account.account_name
        }

    def get_num_of_provider_notes(self, obj):
        return obj.case.provider_note_case.all().count()

    def get_num_of_parent_notes(self, obj):
        return obj.case.parent_note_case.all().count()

    def get_num_of_events(self, obj):
        return obj.no_of_events

    class Meta:
        model = InterpretationData
        fields = (
            'interpretation', 'created_date', 'patient', 'user', 'account', 'num_of_events', 'num_of_provider_notes',
            'num_of_parent_notes', 'account_slug')


class InterpretationDataSerializer(BaseSerializer):
    class Meta:
        model = InterpretationData
        exclude = ('id', 'created_on', 'created_by', 'updated_on', 'updated_by')


class InterpretationDataListSerializer(BaseSerializer):
    class Meta:
        model = InterpretationData
        fields = ('slug', 'date_from', 'date_to', 'no_of_events', 'is_approved')


class InterpretationDataDetailSerializer(BaseSerializer):
    num_of_events = serializers.SerializerMethodField()
    created_date = serializers.SerializerMethodField()
    date_from = serializers.SerializerMethodField()
    date_to = serializers.SerializerMethodField()
    patient = serializers.SerializerMethodField()
    user = serializers.SerializerMethodField()
    account = serializers.SerializerMethodField()
    num_of_provider_notes = serializers.SerializerMethodField()
    num_of_parent_notes = serializers.SerializerMethodField()
    account_slug = serializers.SerializerMethodField()

    def get_account_slug(self, obj):
        return obj.account.slug

    def get_num_of_events(self, obj):
        date_to = self.context.get('date_to')
        date_from = self.context.get('date_from')
        count = 0
        if date_to is not None and date_from is not None:
            events = Event.objects.filter(case__slug=obj.slug)
            for event in events:
                to_year, to_month, to_day = YMD_format1(date_to)
                from_year, from_month, from_day = YMD_format1(date_from)
                between_year, between_month, between_day = YMD_format2(event.event_date_time.strftime('%d-%m-%Y'))
                d2 = date(between_year, between_month, between_day)
                d1 = date(from_year, from_month, from_day)
                d3 = date(to_year, to_month, to_day)
                if d1 <= d2 <= d3:
                    count = count + 1
            return count

        else:
            return obj.events.all().count()

    def get_created_date(self, obj):
        return datetime.today().strftime('%d-%b-%Y')

    def get_date_from(self, obj):
        date_from = self.context.get('date_from')
        if date_from is None:
            event = obj.events.filter(is_interpreted=False).order_by('event_index').first()
            if event is None:
                return None
            else:
                return event.event_date_time.strftime('%d-%b-%Y')
        else:
            return date_from

    def get_date_to(self, obj):
        date_to = self.context.get('date_to')
        if date_to is None:
            event = obj.events.filter(is_interpreted=False).order_by('event_index').last()
            if event is None:
                return None
            else:
                return event.event_date_time.strftime('%d-%b-%Y')
        else:
            return date_to

    def get_patient(self, obj):
        gestational_age_days, gestational_age_weeks = obj.vitals_case.gestational_age
        if gestational_age_days is not None:
            gestational_age_days = str(gestational_age_days) + ' days'

        if gestational_age_weeks is not None:
            gestational_age_weeks = str(gestational_age_weeks) + ' weeks'
        return {
            'name': obj.patient.first_name + ' ' + obj.patient.last_name,
            'date_of_birth': obj.patient.date_of_birth.strftime('%d-%b-%Y'),
            'gestational_age_at_birth_days': obj.vitals_case.gestational_age_at_birth_days,
            'gestational_age_at_birth_weeks': obj.vitals_case.gestational_age_at_birth_weeks,
            'gestational_age_now_days': gestational_age_days,
            'gestational_age_now_weeks': gestational_age_weeks
        }

    def get_user(self, obj):
        return {
            'name': obj.created_by.name,
            'account': obj.created_by.account.account_id + ' ' + obj.created_by.account.account_name
        }

    def get_account(self, obj):
        device = CaseDevice.objects.filter(is_active=True, case=obj).first().device
        return {
            'monitor_config': device.item.item_number + ' ' + device.item.configuration,
            'monitor_serial_number': device.serial_number,
            'monitor_slug': device.slug,
            'device_account': device.account.account_id + ' ' + device.account.account_name
        }

    def get_num_of_provider_notes(self, obj):
        return obj.provider_note_case.all().count()

    def get_num_of_parent_notes(self, obj):
        return obj.parent_note_case.all().count()

    class Meta:
        model = Case
        fields = (
            'num_of_events', 'created_date', 'date_from', 'date_to', 'patient', 'user', 'account',
            'num_of_provider_notes', 'account_slug', 'num_of_parent_notes')

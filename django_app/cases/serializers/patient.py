from django_synergy.cases.serializers.clinical_information import PrescriptionSerializer, HistorySerializer, \
    VitalsSerializer
from django_synergy.synergy_libraries.serializers.diagnosis import DiagnosisSerializer
from django_synergy.synergy_libraries.serializers.ethnicity import EthnicitySerializer
from django_synergy.synergy_libraries.serializers.race import RaceSerializer
from django_synergy.utils.serializers import BaseSerializer, serializers
from django_synergy.cases.models import Patient, PatientEthnicity, PatientRace, Race, Ethnicity, Prescription, Case, \
    Vitals
from datetime import datetime


class PatientSerializer(BaseSerializer):
    prescription = serializers.SerializerMethodField()
    ethnicity = EthnicitySerializer(many=True)
    race = RaceSerializer(many=True)
    diagnosis = DiagnosisSerializer(many=True)
    history = HistorySerializer(many=True, source='history_patient')
    vitals = serializers.SerializerMethodField()

    def get_prescription(self, obj):
        patient_prescription = Prescription.objects.filter(patient_id=obj.id)
        return PrescriptionSerializer(patient_prescription, many=True).data

    def get_vitals(self, obj):
        case = Case.objects.get(patient=obj)
        vitals = Vitals.objects.filter(case=case).first()
        return VitalsSerializer(vitals, many=False).data

    class Meta:
        model = Patient
        fields = (
            'slug', 'first_name', 'last_name', 'middle_name', 'patient_aka', 'national_no', 'gender', 'date_of_birth',
            'address1',
            'address2', 'address3', 'country_name', 'city_name'
            , 'state_name', 'state_name', 'zipcode', 'carrier', 'policy_number', 'group_number', 'contact_person',
            'contact_email', 'contact_phone', 'ethnicity', 'race', 'diagnosis', 'prescription', 'history', 'vitals')


class PatientDetailSerializer(BaseSerializer):
    ethnicity = EthnicitySerializer(many=True, required=False)
    race = RaceSerializer(many=True, required=False)

    date_of_birth = serializers.SerializerMethodField()

    def get_date_of_birth(self, obj):
        if obj.date_of_birth:
            date = datetime.strftime(obj.date_of_birth, "%d-%b-%Y")
            return date
        else:
            return None

    class Meta:
        model = Patient
        fields = (
            'slug', 'first_name', 'last_name', 'middle_name', 'patient_aka', 'national_no', 'gender', 'date_of_birth',
            'address1',
            'address2', 'address3', 'country_name', 'city_name'
            , 'state_name', 'state_name', 'zipcode', 'carrier', 'policy_number', 'group_number', 'contact_person',
            'contact_email', 'contact_phone', 'ethnicity', 'race')


class PatientWritableSerializer(BaseSerializer):
    class Meta:
        model = Patient
        exclude = ('id', 'slug', 'created_on', 'created_by', 'updated_on', 'updated_by')


class PatientEthnicityWritableSerializer(BaseSerializer):
    ethnicity = serializers.SlugRelatedField(slug_field="slug",
                                             queryset=Ethnicity.objects.all())

    class Meta:
        model = PatientEthnicity
        fields = ('patient', 'ethnicity')


class PatientRaceWritableSerializer(BaseSerializer):
    race = serializers.SlugRelatedField(slug_field="slug",
                                        queryset=Race.objects.all())

    class Meta:
        model = PatientRace
        fields = ('patient', 'race')

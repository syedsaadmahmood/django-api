from rest_framework import serializers

from django_synergy.synergy_auth.serializers import User
from django_synergy.cases.models import Patient, Diagnosis
from django_synergy.cases.models.clinical_information import PrescriptionUpload, Prescription, History, \
    PatientDiagnosis, Vitals
from django_synergy.synergy_libraries.serializers.diagnosis import DiagnosisSerializer
from django_synergy.utils.serializers import BaseSerializer
from datetime import datetime


class PrescriptionSerializer(BaseSerializer):
    prescription_upload = serializers.SerializerMethodField()

    def get_prescription_upload(self, obj):
        patient_prescription_upload = PrescriptionUpload.objects.filter(prescription_id=obj.id).last()
        if patient_prescription_upload:
            return PrescriptionUploadSerializer(patient_prescription_upload, many=False).data
        else:
            return None

    class Meta:
        model = Prescription
        fields = ('slug', 'referring_physician_name', 'note', 'referring_physician', 'prescription_upload')


class PrescriptionReadOnlySerializer(BaseSerializer):
    referring_physician = serializers.SlugRelatedField(
        slug_field='slug', queryset=User.objects.all(), required=False, allow_null=True)

    url = serializers.SerializerMethodField()

    def get_url(self, obj):
        patient_prescription_upload = PrescriptionUpload.objects.filter(prescription_id=obj.id).last()
        if patient_prescription_upload and patient_prescription_upload.presigned_url_for_get:
            return patient_prescription_upload.presigned_url_for_get
        else:
            return None

    presigned_url = serializers.SerializerMethodField()

    def get_presigned_url(self, obj):
        patient_prescription_upload = PrescriptionUpload.objects.filter(prescription_id=obj.id).last()
        if patient_prescription_upload and patient_prescription_upload.presigned_url:
            return patient_prescription_upload.presigned_url
        else:
            return None

    uuid = serializers.SerializerMethodField()

    def get_uuid(self, obj):
        patient_prescription_upload = PrescriptionUpload.objects.filter(prescription_id=obj.id).last()
        if patient_prescription_upload and patient_prescription_upload.uuid:
            return patient_prescription_upload.uuid
        else:
            return None

    filename = serializers.SerializerMethodField()

    def get_filename(self, obj):
        patient_prescription_upload = PrescriptionUpload.objects.filter(prescription_id=obj.id).last()
        if patient_prescription_upload and patient_prescription_upload.filename:
            return patient_prescription_upload.filename
        else:
            return None

    class Meta:
        model = Prescription
        fields = ('slug', 'referring_physician_name', 'note', 'referring_physician', 'url', 'uuid', 'filename', 'presigned_url')


class PrescriptionWritableSerializer(BaseSerializer):
    referring_physician = serializers.SlugRelatedField(
        slug_field='slug', queryset=User.objects.all(), required=False, allow_null=True)

    patient = serializers.SlugRelatedField(
        slug_field='slug', queryset=Patient.objects.all())

    class Meta:
        model = Prescription
        exclude = ('id', 'created_on', 'created_by', 'updated_on', 'updated_by')


class PrescriptionUploadSerializer(BaseSerializer):
    prescription = serializers.SlugRelatedField(slug_field="slug",
                                                queryset=Prescription.objects.filter())

    class Meta:
        model = PrescriptionUpload
        fields = (
            "uuid", "url", "filename", "presigned_url",
            "url_expiry", "url_created_on", "uploaded",
            "presigned_url_for_get", "prescription", "created_on",
        )
        read_only_fields = ("presigned_url", "presigned_url_for_get", "url", "created_on")


class PrescriptionUploadWritableSerializer(BaseSerializer):
    prescription = serializers.SlugRelatedField(slug_field="slug",
                                                queryset=Prescription.objects.filter())

    def __init__(self, *args, **kwargs):
        kwargs["partial"] = True
        super().__init__(*args, **kwargs)

    class Meta:
        model = PrescriptionUpload
        fields = (
            "filename", "url_expiry", "get_url_expiry",
            "uploaded", "presigned_url", "uuid",
            "presigned_url_for_get", "prescription", "created_on",
        )
        read_only_fields = ("presigned_url", "presigned_url_for_get", "created_on",)


class HistorySerializer(BaseSerializer):
    class Meta:
        model = History
        fields = ('slug', 'note', 'date')


class HistoryWritableSerializer(BaseSerializer):
    patient = serializers.SlugRelatedField(
        slug_field='slug', queryset=Patient.objects.all())

    class Meta:
        model = History
        exclude = ('id', 'created_on', 'created_by', 'updated_on', 'updated_by')


class PatientDiagnosisSerializer(BaseSerializer):
    class Meta:
        model = PatientDiagnosis
        exclude = ('id', 'slug', 'created_on', 'created_by', 'updated_on', 'updated_by')


class PatientDiagnosisWritableSerializer(BaseSerializer):
    diagnosis = serializers.SlugRelatedField(
        slug_field='slug', queryset=Diagnosis.objects.all())

    class Meta:
        model = PatientDiagnosis
        exclude = ('id', 'slug', 'created_on', 'created_by', 'updated_on', 'updated_by')


class PatientDiagnosisWritableCreateSerializer(BaseSerializer):
    patient = serializers.SlugRelatedField(
        slug_field='slug', queryset=Patient.objects.all())
    diagnosis = serializers.SlugRelatedField(
        slug_field='slug', queryset=Diagnosis.objects.all())

    class Meta:
        model = PatientDiagnosis
        exclude = ('id', 'slug', 'created_on', 'created_by', 'updated_on', 'updated_by')


class PatientDiagnosisReadOnlySerializer(BaseSerializer):
    diagnosis = DiagnosisSerializer()

    class Meta:
        model = PatientDiagnosis
        exclude = ('id', 'created_on', 'created_by', 'updated_on', 'updated_by')


class VitalsWritableSerializer(BaseSerializer):
    class Meta:
        model = Vitals
        exclude = ('id', 'slug', 'created_on', 'created_by', 'updated_on', 'updated_by')


class VitalsSerializer(BaseSerializer):
    class Meta:
        model = Vitals
        exclude = ('id', 'slug', 'created_on', 'created_by', 'updated_on', 'updated_by', 'case')


class VitalsReadOnlySerializer(BaseSerializer):
    discharge_date = serializers.SerializerMethodField()

    @staticmethod
    def get_discharge_date(obj):
        if obj.discharge_date:
            date = datetime.strftime(obj.discharge_date, "%d-%b-%Y")
            return date
        else:
            return None

    class Meta:
        model = Vitals
        exclude = ('id', 'created_on', 'created_by', 'updated_on', 'updated_by', 'case')

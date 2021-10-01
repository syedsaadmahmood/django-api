import csv

from django.utils import timezone

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from .models import Device, DeviceItem, DeviceUpload, DeviceUploadItems, DeviceSettings, EquipmentMaintenanceRecord, \
    DeviceSettingHistory, EquipmentEvent, EQUIPMENT_EVENT_CODES
from django_synergy.utils.serializers import BaseSerializer
from ..accounts.models import Account
from datetime import datetime

from ..cases.models import Case


class DeviceSerializer(BaseSerializer):
    account = serializers.SerializerMethodField()
    item = serializers.SerializerMethodField()
    sub_end_date = serializers.DateField()

    def get_item(self, obj):
        return {
            "item_number": obj.item.item_number,
            "configuration": obj.item.configuration
        }

    def get_account(self, obj):
        if obj.account:
            return {
                "account_id": obj.account.account_id,
                "slug": obj.account.slug,
                "parent_account_id": obj.account.parent_account.account_id if obj.account.parent_account else None,
                "parent_account_name": obj.account.parent_account.account_name if obj.account.parent_account else None,
                "account_name": obj.account.account_name,
            }
        else:
            return None

    class Meta:
        model = Device
        exclude = ['created_on', 'updated_on',
                   'created_by', 'updated_by', 'id']
        lookup_field = 'slug'


class DeviceReadOnlySerializer(BaseSerializer):
    item = serializers.SerializerMethodField()

    def get_item(self, obj):
        return {
            "item_number": obj.item.item_number,
            "configuration": obj.item.configuration
        }

    class Meta:
        model = Device
        fields = ('slug', 'serial_number', 'date_added', 'status', 'sub_start_date',
                  'is_active', 'item')
        lookup_field = 'slug'


class DeviceCreateSerializer(BaseSerializer):
    date_added = serializers.DateField()
    sub_start_date = serializers.DateField(required=False, allow_null=True)
    account = serializers.SlugRelatedField(
        slug_field='slug', queryset=Account.objects.all(), required=False, allow_null=True)
    item = serializers.SlugRelatedField(
        slug_field='slug', queryset=DeviceItem.objects.all(), required=False, allow_null=True)

    def validate(self, attrs):
        return super().validate(attrs)

    def create(self, validated_data):
        account = validated_data.get('account')
        if not account.current_active_subscription:
            # no longer required to check account subscriptions
            # raise ValidationError("Account subscription has expired or does not exist")
            pass
        else:
            if validated_data['sub_start_date'] is None:
                validated_data['sub_start_date'] = timezone.now().date()

        return super().create(validated_data)

    class Meta:
        model = Device
        fields = (
            "serial_number",
            "item",
            "date_added",
            "status",
            "account",
            "sub_start_date"
        )


class DeviceWritableSerializer(BaseSerializer):
    class Meta:
        model = Device
        lookup_field = 'slug'
        fields = (
            "status",
            "is_active",
        )


class SimpleDeviceSerializer(BaseSerializer):
    class Meta:
        model = Device
        lookup_field = 'slug'
        fields = (
            "serial_number",
            'slug'
        )


class DeviceSummarySerializer(BaseSerializer):
    account = serializers.SerializerMethodField()

    def get_account(self, obj):
        return obj.account.account_name

    class Meta:
        model = Device
        fields = (
            'serial_number',
            'account',
            'status',
            'slug'
        )


class DeviceItemSerializer(BaseSerializer):
    class Meta:
        model = DeviceItem
        lookup_field = 'slug'
        fields = (
            "item_number",
            "configuration",
            "slug"
        )


class DeviceUploadItemSerializer(BaseSerializer):
    class Meta:
        model = DeviceUploadItems
        lookup_field = 'slug'
        fields = (
            "device_upload",
            "serial_number",
            "date_added",
            "status",
            "slug",
            "account_number",
            "sub_start_date",
            "item_number",
            "errors"
        )


class DeviceUploadSerializer(BaseSerializer):
    items = DeviceUploadItemSerializer(many=True)

    class Meta:
        model = DeviceUpload
        lookup_field = 'slug'
        fields = (
            "upload",
            "slug",
            'id',
            "items"
        )


class DeviceUploadWritableSerializer(BaseSerializer):
    class Meta:
        model = DeviceUpload
        lookup_field = 'slug'
        fields = (
            "upload",
            'id'
        )


class DeviceSettingsSerializer(BaseSerializer):
    class Meta:
        model = DeviceSettings
        lookup_field = 'id'
        exclude = ['created_on', 'updated_on', 'created_by', 'updated_by']


class DeviceSettingHistoryWritableSerializer(BaseSerializer):
    class Meta:
        model = DeviceSettingHistory
        lookup_field = 'slug'
        exclude = ['created_on', 'updated_on', 'created_by', 'updated_by', 'id']


class DeviceSettingHistorySerializer(BaseSerializer):
    case_no = serializers.SerializerMethodField()
    created_by = serializers.SerializerMethodField()
    created_on = serializers.SerializerMethodField()

    def get_case_no(self, obj):
        return obj.case.case_no

    def get_created_on(self, obj):
        return datetime.strftime(obj.created_on.date(), "%d-%b-%Y")

    def get_created_by(self, obj):
        return obj.created_by.first_name + " " + obj.created_by.last_name

    class Meta:
        model = DeviceSettingHistory
        lookup_field = 'slug'
        fields = ['case_no', 'created_by', 'created_on', 'note', 'slug', 'is_active']


class EquipmentMaintenanceRecordSerializer(BaseSerializer):
    device = serializers.SlugRelatedField(slug_field='slug', queryset=Device.objects.all())

    class Meta:
        model = EquipmentMaintenanceRecord
        lookup_field = 'slug'
        exclude = ['created_on', 'updated_on', 'created_by', 'updated_by', 'id']


class EquipmentMaintenanceRecordReadOnlySerializer(BaseSerializer):
    device = SimpleDeviceSerializer(many=False)
    created_on = serializers.SerializerMethodField()
    created_by = serializers.SerializerMethodField()

    def get_created_on(self, obj):
        return datetime.strftime(obj.created_on.date(), "%d-%b-%Y")

    def get_created_by(self, obj):
        return obj.created_by.first_name + " " + obj.created_by.last_name

    class Meta:
        model = EquipmentMaintenanceRecord
        lookup_field = 'slug'
        fields = (
            "created_by",
            "created_on",
            'note',
            "device"
        )


class EquipmentWritableEventSerializer(BaseSerializer):
    case = serializers.SlugRelatedField(slug_field='slug', queryset=Case.objects.all())
    device = serializers.SlugRelatedField(slug_field='slug', queryset=Device.objects.all())

    class Meta:
        model = EquipmentEvent
        fields = ('case', 'device', 'event_code', 'event_start_date_time', 'event_duration', 'slug')


class EquipmentEventSerializer(BaseSerializer):
    case = serializers.SlugRelatedField(slug_field='slug', queryset=Case.objects.all())
    device = serializers.SlugRelatedField(slug_field='slug', queryset=Device.objects.all())
    event_code = serializers.CharField(source='get_event_code_display')

    class Meta:
        model = EquipmentEvent
        fields = ('case', 'device', 'event_code', 'event_start_date_time', 'event_duration', 'slug', 'id')


class EquipmentEventReportSerializer(BaseSerializer):
    event_code = serializers.CharField(source='get_event_code_display')
    event_date = serializers.DateTimeField(format='%d-%b-%Y', source='event_start_date_time')
    event_time = serializers.DateTimeField(format='%I:%M:%S %p', source='event_start_date_time')

    class Meta:
        model = EquipmentEvent
        fields = ('event_code', 'event_duration', 'event_date', 'event_time')

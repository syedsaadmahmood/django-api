from uuid import uuid4
from datetime import datetime

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.contrib.postgres.fields import JSONField
from django.utils.translation import ugettext_lazy as _

from django_extensions.db.fields import AutoSlugField

from django_synergy.devices.utils import *
from django_synergy.utils.models import AbstractBaseModel
from django_synergy.accounts.models import Account
from django_synergy.events.utils.constants import IDS_SMQEV_MEMFULLWARNING, IDS_SMQEV_MEMFULL, IDS_SMQEV_LOWBAT1, \
    IDS_SMQEV_LOWBAT2, IDS_SMQEV_RESPLOOSE, IDS_SMQEV_OXLOOSE, IDS_SMQEV_XTALARM2, IDS_SMQEV_PWRUP, IDS_SMQEV_KEYBDMODE, \
    IDS_SMQEV_PARMCHG, IDS_SMQEV_OXON, IDS_SMQEV_TIMEDATE, IDS_SMQEV_EVENTDLOAD, IDS_SMQEV_EVENTCLEAR, \
    IDS_ESCORTEV_POWEROFF, IDS_SMQEV_NEWBATT, IDS_SMQEV_HOSTMODE, IDS_ESCORTEV_MARKEDASDOWNLOADED, \
    IDS_SMQEV_PPLOOSE_REVE, IDS_SMQEV_BADRTCBATTERY, IDS_SMQEV_PPCLEARED_REVE, IDS_SMQEV_NEWBATTERY_REVE, \
    IDS_SMQEV_MEMCLEARED_REVE

EQUIPMENT_EVENT_CODES = ((IDS_SMQEV_MEMFULLWARNING, _("Memory Almost Full")), (IDS_SMQEV_MEMFULL, _("Memory Full")),
                         (IDS_SMQEV_LOWBAT1, _("Battery Low Warning")),
                         (IDS_SMQEV_LOWBAT2, _("Battery Very Low Warning")),
                         (IDS_SMQEV_RESPLOOSE, _("Resp/ECG Loose Lead")), (IDS_SMQEV_OXLOOSE, _("Oximeter Loose Lead")),
                         (IDS_SMQEV_XTALARM2, _("External Alarm #2")), (IDS_SMQEV_PWRUP, _("SmartMonitor ON")),
                         (IDS_SMQEV_KEYBDMODE, _("Menu Mode Active")),
                         (IDS_SMQEV_PARMCHG, _("Host System Parm Modified")),
                         (IDS_SMQEV_OXON, _("Oximeter ON")), (IDS_SMQEV_TIMEDATE, _("Time/Date Modified")),
                         (IDS_SMQEV_EVENTDLOAD, _("Request Event Table")),
                         (IDS_SMQEV_EVENTCLEAR, _("Clear Event Table")),
                         (IDS_ESCORTEV_POWEROFF, _("SmartMonitor OFF")), (IDS_SMQEV_NEWBATT, _("New Battery")),
                         (IDS_SMQEV_HOSTMODE, _("Communications Mode")),
                         (IDS_ESCORTEV_MARKEDASDOWNLOADED, _("Successful download")),
                         (IDS_SMQEV_PPLOOSE_REVE, _("Patient Position Sensor Loose Lead")),
                         (IDS_SMQEV_BADRTCBATTERY, _("Real Time Clock Battery Fail")),
                         (IDS_SMQEV_PPCLEARED_REVE, _("Patient Position Space Cleared")),
                         (IDS_SMQEV_NEWBATTERY_REVE, _("New Battery")),
                         (IDS_SMQEV_MEMCLEARED_REVE, _("Memory Cleared")),
                         )


def slugify(content):
    if type(content) == datetime:
        content = str(content.date())
    else:
        content = str(content)
    return content.replace('_', '-').lower()


def slugifyDeviceSettings(content):
    returnValue = 'settings-' + content
    return returnValue.replace('_', '-').lower()


def slugify_upload(content):
    return str(uuid4())


def user_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    name = filename.split('.')[0]
    ext = filename.split('.')[-1]
    return '{0}/device_import/{1}'.format(settings.S3_ENVIRON, '{0}_{1}.{2}'.format(name, uuid4(), ext))


DEVICE_STATUS = [('Assigned', 'Assigned'),
                 ('Available', 'Available'),
                 ('Lost or Broken', 'Lost or Broken'),
                 ('In Checkout', 'In Checkout')]


class DeviceSettings(AbstractBaseModel):
    slug = models.CharField(max_length=1, null=True, blank=True)
    apnea = models.CharField(choices=APNEA_LIST, max_length=50, default='20')
    bradycardia = models.CharField(choices=BRADYCARDIA_LIST, max_length=50, default='80')
    bradycardia_delay = models.CharField(choices=BRADYCARDIADELAY_LIST, max_length=50, default='0')
    low_breadth = models.CharField(choices=LOWBREADTH_LIST, max_length=50, default='Off')
    tachycardia = models.CharField(choices=TACHYCARDIA_LIST, max_length=50, default='230')
    tachycardia_delay = models.CharField(choices=TACHYCARDIADELAY_LIST, max_length=50, default='5')
    high_spo2 = models.CharField(choices=HIGHSPO2_LIST, max_length=50, default='Off')
    low_spo2 = models.CharField(choices=LOWSPO2_LIST, max_length=50, default='90')
    spo2_delay = models.CharField(choices=SPO2DELAY_LIST, max_length=50, default='5')
    record_mode = models.CharField(choices=RECORDMODE_LIST, max_length=50, default='Event Log')
    qrs = models.BooleanField(default=True)
    hr_trend = models.BooleanField(default=True)
    respiration = models.BooleanField(default=True)
    respiratory_rate = models.BooleanField(default=True)
    plethysmograph = models.BooleanField(default=True)
    spo2 = models.BooleanField(default=True)
    pulse_rate = models.BooleanField(default=False)
    apnea_delay_for_record = models.CharField(choices=APNEADELAYFORRECORD_LIST, max_length=50, default='16')
    bradycardia_for_record = models.CharField(choices=BRADYCARDIAFORRECORD_LIST, max_length=50, default='Off')
    spo2_for_record = models.CharField(choices=SPO2FORRECORD_LIST, max_length=50, default='Off')
    pre_post_time = models.CharField(choices=PREPOSTTIME_LIST, max_length=50, default='30/15')
    auxliary_channels1 = models.CharField(choices=AUXLIARYCHANNELS_LIST, max_length=50, default='Off')
    auxliary_channels2 = models.CharField(choices=AUXLIARYCHANNELS_LIST, max_length=50, default='Off')
    auxliary_channels3 = models.CharField(choices=AUXLIARYCHANNELS_LIST, max_length=50, default='Off')
    auxliary_channels4 = models.CharField(choices=AUXLIARYCHANNELS_LIST, max_length=50, default='Off')
    date_format = models.CharField(choices=DATEFORMAT_LIST, max_length=50, default='Month/Day/Year')
    memory_full_alert = models.CharField(choices=MEMORYFULLALERT_LIST, max_length=50, default='50')
    memory_full_audible = models.BooleanField(default=False)
    rate_display_on_lcd = models.BooleanField(default=True)
    front_panel_numeric_display = models.BooleanField(default=True)
    hospital_mode = models.BooleanField(default=False)
    display_hcp_info = models.BooleanField(default=False)
    heart_rate_method = models.CharField(choices=HEARTRATEMETHOD_LIST, max_length=50, default='Time Average')
    external_equipment_trigger = models.CharField(choices=EXTERNALEQUIPMENTTRIGGER_LIST, max_length=50, default='Off')
    external_physiological_trigger = models.CharField(choices=EXTERNALPHYSIOLOGICALTRIGGER_LIST, max_length=50,
                                                      default='Off')
    average_timing = models.CharField(choices=AVERAGETIMING_LIST, max_length=50, default='Off')
    probe_off_processing = models.CharField(choices=PROBEOFFPROCESSING_LIST, max_length=50, default='Off')
    embedded_application = models.FloatField(default=0)
    maintenance_mode = models.FloatField(default=0)
    boot_block = models.FloatField(default=0)
    modem_present = models.BooleanField(default=True)
    pc_card_present = models.BooleanField(default=True)
    oximeter_present = models.BooleanField(default=False)

    def __str__(self):
        return str(self.id)

    # def __eq__(self, other):
    #     if self.apnea == other.get('apnea') and \
    #         self.bradycardia == other.get('bradycardia') and \
    #         self.bradycardia_delay == other.get('bradycardia_delay') and \
    #         self.low_breadth == other.get('low_breadth') and \
    #         self.tachycardia == other.get('tachycardia') and \
    #         self.tachycardia_delay == other.get('tachycardia_delay') and \
    #         self.high_spo2 == other.get('high_spo2') and \
    #         self.low_spo2 == other.get('low_spo2') and \
    #         self.spo2_delay == other.get('spo2_delay') and \
    #         self.record_mode == other.get('record_mode') and \
    #         self.qrs == other.get('qrs') and \
    #         self.hr_trend == other.get('hr_trend') and \
    #         self.respiration == other.get('respiration') and \
    #         self.respiratory_rate == other.get('respiratory_rate') and \
    #         self.plethysmograph == other.get('plethysmograph') and \
    #         self.spo2 == other.get('spo2') and \
    #         self.pulse_rate == other.get('pulse_rate') and \
    #         self.apnea_delay_for_record == other.get('apnea_delay_for_record') and \
    #         self.bradycardia_for_record == other.get('bradycardia_for_record') and \
    #         self.spo2_for_record == other.get('spo2_for_record') and \
    #         self.pre_post_time == other.get('pre_post_time') and \
    #         self.auxliary_channels1 == other.get('auxliary_channels1') and \
    #         self.auxliary_channels2 == other.get('auxliary_channels2') and \
    #         self.auxliary_channels3 == other.get('auxliary_channels3') and \
    #         self.auxliary_channels4 == other.get('auxliary_channels4') and \
    #         self.date_format == other.get('date_format') and \
    #         self.memory_full_alert == other.get('memory_full_alert') and \
    #         self.memory_full_audible == other.get('memory_full_audible') and \
    #         self.rate_display_on_lcd == other.get('rate_display_on_lcd') and \
    #         self.front_panel_numeric_display == other.get('front_panel_numeric_display') and \
    #         self.hospital_mode == other.get('hospital_mode') and \
    #         self.display_hcp_info == other.get('display_hcp_info') and \
    #         self.heart_rate_method == other.get('heart_rate_method') and \
    #         self.external_equipment_trigger == other.get('external_equipment_trigger') and \
    #         self.external_physiological_trigger == other.get('external_physiological_trigger') and \
    #         self.average_timing == other.get('average_timing') and \
    #         self.probe_off_processing == other.get('probe_off_processing') and \
    #         self.embedded_application == other.get('embedded_application') and \
    #         self.maintenance_mode == other.get('maintenance_mode') and \
    #         self.boot_block == other.get('boot_block') and \
    #         self.modem_present == other.get('modem_present') and \
    #         self.pc_card_present == other.get('pc_card_present'):
    #         return True
    #     else:
    #         return False


class Device(AbstractBaseModel):
    serial_number = models.CharField(max_length=10, unique=True)
    date_added = models.DateField()
    status = models.CharField(choices=DEVICE_STATUS,
                              max_length=50, default='Available')
    slug = AutoSlugField(max_length=255, db_index=True, allow_unicode=True,
                         unique=True, populate_from='serial_number', slugify_function=slugify)
    account = models.ForeignKey(
        Account, related_name="devices", on_delete=models.PROTECT, blank=True)
    sub_start_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    item = models.ForeignKey(
        'DeviceItem', on_delete=models.PROTECT, related_name='devices', null=True)
    settings = models.ManyToManyField(DeviceSettings, through='DeviceSettingHistory', related_name='device_settings',
                                      blank=True, symmetrical=False)

    def __str__(self):
        return self.serial_number

    @property
    def sub_end_date(self):
        if len(self.account.user_subscriptions.filter(is_active=True).all()) > 0:
            return self.account.user_subscriptions.order_by('-created_on')[0].user_end_date
        else:
            return None

    class Meta:
        default_permissions = ()
        permissions = [
            ("device-list-account", _("Can view list of account devices")),
            ("device-view-detail-account", _("Can view detail of account devices")),
            ("device-edit-account", _("Can edit account devices")),
            ("device-view-settings-account", _("Can view settings of account devices")),
            ("device-edit-settings-account", _("Can edit settings of account devices")),
            ("device-view-settings-history-account", _("Can view setting history of account devices")),
            ("device-view-eqp-record-account", _("Can view equipment record of account devices")),
            ("device-edit-eqp-record-account", _("Can edit equipment record of account devices")),

            ("device-list-subsidiary", _("Can view list of subsidiary account devices")),
            ("device-view-detail-subsidiary", _("Can view detail of subsidiary account devices")),
            ("device-edit-subsidiary", _("Can edit subsidiary account devices")),
            ("device-view-settings-subsidiary", _("Can view settings of subsidiary account devices")),
            ("device-edit-settings-subsidiary", _("Can edit settings of subsidiary account devices")),
            ("device-view-settings-history-subsidiary", _("Can view setting history of subsidiary account devices")),
            ("device-view-eqp-record-subsidiary ", _("Can view equipment record of subsidiary account devices")),
            ("device-edit-eqp-record-subsidiary", _("Can edit equipment record of subsidiary account devices")),

            ("device-list-hq", _("Can view list of hq account devices")),
            ("device-view-detail-hq", _("Can view detail of hq account devices")),
            ("device-view-settings-hq", _("Can view settings of hq account devices")),
            ("device-view-settings-history-hq", _("Can view setting history of hq account devices")),
            ("device-view-eqp-record-hq ", _("Can view equipment record of hq account devices")),

            ("device-list-assc", _("Can view list of associated account devices")),
            ("device-view-detail-assc", _("Can view detail of associated account devices")),
            ("device-view-settings-assc", _("Can view settings of associated account devices")),
            ("device-view-settings-history-assc", _("Can view setting history of associated account devices")),
            ("device-view-eqp-record-assc ", _("Can view equipment record of associated account devices")),

            ("device-list-assigned", "Can view device of assigned cases"),
            ("device-view-detail-assigned", "Can view detail device of assigned cases"),
            ("device-view-settings-assigned", "Can view device settings of assigned cases"),
            ("device-view-settings-history-assigned", "Can view device setting history of assigned cases"),
            ("device-view-eqp-record-assigned", "Can view equipment record of assigned cases"),
        ]


class DeviceSettingHistory(AbstractBaseModel):
    slug = AutoSlugField(max_length=255, db_index=True, allow_unicode=True, unique=True,
                         populate_from=['device__serial_number', 'created_on'],
                         slugify_function=slugify)
    case = models.ForeignKey('cases.Case', related_name="history_case", on_delete=models.PROTECT)
    device = models.ForeignKey(Device, related_name="history_device", on_delete=models.PROTECT)
    device_settings = models.ForeignKey(DeviceSettings, related_name="history_device_settings",
                                        on_delete=models.PROTECT)
    is_active = models.BooleanField(default=False, null=False)
    note = models.CharField(max_length=512, null=True, blank=True)


class DeviceItem(AbstractBaseModel):
    item_number = models.CharField(max_length=10, unique=True)
    configuration = models.CharField(max_length=255)
    slug = AutoSlugField(max_length=255, db_index=True, allow_unicode=True, unique=True,
                         populate_from='item_number', slugify_function=slugify)

    class Meta:
        permissions = []


def validate_upload(value):
    # Probably worth doing this check first anyway
    if not value.name.endswith(('.csv', '.xlsx', '.xls')):
        raise ValidationError('Invalid file type')


# class DeviceImport(AbstractBaseModel):

#     upload = models.FileField(
#         upload_to='device_imports', validators=[validate_upload])
#     slug = AutoSlugField(max_length=255, db_index=True, allow_unicode=True, unique=True,
#                          populate_from='id', slugify_function=slugify)


class DeviceUpload(AbstractBaseModel):
    _key_prefix = settings.DEVICE_IMPORT_KEY_PREFIX

    upload = models.FileField(
        upload_to=user_directory_path, validators=[validate_upload])
    slug = models.CharField(max_length=1, null=True, blank=True)


class DeviceUploadItems(AbstractBaseModel):
    device_upload = models.ForeignKey(DeviceUpload, on_delete=models.CASCADE, related_name="items")
    serial_number = models.CharField(max_length=20, null=True, blank=True)
    date_added = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=50, null=True, blank=True)
    slug = models.CharField(max_length=1, null=True, blank=True)
    account_number = models.CharField(max_length=50, null=True, blank=True)
    sub_start_date = models.DateField(null=True, blank=True)
    item_number = models.CharField(max_length=50, null=True, blank=True)
    is_imported = models.BooleanField(default=False)
    errors = JSONField()


class EquipmentMaintenanceRecord(AbstractBaseModel):
    device = models.ForeignKey(Device, on_delete=models.PROTECT, related_name='device_record')
    note = models.CharField(max_length=512, null=True, blank=True)
    slug = AutoSlugField(max_length=255, db_index=True, allow_unicode=True, unique=True,
                         populate_from='device__serial_number', slugify_function=slugify)


class EquipmentEvent(AbstractBaseModel):
    slug = models.CharField(max_length=255, unique=True, db_index=True)
    case = models.ForeignKey('cases.Case', related_name="case_equipment_events", on_delete=models.PROTECT)
    device = models.ForeignKey(Device, related_name="device_equipment_events", on_delete=models.PROTECT)
    event_code = models.PositiveSmallIntegerField(max_length=255, choices=EQUIPMENT_EVENT_CODES)
    event_start_date_time = models.DateTimeField()
    event_duration = models.DurationField()

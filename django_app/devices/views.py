import os
from io import TextIOWrapper
from tempfile import mkstemp
import datetime
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError

from django.utils import timezone

# from config.settings.base import MEDIA_URL, MEDIA_ROOT
from django_synergy.utils.views import BaseViewset, isSuperUser
from .models import DEVICE_STATUS, DeviceSettings, EquipmentMaintenanceRecord, DeviceSettingHistory

from .serializers import DeviceSerializer, DeviceCreateSerializer, DeviceWritableSerializer, DeviceItemSerializer, \
    DeviceUploadSerializer, DeviceUploadWritableSerializer, DeviceUploadItemSerializer, DeviceSettingsSerializer, \
    EquipmentMaintenanceRecordSerializer, EquipmentMaintenanceRecordReadOnlySerializer, DeviceSettingHistorySerializer, \
    DeviceSettingHistoryWritableSerializer, DeviceReadOnlySerializer
from .models import Device, DeviceItem, DeviceUpload, DeviceUploadItems
from .permissions import CanViewDeviceList, CanViewDeviceDetail, CanEditDevice, CanViewDeviceSetting, \
    CanViewDeviceSettingHistory, CanViewEquipmentRecord, CanEditEquipmentRecord

from drf_jwt_2fa.authentication import Jwt2faAuthentication
from rest_framework.response import Response
from rest_framework import status
import csv
from xlrd import open_workbook, xldate_as_tuple

from ..accounts.models import Account
from django_synergy.users.permissions import isSuperUser

# key: internal column
# value: external the column file uses
from ..notifications.utils import generate_user_notification
from ..users.models import User
from django_synergy.utils.permissions import get_user_permission_list, user_has_permission
from rest_framework.permissions import IsAuthenticated

DEVICE_IMPORT_DICTIONARY = {
    "serial_number": "serial_number",
    "item_number": "item_number",
    "date_added": "date_added",
    "status": "status",
    # "firmware_revision": "firmware_revision",
    "account_number": "account_number",
    "sub_start_date": "sub_start_date",
}


def try_parsing_date(text):
    for fmt in ('%d-%b-%Y', '%d-%b-%y'):
        try:
            return datetime.datetime.strptime(text, fmt)
        except ValueError:
            pass
    raise ValueError('no valid date format found')


def map_coloumns(to_be_mapped, DEVICE_IMPORT_DICTIONARY):
    my_dict = {}

    for key in DEVICE_IMPORT_DICTIONARY.keys():
        my_dict[key] = to_be_mapped[DEVICE_IMPORT_DICTIONARY[key]]

    to_be_mapped = my_dict


def append_errors(import_device, serial_numbers, result):
    import_device["serial_exists"] = True if Device.objects.filter(
        serial_number=import_device["serial_number"]).count() > 0 else False

    if import_device[DEVICE_IMPORT_DICTIONARY["serial_number"]] in serial_numbers:
        import_device["dublicate_entry"] = True
        result[serial_numbers.index(
            import_device["serial_number"])]["dublicate_entry"] = True
    else:
        import_device["dublicate_entry"] = False

    import_device["account_exist"] = True if Account.objects.filter(
        account_id=import_device["account"]).count() == 0 else False


def get_slug(id):
    try:
        account = Account.objects.get(account_id=id).slug
        return account
    except:
        return ''


class DeviceViewSet(BaseViewset):
    queryset = Device.objects.all()
    lookup_field = 'slug'
    action_serializers = {
        'default': DeviceSerializer,
        'create': DeviceCreateSerializer,
        'update': DeviceWritableSerializer,
        'bulk_create': DeviceCreateSerializer

    }

    @action(["post"], detail=False)
    def bulk_create(self, request, *args, **kwargs):
        data = request.data
        for device in data:
            device['account'] = get_slug(device['account'])
        serializer = self.get_serializer(data=data, many=True)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(status=status.HTTP_200_OK)

    def get_queryset(self):
        user = self.request.user
        devices = Device.objects.none()

        if user.is_superuser:
            return Device.objects.all()
        if hasattr(user, 'account'):
            user_permissions = get_user_permission_list(user)
            if user_has_permission('device-list-account', user_permissions):
                devices = devices | Device.objects.filter(account__id=user.account_id)
            if user_has_permission('device-list-subsidiary', user_permissions):
                devices = devices | Device.objects.filter(account__parent_account__id=user.account_id)
            if user_has_permission('device-list-hq', user_permissions):
                if user.account.parent_account:
                    devices = devices | Device.objects.filter(account__id=user.account.parent_account.id)
            if user_has_permission('device-list-assc', user_permissions):
                associated_to_accounts = [ass_acc.to_account for ass_acc in
                                          user.account.from_account.filter(accepted=True)]
                associated_from_accounts = [ass_acc.from_account for ass_acc in
                                            user.account.to_account.filter(accepted=True)]
                associated_accounts = associated_to_accounts + associated_from_accounts
                associated_devices = Device.objects.filter(account__in=associated_accounts)
                devices = devices | associated_devices
            return devices

        else:
            return Device.objects.none()

    def get_permissions(self):
        if self.action == "create":
            self.permission_classes = [isSuperUser, ]
        elif self.action == "update":
            self.permission_classes = [CanEditDevice, ]
        elif self.action == "list":
            self.permission_classes = [CanViewDeviceList, ]
        elif self.action == "retrieve":
            self.permission_classes = [CanViewDeviceDetail, ]
        elif self.action == "partial_update":
            self.permission_classes = [CanEditDevice, ]
        elif self.action == "destroy":
            self.permission_classes = [isSuperUser, ]
        elif self.action == "set_status":
            self.permission_classes = [CanEditDevice, ]
        elif self.action == "device_current_settings":
            self.permission_classes = [CanViewDeviceSetting, ]
        elif self.action == "device_settings_history":
            self.permission_classes = [CanViewDeviceSettingHistory, ]
        elif self.action == "account_devices":
            self.permission_classes = [CanViewDeviceList, ]
        elif self.action == "transfer_devices":
            self.permission_classes = [isSuperUser, ]
        return super().get_permissions()

    @action(["patch"], detail=True)
    def set_status(self, request, *args, **kwargs):
        try:
            data = request.data
            device = Device.objects.get(slug=kwargs["slug"])
            device.status = data["status"]
            device.save()

            data["device"] = kwargs["slug"]

            maintenance_record_serializer = EquipmentMaintenanceRecordSerializer(data=data,
                                                                                 context=self.get_serializer_context())
            if maintenance_record_serializer.is_valid(raise_exception=True):
                maintenance_record_serializer_data = maintenance_record_serializer.validated_data
                maintenance_record_serializer.save()

            return Response({"status": "success", "message": "Equipment Maintenance Record is created successfully"}
                            , status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"status": "failed", "message": e}
                            , status=status.HTTP_400_BAD_REQUEST)

    @action(["get"], detail=True)
    def device_current_settings(self, request, *args, **kwargs):

        try:
            device = Device.objects.get(slug=kwargs["slug"])

            device_setting_history = DeviceSettingHistory.objects.get(device=device, is_active=True)
            device_setting_serializer = DeviceSettingsSerializer(device_setting_history.device_settings,
                                                                 many=False).data
            return Response(status=status.HTTP_200_OK,
                            data={"success": True, "data": device_setting_serializer})

        except Exception as e:
            return Response({"status": "failed", "message": e}
                            , status=status.HTTP_400_BAD_REQUEST)

    @action(["get"], detail=True)
    def device_settings_history(self, request, *args, **kwargs):
        try:
            device = Device.objects.get(slug=kwargs["slug"])
            device_setting_history = DeviceSettingHistory.objects.filter(device=device, is_active=False)
            device_setting_history_serializer = DeviceSettingHistorySerializer(device_setting_history, many=True).data
            return Response(status=status.HTTP_200_OK,
                            data={"success": True, "data": device_setting_history_serializer})

        except Exception as e:
            return Response({"status": "failed", "message": e}
                            , status=status.HTTP_400_BAD_REQUEST)

    @action(["get"], detail=False, permission_classes=[isSuperUser])
    def account_devices(self, request, *args, **kwargs):
        try:
            account_slug = request.query_params.get('account', None)
            account = Account.objects.get(slug=account_slug)
            device = Device.objects.filter(account=account)
            device_serializer = DeviceReadOnlySerializer(device, many=True).data
            return Response(status=status.HTTP_200_OK,
                            data={"success": True, "data": device_serializer})

        except Exception as e:
            return Response({"status": "failed", "message": e}
                            , status=status.HTTP_400_BAD_REQUEST)

    @action(["post"], detail=False, permission_classes=[isSuperUser])
    def transfer_devices(self, request, *args, **kwargs):
        try:
            data = request.data
            from_account = Account.objects.get(slug=data["from_account"])
            to_account = Account.objects.get(slug=data["to_account"])
            devices = Device.objects.filter(slug__in=data["devices"])
            devices_list = []

            for device in devices:
                device.account = to_account
                devices_list.append(str(device.serial_number))
                device.save()

            serial_numbers = ', '.join(devices_list)

            from_account_users = User.objects.filter(account=from_account)
            from_account_admin = None
            for from_account_user in from_account_users:
                if from_account_user.groups.filter(name='Account Admin').count() > 0:
                    from_account_admin = from_account_user
                    break

            to_account_users = User.objects.filter(account=to_account)
            to_account_admin = None
            for to_account_user in to_account_users:
                if to_account_user.groups.filter(name='Account Admin').count() > 0:
                    to_account_admin = to_account_user
                    break

            if from_account_admin is not None:
                generate_user_notification(
                    action="Devices Transferred From Account", to_user=from_account_admin, from_user=request.user,
                    from_user_name=request.user.first_name + " " + request.user.last_name,
                    to_account_name=to_account.account_name, from_account_name=from_account.account_name,
                    device_serial_Numbers=serial_numbers)

            if to_account_admin is not None:
                generate_user_notification(
                    action="Devices Transferred To Account", to_user=to_account_admin, from_user=request.user,
                    from_user_name=request.user.first_name + " " + request.user.last_name,
                    to_account_name=to_account.account_name, from_account_name=from_account.account_name,
                    device_serial_Numbers=serial_numbers)

            return Response(status=status.HTTP_200_OK,
                            data={"success": True, "message": "Devices transferred successfully"})

        except Exception as e:
            return Response({"status": "failed", "message": e}
                            , status=status.HTTP_400_BAD_REQUEST)


class EquipmentMaintenanceRecordViewSet(BaseViewset):
    queryset = EquipmentMaintenanceRecord.objects.all()
    lookup_field = 'slug'
    action_serializers = {
        'default': EquipmentMaintenanceRecordSerializer,
        'list': EquipmentMaintenanceRecordReadOnlySerializer,
        'retrieve': EquipmentMaintenanceRecordReadOnlySerializer,
    }

    def get_queryset(self):
        user = self.request.user
        eqp_records = EquipmentMaintenanceRecord.objects.none()

        if user.is_superuser:
            return EquipmentMaintenanceRecord.objects.all()
        if hasattr(user, 'account'):
            user_permissions = get_user_permission_list(user)
            if user_has_permission('device-view-eqp-record-account', user_permissions):
                eqp_records = eqp_records | EquipmentMaintenanceRecord.objects.filter(
                    device__account__id=user.account_id)
            if user_has_permission('device-view-eqp-record-subsidiary', user_permissions):
                eqp_records = eqp_records | Device.objects.filter(device__account__parent_account__id=user.account_id)
            if user_has_permission('device-view-eqp-record-hq', user_permissions):
                if user.account.parent_account:
                    eqp_records = eqp_records | EquipmentMaintenanceRecord.objects.filter(
                        device__account__id=user.account.parent_account.id)
            if user_has_permission('device-view-eqp-record-assc', user_permissions):
                associated_to_accounts = [ass_acc.to_account for ass_acc in
                                          user.account.from_account.filter(accepted=True)]
                associated_from_accounts = [ass_acc.from_account for ass_acc in
                                            user.account.to_account.filter(accepted=True)]
                associated_accounts = associated_to_accounts + associated_from_accounts
                associated_eqp_records = EquipmentMaintenanceRecord.objects.filter(
                    device__account__in=associated_accounts)
                eqp_records = eqp_records | associated_eqp_records
            return eqp_records

        else:
            return EquipmentMaintenanceRecord.objects.none()

    def get_permissions(self):
        if self.action == "create":
            self.permission_classes = [isSuperUser, ]
        elif self.action == "update":
            self.permission_classes = [CanEditEquipmentRecord, ]
        elif self.action == "list":
            self.permission_classes = [CanViewEquipmentRecord, ]
        elif self.action == "retrieve":
            self.permission_classes = [CanViewEquipmentRecord, ]
        elif self.action == "partial_update":
            self.permission_classes = [CanEditEquipmentRecord, ]
        elif self.action == "destroy":
            self.permission_classes = [isSuperUser, ]
        return super().get_permissions()

    @action(methods=['GET'], detail=True)
    def device(self, request, *args, **kwargs):
        try:
            eqp_records = EquipmentMaintenanceRecord.objects.filter(device__slug=kwargs['slug'])
            for eqp_record in eqp_records:
                self.check_object_permissions(self.request, eqp_record)
            eqp_record_serializer = EquipmentMaintenanceRecordReadOnlySerializer(eqp_records, many=True).data
            return Response(status=status.HTTP_200_OK,
                            data={"success": True, "data": eqp_record_serializer})

        except Exception as e:
            return Response({"status": "failed", "message": e}
                            , status=status.HTTP_400_BAD_REQUEST)


class DeviceItemViewSet(BaseViewset):
    queryset = DeviceItem.objects.all()
    lookup_field = 'slug'
    action_serializers = {
        'default': DeviceItemSerializer
    }

    def get_permissions(self):
        if self.action == "create":
            self.permission_classes = [isSuperUser, ]
        elif self.action == "update":
            self.permission_classes = [isSuperUser, ]
        elif self.action == "list":
            self.permission_classes = [IsAuthenticated, ]
        elif self.action == "retrieve":
            self.permission_classes = [IsAuthenticated, ]
        elif self.action == "partial_update":
            self.permission_classes = [isSuperUser, ]
        elif self.action == "destroy":
            self.permission_classes = [isSuperUser, ]
        return super().get_permissions()


class DeviceUploadViewSet(BaseViewset):
    queryset = DeviceUpload.objects.all()
    lookup_field = 'id'
    permission_classes = [isSuperUser, ]
    action_serializers = {
        'default': DeviceUploadSerializer,
        'create': DeviceUploadWritableSerializer,

    }

    def get_serializer_context(self):
        context = super(DeviceUploadViewSet, self).get_serializer_context()
        # context.update({
        #     "exclude_email_list": ['test@test.com', 'test1@test.com']
        #     # extra data
        # })
        return context

    def create(self, request, *args, **kwargs):
        file = request.FILES['upload']
        temp_file, temp_path = mkstemp()
        with open(temp_path, 'wb') as f:
            f.write(file.read())
        filename = file.name
        response = super().create(request, args, kwargs)
        device_upload_id = response.data['data']['id']
        DeviceUploadItems.objects.filter(is_imported=False).delete()
        self.parse_file(temp_file, filename, device_upload_id, temp_path)
        os.close(temp_file)
        return response

    def parse_data(self, row, serial_numbers, device_upload_id):
        row_errors = {'error_detail': list()}
        if row['serial_number'] is None or row['serial_number'] == '':
            row_errors['data_missing'] = True
            row_errors['error_detail'].append("Serial number missing")
        else:
            if Device.objects.filter(serial_number=row['serial_number']).count() > 0:
                row_errors['serial_exists'] = True
                row_errors['error_detail'].append("Device with this serial number already exists")
            elif row['serial_number'] in serial_numbers:
                row_errors['dublicate_entry'] = True
                row_errors['error_detail'].append("Duplicate entry")
            elif len(str(row['serial_number'])) > 10:
                row_errors["data_missing"] = True
                row_errors['error_detail'].append("Serial number cannot be greater than 10 characters")
            else:
                serial_numbers.append(row['serial_number'])

        # item_number
        if row['item_number'] is None or row['item_number'] == '':
            row_errors['data_missing'] = True
            row_errors['error_detail'].append("Item number missing")
        else:
            if DeviceItem.objects.filter(item_number=row['item_number']).count() == 0:
                row_errors['item_number_not_exists'] = True
                row_errors['error_detail'].append("Item number does not exist")
            elif len(str(row['item_number'])) > 10:
                row_errors['error_detail'].append("Item number cannot be greater than 10 characters")

        # date_added
        if row['date_added'] is None or row['date_added'] == '':

            row['date_added'] = timezone.now().date()
        else:
            if not type(row['date_added']) == datetime.date:
                try:
                    row['date_added'] = try_parsing_date(row['date_added']).date()
                except Exception:
                    row['date_added'] = None
                    row_errors["data_missing"] = True
                    row_errors['error_detail'].append("Unable to parse date added")

        # status
        if row['status'] is None or row['status'] == '':
            row['status'] = 'Available'
        else:
            if row['status'] not in [i[0] for i in DEVICE_STATUS]:
                row_errors['data_missing'] = True
                row_errors['error_detail'].append("Incorrect Status")
        # firmware
        # if row['firmware_revision'] is None or row['firmware_revision'] == '':
        #     row['firmware_revision'] = None
        # account
        if row['account_number'] is None or row['account_number'] == '':
            row_errors['data_missing'] = True
            row_errors['error_detail'].append("Account number missing")
        else:
            if Account.objects.filter(account_id=row['account_number']).count() == 0:
                row_errors['account_not_exist'] = True
                row_errors['error_detail'].append("Account with this account number does not exist")

        # sub_start_date
        if row['sub_start_date'] is None or row['sub_start_date'] == '':
            row['sub_start_date'] = None
        else:
            if not type(row['sub_start_date']) == datetime.date:
                try:
                    row['sub_start_date'] = try_parsing_date(row['sub_start_date']).date()
                except Exception as e:
                    row['sub_start_date'] = None
                    row_errors["data_missing"] = True
                    row_errors['error_detail'].append("Unable to parse subscription start date")

        # # is_active
        # this field is no longer required
        # if row['is_active'] is None or row['is_active'] == '':
        #     row['is_active'] = True
        # else:
        #     if row['is_active'] not in ('Yes', 'No'):
        #         row_errors['data_missing'] = True
        # row['is_active'] = True if row['is_active'] == 'Yes' else False

        row["device_upload"] = device_upload_id
        row["errors"] = row_errors
        return row

    def parse_file(self, file, filename, device_upload_id, temp_path):
        ext = filename.split('.')[-1]
        imported_rows = []
        serial_numbers = []
        try:
            if ext == 'csv':
                fields = [field for field in DEVICE_IMPORT_DICTIONARY.keys()]
                with open(temp_path, encoding='utf-8') as file_data:
                    reader = csv.DictReader(
                        file_data, fieldnames=fields, delimiter=',')
                    next(reader)
                    for row in reader:
                        imported_rows.append(self.parse_data(
                            row, serial_numbers, device_upload_id))

            elif ext in ('xlsx',):
                book = open_workbook(temp_path)
                sheet = book.sheet_by_index(0)
                keys = [sheet.cell(
                    0, col_index).value for col_index in range(sheet.ncols)]
                for row_index in range(1, sheet.nrows):
                    d = {keys[col_index]: sheet.cell(row_index, col_index).value
                         for col_index in range(sheet.ncols)}
                    for col_index in range(sheet.ncols):
                        cell = sheet.cell(row_index, col_index)
                        val = cell.value
                        if cell.ctype in (2,) and int(val) == val:
                            val = int(val)
                        elif cell.ctype in (3,):
                            val = datetime.datetime(*xldate_as_tuple(val, book.datemode)).date()
                        elif cell.ctype in (4,) and repr(val) == val:
                            val = repr(val)
                        d[keys[col_index]] = val
                    d = self.parse_data(d, serial_numbers, device_upload_id)
                    imported_rows.append(d)

            device_upload_items = DeviceUploadItemSerializer(
                data=imported_rows, many=True, context=self.get_serializer_context())
            if device_upload_items.is_valid(raise_exception=True):
                device_upload_items.save()
        except Exception as e:
            raise e


class DeviceUploadItemsViewSet(BaseViewset):
    queryset = DeviceUploadItems.objects.all()
    lookup_field = 'slug'
    permission_classes = [isSuperUser, ]
    action_serializers = {
        'default': DeviceUploadItemSerializer,

    }

# class DeviceSettingsViewSet(BaseViewset):
#     queryset = DeviceSettings.objects.all()
#     lookup_field = 'id'
#     action_serializers = {
#         'default': DeviceSettingsSerializer,
#     }
#
#
#
# class DeviceSettingHistoryViewSet(BaseViewset):
#     queryset = DeviceSettingHistory.objects.all()
#     lookup_field = 'slug'
#     action_serializers = {
#         'default': DeviceSettingHistorySerializer,
#         'create': DeviceSettingHistoryWritableSerializer
#     }

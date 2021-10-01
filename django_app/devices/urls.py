from django.urls import path
from django.conf.urls import url
from rest_framework.routers import DefaultRouter
from .views import DeviceViewSet, DeviceItemViewSet, DeviceUploadViewSet, DeviceUploadItemsViewSet, \
    EquipmentMaintenanceRecordViewSet


router = DefaultRouter()
router.register(r'devices', DeviceViewSet, basename='device')
router.register(r'deviceItems', DeviceItemViewSet, basename='device-items')
router.register(r'upload-device', DeviceUploadViewSet, basename='device-upload')
router.register(r'device-upload-items', DeviceUploadItemsViewSet, basename='device-upload-items')

# router.register(r'device-settings', DeviceSettingsViewSet, basename='devicesettings')
# router.register(r'device-setting-history', DeviceSettingHistoryViewSet, basename='device-setting-history')
router.register(r'device-maintenance-record', EquipmentMaintenanceRecordViewSet, basename='device-maintenance-record')

app_name = "devices"

urlpatterns = [

]
urlpatterns = urlpatterns + router.urls

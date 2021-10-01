from rest_framework.routers import DefaultRouter

from .views import CaseViewSet, PrescriptionUploadViewSet, DiagnosisViewSet, VitalsViewSet, HistoryViewSet
from .views import PrescriptionViewSet
from .views.case_permission import CasePermissionViewSet, CaseRolePermissionViewSet
from .views.interpretation import InterpretationDataViewSet
from .views.notes import ProviderNoteViewSet, ParentNoteViewSet, ParentNoteFileUploadViewSet
from .views.notification_matrix import NotificationMatrixViewSet, CaseNotificationMatrixViewSet
from .views.parent import ParentViewSet
from .views.patient import PatientViewSet
from .views.roles import CaseDefaultRoleViewSet, CaseRoleViewSet

router = DefaultRouter()
router.register(r'prescription-upload', PrescriptionUploadViewSet, basename='prescription-upload')
router.register(r'prescription', PrescriptionViewSet, basename='prescription')
router.register(r'default-notification-matrix', NotificationMatrixViewSet, basename='default-notification-matrix')
router.register(r'case-notification-matrix', CaseNotificationMatrixViewSet, basename='case-notification-matrix')
router.register(r'case_default-roles', CaseDefaultRoleViewSet, basename='case_default-roles')
router.register(r'case_roles', CaseRoleViewSet, basename='case_roles')
router.register(r'case_permission', CasePermissionViewSet, basename='case_permission')
router.register(r'case_role_permission', CaseRolePermissionViewSet, basename='case_role_permission')
router.register(r'patient', PatientViewSet, basename='patient')
router.register(r'parent', ParentViewSet, basename='parent')
router.register(r'diagnosis', DiagnosisViewSet, basename='diagnosis')
router.register(r'vitals', VitalsViewSet, basename='vitals')
router.register(r'history', HistoryViewSet, basename='history')
router.register(r'provider-note', ProviderNoteViewSet, basename='provider-note')
router.register(r'parent-note', ParentNoteViewSet, basename='parent-note')
router.register(r'parent-note-upload', ParentNoteFileUploadViewSet, basename='parent-note-upload')
router.register(r'interpretation', InterpretationDataViewSet, basename='interpretation')
router.register(r'', CaseViewSet, basename='case')
app_name = "cases"

urlpatterns = [
]
urlpatterns = urlpatterns + router.urls

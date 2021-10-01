from django_synergy.cases.models import DefaultNotificationMatrix, CaseDefaultRole, NotificationType, Case, \
    CaseNotificationMatrix
from django_synergy.cases.serializers.roles import CaseDefaultRoleSerializer
from django_synergy.notifications.serializers import NotificationTypeSerializer, CaseNotificationTypeSerializer
from django_synergy.utils.serializers import BaseSerializer, serializers


class NotificationMatrixSerializer(BaseSerializer):
    notification_type = serializers.SerializerMethodField()

    def get_notification_type(self, obj):
        notifications_matrix = DefaultNotificationMatrix.objects.filter(case_default_role=obj).order_by('created_on')
        notification_list = []
        for notification in notifications_matrix:
            notification_list.append(notification.notification_type)
        return NotificationTypeSerializer(notification_list, many=True, context={"role": obj}).data

    class Meta:
        model = CaseDefaultRole
        fields = ('name', 'slug', 'notification_type')


class NotificationMatrixWritableSerializer(BaseSerializer):
    case_default_role = serializers.SlugRelatedField(slug_field="slug", queryset=CaseDefaultRole.objects.all())
    notification_type = serializers.SlugRelatedField(slug_field="slug", queryset=NotificationType.objects.all())

    class Meta:
        model = DefaultNotificationMatrix
        fields = ('case_default_role', 'notification_type', 'is_notified')


class CaseNotificationMatrixWritableSerializer(BaseSerializer):
    case_default_role = serializers.SlugRelatedField(slug_field="slug", queryset=CaseDefaultRole.objects.all())
    notification_type = serializers.SlugRelatedField(slug_field="slug", queryset=NotificationType.objects.all())
    case = serializers.SlugRelatedField(slug_field="slug", queryset=Case.objects.all())

    class Meta:
        model = CaseNotificationMatrix
        fields = ('case', 'case_default_role', 'notification_type', 'is_notified')


class CaseNotificationMatrixSerializer(BaseSerializer):
    notification_type = serializers.SerializerMethodField()

    def get_notification_type(self, obj):
        case = self.context.get('case')
        notifications_matrix = DefaultNotificationMatrix.objects.filter(case_default_role=obj).order_by('created_on')
        notification_list = []
        for notification in notifications_matrix:
            notification_list.append(notification.notification_type)
        return CaseNotificationTypeSerializer(notification_list, many=True, context={"role": obj, "case": case}).data

    class Meta:
        model = CaseDefaultRole
        fields = ('name', 'slug', 'notification_type')

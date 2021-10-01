from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django_synergy.cases.models import CaseRole, ParentNote, ParentNoteFileUpload
from django_synergy.cases.models.notes import ProviderNote
from django_synergy.cases.permissions import get_user_permission_list, user_has_permission, CanEditNote, \
    CanViewNote, CanViewDetailNote
from django_synergy.cases.serializers.notes import ProviderNoteWritableSerializer, \
    ProviderNoteReadOnlySerializer, ParentNoteReadOnlySerializer, ParentNoteWritableSerializer, \
    ParentNoteFileUploadSerializer, ParentNoteFileUploadWritableSerializer
from django_synergy.utils.views import BaseViewset
from django_synergy.cases.utils import fetchChildAccounts, fetchCasesAssigned, fetchCasesAssignedToUser


class ProviderNoteViewSet(BaseViewset):
    queryset = ProviderNote.objects.all()
    lookup_field = 'slug'
    action_serializers = {
        'default': ProviderNoteReadOnlySerializer,
        'update': ProviderNoteWritableSerializer,
        'partial_update': ProviderNoteWritableSerializer,
        'create': ProviderNoteWritableSerializer
    }

    def get_permissions(self):
        if self.action == "list":
            self.permission_classes = [CanViewNote]
        elif self.action == "retrieve":
            self.permission_classes = [CanViewDetailNote]
        elif self.action == "create":
            self.permission_classes = [CanEditNote]
        elif self.action == "update":
            self.permission_classes = [CanEditNote]
        elif self.action == "partial_update":
            self.permission_classes = [CanEditNote]
        elif self.action == "destroy":
            self.permission_classes = [CanEditNote]
        else:
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    def get_queryset(self):
        if hasattr(self.request.user, 'is_superuser'):
            if self.request.user.is_superuser:
                return ProviderNote.objects.all()
        if hasattr(self.request.user, 'account'):
            if self.request.user.account:
                permission_list = get_user_permission_list(self.request.user)
                account_instance = ProviderNote.objects.none()
                if user_has_permission('case-note-account', user_permissions=permission_list):
                    account_instance = ProviderNote.objects.filter(
                        case__account__id=self.request.user.account.id)

                subsidiary_account_instance = ProviderNote.objects.none()
                if user_has_permission('case-note-subsidiary', user_permissions=permission_list):
                    account_slugs_list = []
                    fetchChildAccounts(account_slugs_list, self.request.user.account)
                    subsidiary_account_instance = ProviderNote.objects.filter(
                        case__account__slug__in=account_slugs_list)

                cases_assigned_instance = ProviderNote.objects.none()
                if user_has_permission('case-note-assigned', user_permissions=permission_list):
                    cases_assigned_slug_list = []
                    fetchCasesAssigned(cases_assigned_slug_list, self.request.user)
                    cases_assigned_instance = ProviderNote.objects.filter(
                        case__slug__in=cases_assigned_slug_list)

                case_list_assigned_to_users = ProviderNote.objects.none()
                if user_has_permission('case-note-assigned-to-users', user_permissions=permission_list):
                    cases_assigned_slug_list = []
                    fetchCasesAssignedToUser(cases_assigned_slug_list, self.request.user.account)
                    case_list_assigned_to_users = ProviderNote.objects.filter(
                        case__slug__in=cases_assigned_slug_list)

                return account_instance | subsidiary_account_instance | cases_assigned_instance | case_list_assigned_to_users

        else:
            return ProviderNote.objects.none()

    def create(self, request, *args, **kwargs):
        try:
            data = request.data
            default_roles = []
            case_roles = CaseRole.objects.filter(case__slug=data["case"], user=request.user)
            for case_role in case_roles:
                default_roles.append(case_role.case_default_role.name)

            data["default_case_roles"] = default_roles
            data["user"] = request.user.slug

            provider_note_serializer = ProviderNoteWritableSerializer(data=data,
                                                                      context=self.get_serializer_context())

            if provider_note_serializer.is_valid(raise_exception=True):
                provider_note_serializer_data = provider_note_serializer.validated_data
                provider_note_data = provider_note_serializer.save()

                return Response(status=status.HTTP_200_OK,
                                data={"success": True,
                                      "data": ProviderNoteReadOnlySerializer(provider_note_data,
                                                                             many=False).data})

        except Exception as e:
            return Response({"status": "failed", "message": e}
                            , status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        try:
            all_notes = self.get_queryset().all()
            notes = all_notes.filter(case__slug=kwargs["slug"])

            return Response(status=status.HTTP_200_OK,
                            data={"success": True,
                                  "data": ProviderNoteReadOnlySerializer(notes,
                                                                         many=True).data})

        except Exception as e:
            return Response({"status": "failed", "message": e}
                            , status=status.HTTP_400_BAD_REQUEST)


class ParentNoteViewSet(BaseViewset):
    queryset = ParentNote.objects.all()
    lookup_field = 'slug'
    action_serializers = {
        'default': ParentNoteReadOnlySerializer,
        'update': ParentNoteWritableSerializer,
        'partial_update': ParentNoteWritableSerializer,
        'create': ParentNoteWritableSerializer
    }

    def get_permissions(self):
        if self.action == "list":
            self.permission_classes = [CanViewNote]
        elif self.action == "retrieve":
            self.permission_classes = [CanViewDetailNote]
        elif self.action == "create":
            self.permission_classes = [CanEditNote]
        elif self.action == "update":
            self.permission_classes = [CanEditNote]
        elif self.action == "partial_update":
            self.permission_classes = [CanEditNote]
        elif self.action == "destroy":
            self.permission_classes = [CanEditNote]
        else:
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    def get_queryset(self):
        if hasattr(self.request.user, 'is_superuser'):
            if self.request.user.is_superuser:
                return ParentNote.objects.all()
        if hasattr(self.request.user, 'account'):
            if self.request.user.account:
                permission_list = get_user_permission_list(self.request.user)
                account_instance = ParentNote.objects.none()
                if user_has_permission('case-note-account', user_permissions=permission_list):
                    account_instance = ParentNote.objects.filter(
                        case__account__id=self.request.user.account.id)

                subsidiary_account_instance = ParentNote.objects.none()
                if user_has_permission('case-note-subsidiary', user_permissions=permission_list):
                    account_slugs_list = []
                    fetchChildAccounts(account_slugs_list, self.request.user.account)
                    subsidiary_account_instance = ParentNote.objects.filter(
                        case__account__slug__in=account_slugs_list)

                cases_assigned_instance = ParentNote.objects.none()
                if user_has_permission('case-note-assigned', user_permissions=permission_list):
                    cases_assigned_slug_list = []
                    fetchCasesAssigned(cases_assigned_slug_list, self.request.user)
                    cases_assigned_instance = ParentNote.objects.filter(
                        case__slug__in=cases_assigned_slug_list)

                case_list_assigned_to_users = ParentNote.objects.none()
                if user_has_permission('case-note-assigned-to-users', user_permissions=permission_list):
                    cases_assigned_slug_list = []
                    fetchCasesAssignedToUser(cases_assigned_slug_list, self.request.user.account)
                    case_list_assigned_to_users = ParentNote.objects.filter(
                        case__slug__in=cases_assigned_slug_list)

                return account_instance | subsidiary_account_instance | cases_assigned_instance | case_list_assigned_to_users

        else:
            return ParentNote.objects.none()

    def create(self, request, *args, **kwargs):
        try:
            data = request.data
            default_roles = []
            case_roles = CaseRole.objects.filter(case__slug=data["case"], user=request.user)
            for case_role in case_roles:
                default_roles.append(case_role.case_default_role.name)

            data["default_case_roles"] = default_roles
            data["user"] = request.user.slug

            parent_note_serializer = ParentNoteWritableSerializer(data=data,
                                                                  context=self.get_serializer_context())

            if parent_note_serializer.is_valid(raise_exception=True):
                parent_note_serializer_data = parent_note_serializer.validated_data
                parent_note_data = parent_note_serializer.save()

                return Response(status=status.HTTP_200_OK,
                                data={"success": True,
                                      "data": ParentNoteReadOnlySerializer(parent_note_data,
                                                                           many=False).data})

        except Exception as e:
            return Response({"status": "failed", "message": e}
                            , status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        try:
            all_notes = self.get_queryset().all()
            notes = all_notes.filter(case__slug=kwargs["slug"])

            return Response(status=status.HTTP_200_OK,
                            data={"success": True,
                                  "data": ParentNoteReadOnlySerializer(notes,
                                                                       many=True).data})

        except Exception as e:
            return Response({"status": "failed", "message": e}
                            , status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        try:
            self.check_object_permissions(request, self.get_object())

            ParentNoteFileUpload.objects.filter(parent_note__slug=kwargs['slug']).delete()
            ParentNote.objects.filter(slug=kwargs['slug']).delete()
            return Response({"status": "success", "message": 'Parent note deleted successfully'}
                            , status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"status": "failed", "message": e}
                            , status=status.HTTP_400_BAD_REQUEST)


class ParentNoteFileUploadViewSet(BaseViewset):
    queryset = ParentNoteFileUpload.objects.all()
    action_serializers = {
        'default': ParentNoteFileUploadSerializer,
        'create': ParentNoteFileUploadWritableSerializer,
        'update': ParentNoteFileUploadWritableSerializer,
    }

    def partial_update(self, request, *args, **kwargs):
        try:
            data = request.data
            parent_note_upload = ParentNoteFileUpload.objects.get(uuid=kwargs['slug'])
            if data['uploaded'] is True or data['uploaded'] == "true":
                parent_note_upload.uploaded = True
            elif data['uploaded'] is False or data['uploaded'] == "false":
                parent_note_upload.uploaded = False
            parent_note_upload.save()
            return Response({"status": "success", "message": 'parent note upload updated'}
                            , status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"status": "failed", "message": e}
                            , status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        try:
            data = request.data
            parent_note_upload = ParentNoteFileUpload.objects.get(parent_note__slug=kwargs['slug'])
            parent_note_upload.filename = data["filename"]
            parent_note_upload.save()
            return Response(status=status.HTTP_200_OK,
                            data={"success": True,
                                  "data": ParentNoteFileUploadWritableSerializer(parent_note_upload, many=False).data})

        except Exception as e:
            return Response({"status": "failed", "message": e}
                            , status=status.HTTP_400_BAD_REQUEST)

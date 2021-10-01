from django.urls import path
from django.conf.urls import url

from rest_framework.routers import DefaultRouter

from .views import UserViewSet, getTimezones, getGroups, getPermissions, getLanguages, savePermissionGroups, \
    getGroupPermissions, inviteContact, getUserListSummaries

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')

# from django_synergy.users.views import (
#     user_redirect_view,
#     user_update_view,
#     user_detail_view,
# )


app_name = "users"
urlpatterns = [

    # url('auth', CustomTokenObtainPairView.as_view(), name="get-token"),
    url('lookups/timezones', getTimezones, name="get-timezones"),
    url('getGroupPermissions', getGroupPermissions, name="get-group-permissions"),
    path(r'groups/', getGroups, name="get-groups"),
    url('savePermissions', savePermissionGroups, name="save-permissions"),
    url('permissions', getPermissions, name="get-permissions"),
    url('lookups/languages', getLanguages, name="get-languages"),
    url('invite', inviteContact, name="invite-contact"),
    url('getUserListSummaries', getUserListSummaries, name="get-summaries"),
]
urlpatterns = urlpatterns + router.urls
# urlpatterns = [
#     path("~redirect/", view=user_redirect_view, name="redirect"),
#     path("~update/", view=user_update_view, name="update"),
#     path("<str:username>/", view=user_detail_view, name="detail"),
# ]

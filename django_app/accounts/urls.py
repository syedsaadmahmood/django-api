from django.urls import path
from django.conf.urls import url
from rest_framework.routers import DefaultRouter

from .views import AccountsViewSet, AccountAssociationViewSet,SubsidiaryAccountsViewset
from .views import AccountUploadViewSet, AccountUploadItemsViewSet, AssociatedAccountsViewset, ContactAssociationViewSet

router = DefaultRouter()
router.register(r'accounts', AccountsViewSet, basename='account')
router.register(r'associated-accounts', AccountAssociationViewSet, basename='associated-accounts')
router.register(r'upload-account', AccountUploadViewSet, basename='upload-account')
router.register(r'account-upload-items', AccountUploadItemsViewSet, basename='account-upload-items')
router.register(r'list-associated-accounts', AssociatedAccountsViewset, basename='list-associated-accounts')
router.register(r'list-subsidiary-accounts', SubsidiaryAccountsViewset, basename='list-subsidiary-accounts'),
router.register(r'associated-contacts', ContactAssociationViewSet, basename='associated-contacts')

app_name = "accounts"

urlpatterns = [
]
urlpatterns = urlpatterns + router.urls

from django_synergy.accounts.models import Account
from django_synergy.cases.models import CaseRole, User, Case


def fetchChildAccounts(account_list, current_account):
    subsidiaries = Account.objects.filter(parent_account_id=current_account.id)
    subsidiaries_slugs = [s.slug for s in subsidiaries]
    account_list += subsidiaries_slugs


def fetchCasesAssigned(cases_assigned, current_account):
    case_roles = CaseRole.objects.filter(user=current_account)
    cases = [c.case for c in case_roles]
    cases_slugs = [s.slug for s in cases if s.is_archived is False]
    cases_assigned += cases_slugs


def fetchCasesAssignedToUser(cases_assigned_slugs, current_account):
    users = User.objects.filter(account=current_account)
    case_accounts_list = []
    for user in users:
        case_roles = CaseRole.objects.filter(user=user)
        cases = [c.case for c in case_roles]
        cases_slugs = [s.slug for s in cases]
        cases_assigned = Case.objects.filter(slug__in=cases_slugs)
        case_accounts_list += cases_assigned

    cases_assigned_slugs += [s.slug for s in case_accounts_list]

"""Closes /accounts/signup/ so GitHub stays the only way to get an account."""

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class NoPasswordSignupAdapter(DefaultAccountAdapter):
    """Refuses password signup."""

    def is_open_for_signup(self, request):
        return False


class GithubSignupAdapter(DefaultSocialAccountAdapter):
    """Keeps GitHub signup open.

    NOTE: allauth's social adapter delegates is_open_for_signup to the account adapter,
    so without this override closing password signup also blocks every GitHub sign-up.
    """

    def is_open_for_signup(self, request, sociallogin):
        return True

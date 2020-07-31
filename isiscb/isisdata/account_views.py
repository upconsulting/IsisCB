from allauth.account.views import PasswordChangeView as allauth_PasswordChangeView
from django.urls import reverse_lazy

class PasswordChangeView(allauth_PasswordChangeView):
    success_url = reverse_lazy('home')

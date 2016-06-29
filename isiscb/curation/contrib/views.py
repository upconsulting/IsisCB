from functools import wraps

from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied, ImproperlyConfigured, FieldError
from django.shortcuts import get_object_or_404
from django.utils import six
from django.utils.decorators import available_attrs
from django.utils.encoding import force_text
from django.template import loader, RequestContext
from django.http import HttpResponse


import rules

# taken from django-rules
# https://github.com/dfunckt/django-rules
def check_rules(perm, fn=None, login_url=None, raise_exception=False, redirect_field_name=REDIRECT_FIELD_NAME):
    """
    View decorator that checks for the given permissions before allowing the
    view to execute. Use it like this::
        from django.shortcuts import get_object_or_404
        from rules.contrib.views import permission_required
        from posts.models import Post
        def get_post_by_pk(request, post_id):
            return get_object_or_404(Post, pk=post_id)
        @permission_required('posts.change_post', fn=get_post_by_pk)
        def post_update(request, post_id):
            # ...
    ``perm`` is either a permission name as a string, or a list of permission
    names.
    ``fn`` is an optional callback that receives the same arguments as those
    passed to the decorated view and must return the object to check
    permissions against. If omitted, the decorator behaves just like Django's
    ``permission_required`` decorator, i.e. checks for model-level permissions.
    ``raise_exception`` is a boolean specifying whether to raise a
    ``django.core.exceptions.PermissionDenied`` exception if the check fails.
    You will most likely want to set this argument to ``True`` if you have
    specified a custom 403 response handler in your urlconf. If ``False``,
    the user will be redirected to the URL specified by ``login_url``.
    ``login_url`` is an optional custom URL to redirect the user to if
    permissions check fails. If omitted or empty, ``settings.LOGIN_URL`` is
    used.
    """
    def decorator(view_func):
        @wraps(view_func, assigned=available_attrs(view_func))
        def _wrapped_view(request, *args, **kwargs):

            # Get the object to check permissions against
            if callable(fn):
                obj = fn(request, *args, **kwargs)
            else:
                obj = fn

            # Get the user
            user = request.user

            if not rules.test_rule(perm, request.user, obj):
                template = loader.get_template('curation/access_denied.html')
                return HttpResponse(template.render(RequestContext(request, {})))

            else:
                # User has all required permissions -- allow the view to execute
                return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator

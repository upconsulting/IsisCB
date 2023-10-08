
class IncludeAllTenantsMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        # We use a cookie on the public site to include or exclude all data
        # this middleware makes sure views have access to a flag reflecting the cookies value
        if 'tenant_id' in view_kwargs:
            request.include_all_tenants = request.COOKIES.get('cbexplore-{}-include-all-tenants'.format(view_kwargs['tenant_id'], None)) == 'true'
        else:
            request.include_all_tenants = False
        return None

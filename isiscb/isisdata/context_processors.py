import json

def server_start(request):
    """
    Add the datetime of last server start to the template context.
    """
    with open('server_start', 'r') as f:
        start_datetime = json.load(f)
    return {'server_start': start_datetime}

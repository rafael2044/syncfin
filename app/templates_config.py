from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")


def get_user_perms(request):
    return getattr(request.state, "permissions", [])

from pathlib import Path
from django.http import Http404, HttpResponse


_INSTALL_SH = Path(__file__).parents[4] / "install.sh"


def serve_install_sh(request):
    if not _INSTALL_SH.exists():
        raise Http404("install.sh not found")
    content = _INSTALL_SH.read_bytes()
    return HttpResponse(content, content_type="text/plain; charset=utf-8")

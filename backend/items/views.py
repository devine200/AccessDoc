from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods
from rest_framework import mixins, viewsets
from rest_framework.permissions import AllowAny

from items.models import PublishedItem
from items.pdf_validation import pdf_upload_rejection_reason
from items.serializers import PublishedItemReadSerializer
from items.tasks import schedule_process_published_item
from items.utils import slugify_label, unique_slug, viewer_item_docs_url


class PublishedItemViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    """
    Read-only metadata for published (ready) items — pilot scope.
    """

    permission_classes = [AllowAny]
    serializer_class = PublishedItemReadSerializer
    lookup_field = "pk"

    def get_queryset(self):
        return PublishedItem.objects.filter(status=PublishedItem.Status.READY)


def _safe_next_url(request: HttpRequest) -> str:
    next_url = request.POST.get("next") or request.GET.get("next") or ""
    if next_url and url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return reverse("dashboard")


@require_http_methods(["GET", "POST"])
def staff_login(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated and request.user.is_staff:
        return redirect(_safe_next_url(request))
    error: str | None = None
    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        password = request.POST.get("password") or ""
        user = authenticate(request, username=username, password=password)
        if user is None:
            error = "Invalid username or password."
        elif not user.is_staff:
            error = "Staff access is required to sign in here."
        else:
            login(request, user)
            return redirect(_safe_next_url(request))
    next_param = request.POST.get("next") or request.GET.get("next", "")
    return render(
        request,
        "items/login.html",
        {
            "error": error,
            "next": next_param,
        },
    )


@require_http_methods(["POST"])
def staff_logout(request: HttpRequest) -> HttpResponse:
    logout(request)
    return redirect("home")


def home(request):
    if request.user.is_staff:
        return redirect("dashboard")
    return render(request, "items/home.html")


@staff_member_required
def dashboard(request):
    items = PublishedItem.objects.all()[:200]
    return render(
        request,
        "items/dashboard.html",
        {
            "items": items,
            "viewer_prefix": settings.DOCUSAURUS_BASE_URL.rstrip("/"),
            "poll_interval_ms": settings.DASHBOARD_POLL_INTERVAL_MS,
        },
    )


@staff_member_required
def dashboard_items_json(request: HttpRequest) -> JsonResponse:
    """Staff-only JSON for live processing status on the dashboard."""
    items = PublishedItem.objects.all().order_by("-created_at")[:200]
    data = []
    for i in items:
        data.append(
            {
                "id": str(i.pk),
                "title": i.title,
                "slug": i.slug,
                "status": i.status,
                "status_display": i.get_status_display(),
                "page_count": i.page_count,
                "error_message": (i.error_message or "")[:280],
                "created_at": i.created_at.isoformat(),
                "processed_at": i.processed_at.isoformat()
                if i.processed_at
                else None,
                "viewer_docs_url": viewer_item_docs_url(str(i.pk))
                if i.status == PublishedItem.Status.READY
                else "",
            }
        )
    return JsonResponse({"items": data})


@staff_member_required
@require_http_methods(["GET", "POST"])
def upload_document(request):
    if request.method == "GET":
        return render(request, "items/upload.html")

    title = (request.POST.get("title") or "").strip()
    description = (request.POST.get("description") or "").strip()
    upload = request.FILES.get("source_file")

    errors = []
    if not title:
        errors.append("Title is required.")
    if not upload:
        errors.append("Choose a PDF file to upload.")
    elif upload.size > settings.MAX_UPLOAD_BYTES:
        errors.append(
            f"File is too large (max {settings.MAX_UPLOAD_BYTES // (1024 * 1024)} MB)."
        )
    else:
        pdf_error = pdf_upload_rejection_reason(upload)
        if pdf_error:
            errors.append(pdf_error)

    if errors:
        return render(
            request,
            "items/upload.html",
            {"errors": errors, "title": title, "description": description},
            status=400,
        )

    base_slug = slugify_label(title)

    def slug_taken(s):
        return PublishedItem.objects.filter(slug=s).exists()

    slug = unique_slug(base_slug, slug_taken)

    item = PublishedItem.objects.create(
        slug=slug,
        title=title,
        description=description,
        document_type="application/pdf",
        source_file=upload,
        status=PublishedItem.Status.PENDING,
        created_by=request.user if request.user.is_authenticated else None,
        processed_at=None,
    )
    schedule_process_published_item(str(item.pk))
    return redirect("dashboard")

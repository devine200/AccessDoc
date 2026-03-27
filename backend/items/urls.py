from django.urls import include, path
from rest_framework.routers import DefaultRouter

from items import views

router = DefaultRouter()
router.register(
    r"api/items",
    views.PublishedItemViewSet,
    basename="publisheditem",
)

urlpatterns = [
    path("", views.home, name="home"),
    path("login/", views.staff_login, name="login"),
    path("logout/", views.staff_logout, name="logout"),
    path("upload/", views.upload_document, name="upload"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path(
        "dashboard/items.json",
        views.dashboard_items_json,
        name="dashboard_items_json",
    ),
    path("", include(router.urls)),
]

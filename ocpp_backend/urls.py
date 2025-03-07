from django.contrib import admin
from django.urls import path, include
from rest_framework import routers
from chargers.api import views

router = routers.DefaultRouter()
router.register(r'chargers', views.ChargerViewSet)
router.register(r'transactions', views.TransactionViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api-auth/', include('rest_framework.urls')),
]

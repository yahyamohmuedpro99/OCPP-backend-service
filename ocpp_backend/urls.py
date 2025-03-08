from django.contrib import admin
from django.urls import path, include
from rest_framework import routers
from chargers.api import views
from chargers import views as charger_views

router = routers.DefaultRouter()
router.register(r'chargers', views.ChargerViewSet)
router.register(r'transactions', views.TransactionViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api-auth/', include('rest_framework.urls')),
    path('test/', charger_views.test_interface, name='test_interface'),
]

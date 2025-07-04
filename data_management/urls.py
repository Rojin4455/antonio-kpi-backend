from django.urls import path
from .views import DashboardAPIView,view_logs, RevenueMetricsView,OpportunityListGenericView

urlpatterns = [
    path('dashboard/', DashboardAPIView.as_view(), name='dashboard-api'),
    path('admin/logs/', view_logs, name='view_logs'),
    path("revenue-metrics/", RevenueMetricsView.as_view(), name="revenue-metrics"),
    path('opportunities/', OpportunityListGenericView.as_view(), name='opportunity-list'),

    # path("get-details/")
]
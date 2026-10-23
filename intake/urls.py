from django.urls import path
from . import views

urlpatterns = [
    path('', views.intake_view, name='intake'),
    path('status/', views.status_view, name='status'),
    path('health/', views.health_check, name='health'),
    path('api/validate/', views.validate_intake_view, name='validate_intake'),
    path('api/process/', views.process_intake_view, name='process_intake'),
]

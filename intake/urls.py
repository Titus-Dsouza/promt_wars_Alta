from django.urls import path
from . import views

urlpatterns = [
    path('', views.status_view, name='status'),
    path('health/', views.health_check, name='health'),
]

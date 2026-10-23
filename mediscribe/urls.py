"""
URL configuration for MediScribe project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('intake.urls')),
]

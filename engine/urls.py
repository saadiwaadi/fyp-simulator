from django.urls import path
from . import views

urlpatterns = [
    path('', views.match_dashboard, name='match_dashboard'),
]
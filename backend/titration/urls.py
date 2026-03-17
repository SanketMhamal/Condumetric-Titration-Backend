from django.urls import path
from . import views

urlpatterns = [
    path("calculate/", views.calculate, name="calculate"),
    path("download-input/", views.download_input, name="download-input"),
    path("download-results/", views.download_results, name="download-results"),
]

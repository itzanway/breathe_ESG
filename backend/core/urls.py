from django.contrib import admin
from django.urls import path
from ingestion import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', views.health),
    path('api/clients/', views.clients),
    path('api/ingest/sap/', views.ingest_sap),
    path('api/ingest/utility/', views.ingest_utility),
    path('api/ingest/travel/', views.ingest_travel),
    path('api/records/', views.records_list),
    path('api/records/<uuid:record_id>/approve/', views.approve_record),
    path('api/records/<uuid:record_id>/reject/', views.reject_record),
    path('api/batches/', views.batches_list),
    path('api/batches/<uuid:batch_id>/lock/', views.lock_batch),
    path('api/summary/', views.summary),
]


# Serve React frontend for all non-API routes
from django.views.generic import TemplateView
from django.conf.urls.static import static
from django.conf import settings

urlpatterns += [
    path('', TemplateView.as_view(template_name='index.html')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

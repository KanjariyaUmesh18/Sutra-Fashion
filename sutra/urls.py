from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('', include('core.urls')),
]

handler404 = 'sutra.views.custom_404'
handler500 = 'sutra.views.custom_500'

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

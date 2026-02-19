from django.contrib import admin
from django.urls import path, include  # Make sure 'include' is imported!

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # This points the root URL '' to your engine app
    # It will now look at engine/urls.py for instructions
    path('', include('engine.urls')), 
]
from django.contrib import admin
from django.urls import path, include
from engine import views  # Import your views

urlpatterns = [
    # 1. ADMIN MUST BE FIRST
    path('admin/', admin.site.urls),

    # 2. THE DASHBOARD (Root URL)
    path('', views.match_dashboard, name='dashboard'),
    
    # 3. (Optional) Any other paths would go here
]
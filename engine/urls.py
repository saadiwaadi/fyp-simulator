from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('match/<int:match_id>/report/', views.match_analysis, name='match_analysis'),
    
    # 1. Configuration (The Lab)
    path('', views.tactical_lab, name='tactical_lab'),
    
    # 2. Execution (The Engine)
    # We use 'execute/' to match the previous setup. 
    # If your browser is stuck on 'match/run/', just go back to the homepage (/) and click Execute again.
    path('execute/', views.match_execution, name='match_execution'),
    
    # 3. Analysis (The Report)
    # IMPORTANT: The name must be 'tactical_report' to match the button in match_live.html
    path('report/', views.match_analysis, name='tactical_report'),
    
    # Optional: View specific history logs by ID
    path('report/<int:match_id>/', views.match_analysis, name='match_history'),
]
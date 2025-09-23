from django.urls import path
from . import views

app_name = 'main'

urlpatterns = [
    # Main frontend pages
    path('', views.HomeView.as_view(), name='home'),
    path('about/', views.AboutView.as_view(), name='about'),
    path('register/', views.register_view, name='register'),
    
    # Campaign frontend pages
    path('campaigns/', views.CampaignListView.as_view(), name='campaigns_list'),
    path('campaigns/<int:pk>/', views.CampaignDetailView.as_view(), name='campaign_detail'),
    
    # NGO frontend pages
    path('ngos/apply/', views.NGOApplyView.as_view(), name='ngo_apply'),
    
    # AJAX API endpoints for frontend
    path('frontend-api/campaigns/<int:campaign_id>/stats/', views.campaign_stats_api, name='campaign_stats_api'),
    path('frontend-api/campaigns/<int:campaign_id>/donations/', views.recent_donations_api, name='recent_donations_api'),
]
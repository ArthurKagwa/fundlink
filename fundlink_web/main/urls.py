from django.urls import path
from . import views

app_name = 'main'

urlpatterns = [
    # Main frontend pages
    path('', views.HomeView.as_view(), name='home'),
    path('about/', views.AboutView.as_view(), name='about'),
    path('register/', views.register_view, name='register'),
    path('accounts/profile/', views.UserProfileView.as_view(), name='user_profile'),
    
    # Dashboard pages
    path('dashboard/', views.PublicDashboardView.as_view(), name='public_dashboard'),
    
    # Campaign frontend pages
    path('campaigns/', views.CampaignListView.as_view(), name='campaigns_list'),
    path('campaigns/<int:pk>/', views.CampaignDetailView.as_view(), name='campaign_detail'),
    
    # NGO frontend pages
    path('ngos/apply/', views.NGOApplyView.as_view(), name='ngo_apply'),
    path('ngo/dashboard/', views.NGODashboardView.as_view(), name='ngo_dashboard'),
    path('admin/review/campaigns/', views.StaffCampaignReviewView.as_view(), name='staff_campaign_review'),
    
    # AJAX API endpoints for frontend
    path('frontend-api/campaigns/<int:campaign_id>/stats/', views.campaign_stats_api, name='campaign_stats_api'),
    path('frontend-api/campaigns/<int:campaign_id>/donations/', views.recent_donations_api, name='recent_donations_api'),
    path('api/dashboard/overview/', views.dashboard_overview_api, name='dashboard_overview_api'),
]
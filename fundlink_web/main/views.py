from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.generic import TemplateView
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.utils import timezone
from campaigns.models import Campaign
from ngos.models import NGO
from ngos.serializers import NGOApplicationSerializer
from donations.models import Donation
from django.db.models import Count, Sum
from django.contrib.auth.decorators import user_passes_test


class HomeView(TemplateView):
    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get featured campaigns (latest 3 active campaigns)
        context['featured_campaigns'] = Campaign.objects.filter(
            active=True,
            ngo__approved=True
        ).select_related('ngo').order_by('-created_at')[:3]
        
        # Basic stats for the homepage
        context['total_campaigns'] = Campaign.objects.filter(active=True, ngo__approved=True).count()
        context['total_ngos'] = NGO.objects.filter(approved=True).count()
        context['total_donations'] = Donation.objects.filter(confirmed_at__isnull=False).count()
        
        return context


class CampaignListView(TemplateView):
    template_name = 'campaigns/list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Active Campaigns'
        return context


class CampaignDetailView(TemplateView):
    template_name = 'campaigns/detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        campaign_id = kwargs.get('pk')
        
        campaign = get_object_or_404(
            Campaign.objects.select_related('ngo'),
            id=campaign_id,
            active=True,
            ngo__approved=True
        )
        
        context['campaign'] = campaign
        context['page_title'] = campaign.title
        
        return context


class NGOApplyView(TemplateView):
    template_name = 'ngos/apply.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Register Your NGO'
        # Pass along any previous form data/errors for graceful re-render after POST
        if 'form_data' in kwargs:
            context['form_data'] = kwargs['form_data']
        if 'errors' in kwargs:
            context['errors'] = kwargs['errors']
        return context

    def post(self, request, *args, **kwargs):
        """Handle non-JS (progressive enhancement) form submissions.

        The primary submission path in the template uses JS to hit the REST endpoint
        at /api/ngos/apply/. If JS fails or is disabled, this provides a graceful
        server-side fallback using the same serializer logic.
        """
        serializer = NGOApplicationSerializer(data=request.POST)
        if serializer.is_valid():
            serializer.save()
            messages.success(request, 'Application submitted successfully. Awaiting admin approval.')
            return redirect('main:ngo_apply')
        # Re-render with errors and previously entered data
        context = self.get_context_data(form_data=request.POST, errors=serializer.errors)
        return self.render_to_response(context, status=400)


class AboutView(TemplateView):
    template_name = 'about.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'About FundLink'
        return context


# API Views for AJAX requests
def campaign_stats_api(request, campaign_id):
    """Get campaign statistics for AJAX requests"""
    try:
        campaign = get_object_or_404(Campaign, id=campaign_id, active=True)
        
        # Get donation statistics
        donations = Donation.objects.filter(
            campaign=campaign,
            confirmed_at__isnull=False
        )
        
        stats = {
            'total_donations': donations.count(),
            'total_amount': float(donations.aggregate(
                total=Sum('amount_decimal')
            )['total'] or 0),
            'primary_token': campaign.token_options[0] if campaign.token_options else 'AVAX',
            'donations_by_token': {}
        }
        
        # Group donations by token
        for token in campaign.token_options:
            token_donations = donations.filter(token=token)
            stats['donations_by_token'][token] = {
                'count': token_donations.count(),
                'total_amount': float(token_donations.aggregate(
                    total=Sum('amount_decimal')
                )['total'] or 0)
            }
        
        return JsonResponse(stats)
        
    except Campaign.DoesNotExist:
        return JsonResponse({'error': 'Campaign not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def recent_donations_api(request, campaign_id):
    """Get recent donations for a campaign"""
    try:
        campaign = get_object_or_404(Campaign, id=campaign_id, active=True)
        
        donations = Donation.objects.filter(
            campaign=campaign,
            confirmed_at__isnull=False
        ).order_by('-confirmed_at')[:10]
        
        donations_data = []
        for donation in donations:
            donations_data.append({
                'id': donation.id,
                'amount_decimal': str(donation.amount_decimal),
                'token': donation.token,
                'tx_hash': donation.tx_hash,
                'confirmed_at': donation.confirmed_at.isoformat() if donation.confirmed_at else None,
                'donor_id': donation.donor_telegram_id or 'Anonymous'
            })
        
        return JsonResponse({'results': donations_data})
        
    except Campaign.DoesNotExist:
        return JsonResponse({'error': 'Campaign not found'}, status=404)


def dashboard_overview_api(request):
    """Public dashboard API endpoint with comprehensive tracking"""
    try:
        # Get all approved campaigns
        campaigns = Campaign.objects.filter(
            status=Campaign.STATUS_APPROVED, 
            ngo__status='approved'
        )
        
        # Calculate overview statistics
        total_campaigns = campaigns.count()
        total_raised = sum(c.total_donations for c in campaigns)
        total_intents = sum(c.total_intents for c in campaigns)
        total_confirmations = sum(c.total_confirmations for c in campaigns)
        
        # Calculate overall intent-to-confirmation rate
        overall_conversion_rate = 0
        if total_intents > 0:
            overall_conversion_rate = (total_confirmations / total_intents) * 100
        
        # Get campaigns with progress data
        campaign_progress = []
        for campaign in campaigns.order_by('-created_at')[:10]:
            progress_data = campaign.funding_progress
            progress_data.update({
                'id': campaign.id,
                'title': campaign.title,
                'ngo_name': campaign.ngo.name,
                'created_at': campaign.created_at.isoformat(),
            })
            campaign_progress.append(progress_data)
        
        # Get NGO statistics  
        approved_ngos = NGO.objects.filter(status='approved')
        ngo_stats = []
        for ngo in approved_ngos[:5]:
            ngo_stats.append({
                'id': ngo.id,
                'name': ngo.name,
                'total_campaigns': ngo.total_campaigns,
                'active_campaigns': ngo.active_campaigns,
                'total_raised': float(ngo.total_donations_received),
                'total_donors': ngo.total_donors,
            })
        
        return JsonResponse({
            'overview': {
                'total_campaigns': total_campaigns,
                'total_raised': float(total_raised),
                'total_intents': total_intents,
                'total_confirmations': total_confirmations,
                'conversion_rate': round(overall_conversion_rate, 1),
                'total_ngos': approved_ngos.count(),
            },
            'campaign_progress': campaign_progress,
            'featured_ngos': ngo_stats,
            'last_updated': timezone.now().isoformat(),
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def register_view(request):
    """User registration view"""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}! You can now log in.')
            return redirect('login')
    else:
        form = UserCreationForm()
    
    return render(request, 'registration/register.html', {'form': form})


class NGODashboardView(TemplateView):
    template_name = 'ngos/dashboard.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not hasattr(request.user, 'ngo'):
            messages.info(request, 'No NGO profile associated with this user.')
            return redirect('main:home')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ngo = self.request.user.ngo
        context['ngo'] = ngo
        context['campaigns'] = ngo.campaigns.all().order_by('-created_at')[:25]
        context['pending_campaigns'] = ngo.campaigns.filter(status__in=['submitted'])
        context['rejected_campaigns'] = ngo.campaigns.filter(status='rejected')
        return context


@method_decorator(login_required, name='dispatch')
class UserProfileView(TemplateView):
    template_name = 'registration/profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['user_obj'] = user
        # If user has an NGO profile, include quick stats
        ngo = getattr(user, 'ngo', None)
        if ngo:
            context['ngo'] = ngo
            context['campaign_count'] = ngo.campaigns.count()
            context['approved_campaigns'] = ngo.campaigns.filter(active=True).count()
        return context


@method_decorator(user_passes_test(lambda u: u.is_authenticated and u.is_staff, login_url='login'), name='dispatch')
class StaffCampaignReviewView(TemplateView):
    template_name = 'campaigns/review.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Review Submitted Campaigns'
        context['pending_campaigns'] = Campaign.objects.select_related('ngo').filter(status=Campaign.STATUS_SUBMITTED)
        context['recent_rejected'] = Campaign.objects.select_related('ngo').filter(status=Campaign.STATUS_REJECTED).order_by('-updated_at')[:10]
        return context


class PublicDashboardView(TemplateView):
    """Public dashboard with comprehensive tracking for all users"""
    template_name = 'dashboard/public.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Impact Dashboard'
        return context

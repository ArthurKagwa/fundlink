from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.generic import TemplateView
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib import messages
from campaigns.models import Campaign
from ngos.models import NGO
from ngos.serializers import NGOApplicationSerializer
from donations.models import Donation
from django.db.models import Count, Sum


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

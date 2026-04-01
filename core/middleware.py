"""
Middleware to track clicks using URL parameters without creating new endpoints
"""
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from .models import SwapRequest, SwapLinkClick

class ClickTrackingMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Check for swap_track parameter in any URL
        track_param = request.GET.get('swap_track')
        
        if track_param:
            try:
                # Try to find existing link click
                link_click = SwapLinkClick.objects.get(id=track_param)
                link_click.clicks += 1
                link_click.save()
                
                # Return JSON response with redirect URL
                return JsonResponse({
                    'redirect_to': link_click.destination_url,
                    'tracked': True
                })
                
            except SwapLinkClick.DoesNotExist:
                # Try to create from swap ID
                try:
                    swap = SwapRequest.objects.get(id=track_param)
                    if swap.book:
                        # Priority: 1. swap.site_url, 2. book.site_url (comma-separated), 3. "#"
                        destination_url = "#"
                        if swap.site_url:
                            destination_url = swap.site_url
                        elif swap.book.site_url:
                            urls = [u.strip() for u in swap.book.site_url.split(',') if u.strip()]
                            if urls:
                                destination_url = urls[0]
                        
                        link_click, created = SwapLinkClick.objects.get_or_create(
                            swap=swap,
                            link_name=f"Swap Promo - {swap.book.title}",
                            destination_url=destination_url,
                            defaults={'clicks': 0}
                        )
                        link_click.clicks += 1
                        link_click.save()
                        
                        return JsonResponse({
                            'redirect_to': link_click.destination_url,
                            'tracked': True
                        })
                except SwapRequest.DoesNotExist:
                    pass
        
        return None

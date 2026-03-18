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
                        link_click, created = SwapLinkClick.objects.get_or_create(
                            swap=swap,
                            link_name=f"Swap Promo - {swap.book.title}",
                            destination_url=getattr(swap.book, 'amazon_url', '#') or "#",
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

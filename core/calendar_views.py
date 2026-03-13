from django.http import HttpResponse, JsonResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import datetime, timedelta
import json
import urllib.parse
from core.models import NewsletterSlot


class GoogleCalendarExportView(APIView):
    """
    Export newsletter slots to Google Calendar
    GET /api/calendar/google/
    Returns: Google Calendar integration URL
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        # Get user's newsletter slots
        slots = NewsletterSlot.objects.filter(user=user).order_by('send_date')
        
        if not slots.exists():
            return JsonResponse({'error': 'No newsletter slots found'}, status=404)
        
        # Create Google Calendar events
        events = []
        for slot in slots:
            if slot.send_date:
                # Create event details
                event = {
                    'summary': f'Newsletter: {slot.get_preferred_genre_display()}',
                    'description': f'Newsletter slot for {slot.get_preferred_genre_display()}',
                    'start': {
                        'dateTime': slot.send_date.isoformat(),
                        'timeZone': 'UTC'
                    },
                    'end': {
                        'dateTime': (slot.send_date + timedelta(hours=1)).isoformat(),
                        'timeZone': 'UTC'
                    }
                }
                events.append(event)
        
        # Generate Google Calendar URL
        base_url = 'https://calendar.google.com/calendar/render'
        
        # Create multiple events by joining them
        event_details = []
        for event in events:
            details = f"{event['summary']} on {event['start']['dateTime']}"
            event_details.append(details)
        
        # Create calendar URL with action=TEMPLATE
        params = {
            'action': 'TEMPLATE',
            'text': 'Newsletter Schedule',
            'details': '\n'.join(event_details),
            'dates': f"{slots.first().send_date.strftime('%Y%m%d')}/{slots.last().send_date.strftime('%Y%m%d')}"
        }
        
        calendar_url = f"{base_url}?{urllib.parse.urlencode(params)}"
        
        return JsonResponse({
            'success': True,
            'calendar_url': calendar_url,
            'events_count': len(events)
        })


class OutlookCalendarExportView(APIView):
    """
    Export newsletter slots to Outlook Calendar
    GET /api/calendar/outlook/
    Returns: Outlook Calendar integration URL
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        # Get user's newsletter slots
        slots = NewsletterSlot.objects.filter(user=user).order_by('send_date')
        
        if not slots.exists():
            return JsonResponse({'error': 'No newsletter slots found'}, status=404)
        
        # Create Outlook Calendar events
        events = []
        for slot in slots:
            if slot.send_date:
                event = {
                    'subject': f'Newsletter: {slot.get_preferred_genre_display()}',
                    'body': f'Newsletter slot for {slot.get_preferred_genre_display()}',
                    'start': slot.send_date.isoformat(),
                    'end': (slot.send_date + timedelta(hours=1)).isoformat()
                }
                events.append(event)
        
        # Generate Outlook Calendar URL
        base_url = 'https://outlook.live.com/calendar/0/deeplink/compose'
        
        # Create event details for Outlook
        event_details = []
        for event in events:
            details = f"{event['subject']} - {event['start']}"
            event_details.append(details)
        
        params = {
            'subject': 'Newsletter Schedule',
            'body': '\n'.join(event_details),
            'startdt': slots.first().send_date.strftime('%Y-%m-%dT%H:%M:%S'),
            'enddt': (slots.first().send_date + timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%S')
        }
        
        outlook_url = f"{base_url}?{urllib.parse.urlencode(params)}"
        
        return JsonResponse({
            'success': True,
            'calendar_url': outlook_url,
            'events_count': len(events)
        })


class ICSExportView(APIView):
    """
    Export newsletter slots as ICS file
    GET /api/calendar/ics/
    Returns: ICS file download
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        # Get user's newsletter slots
        slots = NewsletterSlot.objects.filter(user=user).order_by('send_date')
        
        if not slots.exists():
            return JsonResponse({'error': 'No newsletter slots found'}, status=404)
        
        # Generate ICS content
        ics_content = self.generate_ics_content(slots)
        
        # Create HTTP response with ICS file
        response = HttpResponse(ics_content, content_type='text/calendar')
        response['Content-Disposition'] = f'attachment; filename="newsletter_schedule_{user.username}.ics"'
        
        return response
    
    def generate_ics_content(self, slots):
        """Generate ICS file content from newsletter slots"""
        now = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
        
        ics_lines = [
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            'PRODID:-//AuthorSwap//Newsletter Schedule//EN',
            'CALSCALE:GREGORIAN',
            'METHOD:PUBLISH'
        ]
        
        for slot in slots:
            if slot.send_date:
                # Convert to UTC for ICS format
                start_time = slot.send_date.strftime('%Y%m%dT%H%M%SZ')
                end_time = (slot.send_date + timedelta(hours=1)).strftime('%Y%m%dT%H%M%SZ')
                
                # Create unique ID for event
                event_id = f"{slot.id}@authorswap.com"
                
                # Add event to ICS
                ics_lines.extend([
                    'BEGIN:VEVENT',
                    f'UID:{event_id}',
                    f'DTSTAMP:{now}',
                    f'DTSTART:{start_time}',
                    f'DTEND:{end_time}',
                    f'SUMMARY:Newsletter: {slot.get_preferred_genre_display()}',
                    f'DESCRIPTION:Newsletter slot for {slot.get_preferred_genre_display()}',
                    'STATUS:CONFIRMED',
                    'END:VEVENT'
                ])
        
        ics_lines.append('END:VCALENDAR')
        
        return '\r\n'.join(ics_lines)


class CalendarExportOptionsView(APIView):
    """
    Get available calendar export options
    GET /api/calendar/options/
    Returns: List of available export options
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        # Get user's newsletter slots count
        slots_count = NewsletterSlot.objects.filter(user=user).count()
        
        options = [
            {
                'id': 'google',
                'name': 'Google Calendar',
                'description': 'Export to Google Calendar',
                'url': '/api/calendar/google/',
                'icon': 'google'
            },
            {
                'id': 'outlook',
                'name': 'Outlook Calendar',
                'description': 'Export to Outlook Calendar',
                'url': '/api/calendar/outlook/',
                'icon': 'outlook'
            },
            {
                'id': 'ics',
                'name': 'Download ICS File',
                'description': 'Download calendar file for any calendar app',
                'url': '/api/calendar/ics/',
                'icon': 'download'
            }
        ]
        
        return JsonResponse({
            'success': True,
            'slots_count': slots_count,
            'options': options
        })

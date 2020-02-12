from datetime import datetime, timedelta
from os import path
from pytz import timezone
from urllib.parse import urlparse
import requests

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from ...models import Event


class Command(BaseCommand):
    def _get_events(self):
        events_list = []

        events = requests.get(
            'https://api.meetup.com/%s/events?fields=featured_photo'
            % settings.MEETUP_GROUP
        ).json()

        for event in events:
            start = datetime.fromtimestamp(
                event['time'] / 1000,
                timezone('UTC'),
            )
            end = start + timedelta(milliseconds=event['duration'])
            events_list.append({
                'image': event['featured_photo']['highres_link'],
                'title': event['name'],
                'link': event['link'],
                'event_id': 'mu:%s:%s' % (
                    event['group']['urlname'],
                    event['id'],
                ),
                'start': start,
                'end': end,
                'location': event['venue']['name'],
                'description': event['description'],
                'attending': event['yes_rsvp_count'],
            })

        return events_list

    def handle(self, *args, **options):
        # All upcoming / future events
        known_events = Event.objects.filter(
            event_id__startswith='mu:',
            start_time__gte=datetime.now(),
        )
        events = self._get_events()

        # Delete events in our system that are not listed on meetup
        (
            known_events
                .exclude(
                    event_id__in=[event['event_id'] for event in events]
                )
                .delete()
        )
        # Create and update events listed
        for event in events:
            try:
                obj = Event.objects.get(event_id=event['event_id'])
            except Event.DoesNotExist:
                obj = Event(event_id=event['event_id'])
            obj.title = event['title']
            obj.location = event['location']
            obj.start_time = event['start']
            obj.end_time = event['end']
            obj.description = event['description']
            obj.attending = event['attending']
            if not event['image']:
                obj.image_url = None
                obj.image.delete()
                obj.image = None
            elif obj.image_url != event['image']:
                obj.image_url = event['image']
                parsed = urlparse(event['image'])
                obj.image.save(
                    '%s%s' % (
                        event['event_id'],
                        path.splitext(parsed.path)[1],
                    ),
                    ContentFile(requests.get(event['image']).content),
                    save=False,
                )
            obj.save()

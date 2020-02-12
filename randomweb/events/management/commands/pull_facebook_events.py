# Scraping in this manner is prohibited by facebook:
# https://www.facebook.com/apps/site_scraping_tos_terms.php

from datetime import datetime, timedelta
from lxml import html
from urllib.parse import urlparse
from os import path
import parsedatetime
import re
import requests

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from ...models import Event

fb_root = 'https://mbasic.facebook.com'


class Command(BaseCommand):
    def _login(self, user, password):
        session = requests.session()
        # Facebook seems to block "legit" UAs...?
        # session.headers['User-Agent'] = (
        #     'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
        #     '(KHTML, like Gecko) Ubuntu Chromium/79.0.3945.79 '
        #     'Chrome/79.0.3945.79 Safari/537.36'
        # )

        login = html.document_fromstring(
            session.get(fb_root + '/login').content
        )
        target = login.forms[0].action
        values = dict(login.forms[0].fields)
        values.pop('sign_up')
        values.update({'email': user, 'pass': password})

        session.post(fb_root + target, values)

        return session

    def _get_events(self, session, groupid):
        events = []
        url = '%s/groups/%s?view=events' % (fb_root, groupid)
        while True:
            page = html.document_fromstring(session.get(url).content)
            for event in page.cssselect('.bi.ca'):
                events.append(event)

            next_link = page.cssselect('#m_more_item a')
            if next_link:
                url = '%s%s' % (fb_root, next_link[0].attrib['href'])
            else:
                break
        return events

    def _get_event(self, session, eventid):
        return html.document_fromstring(
            session
                .get('%s/events/%s' % (fb_root, eventid))
                .content
        )

    def _parse_events(self, events):
        events_list = []

        for event in events:
            image = (
                event.cssselect('img')[0].attrib['src']
                if event.cssselect('img') else
                None
            )
            title = event.cssselect('h4')[0].text
            link = event.cssselect('a')[0].attrib['href']
            event_id = 'fb:%s' % re.findall(r'/events/(\d+)\?', link)[0]

            # emdashes confuse parsedatetime
            meta_date = event.cssselect('.co')[1].text.replace('–', '-')
            cal = parsedatetime.Calendar()
            if '-' in meta_date:
                start, end, valid = cal.evalRanges(meta_date)
                # Time range
                if valid:
                    start, end = datetime(*start[:6]), datetime(*end[:6])
                    if start > end:
                        # Past midnight
                        end += timedelta(days=1)
                # Date range
                else:
                    start, end = meta_date.split('-')
                    start = cal.parse(start)
                    end = cal.parse(end)
                    # Specific time range
                    if start[1] == end[1] == 3:
                        start = datetime(*start[0][:6])
                        end = datetime(*end[0][:6])
                    else:
                        # Generic date range; scheduled / repeating?
                        # Ignore
                        continue
            # Normal date
            else:
                start, valid = cal.parse(meta_date)
                if valid:
                    # Start time only
                    start = datetime(*start[:6])
                    end = None
                else:
                    # No idea...
                    continue

            try:
                location = event.cssselect('.cu')[0].text
            except IndexError:
                location = None

            events_list.append({
                'element': event,
                'image': image,
                'title': title,
                'link': link,
                'event_id': event_id,
                'start': start,
                'end': end,
                'location': location,
            })

        return events_list

    def handle(self, *args, **options):
        session = self._login(settings.FACEBOOK_USER, settings.FACEBOOK_PASS)
        events = self._get_events(session, settings.FACEBOOK_GROUP)
        events_list = self._parse_events(events)

        # All upcoming / future events
        known_events = Event.objects.filter(
            event_id__startswith='fb:',
            start_time__gte=datetime.now(),
        )

        # Delete events in our system that are not listed on facebook
        (
            known_events
                .exclude(
                    event_id__in=[event['event_id'] for event in events_list]
                )
                .delete()
        )
        # Create and update events listed
        for event in events_list:
            data = self._get_event(session, event['event_id'][3:])
            description = data.cssselect('.bx .cv.ck')
            if description:
                description[0].getchildren()[0].drop_tree()
                description = description[0].text
            else:
                description = ''
            going = data.cssselect('.de.cq.df')
            if going:
                going = int(going[0].text)
            else:
                going = 0

            try:
                obj = Event.objects.get(event_id=event['event_id'])
            except Event.DoesNotExist:
                obj = Event(event_id=event['event_id'])
            obj.title = event['title']
            obj.location = event['location']
            obj.start_time = event['start']
            obj.end_time = event['end']
            obj.description = description
            obj.attending = going
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
                    ContentFile(session.get(event['image']).content),
                    save=False,
                )
            obj.save()

from django.db import models


class Event(models.Model):
    event_id = models.CharField(max_length=64, unique=True)
    title = models.CharField(max_length=128)
    image = models.ImageField(upload_to='events/', null=True)
    image_url = models.CharField(max_length=1024, null=True)
    location = models.CharField(max_length=512, null=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True)
    description = models.TextField()
    attending = models.PositiveIntegerField(default=0)

    def link(self):
        if self.event_id.startswith('fb:'):
            _, event_id = self.event_id.split(':')
            return 'https://facebook.com/events/%s' % event_id
        elif self.event_id.startswith('mu:'):
            _, group, event_id = self.event_id.split(':')
            return 'https://meetup.com/%s/events/%s' % (group, event_id)

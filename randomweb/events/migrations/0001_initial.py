# Generated by Django 2.1.15 on 2020-02-03 20:10

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Event',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_id', models.CharField(max_length=64, unique=True)),
                ('title', models.CharField(max_length=128)),
                ('image', models.ImageField(null=True, upload_to='events/')),
                ('image_url', models.CharField(max_length=1024, null=True)),
                ('location', models.CharField(max_length=512, null=True)),
                ('start_time', models.DateTimeField()),
                ('end_time', models.DateTimeField(null=True)),
                ('description', models.TextField()),
                ('attending', models.PositiveIntegerField(default=0)),
            ],
        ),
    ]
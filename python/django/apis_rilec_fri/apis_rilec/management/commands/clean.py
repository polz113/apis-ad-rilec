from django.core.management.base import BaseCommand, CommandError
from apis_rilec.models import DataSource, UserData, UserDataField, MergedUserData
from django.utils import timezone
from datetime import timedelta, datetime

class Command(BaseCommand):
    help = "Clean old, unused user data"

    def add_arguments(self, parser):
        parser.add_argument('-t', '--timestamp', type=datetime.fromisoformat,
                            help='Delete user data older than timestamp, in ISOformat - YYYY-MM-DD:HH:mm:ss')
        parser.add_argument('-d', '--days', type=int,
                            help='Delete user data older than D days')

    def clean_userdata(self, older_than):
        UserData.objects.filter(mergeduserdata=None).delete()
        DataSource.objects.filter(timestamp__lte=older_than).delete()
        UserDataField.objects.filter(changed_t__lte=older_than).delete()
        UserData.objects.filter(fields=None).delete()
        UserData.objects.filter(dataset=None).delete()
        MergedUserData.objects.filter(data=None).delete()

    def clean_ldapdata(self):
        pass

    def handle(self, *args, **options):
        iso_timestamp = options.get('timestamp', None)
        if iso_timestamp is not None:
            iso_timestamp = timezone.make_aware(iso_timestamp)
        days = options.get('days', None)
        days_timestamp = None
        if days is not None:
            days_timestamp = timezone.now() - timedelta(days=days)
        all_timestamps = [days_timestamp, iso_timestamp]
        valid_timestamps = list(filter(lambda x: x is not None, all_timestamps))
        timestamp = None
        if len(valid_timestamps) > 0:
            timestamp = max(valid_timestamps)
        if timestamp is not None:
            print("Deleting user data older than", timestamp)
            self.clean_userdata(older_than=timestamp)


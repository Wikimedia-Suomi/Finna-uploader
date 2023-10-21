from django.core.management.base import BaseCommand
from django.db import transaction
import time
from images.models import FinnaImage
from images.finna import do_finna_search


class Command(BaseCommand):
    help = 'Import records from Finna search result to the database'

    def handle(self, *args, **kwargs):
        lookfor = None
        type = None
        collection = 'Studio Kuvasiskojen kokoelma'
#        collection = 'JOKA Journalistinen kuva-arkisto'

        for page in range(1, 201):
            # Prevent looping too fast for Finna server
            time.sleep(1)
            data = do_finna_search(page, lookfor, type, collection)
            if 'records' in data:
                with transaction.atomic():
                    for record in data['records']:
                        # Import code is in images/models.py
                        r = FinnaImage.objects.create_from_finna_record(record)
                        print(f'{r.id} {r.finna_id} {r.title} saved')
            else:
                break

        self.stdout.write(self.style.SUCCESS('Images saved succesfully!'))

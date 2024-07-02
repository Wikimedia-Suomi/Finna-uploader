from django.core.management.base import BaseCommand
from django.db import transaction
import time
from images.models import FinnaImage
from images.finna import do_finna_search, \
                         get_supported_collections


class Command(BaseCommand):
    help = 'Import records from Finna search result to the database'

    def add_arguments(self, parser):
        # Named (optional) arguments
        parser.add_argument(
            '--collection',
            type=str,
            choices=get_supported_collections(),
            help=('Finna type argument. '
                  'Argument selects where lookfor matches.')
        )

        parser.add_argument(
            '--type',
            type=str,
            choices=['AllFields', 'Subjects'],
            help=('Finna type argument. '
                  'Argument selects where lookfor matches.')
        )

        parser.add_argument(
            '--lookfor',
            type=str,
            help='Finna lookfor argument.',
        )

    def handle(self, *args, **options):
        lookfor = options['lookfor'] or None
        type = options['type'] or None
        default_collection = 'Studio Kuvasiskojen kokoelma'
        collection = options['collection'] or default_collection

        for page in range(1, 201):
            # Prevent looping too fast for Finna server
            time.sleep(1)

            # images.finna.do_finna_search() will look again for a collection
            data = do_finna_search(page, lookfor, type, collection)
            if 'records' in data:
                with transaction.atomic():
                    for record in data['records']:
                        # Import code is in images/models.py
                        r = FinnaImage.objects.create_from_data(record)
                        print(f'{r.id} {r.finna_id} {r.title} saved')
            else:
                break

        FinnaImage.objects.update_wikidata_ids()
        self.stdout.write(self.style.SUCCESS('Images saved succesfully!'))

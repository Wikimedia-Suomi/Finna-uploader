from django.core.management.base import BaseCommand
from django.db import transaction
import time
from images.models import FinnaImage
from images.finna_record_api import do_finna_search, get_supported_collections

from images.wikitext.wikidata_helpers import get_collection_name_from_alias, \
                                            get_collection_aliases


class Command(BaseCommand):
    help = 'Import records from Finna search result to the database'

    # TODO: support for alias or institution:
    # Helsingin kaupunginmuseo and SA-kuva have institution but no collection information
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
            '--alias',
            type=str,
            choices=get_collection_aliases(),
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

    # save one record from data
    def save_record_data(self, record):
        # Import code is in images/models.py
        print(f' - - - -') # just separate where next record begins for clarity in log
        try:
            r = FinnaImage.objects.create_from_data(record)
            print(f'{r.id} {r.finna_id} {r.title} saved')
            return True
        except:
            print("ERROR saving record: ")
            print(record)
            exit(1)
        return False

    # parse record(s) from query
    def parse_finna_records(self, data):
        if not data:
            return False
        if not 'records' in data:
            return False
        
        with transaction.atomic():
            for record in data['records']:
                # Import code is in images/models.py
                if (self.save_record_data(record) == False):
                    return False
        return True
        

    def handle(self, *args, **options):
        lookfor = options['lookfor'] or None
        type = options['type'] or None
        default_collection = 'Studio Kuvasiskojen kokoelma'
        collection = options['collection'] or default_collection
        aliascoll = options['alias'] or None

        if (aliascoll != None):
            collection = get_collection_name_from_alias(aliascoll)
        
        #if (collection == None and aliases != None):
        #    collection = aliases

        for page in range(1, 301):

            # images.finna.do_finna_search() will look again for a collection
            data = do_finna_search(page, lookfor, type, collection)
            if (self.parse_finna_records(data) == False):
                return False
            else:
                # Prevent looping too fast for Finna server
                time.sleep(1)

        FinnaImage.objects.update_wikidata_ids()
        self.stdout.write(self.style.SUCCESS('Images saved succesfully!'))

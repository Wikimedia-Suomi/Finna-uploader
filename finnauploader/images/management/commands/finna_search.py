from django.core.management.base import BaseCommand
import time
from images.finna_record_api import get_supported_collections, \
                                    get_collection_aliases
from images.import_helper import do_finna_import

class Command(BaseCommand):
    help = 'Import records from Finna search result to the database'

    # support for alias or institution:
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

        parser.add_argument(
            '--skipupdate', action='store_true',
            help='Do not run slow update of previously uploaded images.',
        )


    def handle(self, *args, **options):
        lookfor = options['lookfor'] or None
        type = options['type'] or None
        collection = options['collection'] or None
        alias = options['alias'] or None
        skip_update = options['skipupdate'] or False
        
        #if (collection == None and aliases != None):
        #    collection = aliases
        do_finna_import(lookfor, type, collection, alias, skip_update)

        self.stdout.write(self.style.SUCCESS('Search completed!'))

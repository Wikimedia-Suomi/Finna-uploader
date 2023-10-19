import json
from django.core.management.base import BaseCommand
from images.models import Image,ToolforgeImageHashCache
import requests
from django.db.models import Count
from images.conversion import unsigned_to_signed
from django.db import transaction

class Command(BaseCommand):
    help = 'Import Commons Finna imagehashes from Toolforge to database'

    def handle(self, *args, **kwargs):
        url = 'https://imagehash.toolforge.org/static/commons_finna_imagehashes.json.gz'

        # Fetch the data
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors

        # Decode the gzipped content
        #decompressed_data = gzip.decompress(response.content)

        # Load JSON data
        rows = json.loads(response.content)

        with transaction.atomic():
            for row in rows:
                imagehash, created=ToolforgeImageHashCache.objects.get_or_create(
                                  page_id=row['commons'],
                                  phash=unsigned_to_signed(row['phash']),
                                  dhash=unsigned_to_signed(row['dhash']),
                               )
                if created:
                    imagehash.save()
        photos=Image.objects.all()          
        imagehashes=ToolforgeImageHashCache.objects.all()

        print(photos.count())
        print(imagehashes.count())
        
   

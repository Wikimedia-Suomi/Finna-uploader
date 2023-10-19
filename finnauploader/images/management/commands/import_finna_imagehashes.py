import json
from django.core.management.base import BaseCommand
from images.models import FinnaImage, FinnaImageHash, FinnaImageHashURL
import pywikibot
from pywikibot.data import sparql
import requests
from django.db.models import Count
from images.conversion import unsigned_to_signed
import gzip
from django.db import transaction

class Command(BaseCommand):
    help = 'Import Finna imagehashes from https://github.com/Wikimedia-Suomi/Finna-uploader/raw/main/finna_imagehashes.json.gz  to database'

    def handle(self, *args, **kwargs):
        url = 'https://github.com/Wikimedia-Suomi/Finna-uploader/raw/main/finna_imagehashes.json.gz'

        # Fetch the data
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors

        # Decode the gzipped content
        decompressed_data = gzip.decompress(response.content)

        # Load JSON data
        rows = json.loads(decompressed_data)

        with transaction.atomic():
            for row in rows:
                print(row)
                photo=FinnaImage.objects.filter(finna_id=row['finna_id']).first()

                #Skip if there is no relevant photo in db
                if not photo:
                    continue

                imagehash, created=FinnaImageHash.objects.get_or_create(
                                  finna_image=photo,
                                  phash=unsigned_to_signed(row['phash']),
                                  dhash=unsigned_to_signed(row['dhash']),
                                  dhash_vertical=unsigned_to_signed(row['dhash_vertical'])
                               )
                if created:
                    imagehash.save()
          
                imagehash_url, created=FinnaImageHashURL.objects.get_or_create(
                                       imagehash=imagehash,
                                       url=row['url'],
                                       width=row['width'],
                                       height=row['height'],
                                       index=row['index'],
                                       thumbnail=row['thumbnail']
                                   )
                if created:
                    imagehash_url.save()

        photos=FinnaImage.objects.all()
        imagehashes=FinnaImageHash.objects.all()
        imagehashurls=FinnaImageHashURL.objects.all()

        print(photos.count())
        print(imagehashes.count())
        print(imagehashurls.count())
        

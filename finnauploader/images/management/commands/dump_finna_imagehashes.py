import json
from django.core.management.base import BaseCommand
from images.models import FinnaImage, FinnaImageHash, FinnaImageHashURL
import pywikibot
from pywikibot.data import sparql
import requests
from django.db.models import Count
from images.conversion  import signed_to_unsigned

class Command(BaseCommand):
    help = 'Print stats on images on database'

    def handle(self, *args, **kwargs):
        rows=[]
        images=FinnaImage.objects.all()
        for image in images:
            imagehashes=FinnaImageHash.objects.filter(finna_image=image)
            for imagehash in imagehashes:
                imagehash_urls=FinnaImageHashURL.objects.filter(imagehash=imagehash)
                for imagehash_url in imagehash_urls:
                    row={}
                    row['finna_id'] = image.finna_id
                    row['phash'] = signed_to_unsigned(imagehash.phash)
                    row['dhash'] = signed_to_unsigned(imagehash.dhash)
                    row['dhash_vertical'] = signed_to_unsigned(imagehash.dhash_vertical)
                    row['width'] = imagehash_url.width
                    row['height'] = imagehash_url.height
                    row['index'] = imagehash_url.index
                    row['url'] = imagehash_url.url
                    row['thumbnail'] = imagehash_url.thumbnail
                    row['created'] = imagehash_url.created.strftime('%Y-%m-%d %H:%M:%S') 
                    rows.append(row)
        out=json.dumps(rows)
        out=out.replace('},','},\n')  # Pretty print one row per line
        out=out.replace('[{','[\n{')  # Pretty print first line
        out=out.replace('}]','}\n]')  # Pretty print last line
        print(out)

   

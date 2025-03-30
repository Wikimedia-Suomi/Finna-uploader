import json
from django.core.management.base import BaseCommand
from images.models import Image,ToolforgeImageHashCache
import requests
from django.db.models import Count
from images.conversion import unsigned_to_signed
import gzip
from django.db import transaction

class Command(BaseCommand):
    help = 'Import Commons Finna imagehashes from Toolforge to database'

    def saverow(self, page_id_in, phash_in, dhash_in):
        imagehash, created=ToolforgeImageHashCache.objects.get_or_create(
                            page_id=page_id_in,
                            phash=unsigned_to_signed(phash_in),
                            dhash=unsigned_to_signed(dhash_in),
                        )
        if created:
            imagehash.save()

    def fromurl(self):
        url = 'https://imagehash.toolforge.org/static/commons_finna_imagehashes.json.gz'

        # Fetch the data
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors

        # Decode the gzipped content
        #decompressed_data = gzip.decompress(response.content)

        return response.content

    def fromjsondata(self, data):
        # Load JSON data
        rows = json.loads(data)

        with transaction.atomic():
            for row in rows:
                self.saverow(row['commons'], row['phash'], row['dhash'])


    def fromtabulatedfile(self):
        name = '/tmp/imagehash_commons_page_id_phash_dhash.tsv'
        f = open(name)
        
        d = []
        for line in f:
            fields = line.split('\t')
            d.append(fields)

        # debug
        #for row in d:
        #    print("id: ",  row[0], ", phash: ", row[1], ", dhash: ", row[2])

        #
        # this is incredibly SLOW: we should use batch import instead
        # 
        #
        with transaction.atomic():
            for row in d:
                page_id = int(row[0].lstrip().rstrip())
                phash = int(row[1].lstrip().rstrip())
                dhash = int(row[2].lstrip().rstrip())
                self.saverow(page_id, phash, dhash)
     

    def handle(self, *args, **kwargs):

        # Load JSON data
        data = self.fromurl()
        self.fromjsondata(data)

        # or tabulated data from local file
        #self.fromtabulatedfile()
        
        photos=Image.objects.all()          
        imagehashes=ToolforgeImageHashCache.objects.all()

        print(photos.count())
        print(imagehashes.count())
        
   

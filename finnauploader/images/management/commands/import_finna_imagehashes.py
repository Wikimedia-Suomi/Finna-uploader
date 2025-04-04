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
import hashlib
import imagehash

class Command(BaseCommand):
    help = 'Import Finna imagehashes from https://github.com/Wikimedia-Suomi/Finna-uploader/raw/main/finna_imagehashes.json.gz  to database'

    # convert string to base 16 integer for calculating difference
    #def converthashtoint(h, base=16):
    #    return int(h, base)

    def converthashstringtoint(self, h_in):
        hstr = str(h_in).lstrip().rstrip()
        #htmp = hash(hstr)
        return int(hstr, 16)


    def get_sparql_query(self, query):

        # Set up the SPARQL endpoint and entity URL
        # Note: https://commons-query.wikimedia.org requires
        # user to be logged in

        entity_url = 'https://commons.wikimedia.org/entity/'
        endpoint = 'https://commons-query.wikimedia.org/sparql'

        # Create a SparqlQuery object
        query_object = sparql.SparqlQuery(endpoint=endpoint,
                                          entity_url=entity_url)

        # Execute the SPARQL query and retrieve the data
        data = query_object.select(query, full_data=True)
        if data is None:
            print("SPARQL Failed. login BUG?")
            exit(1)

        return data

    def get_existing_finna_ids_and_imagehashes_from_sparql(self):
        print("Loading existing photo Finna ids and imagehashes using SPARQL")

        # media id for commons image id?

        # Define the SPARQL query
        query = "SELECT * WHERE {"
        query += " ?media wdt:P9478 ?finna_id ."
        query += " ?media schema:url ?image."
        query += " OPTIONAL { ?media wdt:P9310 ?phash }"
        query += " OPTIONAL { ?media wdt:P12563 ?dhash }"
        query += "}"

        return self.get_sparql_query(query)

    def add_imagehash(self, finna_id_in, phash_in, dhash_in):

        # should check for Image for Commons-image?
        # also link to WikimediaCommonsImage?
        # commons might have images that we haven't yet loaded from finna?
        photo = FinnaImage.objects.filter(finna_id=finna_id_in).first()

        # finna image url
        #url = 'https://finna.fi/Cover/Show?source=Solr&size=large'
        #url += f'&id={photo.finna_id}'
        #url += f'&index={index}'
        # should use record?
        #url = 'https://finna.fi/Record/'
        #url += f'{photo.finna_id}'


        #Skip if there is no relevant photo in db
        if not photo:
            print("image with finna_id:", finna_id_in, " does not exist, skipping")
            return
        
        if (phash_in == None or dhash_in == None):
            print("No hashes given for image with finna_id:", finna_id_in, ", skipping")
            return 

        phash_int = self.converthashstringtoint(phash_in)
        dhash_int = self.converthashstringtoint(dhash_in)

        # we can't add duplicates to database even if duplicates may exist
        # -> check and skip
        exists = False
        try:
            imageobj = FinnaImageHash.objects.get(phash=unsigned_to_signed(phash_int))
            if (imageobj):
                exists = True
        except FinnaImageHash.MultipleObjectsReturned:
            # key checks for pair: might have same duplicates
            print("Exception: multiple objects found -> skip")
            return
        except FinnaImageHash.DoesNotExist:
            # should not get exception in this case?
            # -> ignore as we will add this next
            print("Exception: hash does not exist?")

        # might have phash but not dhash or vice versa -> check separately
        try:
            imageobj = FinnaImageHash.objects.get(dhash=unsigned_to_signed(dhash_int))
            if (imageobj):
                exists = True
        except FinnaImageHash.MultipleObjectsReturned:
            # key checks for pair: might have same duplicates
            print("Exception: multiple objects found -> skip")
            return
        except FinnaImageHash.DoesNotExist:
            # should not get exception in this case?
            # -> ignore as we will add this next
            print("Exception: hash does not exist?")

        # also, there may be different image with same hash or same image id with different hash
        # in case of cropped/modified images: hash may be saved before cropping or contrast changes
        # or there may be another version of same image where the modifications are made
        try:
            # key checks for pair
            imageobj = FinnaImageHash.objects.get(finna_image=photo)
            if (imageobj):
                exists = True
        except FinnaImageHash.MultipleObjectsReturned:
            print("Exception: multiple objects found -> skip")
            return
        except FinnaImageHash.DoesNotExist:
            # should not get exception in this case?
            # -> ignore as we will add this next
            print("Exception: image does not exist?")

        if (exists):
            print("Hash or iamge already exists, skipping")
            return 

        imagehash, created=FinnaImageHash.objects.get_or_create(
                            finna_image=photo,
                            phash=unsigned_to_signed(phash_int),
                            dhash=unsigned_to_signed(dhash_int)
                            #dhash_vertical=unsigned_to_signed(row['dhash_vertical'])
                        )
        if created:
            imagehash.save()
            print("saved hashes to image with finna_id:", finna_id_in)


    def fetch_finna_ids_and_imagehashes(self):
        site = pywikibot.Site("commons", "commons")
        site.login()

        # fetch hashes too
        rows = self.get_existing_finna_ids_and_imagehashes_from_sparql()
        for row in rows:
            print(row)
            finna_id = str(row['finna_id'])
            phash = row['phash'] # may be None
            dhash = row['dhash'] # may be None

            print("found image with finna_id:'",finna_id,"' phash:'",phash,"' dhash:'",dhash,"'")

            #with transaction.atomic():
            self.add_imagehash(finna_id, phash, dhash)


    def fromurl(self, url):

        # Fetch the data
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors

        # Decompress the gzipped content
        return gzip.decompress(response.content)


    def fromfile(self):
        name = 'finna_imagehashes.json.gz'
        
        f = gzip.open(name, 'rb')
        return f.read()


    def fetch_file_with_finna_ids_and_imagehashes(self):
        url = 'https://github.com/Wikimedia-Suomi/Finna-uploader/raw/main/finna_imagehashes.json.gz'

        # Decompress the gzipped content
        decompressed_data = self.fromurl(url)

        #decompressed_data = self.fromfile()

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


    def handle(self, *args, **kwargs):
        
        # download file and import
        #self.fetch_file_with_finna_ids_and_imagehashes()

        # use sparql query and import
        self.fetch_finna_ids_and_imagehashes()

        photos=FinnaImage.objects.all()
        imagehashes=FinnaImageHash.objects.all()
        imagehashurls=FinnaImageHashURL.objects.all()

        print(photos.count())
        print(imagehashes.count())
        print(imagehashurls.count())
        

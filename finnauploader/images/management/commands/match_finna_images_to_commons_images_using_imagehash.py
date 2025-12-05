#

from django.core.management.base import BaseCommand
from images.models import Image, ImageURL, FinnaImage, FinnaBuilding, FinnaNonPresenterAuthor, FinnaImageHash, FinnaImageHashURL, SdcFinnaID
import pywikibot
from pywikibot.data import sparql
import requests
import time
from images.finna_record_api import do_finna_search
from images.imagehash_helpers import get_imagehashes
from images.conversion import unsigned_to_signed, signed_to_unsigned

class Command(BaseCommand):
    help = 'Match Finna images to commons images using imagehash.'
    
    def fetch(self, session, url):
        print("fetching url:", url)
        start_time = time.time()
        response = session.get(url)
        end_time = time.time()
        print("fetch time:", end_time-start_time)
        return response

    def handle(self, *args, **kwargs):
        site = pywikibot.Site("commons", "commons")  # for Wikimedia Commons
        session = requests.Session()
        session.headers.update({'User-Agent': 'FinnaUploader 0.1'})

        imagehashes=FinnaImageHash.objects.all()
        for imagehash in imagehashes:
            finna_id=imagehash.finna_image.finna_id
#            if finna_id != 'museovirasto.B0ACA4613D5CF819619E461288E6CB01':
#                continue

            sdc_finna_id=SdcFinnaID.objects.filter(finna_id=finna_id).first()
            if sdc_finna_id:
                continue

            photo=Image.objects.filter(finna_id=finna_id).first()
            if photo:
                continue

#            print(f'{imagehash.finna_image.finna_id}\t{imagehash.finna_image.title}')
            phash=signed_to_unsigned(imagehash.phash)
            dhash=signed_to_unsigned(imagehash.dhash)
            url=f'https://imagehash.toolforge.org/search?dhash={dhash}&phash={phash}'

            response = self.fetch(session, url)

            # Check if the request was successful
            if response.status_code == 200:
                rows = response.json()
                for row in rows:
                    file_page = pywikibot.FilePage(site, row['page_title'])
                    item = file_page.data_item()
                    data=item.get()
                    if 'P9478' not in str(data):
                        print(f'P9478 missing: {file_page}')
                        
                    # should save match somewhere?
 
            else:
                print("Failed to retrieve data. Status code:", response.status_code)

        #print("Hash matches done")


        self.stdout.write(self.style.SUCCESS(f'Images counted succesfully!'))
        session.close()

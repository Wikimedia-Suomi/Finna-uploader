from django.db.models import Q
from django.core.management.base import BaseCommand
from images.models import Image, FinnaImage, FinnaImageHash, ToolforgeImageHashCache, SdcFinnaID
import pywikibot
from pywikibot.data import sparql
import requests
import time
from images.imagehash_helpers import unsigned_to_signed, signed_to_unsigned, compare_image_hashes

class Command(BaseCommand):
    help = 'Match Finna images to commons images using imagehash.'

    def handle(self, *args, **kwargs):
        site = pywikibot.Site("commons", "commons")  # for Wikimedia Commons

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
            img1 = {
                'phash':signed_to_unsigned(imagehash.phash),
                'dhash': signed_to_unsigned(imagehash.dhash),
                'dhash_vertical':0
            }

            # "SELECT DISTINCT(*) FROM ToolforgeImageHashCache WHERE dhash=imagehash.dhash OR phash=imagehash.phash"
            rows=ToolforgeImageHashCache.objects.filter(Q(dhash=imagehash.dhash) | Q(phash=imagehash.phash)).distinct()
            for row in rows:
                img2 = {
                    'phash':signed_to_unsigned(row.phash),
                    'dhash':signed_to_unsigned(row.dhash),
                    'dhash_vertical':255

                }
                if compare_image_hashes(img1, img2):
                    print(".", end='',flush=True)
                    pages = site.load_pages_from_pageids([row.page_id])
                    for page in pages:

                        # Converting page to FilePage
                        file_page = pywikibot.FilePage(site, page.title())
                        item = file_page.data_item()
                        data=item.get()

                        if 'P9478' not in str(data):
                           print(f'\nP9478 missing: {file_page}')

        self.stdout.write(self.style.SUCCESS(f'Images matched succesfully!'))

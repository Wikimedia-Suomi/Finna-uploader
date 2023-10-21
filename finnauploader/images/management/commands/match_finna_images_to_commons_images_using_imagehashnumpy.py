from django.db.models import Q
from django.core.management.base import BaseCommand
from images.models import Image, FinnaImage, FinnaImageHash, ToolforgeImageHashCache, SdcFinnaID
import pywikibot
from pywikibot.data import sparql
import requests
import time
from images.imagehash_helpers import compare_image_hashes, is_correct_finna_record
from images.conversion import unsigned_to_signed, signed_to_unsigned
import numpy as np
from images.duplicatedetection import search_from_sparql_finna_ids

phashes_signed=toolforgeimagehashes=ToolforgeImageHashCache.objects.values_list('phash', flat=True)
haystack_phash = np.array(phashes_signed) 

dhashes_signed=toolforgeimagehashes=ToolforgeImageHashCache.objects.values_list('dhash', flat=True)
haystack_dhash = np.array(dhashes_signed) 


def bit_count(n):
    return np.vectorize(lambda x: bin(x).count('1'))(n)

def get_nearest_numbers_dhash(needle, max_distance=4):
    distances = np.bitwise_xor(haystack_dhash, needle)
    bit_counts = bit_count(distances)

    # Filter haystack based on hamming distance being less than 4
    nearest_numbers = haystack_dhash[bit_counts < max_distance]

    # Filter out duplicates
    unique_nearest_numbers = np.unique(nearest_numbers)
    return unique_nearest_numbers

def get_nearest_numbers_phash(needle, max_distance=4):
    distances = np.bitwise_xor(haystack_phash, needle)
    bit_counts = bit_count(distances)

    # Filter haystack based on hamming distance being less than 4
    nearest_numbers = haystack_phash[bit_counts < max_distance]

    # Filter out duplicates
    unique_nearest_numbers = np.unique(nearest_numbers)
    return unique_nearest_numbers



class Command(BaseCommand):
    help = 'Match Finna images to commons images using imagehash.'

    def handle(self, *args, **kwargs):
        commons_site = pywikibot.Site("commons", "commons")  # for Wikimedia Commons
        wikidata_site = pywikibot.Site("wikidata", "wikidata")  # for Wikidata

        imagehashes=FinnaImageHash.objects.all()
        print(len(imagehashes))

        for imagehash in imagehashes:
            finna_id=imagehash.finna_image.finna_id
#            if finna_id != 'museovirasto.B0ACA4613D5CF819619E461288E6CB01':
#                continue

            phashes=get_nearest_numbers_phash(imagehash.phash, 6)
            dhashes=get_nearest_numbers_dhash(imagehash.dhash, 6)
            photos=ToolforgeImageHashCache.objects.filter(phash__in=phashes, dhash__in=dhashes).values_list('page_id', flat=True).distinct()
            for photo in photos:
                print(".", end='',flush=True)
#                print(photo)
                pages = commons_site.load_pages_from_pageids([photo])
                for page in pages:
#                    print(page.title())
                    file_page = pywikibot.FilePage(commons_site, page.title())
                    item = file_page.data_item()
                    try:
                        data=item.get()
                    except:
                        continue
                    if search_from_sparql_finna_ids(f'M{photo}'):
#                        print('SKIPPING')
                        continue

                    if 'P9478' not in str(data):
                        print(f'\nP9478 missing: {file_page}')
                        commons_thumbnail_url=file_page.get_file_url(url_width=500)
                        confirmed_finna_id=is_correct_finna_record(finna_id, commons_thumbnail_url)
                        if confirmed_finna_id:
                            print('adding P9478')
                            new_claim = pywikibot.Claim(wikidata_site, 'P9478')
                            new_claim.setTarget(finna_id)
                            commons_site.addClaim(item,new_claim)

            
            if 1:
                continue


            sdc_finna_id=SdcFinnaID.objects.filter(finna_id=finna_id).first()
            if sdc_finna_id:
                continue

            photo=Image.objects.filter(finna_id=finna_id).first()
            if photo:
                continue

#            print(f'{imagehash.finna_image.finna_id}\t{imagehash.finna_image.title}')
            img1 = {
                'phash':signed_to_unsigned(imagehash.phash),
                'dhash':signed_to_unsigned(imagehash.dhash),
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
                    pages = commons_site.load_pages_from_pageids([row.page_id])
                    for page in pages:

                        # Converting page to FilePage
                        file_page = pywikibot.FilePage(commons_site, page.title())
                        item = file_page.data_item()
                        try:
                            data=item.get()
                        except:
                            continue

                        if 'P9478' not in str(data):
                           print(f'\nP9478 missing: {file_page}')

                           commons_thumbnail_url=file_page.get_file_url(url_width=500)
                           confirmed_finna_id=is_correct_finna_record(finna_id, commons_thumbnail_url)
                           if confirmed_finna_id:
                               print('adding P9478')
                               new_claim = pywikibot.Claim(wikidata_site, 'P9478')
                               new_claim.setTarget(finna_id)
                               commons_site.addClaim(item,new_claim)                              

        self.stdout.write(self.style.SUCCESS(f'Images matched succesfully!'))

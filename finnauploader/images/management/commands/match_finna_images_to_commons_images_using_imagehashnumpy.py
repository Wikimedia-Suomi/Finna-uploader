#

from django.core.management.base import BaseCommand
from images.models import FinnaImageHash, ToolforgeImageHashCache
import pywikibot
from images.finna_record_api import get_finna_image_urls
from images.imagehash_helpers import compare_finna_hash, get_imagehashes
import numpy as np
from images.duplicatedetection import search_from_sparql_finna_ids

phashes_signed = ToolforgeImageHashCache.objects.values_list('phash',
                                                             flat=True)
haystack_phash = np.array(phashes_signed)

dhashes_signed = ToolforgeImageHashCache.objects.values_list('dhash',
                                                             flat=True)
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
        commons_site = pywikibot.Site("commons", "commons")
        wikidata_site = pywikibot.Site("wikidata", "wikidata")

        imagehashes = FinnaImageHash.objects.all()
        print(len(imagehashes))

        for imagehash in imagehashes:
            finna_id = imagehash.finna_image.finna_id
#            if finna_id != 'museovirasto.B0ACA4613D5CF819619E461288E6CB01':
#                continue

            #finna_record = get_finna_record(finna_id, True)
            finnaurls = get_finna_image_urls(finna_id)

            phashes = get_nearest_numbers_phash(imagehash.phash, 6)
            dhashes = get_nearest_numbers_dhash(imagehash.dhash, 6)
            p = ToolforgeImageHashCache.objects
            filtered_p = p.filter(phash__in=phashes, dhash__in=dhashes)
            photolist = filtered_p.values_list('page_id', flat=True).distinct()

            for photo in photolist:
                print(".", end='', flush=True)
                pages = commons_site.load_pages_from_pageids([photo])
                for page in pages:
                    file_page = pywikibot.FilePage(commons_site, page.title())
                    item = file_page.data_item()
                    try:
                        data = item.get()
                    except:
                        continue
                    if search_from_sparql_finna_ids(f'M{photo}'):
                        print('SKIPPING')
                        continue

                    if 'P9478' not in str(data):
                        print(f'\nP9478 missing: {file_page}')
                        thumbnail_url = file_page.get_file_url(url_width=500)
                        commons_img_hash = get_imagehashes(commons_thumbnail_url)
                        confirmed = compare_finna_hash(finnaurls, commons_img_hash)
                        if confirmed:
                            print('adding P9478')
                            new_claim = pywikibot.Claim(wikidata_site, 'P9478')
                            new_claim.setTarget(finna_id)
                            commons_site.addClaim(item, new_claim)

        self.stdout.write(self.style.SUCCESS('Images matched succesfully!'))

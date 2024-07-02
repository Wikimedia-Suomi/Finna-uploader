from django.core.management.base import BaseCommand
from images.models import FinnaImage
from images.imagehash_helpers import is_correct_finna_record
import pywikibot
import time
from pywikibot.data.sparql import SparqlQuery

wdsite = pywikibot.Site("wikidata", "wikidata")
wdrepo = wdsite.data_repository()

csite = pywikibot.Site('commons', 'commons')
csite.login()

qid_cache = {}


def set_sdc_data(page, data):

    # Add the claim to the file
    filtered_parts = []
    parts = data['P5997'].replace(';', ',').split(',')
    for part in parts:
        part = part.strip()
        if part not in filtered_parts:
            filtered_parts.append(part)
    filtered_location_string = ", ".join(filtered_parts)

    if not page.exists():
        print(f"The file {page} does not exist on Wikimedia Commons.")
        return

    # Check if the file already has a P1071 value
    item = page.data_item()
    item.get()

    if 'P1071' in item.claims:
        print(f"The file {page} already has a P1071 value.")
        return

    # Create a new Claim
    # P1071 is 'location'
    claim = pywikibot.Claim(wdrepo, 'P1071')
    target = pywikibot.ItemPage(wdrepo, data['P1071'])
    claim.setTarget(target)

    # Create source Claims
    source_claims = []

    # Location text
    ref_claim = pywikibot.Claim(wdrepo, 'P5997')
    ref_claim.setTarget(filtered_location_string)
    source_claims.append(ref_claim)

    # Source url
    ref_claim = pywikibot.Claim(wdrepo, 'P854')
    ref_claim.setTarget(data['P854'])
    source_claims.append(ref_claim)

    # Date
    ref_claim = pywikibot.Claim(wdrepo, 'P813')
    ref_claim.setTarget(data['P813'])
    source_claims.append(ref_claim)

    P1071_value = data['P1071']
    summary = f'Adding referenses to P1071 (location) = {P1071_value}'
    claim.addSources(source_claims, summary=summary)

    summary = f'from location "{filtered_location_string}"'

    print(f'{filtered_location_string}')
    print(data['P5997'])
    item.addClaim(claim, summary=summary)
    print("OK")


def get_label(qid):
    qid = str(qid).replace('http://www.wikidata.org/entity/', '')
    if qid in qid_cache:
        return qid_cache[qid]

    item = pywikibot.ItemPage(wdrepo, qid)
    item.get()
    finnish_label = item.labels.get('fi')
    qid_cache[qid] = finnish_label
    return finnish_label


def get_confirmed_filename(image, finna_id):
    file_page = pywikibot.FilePage(csite, image.title())
    commons_thumbnail_url = file_page.get_file_url(url_width=1024)
    confirmed_finna_id = is_correct_finna_record(finna_id,
                                                 commons_thumbnail_url)
    if confirmed_finna_id:
        return file_page
    else:
        return None


def get_sparql():
    query = """
SELECT DISTINCT ?media ?finna_id ?phash ?dhash ?location WHERE {
    ?media wdt:P195 wd:Q113292201 .
    ?media wdt:P9478 ?finna_id .
    OPTIONAL { ?media wdt:P9310 ?phash }
    OPTIONAL { ?media wdt:P12563 ?dhash }
    OPTIONAL { ?media wdt:P1071 ?location }
}
"""

    endpoint = 'https://commons-query.wikimedia.org/sparql'
    entity_url = 'https://commons.wikimedia.org/entity/'
    sparql = SparqlQuery(endpoint=endpoint, entity_url=entity_url)
    data = sparql.select(query)
    return data


class Command(BaseCommand):
    help = 'Add best wikidata location values to SDC'

    def handle(self, *args, **options):

        finna_ids = {}
        images = FinnaImage.objects
        for image in images.all():
            location_strings = []
            subject_places = image.subject_places.all()
            ordered_subject_places = sorted(subject_places,
                                            key=lambda sp: len(sp.name),
                                            reverse=True)
            print('')
            print(image.finna_id)

            for place in ordered_subject_places:
                if place.name not in "; ".join(location_strings):
                    location_strings.append(place.name)
#               print(f'{place.wikidata_id}\t{place}')

#            for wikidata_location in image.best_wikidata_location.all():
#                finnish_label = get_label(wikidata_location)
#                print(f'{wikidata_location}\t{finnish_label}')
#                print(f'{wikidata_location}')

            wikidata_locations = image.best_wikidata_location.all()
            if len(wikidata_locations) != 1:
                continue

            wikidata_location = wikidata_locations.first()

            location_string = "; ".join(location_strings)
            location_string = location_string.replace(";, ", "; ").lstrip(", ")

            p1071 = str(wikidata_location)
            p1071 = p1071.replace('http://www.wikidata.org/entity/', '')
            finna_data = {
                'P1071': p1071,
                'P5997': location_string,
                'P813': pywikibot.WbTime(year=2024, month=7, day=2),
                'P854': 'https://finna.fi/Record/' + image.finna_id
            }

            finna_ids[image.finna_id] = finna_data

        rows = get_sparql()
        for row in rows:
            if row['location']:
                continue

            if row['finna_id'] not in finna_ids:
                print('MISSING: ' + row['finna_id'])
                continue

            finna_data = finna_ids[row['finna_id']]
            entity_prefix = 'https://commons.wikimedia.org/entity/M'
            page_id = row['media'].replace(entity_prefix, '')
            page_id = int(page_id)
            finna_id = row['finna_id']
            image = list(csite.load_pages_from_pageids([page_id]))[0]
            fp = get_confirmed_filename(image, finna_id)
            print(fp)
            print(row)
            set_sdc_data(fp, finna_data)
            time.sleep(5)

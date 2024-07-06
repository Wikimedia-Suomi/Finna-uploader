from django.core.management.base import BaseCommand
from images.models import FinnaImage
from images.imagehash_helpers import is_correct_finna_record
import pywikibot
import time
import json
from pywikibot.data.sparql import SparqlQuery
from openai import OpenAI

wdsite = pywikibot.Site("wikidata", "wikidata")
wdrepo = wdsite.data_repository()

csite = pywikibot.Site('commons', 'commons')
csite.login()

qid_cache = {}


# Point to the local server
client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")

phi_cache = {}
skip_cache = []


def get_phi_sorted(location_string):
    if location_string in phi_cache:
        return phi_cache[location_string]

    filtered_location_string = get_filtered_location_string(location_string)
    if filtered_location_string == 'Suomi':
        print(filtered_location_string)
        print("----")
        return
    else:
        time.sleep(1)

    msg = "Sort these by hierarcy to be largest to smallest.\n\n"
#    msg = "Sort these by hierarcy to be smallest to largest.\n\n"
    orig_places = filtered_location_string.split(', ')
    for place in orig_places:
        place = place.strip()
        if place == '':
            continue
        msg += f'{place}\n'

    print(msg)
    system = "Return only input words. Answer as python list. No explanation."
    completion = client.chat.completions.create(
        # model="Nabokov/Phi-3-mini-4k-instruct-Q8_0-GGUF",
        model="bartowski/Phi-3-medium-4k-instruct-GGUF",
        messages=[
            {
                "role": "system",
                "content": system
            },
            {"role": "user", "content": msg}
        ],
        temperature=0.1,
    )
    message = completion.choices[0].message
    content_str = message.content.strip().replace("'", '"')

    print(content_str)
    try:
        phi_locations = json.loads(content_str)
    except:
        return location_string

    for phi_location in phi_locations:
        print(phi_location)
        if phi_location.strip() == '':
            continue

        if phi_location not in orig_places:

            print(orig_places)
            print("ERROR: phi location missing")
            return location_string

    for orig_place in orig_places:
        orig_place = orig_place.strip()
        if orig_place == '':
            continue

        if orig_place not in phi_locations:
            print(orig_place)
            print(phi_locations)
            print("ERROR: orig location missing")
            return location_string

    phi_cache[location_string] = ", ".join(phi_locations)
    print(phi_cache[location_string])
    return phi_cache[location_string]


def get_filtered_location_string(location_string):
    filtered_parts = []
    parts = location_string.replace(';', ',').split(',')

    for part in parts:
        part = part.strip()
        if part == '':
            continue
        if part not in filtered_parts:
            filtered_parts.append(part)

    if len(filtered_parts) < 4:
        return None

    filtered_location_string = ", ".join(filtered_parts)
    return filtered_location_string


def set_sdc_data(page, data):

    # Add the claim to the file

    if not page.exists():
        print(f"The file {page} does not exist on Wikimedia Commons.")
        return

    filtered_location_string = get_filtered_location_string(data['P5997'])
    if not filtered_location_string:
        return

    filtered_location_string = get_phi_sorted(filtered_location_string)
    if not filtered_location_string:
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

    if csite.userinfo['messages']:
        print("Warning: You have received a talk page message. Exiting.")
        exit()

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
            if not get_filtered_location_string(finna_data['P5997']):
                continue

            entity_prefix = 'https://commons.wikimedia.org/entity/M'
            page_id = row['media'].replace(entity_prefix, '')
            page_id = int(page_id)
            finna_id = row['finna_id']
            image = list(csite.load_pages_from_pageids([page_id]))[0]
            fp = get_confirmed_filename(image, finna_id)
            if not fp:
                continue
            print(fp)
            print(row)
#            get_phi_sorted(finna_data['P5997'])
            set_sdc_data(fp, finna_data)

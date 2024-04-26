from django.core.management.base import BaseCommand
from images.models import FinnaImage, CacheSparqlBool, FintoYsoLabel, \
                          FinnaSubjectWikidataPlace
import pywikibot
import time
from images.finna import do_finna_search, get_collection_names
from images.locations import is_location_within_administrative_entity, \
                             parse_subject_place_string, \
                             update_yso_places, test_property_value, \
                             get_p31_values, get_wikidata_items_using_yso, \
                             FintoYsoMissingCache, get_location_override
from images.wikitext.cache_wikidata import parse_cache_page

#CacheSparqlBool.objects.all().delete()
#FintoYsoMissingCache.objects.all().delete()
page_title = 'User:FinnaUploadBot/data/locationOverride'
locationOverrideCache = parse_cache_page(page_title)
print(locationOverrideCache)


# Function to update the list on Wikimedia Commons
def update_commons_list(name, wikidata_id):
    commons_site = pywikibot.Site('commons', 'commons')
    wikidata_id = wikidata_id.replace('http://www.wikidata.org/entity/', '')
    page_title = "User:FinnaUploadBot/data/locationOverride"
    page = pywikibot.Page(commons_site, page_title)
    target_text = f"\n* {name} : {{{{Q|{wikidata_id}}}}}"
    if target_text not in page.text:
        page.text += f"\n* {name} : {{{{Q|{wikidata_id}}}}}"
        page.save("Adding new entry for %s" % name)


def find_wikidata_url(data):
    if not data:
        return None

    # Check if data is a list of dictionaries
    if isinstance(data, list):
        # Iterate through each dictionary in the list
        for item in data:
            # Check if 'uri' key exists and contains 'wikidata.org'
            if 'uri' in item and 'wikidata.org' in item['uri']:
                return item
    # Check if data is a single dictionary
    elif isinstance(data, dict):
        # Check if 'uri' key exists and contains 'wikidata.org'
        if 'uri' in data and 'wikidata.org' in data['uri']:
            return data

    # Return None if no matching URL is found
    return None


def is_in_haystack(qids, types):
    for qid in qids:
        qid = qid.replace('http://www.wikidata.org/entity/', '')
        if qid in types:
            return True
    return False


def is_maanosa(place, wikidata_types, mml_types, other_types):
    known_place_ids = ['http://www.wikidata.org/entity/Q21195',
                       'http://www.wikidata.org/entity/Q1156427',
                       'http://www.wikidata.org/entity/Q98']
    maanosa_qids = ['Q113965177', 'Q1620908', 'Q5107']
    types = wikidata_types + mml_types + other_types

    if 'Q39731' in place:
        return True
    if place in known_place_ids:
        return True
    elif is_in_haystack(types, maanosa_qids):
        return True
    elif test_property_value(place, '(wdt:P279|wdt:P31)*', 'Q15646667'):
        return True
    elif test_property_value(place, 'wdt:P361/wdt:P31', 'Q15646667'):
        return True
    return False


def is_valtio(place, wikidata_types, mml_types, other_types):
    valtio_qids = ['Q7275', 'Q6256', 'Q3024240', 'Q788046']
    types = wikidata_types + mml_types + other_types
    if is_in_haystack(types, valtio_qids):
        return True
    return False


def is_maakunta(place, wikidata_types, mml_types, other_types):
    maakunta_qids = ['Q113965203', 'Q10742', 'Q629870', 'Q217691', 'Q853697']
    if 'Q11880042' in place:
        return True
    types = wikidata_types + mml_types + other_types
    if is_in_haystack(types, maakunta_qids):
        return True
    return False


def is_luonto(place, wikidata_types, mml_types, other_types):
    luonto_qids = ['Q355304', 'Q106589819', 'Q39594', 'Q113965178']
    types = wikidata_types + mml_types + other_types
    if is_in_haystack(types, luonto_qids):
        return True
    if test_property_value(place, '(wdt:P279|wdt:P31)*', 'Q33837'):
        return True
    if test_property_value(place, '(wdt:P279|wdt:P31)*', 'Q23397'):
        return True
    if 'Q6305010' in place:
        return True
    if 'Q1129324' in place:
        return True
    if 'Q209010' in place:
        return True
    return False


def is_kunta(place, wikidata_types, mml_types, other_types):
    kunta_qids = ['Q515', 'Q113965206', 'Q127448', 'Q42744322']
    types = wikidata_types + mml_types + other_types
    if is_in_haystack(types, kunta_qids):
        return True
    if test_property_value(place, '(wdt:P279|wdt:P31)*', 'Q515'):
        return True
    return False


def is_kaupunginosa(place, wikidata_types, mml_types, other_types):
    kaupunginosa_qids = ['Q103910131', 'Q103910453', 'Q103910131',
                         'Q103910177', 'Q63135009', 'Q63134896',
                         'Q17468533', 'Q60495698', 'Q6566301', 'Q18333556'
                         'Q1523821', 'Q12813115', 'Q532', 'Q5084', 'Q1523821']
    types = wikidata_types + mml_types + other_types
    if is_in_haystack(types, kaupunginosa_qids):
        return True

    # Pasila
    if 'Q1636613' in place:
        return True
    if 'Q21721289' in place:
        return True
    return False


def is_paikka(place, wikidata_types, mml_types, other_types):
    place_qids = ['Q618123', 'Q113965186', 'Q113965195', 'Q113965279',
                  'Q107549321', 'Q811979']
    types = wikidata_types + mml_types + other_types

    # Ahvenanmaa
    if 'Q5689' in place:
        return False
    if 'Q10426741' in place:
        return True
    if 'Q3087729' in place:
        return True
    if 'Q2298076' in place:
        return True

    if is_in_haystack(types, place_qids):
        return True
    if test_property_value(place, '(wdt:P279|wdt:P31)*', 'Q83620'):
        return True
    if test_property_value(place, '(wdt:P279|wdt:P31)*', 'Q41176'):
        return True
    if test_property_value(place, '(wdt:P279|wdt:P31)*', 'Q18247357'):
        return True
    if test_property_value(place, '(wdt:P279|wdt:P31)*', 'Q811979'):
        return True

    return False


def detect_place_type(place, wikidata_types, mml_types):
    other_types = []
    wikidata_types = list(wikidata_types)
    mml_types = list(mml_types)
    if len(mml_types) + len(wikidata_types) == 0:
        other_types = get_p31_values(place)
    ret = {
        'maanosa': is_maanosa(place, wikidata_types, mml_types, other_types),
        'valtio': is_valtio(place, wikidata_types, mml_types, other_types),
        'maakunta': is_maakunta(place, wikidata_types, mml_types, other_types),
        'luonto': is_luonto(place, wikidata_types, mml_types, other_types),
        'kunta': is_kunta(place, wikidata_types, mml_types, other_types),
        'kaupunginosa': is_kaupunginosa(place, wikidata_types,
                                        mml_types, other_types),
        'paikka': is_paikka(place, wikidata_types, mml_types, other_types),
    }

    found = False
    for k in ret:
        if ret[k]:
            found = True

    if not found:
        print(f'ERROR: No wikidata ids: {place}')
        print(mml_types)
        print(wikidata_types)
        print(get_p31_values(place))
        exit(1)

    return ret


def location_test(row, key1, key2, slow_mode=False):
    # If unable to test then return True

    key1_len = len(row[key1])
    key2_len = len(row[key2])

    # return True if there is no location
    # ( Nothing to test )
    if not key1_len:
        return True

    # return false if location is defined but no admin area
    if not key2_len:
        return True

    # Return False if any of the locations is not found
    # in admin areas

    for location in row[key1]:
        ret = False
        for administrative_entity in row[key2]:
            if is_location_within_administrative_entity(
                                                 location,
                                                 administrative_entity,
                                                 slow_mode):
                ret = True
                break
        if not ret:
            break

    return ret


def validate_location_row2(row):
    # Test maakunta & valtio
    tests = [
        ['maakunta', 'valtio'],
        ['luonto', 'maakunta'],
        ['kunta', 'valtio'],
        ['kunta', 'maakunta'],
        ['kaupunginosa', 'kunta'],
        ['kaupunginosa', 'maakunta'],
        ['kaupunginosa', 'valtio'],
        ['paikka', 'kaupunginosa'],
        ['paikka', 'kunta'],
        ['paikka', 'maakunta'],
        ['paikka', 'valtio']
    ]
    for test in tests:
        location = test[0]
        administrative_entity = test[1]
        ok = location_test(row, location, administrative_entity, False)
        if not ok:
            ok = location_test(row, location, administrative_entity, True)

        if ok:
            print(f'test: {location} {administrative_entity} OK')
        else:
            print(f'test: {location} {administrative_entity} not OK')
            print(row)
            exit(1)


def convert_finto_to_wikidata(subject_places):

    ignore = ['http://www.wikidata.org/entity/Q18681872']
    row = {
            'maanosa': set(),
            'valtio': set(),
            'maakunta': set(),
            'luonto': set(),
            'kunta': set(),
            'kaupunginosa': set(),
            'paikka': set()
    }

    for subject_place in subject_places:
        wikidata_uris = set()
        wikidata_type_uris = set()
        mml_type_uris = set()

        keyword = str(subject_place)
        qs = FintoYsoLabel.objects.filter(value=keyword)

        for r in qs:
            for place in r.places.all():
                print(f'{r.lang} {r.value} {place.yso_id}')
                wikidata_uri_qs = place.close_matches.filter(
                                        uri__icontains="wikidata.org"
                                        )
                if wikidata_uri_qs.exists():
                    for u in wikidata_uri_qs.distinct():
                        if u.uri in ignore:
                            continue
                        u.uri = u.uri.replace('www.wikidata.org/wiki/',
                                              'www.wikidata.org/entity/')
                        wikidata_uris.add(u.uri)
                else:
                    uris = get_wikidata_items_using_yso(place.yso_id)
                    for uri in uris:
                        wikidata_uris.add(uri)
                    if len(uris) == 0:
                        print(f'Error: No wikidata uris for {place.yso_id}')
                        exit(1)

                for u in place.wikidata_place_types.all():
                    wikidata_type_uris.add(u.uri)
                for u in place.mml_place_types.all():
                    mml_type_uris.add(u.uri)

        print("---")
        print(wikidata_uris)
        for wikidata_uri in wikidata_uris:
            detected_types = detect_place_type(wikidata_uri,
                                               wikidata_type_uris,
                                               mml_type_uris)
            for detected_type in detected_types:
                if detected_types[detected_type]:
                    row[detected_type].add(wikidata_uri)

    validate_location_row2(row)
    return row


def get_best_location_ids(row):

    types = ['paikka', 'kaupunginosa', 'kunta', 'maakunta', 'valtio']
    best_ids = []
    for type in types:
        if len(row[type]):
            best_ids = row[type]
            break

    if not best_ids:
        print("ERROR: no best location ids")
        print(row)
        exit(1)

    alt_ids = []
    slow_mode = False
    for location in row['luonto']:
        for administrative_entity in best_ids:
            if is_location_within_administrative_entity(
                                                 location,
                                                 administrative_entity,
                                                 slow_mode):
                alt_ids.append(location)
    if len(alt_ids):
        print("ALT_IDS:")
        print(alt_ids)
        known_ids = ['http://www.wikidata.org/entity/Q1472085',
                     'http://www.wikidata.org/entity/Q2092330'
                     'http://www.wikidata.org/entity/Q2092330'
                     'http://www.wikidata.org/entity/Q27898927',
                     'http://www.wikidata.org/entity/Q6305010',
                     'http://www.wikidata.org/entity/Q3745222',
                     'http://www.wikidata.org/entity/Q68194119',
                     'http://www.wikidata.org/entity/Q1636182',
                     'http://www.wikidata.org/entity/Q10426741']

        for known_id in known_ids:
            if known_id in alt_ids:
                best_ids = alt_ids
                return best_ids
        raise Exception(f'NON-WHITELISTED ALT ID: {alt_ids}')
    return best_ids


class Command(BaseCommand):
    help = 'Testing Finna record parsing and converting to SDC'

    def add_arguments(self, parser):
        # Named (optional) arguments
        parser.add_argument(
            '--collection',
            type=str,
            choices=get_collection_names(),
            help=('Finna type argument. '
                  'Argument selects where lookfor matches.')
        )

        parser.add_argument(
            '--lookfor',
            type=str,
            help='Finna lookfor argument.',
        )

        parser.add_argument(
            '--seek',
            type=str,
            help='Seek until record with text is found.',
        )

    def process_finna_record(self, data):
        print(data['id'])
        r = FinnaImage.objects.create_from_data(data)
        if r.finna_id == 'museovirasto.25B891D0C4EB778A6DEF6B86ADC0138F':
            return
        if r.finna_id == 'museovirasto.435B512AF60C1ABB6BEDC3238803D84B':
            return
        if r.finna_id == 'museovirasto.3A4800D8302EE6BE67ABF6ADD37FF626':
            return
        if r.finna_id == 'museovirasto.C6EAF127009738B35052BE9108026B38':
            return
        if r.finna_id == 'museovirasto.C80AA2077007023DE5A691B575F20BD1':
            return
        if r.finna_id == 'museovirasto.0C0007A8A417CE9B274F9FB40DE45994':
            return
        if r.finna_id == 'museovirasto.E5DC08AEADDE5222D8DA081FBC63F735':
            return
        if r.finna_id == 'museovirasto.2C35EC09B2F6F9B2031A236E786FD506':
            return
        if r.finna_id == 'museovirasto.5403628c-bf32-4b0a-84de-819217dbb151':
            return
        if r.finna_id == 'museovirasto.d694af91-4222-4501-99b8-646e67c94efe':
            return
        if r.finna_id == 'museovirasto.99cabab6-26d4-4028-8049-4d3b1ca6dc25':
            return
        if r.finna_id == 'museovirasto.340b5bc4-e6de-414e-aceb-440964210447':
            return
        if r.finna_id == 'museovirasto.BF9E5910300AD9A84FD041642CAA09E8':
            return
        if r.finna_id == 'museovirasto.778C10B2FB5E1AA7CEA251831875611B':
            return
        if r.finna_id == 'museovirasto.5BC9610B7A4F964EDC33F27B357B145C':
            return

        if r.best_wikidata_location.exists():
            print("Skipping: best_wikidata_location.exists()")
        print(r.finna_json_url)

        print("parsed_subject_places")
        parsed_subject_places = parse_subject_place_string(r)
        print("update_yso_places")
        update_yso_places(parsed_subject_places, r.finna_id)

        wikidata_location_ids = get_location_override(r)
        if len(parsed_subject_places) and not wikidata_location_ids:
            row = convert_finto_to_wikidata(parsed_subject_places)
            print(row)
            try:
                wikidata_location_ids = get_best_location_ids(row)
            except:
                return
        obj = FinnaSubjectWikidataPlace.objects
        for wikidata_location_id in wikidata_location_ids:
            location, created = obj.get_or_create(uri=wikidata_location_id)
            r.best_wikidata_location.add(location)

    def handle(self, *args, **options):
        seek = options['seek'] or None
        lookfor = options['lookfor'] or None
        collection = options['collection'] or None

        type = None
        n = 0

        for page in range(1, 201):
            # Prevent looping too fast for Finna server
            time.sleep(1)
            data = do_finna_search(page, lookfor, type, collection)
            if 'records' in data:
                for record in data['records']:
                    n += 1
                    if seek and seek != record['id']:
                        print(f'{n} skipping ' + str(record['id']))
                        continue
                    seek = ''
                    if 'Oulujoki' in str(record):
                        continue
                    if 'Salpausselkä' in str(record):
                        continue
                    if 'Tyris' in str(record):
                        continue
                    if 'Tammela' in str(record):
                        continue
                    if 'Siperia' in str(record):
                        continue

                    self.process_finna_record(record)
            else:
                print("XXX")
                break

        self.stdout.write(self.style.SUCCESS('Images counted succesfully!'))

from django.core.management.base import BaseCommand
from images.models import FinnaSubjectPlace, FintoYsoLabel
from pywikibot.data.sparql import SparqlQuery
from django.db.models import Count
import time
from images.locations import update_yso_places, \
                      is_location_within_administrative_entity, \
                      test_property_value, get_p31_values, \
                      get_wikidata_items_using_yso
from images.wikitext.wikidata_helpers import get_subject_place_wikidata_id


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
        ['entinenkunta', 'valtio'],
        ['entinenkunta', 'maakunta'],
        ['entinenkunta', 'kunta'],
        ['kaupunginosa', 'entinenkunta'],
        ['kaupunginosa', 'kunta'],
        ['kaupunginosa', 'maakunta'],
        ['kaupunginosa', 'valtio'],
        ['paikka', 'kaupunginosa'],
        ['paikka', 'entinenkunta'],
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


def get_best_location_ids(row, allow_alt):

    types = ['paikka', 'kaupunginosa', 'entinenkunta',
             'kunta', 'maakunta', 'valtio']
    best_ids = []
    for type in types:
        if len(row[type]):
            best_ids = row[type]
            break

    if not best_ids:
        print("ERROR: no best location ids")
        print(row)
        exit(1)

    alt_ids = set()
    slow_mode = False
    for location in row['luonto']:
        for administrative_entity in best_ids:
            if is_location_within_administrative_entity(
                                                 location,
                                                 administrative_entity,
                                                 slow_mode):
                alt_ids.add(location)
    if len(alt_ids):
        print("ALT_IDS:")
        print(alt_ids)
        known_ids = ['https://www.wikidata.org/wiki/Q24480334',
                     'http://www.wikidata.org/entity/Q1472085',
                     'http://www.wikidata.org/entity/Q2092330'
                     'http://www.wikidata.org/entity/Q2092330'
                     'http://www.wikidata.org/entity/Q27898927',
                     'http://www.wikidata.org/entity/Q18659190',
                     'http://www.wikidata.org/entity/Q6305010',
                     'http://www.wikidata.org/entity/Q3745222',
                     'http://www.wikidata.org/entity/Q68194119',
                     'http://www.wikidata.org/entity/Q1636182',
                     'http://www.wikidata.org/entity/Q10426741']
        if 1:
            return list(alt_ids)
        for known_id in known_ids:
            if known_id in alt_ids:
                best_ids = alt_ids
                return best_ids
        raise Exception(f'NON-WHITELISTED ALT ID: {alt_ids}')
    return best_ids


def is_kunta(place, wikidata_types, mml_types, other_types):
    kunta_qids = ['Q515', 'Q113965206', 'Q127448',
                  'Q42744322', 'Q1907114', 'Q3957', 'Q856076']
    types = wikidata_types + mml_types + other_types

    if is_in_haystack(types, kunta_qids):
        if test_property_value(place, '(wdt:P279|wdt:P31)*', 'Q17468533'):
            return False
        return True
    if test_property_value(place, '(wdt:P279|wdt:P31)*', 'Q515'):
        if test_property_value(place, '(wdt:P279|wdt:P31)*', 'Q17468533'):
            return False
        return True
    return False


def is_entinenkunta(place, wikidata_types, mml_types, other_types):
    kunta_qids = ['Q17468533']
    types = wikidata_types + mml_types + other_types
    print("YYYY")
    print(place)
    print(types)
    print("XXX")
    if test_property_value(place, '(wdt:P279|wdt:P31)*', 'Q17468533'):
        return True

    if is_in_haystack(types, kunta_qids):
        return True
    return False


def is_kaupunginosa(place, wikidata_types, mml_types, other_types):
    kaupunginosa_qids = ['Q378636', 'Q15715406', 'Q5283513', 'Q21682724',
                         'Q17468479', 'Q185113', 'Q102217423', 'Q21130185',
                         'Q2983893', 'Q47254761', 'Q103910131',
                         'Q103910453', 'Q103910131', 'Q28480345',
                         'Q103910177', 'Q63135009', 'Q63134896',
                         'Q123705', 'Q17468479', 'Q60495698', 'Q6566301',
                         'Q18333556', 'Q61492541', 'Q1523821',
                         'Q12813115', 'Q532', 'Q5084', 'Q1523821']
    types = wikidata_types + mml_types + other_types
    print(types)
    print(kaupunginosa_qids)
    if is_in_haystack(types, kaupunginosa_qids):
        if test_property_value(place, '(wdt:P279|wdt:P31)*', 'Q17468533'):
            return False
        return True

    # Pasila
    if 'Q1636613' in place:
        return True
    if 'Q21721289' in place:
        return True
    return False


def is_paikka(place, wikidata_types, mml_types, other_types):
    place_qids = ['Q79007', 'Q113965354', 'Q113965153', 'Q191992',
                  'Q1623285', 'Q695793', 'Q1143635', 'Q27686',
                  'Q20819922', 'Q30504418', 'Q744099', 'Q618123',
                  'Q113965186', 'Q113965195', 'Q113965279',
                  'Q107549321', 'Q811979', 'Q23413']
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


def is_maakunta(place, wikidata_types, mml_types, other_types):
    maakunta_qids = ['Q52062', 'Q113965203', 'Q10742', 'Q629870',
                     'Q217691', 'Q853697', 'Q20719690', 'Q193512']
    if 'Q11880042' in place:
        return True
    types = wikidata_types + mml_types + other_types
    if is_in_haystack(types, maakunta_qids):
        return True
    return False


def is_luonto(place, wikidata_types, mml_types, other_types):
    luonto_qids = ['Q355304', 'Q106589819', 'Q39594',
                   'Q113965178', 'Q23442', 'Q185113', 'Q54050']
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
        'entinenkunta': is_entinenkunta(place, wikidata_types,
                                        mml_types, other_types),
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
        print(ret)
        print(mml_types)
        print(wikidata_types)
        print(get_p31_values(place))
        exit(1)

    return ret


def get_sparql_subject_place(keyword, p131s, allow_empty_p131=False):
    langs = ['fi', 'sv', 'se']
    for lang in langs:
        sparql = SparqlQuery()
        if len(p131s):
            p131str = ''
            for p131 in p131s:
                p131 = p131.replace('http://www.wikidata.org/entity/', '')
                p131str += f' wd:{p131}'

            query = 'SELECT * WHERE { VALUES ?p131s {' + p131str + '} . '
            query += '?item wdt:P17 wd:Q33 . '
            query += '?item wdt:P131 ?p131s . '
            query += '?item (rdfs:label|skos:altLabel) "' + keyword +'"@' + lang +' . ' # noqa
            query += 'FILTER NOT EXISTS { ?item wdt:P31 wd:Q55488 } . '
            query += 'FILTER NOT EXISTS { ?item wdt:P31 wd:Q10476836 } . '
            query += 'FILTER NOT EXISTS { ?item wdt:P31 wd:Q55678 } } LIMIT 1'

            print(query)
            rows = sparql.select(query)
            for row in rows:
                return row['item']

            # Just crude case-insensitive failback
            formatted_keyword = keyword[0] + keyword[1:].lower()
            if formatted_keyword != keyword:
                query = 'SELECT * WHERE {  VALUES ?p131s {' + p131str + '} . '
                query += '?item wdt:P17 wd:Q33 . '
                query += '?item wdt:P131 ?p131s . '
                query += '?item (rdfs:label|skos:altLabel) "' + formatted_keyword +'"@' + lang +' . ' # noqa
                query += 'FILTER NOT EXISTS { ?item wdt:P31 wd:Q55488 } . '
                query += 'FILTER NOT EXISTS { ?item wdt:P31 wd:Q10476836 } . '
                query += 'FILTER NOT EXISTS { ?item wdt:P31 wd:Q55678 } } LIMIT 1' # noqa

                print(query)
                rows = sparql.select(query)
                for row in rows:
                    return row['item']

        if not allow_empty_p131:
            return None

        query = 'SELECT * WHERE { ?item wdt:P17 wd:Q33 . '
        query += '?item wdt:P131 ?p131 . '
        query += '?item (rdfs:label|skos:altLabel) "' + keyword +'"@' + lang +' . ' # noqa
        query += 'FILTER NOT EXISTS { ?item wdt:P31 wd:Q55488 } . '
        query += 'FILTER NOT EXISTS { ?item wdt:P31 wd:Q10476836 } . '
        query += 'FILTER NOT EXISTS { ?item wdt:P31 wd:Q55678 } } LIMIT 1'

        print(query)
        rows = sparql.select(query)
        for row in rows:
            return row['item']

        # Just crude case-insensitive failback
        formatted_keyword = keyword[0] + keyword[1:].lower()
        if formatted_keyword != keyword:
            query = 'SELECT * WHERE {  ?item wdt:P17 wd:Q33 . '
            query += '?item wdt:P131 ?p131 . '
            query += '?item (rdfs:label|skos:altLabel) "' + formatted_keyword +'"@' + lang +' . ' # noqa
            query += 'FILTER NOT EXISTS { ?item wdt:P31 wd:Q55488 } . '
            query += 'FILTER NOT EXISTS { ?item wdt:P31 wd:Q10476836 } . '
            query += 'FILTER NOT EXISTS { ?item wdt:P31 wd:Q55678 } } LIMIT 1'
            print(query)
            rows = sparql.select(query)
            for row in rows:
                return row['item']


def convert_finto_to_wikidata(subject_places):

    ignore = ['http://www.wikidata.org/entity/Q18681872']
    row = {
            'maanosa': set(),
            'valtio': set(),
            'maakunta': set(),
            'luonto': set(),
            'kunta': set(),
            'entinenkunta': set(),
            'kaupunginosa': set(),
            'paikka': set()
    }

    missing_keywords = []
    for subject_place in subject_places:
        wikidata_uris = set()
        wikidata_type_uris = set()
        mml_type_uris = set()

        keyword = str(subject_place)
        if keyword == 'Länsi-Uusimaa':
            wikidata_uris.add('http://www.wikidata.org/entity/Q11880042')
        else:
            if ' Helsinki' in keyword:
                keyword = keyword.replace(' Helsinki', ' (Helsinki)')
            elif ' Vantaa' in keyword:
                keyword = keyword.replace(' Vantaa', ' (Vantaa)')

            qs = FintoYsoLabel.objects.filter(value=keyword)
            orig_keyword = keyword
            if qs.count() == 0:
                keyword_parts = keyword.split(' ')
                if len(keyword_parts) == 2:
                    keyword = keyword_parts[0] + ' (' + keyword_parts[1] + ')'
                    qs = FintoYsoLabel.objects.filter(value=keyword)

            qualifiers = ['kunta', 'kaupunki', 'kylä']
            for qualifier in qualifiers:
                if qs.count() == 0:
                    keyword_parts = orig_keyword.split(' ')
                    if len(keyword_parts) == 2:
                        qualifier_part = keyword_parts[1]\
                                         .replace('(', '')\
                                         .replace(')', '')
                        keyword = f'{keyword_parts[0]} ({qualifier_part} : {qualifier})' # noqa
                        qs = FintoYsoLabel.objects.filter(value=keyword)

            qualifier_texts = []
            qualifiers = ['kunta', 'kaupunki', 'kylä']
            qualifier_texts += qualifiers
            qualifier_texts += subject_places
            for subject_place in subject_places:
                for qualifier in qualifiers:
                    long_qualifier = f'{subject_place} : {qualifier}'
                    qualifier_texts.append(long_qualifier)

            for qualifier in qualifier_texts:
                if qs.count() == 0:
                    keyword = f'{orig_keyword} ({qualifier})'
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
                            print(f'Error: No wikidata uris for {place.yso_id}') # noqa
                            exit(1)

                    for u in place.wikidata_place_types.all():
                        wikidata_type_uris.add(u.uri)
                    for u in place.mml_place_types.all():
                        mml_type_uris.add(u.uri)

            if qs.count() == 0:
                missing_keywords.append(orig_keyword)

        for wikidata_uri in wikidata_uris:
            detected_types = detect_place_type(wikidata_uri,
                                               wikidata_type_uris,
                                               mml_type_uris)
            for detected_type in detected_types:
                if detected_types[detected_type]:
                    row[detected_type].add(wikidata_uri)

    for missing_keyword in missing_keywords:
        subject_place_from_sparql = None
        if len(row['entinenkunta']):
            subject_place_from_sparql = get_sparql_subject_place(missing_keyword, row['entinenkunta']) # noqa
        if not subject_place_from_sparql:
            subject_place_from_sparql = get_sparql_subject_place(missing_keyword, row['kunta'], True) # noqa
        if subject_place_from_sparql:
            wikidata_type_uris = set()
            mml_type_uris = set()
            detected_types = detect_place_type(subject_place_from_sparql,
                                               wikidata_type_uris,
                                               mml_type_uris)
            for detected_type in detected_types:
                if detected_types[detected_type]:
                    row[detected_type].add(subject_place_from_sparql)
        else:
            print(f"Subject place '{orig_keyword}' not found")
            exit(1)
    validate_location_row2(row)
    return row


def parse_subject_place_string(subject_place_string):
    subject_places = []
    for place_name in subject_place_string.split(', '):
        place_name = place_name.strip().rstrip(',').strip()
        if place_name == 'Suomen entinen kunta/pitäjä':
            continue
        # Too complex matches
        if place_name == 'Lappi':
            continue
#        place_name = translate_location_keyword(place_name)
        if place_name and place_name not in subject_places:
            subject_places.append(place_name)
    return subject_places


def save_wikidata_id(place, wikidata_id):
    place.wikidata_id = wikidata_id
    place.save()


class Command(BaseCommand):
    help = 'Print places'

    def handle(self, *args, **kwargs):
        seek = False
#        seek='Suomi, Uusimaa, Helsinki, Malmi Helsinki, Malmin lentokenttä'
        common_places = FinnaSubjectPlace.objects.annotate(num_images=Count('finnaimage')).order_by('-num_images') # noqa
        print(common_places.filter(wikidata_id__isnull=True).count())
        time.sleep(7)
        for place in common_places:
            if place.wikidata_id:
                print(f'{place.wikidata_id} EXISTS. SKIPPING')
                continue
            place_name = place.name.strip().replace('\n', ', ').rstrip(',')
            if seek and place_name != seek:
                continue
            seek = False
            subject_place_wikidata_id = get_subject_place_wikidata_id(place_name) # noqa
            if subject_place_wikidata_id:
                save_wikidata_id(place, subject_place_wikidata_id)
                continue
            sample_finna_image = place.finnaimage_set.first()
            sample_finna_id = sample_finna_image.finna_id if sample_finna_image else "No Image" # noqa
            print(f'\n{place.name}: {place.num_images} times. {sample_finna_id}') # noqa
            parsed_subject_places = parse_subject_place_string(place.name)
            print(parsed_subject_places)
            update_yso_places(parsed_subject_places, sample_finna_id)

            if len(parsed_subject_places):
                row = convert_finto_to_wikidata(parsed_subject_places)
                try:
                    wikidata_location_ids = get_best_location_ids(row, len(parsed_subject_places)) # noqa
                except:
                    print("ERROR")
                    exit(1)
                print(wikidata_location_ids)
                if len(wikidata_location_ids) == 1:
                    new_wikidata_id = next(iter(wikidata_location_ids), None)
                    if new_wikidata_id != place.wikidata_id:
                        print(f'SAVING {new_wikidata_id} to {place}')
                        place.wikidata_id = new_wikidata_id
                        place.save()
                elif len(wikidata_location_ids) > 1:
                    print(row)
                    continue
                print("--- ### ---")

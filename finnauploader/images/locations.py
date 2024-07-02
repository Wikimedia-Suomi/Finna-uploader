import hashlib
from pywikibot.data.sparql import SparqlQuery
from images.models import LocationTestCache, FintoYsoMissingCache, \
                          FintoYsoPlace, FintoYsoCloseMatch, \
                          FintoYsoMMLPlaceType, FintoYsoWikidataPlaceType, \
                          FintoYsoLabel, CacheSparqlBool
from images.finto import finto_search

sparql = SparqlQuery()


def get_wikidata_items_using_yso(yso_id):
    ret = []
    yso_id = str(yso_id)
    yso_id = yso_id.replace('https://finto.fi/yso-paikat/fi/page/p', '')
    yso_id = yso_id.replace('p', '')
    query = f'SELECT * WHERE {{ ?item wdt:P2347 "{yso_id}" }}'
    rows = sparql.select(query)
    for row in rows:
        ret.append(row['item'])

    if len(ret) == 0:
        query = f'SELECT ?item WHERE {{ ?item p:P2347 ?a . ?a ps:P2347 "{yso_id}" }}'  # noqa
        rows = sparql.select(query)
        for row in rows:
            try:
                ret.append(row['item'])
            except:
                print(rows)
                exit(1)

    return ret


def get_yso_using_wikidata_id(qid):
    qid = qid.replace('http://www.wikidata.org/entity/', '')
    qid = qid.replace('https://www.wikidata.org/wiki/', '')

    ret = []
    query = f'SELECT * WHERE {{ wd:{qid} wdt:P2347 ?yso }}'
    rows = sparql.select(query)
    if len(rows) > 1:
        print("ERROR: get_yso_using_wikidata_id(): Multiple results")
        print(query)
        exit(1)
    for row in rows:
        uri = 'http://www.yso.fi/onto/yso/p' + str(row['yso'])
        ret.append(uri)
    return ret


def get_urls(data):
    print(data)
    ret = []
    if isinstance(data, list):
        for row in data:
            ret.append(row['uri'])
    else:
        ret.append(data['uri'])
    return ret


def get_p31_values(qid):
    ret = []
    qid = qid.replace('http://www.wikidata.org/entity/', '')
    query = f'SELECT * WHERE {{ wd:{qid} wdt:P31 ?values }} '

    print(query)
    rows = sparql.select(query)
    if rows:
        for row in rows:
            ret.append(row['values'])
    return ret


def is_location_within_administrative_entity(location, entity, slow):
    """
    Checks if the given location (Wikidata ID) is within the specified
    administrative entity (Wikidata ID).

    Parameters:
    location (str): Wikidata URI of the location.
    entity (str): Wikidata URI of the administrative entity.

    Returns:
    bool: True if the location is within the administrative entity,
          False otherwise.
    """

    # support urls in input format for making usage more straightforward
    cached_result = LocationTestCache.objects.filter(
                                              location=location,
                                              entity=entity).first()
    if 0 and cached_result:
        return cached_result.value

    location_id = location.replace('http://www.wikidata.org/entity/', '')
    location_id = location_id.replace('https://www.wikidata.org/wiki/', '')

    entity_id = entity.replace('http://www.wikidata.org/entity/', '')
    entity_id = entity_id.replace('https://www.wikidata.org/wiki/', '')

    if slow:
        query = f'SELECT * WHERE {{ wd:{location_id}  (wdt:P7888|wdt:P276|p:P1365/ps:P1365|p:P1366/ps:P1366|p:P361/ps:P361|p:P131/ps:P131)* wd:{entity_id} }}' # noqa
    else:
        query = f'SELECT * WHERE {{ wd:{location_id} (wdt:P7888|wdt:P276|wdt:P1365|wdt:P1366|wdt:P361|wdt:P131)* wd:{entity_id} }}' # noqa
    data = sparql.select(query)

    if data:
        LocationTestCache.objects.get_or_create(
                                  location=location,
                                  entity=entity,
                                  value=True)
        return True
    else:
        LocationTestCache.objects.get_or_create(
                                  location=location,
                                  entity=entity,
                                  value=True)
        return False


def calculate_md5(content):
    """
    Calculate the MD5 checksum of the provided content.

    Parameters:
    content (str): The content to hash.

    Returns:
    str: The MD5 checksum of the content.
    """
    # Create an MD5 hash object
    hash_md5 = hashlib.md5()

    # Update the hash object with the content encoded as bytes
    hash_md5.update(content.encode('utf-8'))

    # Return the hexadecimal digest of the hash
    return hash_md5.hexdigest()


def test_property_value(entity, property, target):
    target_id = target.replace('http://www.wikidata.org/entity/', '')
    target_id = target_id.replace('https://www.wikidata.org/wiki/', '')

    entity_id = entity.replace('http://www.wikidata.org/entity/', '')
    entity_id = entity_id.replace('https://www.wikidata.org/wiki/', '')

    query = f'SELECT * WHERE {{ wd:{entity_id} {property} wd:{target_id} }}'

    hashkey = calculate_md5(query)
    cached_result = CacheSparqlBool.objects.filter(query_id=hashkey).first()
    if cached_result:
        return cached_result.value

    data = sparql.select(query)
    if data:
        CacheSparqlBool.objects.get_or_create(
                                query_id=hashkey,
                                value=True)
        return True
    else:
        CacheSparqlBool.objects.get_or_create(
                                query_id=hashkey,
                                value=False)
        return False


def test_is_property_placename(location):
    location_id = location.replace('http://www.wikidata.org/entity/', '')
    location_id = location_id.replace('https://www.wikidata.org/wiki/', '')

    query = f'SELECT * WHERE {{ wd:{location_id}  wdt:P131* ?p131 . ?p131 wdt:P31 wd:Q856076  }}' # noqa

    data = sparql.select(query)
    if data:
        return True
    else:
        return False


def update_yso_places(subject_places, finna_id):
    for subject_place in subject_places:
        keyword = str(subject_place)
        qs = FintoYsoLabel.objects.filter(value=keyword)

        if qs.exists():
            continue

        ret = add_finto_location(keyword, finna_id, 'fi', subject_places)
        if not ret:
            ret = add_finto_location(keyword, finna_id, 'sv', subject_places)


def add_finto_location(keyword, finna_id, lang, subject_places):
    f = None
    ret = False

    if not ret:
        f = finto_search(keyword, vocab='yso-paikat')
        if f:
            ret = confirm_finto_location(f, keyword, lang, subject_places)

    if not ret:
        f = finto_search(keyword, vocab='yso')
        if f:
            ret = confirm_finto_location(f, keyword, lang, subject_places)

    if not ret:
        FintoYsoMissingCache.objects.get_or_create(
                                     value=keyword,
                                     finna_id=finna_id)
        print(f'Not found: {keyword}')
        return ret


def confirm_finto_location(finto_result, keyword, lang, subject_places):
    ret = False

    mml_place_type_uri = 'http://www.yso.fi/onto/yso-meta/mmlPlaceType'
    wd_place_type_uri = 'http://www.yso.fi/onto/yso-meta/wikidataPlaceType'
    wgs84_uri = 'http://www.w3.org/2003/01/geo/wgs84_pos'

    orig_keyword = keyword
    for graph in finto_result['graph']:
        if 'prefLabel' in graph:
            print(graph['prefLabel'])

            if 'lang' in graph['prefLabel']:
                graph['prefLabel'] = [graph['prefLabel']]

            for label in graph['prefLabel']:

                if label['value'] != keyword and label['lang'] == lang:
                    key_parts = keyword.split(' ')
                    if len(key_parts) == 2:
                        new_keyword = f'{key_parts[0]} ({key_parts[1]})'
                        label_value = label['value']
                        label_lang = label['lang']
                        if label_value == new_keyword and label_lang == lang:
                            keyword = new_keyword

                qualifiers = ['kunta', 'kaupunki', 'kylä']
                for qualifier in qualifiers:
                    if label['value'] != keyword and label['lang'] == lang:
                        key_parts = orig_keyword.split(' ')
                        if len(key_parts) == 2:
                            new_keyword = f'{key_parts[0]} ({key_parts[1]} : {qualifier})' # noqa
                            label_value = label['value']
                            label_lang = label['lang']

                            if label_value == new_keyword and label_lang == lang: # noqa
                                keyword = new_keyword

                qualifier_texts = []
                qualifiers = ['kunta', 'kaupunki', 'kylä']
                qualifier_texts += qualifiers
                qualifier_texts += subject_places
                for subject_place in subject_places:
                    for qualifier in qualifiers:
                        long_qualifier = f'{subject_place} : {qualifier}'
                        qualifier_texts.append(long_qualifier)

                label_value = label['value']
                label_lang = label['lang']

                for qualifier in qualifier_texts:
                    if label_value != keyword and label_lang == lang:
                        new_keyword = f'{orig_keyword} ({qualifier})'
                        if label_value == new_keyword and label_lang == lang:
                            keyword = new_keyword

                if label_value == keyword and label_lang == lang:
                    print(graph['prefLabel'])
                    print(graph['uri'])
                    if 'closeMatch' in graph:
                        print(graph['closeMatch'])

                    if mml_place_type_uri in graph:
                        print(graph[mml_place_type_uri])

                    if wd_place_type_uri in graph:
                        print(graph[wd_place_type_uri])

                    if f'{wgs84_uri}#lat' in graph:
                        print(graph[f'{wgs84_uri}#lat'])
                        print(graph[f'{wgs84_uri}#long'])

                    yso_id = graph['uri'].replace(
                                          'http://www.yso.fi/onto/yso/',
                                          '')
                    r, created = FintoYsoPlace.objects.get_or_create(
                                                       yso_id=yso_id)

                    if 'closeMatch' in graph:
                        urls = get_urls(graph['closeMatch'])
                        obj = FintoYsoCloseMatch.objects
                        for url in urls:
                            close_match, created = obj.get_or_create(uri=url)
                            r.close_matches.add(close_match)

                    if mml_place_type_uri in graph:
                        urls = get_urls(graph[mml_place_type_uri])
                        obj = FintoYsoMMLPlaceType.objects
                        for url in urls:
                            mml_url, created = obj.get_or_create(uri=url)
                            r.mml_place_types.add(mml_url)

                    if wd_place_type_uri in graph:
                        urls = get_urls(graph[wd_place_type_uri])
                        obj = FintoYsoWikidataPlaceType.objects
                        for url in urls:
                            wikidata_url, created = obj.get_or_create(uri=url)
                            r.wikidata_place_types.add(wikidata_url)

                    obj = FintoYsoLabel.objects
                    for prefLabel in graph['prefLabel']:
                        label, created = obj.get_or_create(
                                             lang=prefLabel['lang'],
                                             value=prefLabel['value'])
                        r.labels.add(label)

                    if f'{wgs84_uri}#lat' in graph:
                        r.lat = float(graph[f'{wgs84_uri}#lat'])
                        r.long = float(graph[f'{wgs84_uri}#long'])
                    r.save()
                    ret = True
    return ret

import datetime
from images.wikitext.timestamps import parse_timestamp
from .sdc_helpers import create_P7482_source_of_file, \
                         create_P275_licence, \
                         create_P6216_copyright_state, \
                         create_P9478_finna_id, \
                         create_P170_author, \
                         create_P195_collection, \
                         create_P180_depicts, \
                         create_P571_timestamp

from images.wikitext.creator import get_author_wikidata_id, \
                                    get_collection_wikidata_id, \
                                    get_subject_actors_wikidata_id


def get_P7482_source_of_file_claim(finna_image):
    operator = 'Q420747'    # National library
    publisher = 'Q3029524'  # Finnish Heritage Agency
    url = finna_image.url
    return create_P7482_source_of_file(url, operator, publisher)


def get_P275_licence_claim(finna_image):
    value = finna_image.image_right.copyright
    return create_P275_licence(value=value)


def get_P6216_copyright_state_claim(finna_image):
    value = finna_image.image_right.copyright
    return create_P6216_copyright_state(value=value)


def get_P9478_finna_id_claim(finna_image):
    finna_id = finna_image.finna_id
    return create_P9478_finna_id(finna_id)


def get_P170_author_claims(finna_image):
    ret = []
    for author in finna_image.non_presenter_authors.all():
        if author.role == 'reprokuvaaja':
            continue
        elif author.role == 'kuvaaja':
            wikidata_id = get_author_wikidata_id(author.name)
            # Q33231 = kuvaaja
            claim = create_P170_author(wikidata_id, 'Q33231')
            ret.append(claim)
        else:
            print(f'Error: Unknown role: {author.role}')
    return ret


def get_P195_collection_claims(finna_image):
    ret = []
    for collection in finna_image.collections.all():
        wikidata_id = get_collection_wikidata_id(collection.name)
        identifier = finna_image.identifier_string
        claim = create_P195_collection(wikidata_id, identifier)
        ret.append(claim)
    return ret


def get_P180_subject_actors_claims(finna_image):
    ret = []
    for subject in finna_image.subject_actors.all():
        wikidata_id = get_subject_actors_wikidata_id(subject.name)
        claim = create_P180_depicts(wikidata_id)
        ret.append(claim)
    return ret


def get_P571_timestamp_claim(finna_image):
    if not finna_image.date_string:
        return None

    timestamp = finna_image.date_string
    parsed_timestamp, precision = parse_timestamp(timestamp)

    if parsed_timestamp:
        timestamp = datetime.strptime(parsed_timestamp, "+%Y-%m-%dT%H:%M:%SZ")
        claim = create_P571_timestamp(timestamp, precision)
        return claim

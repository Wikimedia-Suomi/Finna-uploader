import requests
import urllib
import re
import xml.etree.ElementTree as ET
import html

from images.wikitext.wikidata_helpers import get_collection_names, \
                                    get_collection_name_from_alias

from images.imagehash_helpers import isimageformatsupported

s = requests.Session()
s.headers.update({'User-Agent': 'FinnaUploader 0.2 (https://commons.wikimedia.org/wiki/User:FinnaUploadBot)'}) # noqa

# TODO: responses could be cached instead of possibly repeating
def get_json_response(session, url):
    if not url:
        print("empty url, cannot request")
        return None
    
    try:
        response = session.get(url)
        return response.json()
    except ValueError as e:
        print("Failed parsing JSON:", e)
    except:
        print("Finna API query failed: " + url)

    return None

# used by finna_search.py
def get_supported_collections():
    # uses list stored in Commons or some hard-coded values as default
    # this could be improved to support alias-names
    # (see get_collection_name_from_alias)
    
    return get_collection_names()

# aliases supported in search (institutions)
#def get_supported_aliases():
#    return get_collection_aliases()


# urlencode Finna parameters
def finna_api_parameter(name, value):
    name = urllib.parse.quote_plus(name)
    value = urllib.parse.quote_plus(value)
    return f'&{name}={value}'


def add_finna_api_free_images_only_parameters():
    url = ''
    url += finna_api_parameter('filter[]', '~format_ext_str_mv:"0/Image/"')
    url += finna_api_parameter('filter[]', 'free_online_boolean:"1"')
    url += finna_api_parameter('filter[]', '~usage_rights_str_mv:"usage_B"')
    return url


def add_finna_api_default_field_parameters():
    url = ''
    url += finna_api_parameter('field[]', 'id')
    url += finna_api_parameter('field[]', 'title')
    url += finna_api_parameter('field[]', 'subTitle')
    url += finna_api_parameter('field[]', 'alternativeTitles')
    url += finna_api_parameter('field[]', 'shortTitle')
    url += finna_api_parameter('field[]', 'titleSection')
    url += finna_api_parameter('field[]', 'titleStatement')
    url += finna_api_parameter('field[]', 'uniformTitles')
    url += finna_api_parameter('field[]', 'summary')
    url += finna_api_parameter('field[]', 'imageRights')
    url += finna_api_parameter('field[]', 'images')
    url += finna_api_parameter('field[]', 'imagesExtended')
    url += finna_api_parameter('field[]', 'onlineUrls')
    url += finna_api_parameter('field[]', 'openUrl')
    url += finna_api_parameter('field[]', 'nonPresenterAuthors')
    url += finna_api_parameter('field[]', 'onlineUrls')
    url += finna_api_parameter('field[]', 'subjects')
    url += finna_api_parameter('field[]', 'subjectsExtendet')
    url += finna_api_parameter('field[]', 'subjectPlaces')
    url += finna_api_parameter('field[]', 'subjectActors')
    url += finna_api_parameter('field[]', 'subjectDetails')
    url += finna_api_parameter('field[]', 'geoLocations')
    url += finna_api_parameter('field[]', 'buildings')
    url += finna_api_parameter('field[]', 'identifierString')
    url += finna_api_parameter('field[]', 'collections')
    url += finna_api_parameter('field[]', 'institutions')
    url += finna_api_parameter('field[]', 'classifications')
    url += finna_api_parameter('field[]', 'events')
    url += finna_api_parameter('field[]', 'languages')
    url += finna_api_parameter('field[]', 'originalLanguages')
    url += finna_api_parameter('field[]', 'year')
    url += finna_api_parameter('field[]', 'hierarchicalPlaceNames')
    url += finna_api_parameter('field[]', 'formats')
    url += finna_api_parameter('field[]', 'physicalDescriptions')
    url += finna_api_parameter('field[]', 'physicalLocations')
    url += finna_api_parameter('field[]', 'measurements')
    url += finna_api_parameter('field[]', 'recordLinks')
    url += finna_api_parameter('field[]', 'recordPage')
    url += finna_api_parameter('field[]', 'systemDetails')
    url += finna_api_parameter('field[]', 'fullRecord')
    url += finna_api_parameter('field[]', 'containerReference')
    url += finna_api_parameter('field[]', 'corporateAuthors')
    url += finna_api_parameter('field[]', 'dedupIds')
    url += finna_api_parameter('field[]', 'dissertationNote')
    url += finna_api_parameter('field[]', 'genres')
    url += finna_api_parameter('field[]', 'humanReadablePublicationDates')
    url += finna_api_parameter('field[]', 'inscriptions')
    url += finna_api_parameter('field[]', 'openUrl')
    url += finna_api_parameter('field[]', 'previousTitles')
    url += finna_api_parameter('field[]', 'primaryAuthors')
    url += finna_api_parameter('field[]', 'subjectsExtended')
    url += finna_api_parameter('field[]', 'first_indexed')
    url += finna_api_parameter('field[]', 'firstIndexed')
    url += finna_api_parameter('field[]', 'last_indexed')
    url += finna_api_parameter('field[]', 'lastIndexed')
    return url


def do_finna_search(page=1, lookfor=None, type='AllFields', collection=None, full=True): # noqa

    url = "https://api.finna.fi/v1/search?"
    url += add_finna_api_free_images_only_parameters()
    if full:
        url += add_finna_api_default_field_parameters()

    # with limit=20 maximum page=5000 api returns 100 000 records, see last_indexed
    url += finna_api_parameter('limit', '100') # 0-100, use 0 to get number of results
    url += finna_api_parameter('page', str(page))

    if collection == '0/SA-kuva/':
        collection_rule = f'~building:"{collection}"'
        url += finna_api_parameter('filter[]', collection_rule)
    elif collection == '0/Kansallisgalleria Ateneumin taidemuseo/':
        collection_rule = f'~building:"{collection}"'
        url += finna_api_parameter('filter[]', collection_rule)
    elif collection:
        collection_rule = f'~hierarchy_parent_title:"{collection}"'
        url += finna_api_parameter('filter[]', collection_rule)

    # Example search value '"professorit"+"miesten+puvut"'
    if lookfor:
        url += finna_api_parameter('lookfor', f'{lookfor}')

    # Where lookfor is targeted. Known values 'AllFields', 'Subjects'
    if type:
        url += finna_api_parameter('type', f'{type}')

    return get_json_response(s, url)


# called from imagehash_helpers.py
def is_valid_finna_record(finna_record):
    if not finna_record:
        return False

    if not 'status' in finna_record:
        return False

    if finna_record['status'] != 'OK':
        return False

    if not 'records' in finna_record:
        return False

    #if not 'resultCount' in finna_record:
    #    return False

    return True

# called from imagehash_helpers.py
def is_supported_copyright(imageExtended):
    # Test copyright
    # note: public domain mark may need additional logic
    allowed_copyrighs = ['CC BY 4.0', 'CC0', 'PDM']
    if "rights" not in imageExtended:
        # malformed?
        return False

    if "copyright" not in imageExtended['rights']:
        # malformed?
        return False
    
    if imageExtended['rights']['copyright'] in allowed_copyrighs:
        # if is in known supported -> true
        return True

    # not in known supported -> False
    copyright_msg = imageExtended['rights']['copyright']
    print(f'Incorrect copyright: {copyright_msg}')
    return False

# TODO: check this
def is_valid_image_copyright(finna_record):

    allowed_copyrighs = ['CC BY 4.0', 'CC0', 'PDM']

    record = finna_record['records'][0]
    if "imageRights" not in record:
        # malformed?
        return False
    
    if "copyright" not in record['imageRights']:
        # malformed?
        return False

    if record['imageRights']['copyright'] in allowed_copyrighs:
        # if is in known supported -> true
        return True
    return False

def get_finna_image_urls(finna_id):
    finnaurllist = list()

    finna_record = get_finna_record(finna_id, True)
    if (is_valid_finna_record(finna_record) == False):
        print('Not valid record, id:', finna_id)
        return None

    if finna_record['resultCount'] != 1:
        print('Finna resultCount != 1')
        return None

    #if (not allow_multiple_images and len(finna_record['records'][0]['imagesExtended']) > 1):
    #    print('Multiple images in single record. Skipping')
    #    return False

    record_finna_id = finna_record['records'][0]['id']
    if record_finna_id != finna_id:
        print(f'finna_id update: {finna_id} -> {record_finna_id}')

    for imageExtended in finna_record['records'][0]['imagesExtended']:
        if (is_supported_copyright(imageExtended) == False):
            return None

        # Confirm that images are same using imagehash

        file_path = imageExtended['urls']['large']
        finna_thumbnail_url = f'https://finna.fi{file_path}'
        print(finna_thumbnail_url)

        # try to catch unsupported format before pillow
        # note! might have smaller resolution image in another format
        if "highResolution" in imageExtended:
            hires = imageExtended['highResolution']
            if "original" in hires:
                hires = imageExtended['highResolution']['original'][0]
                if "format" in hires:
                    if (isimageformatsupported(hires["format"]) == False):
                        print("Unknown image format in Finna-data, might not be supported:", hires["format"])
    
        finnaurllist.append(finna_thumbnail_url)
    return finnaurllist


# Get finna API record with most of the information
# Finna API documentation
# * https://api.finna.fi
# * https://www.kiwi.fi/pages/viewpage.action?pageId=53839221
def get_finna_record_url(id, full=False, lang=None):
    if not id:
        return None
    
    urlencoded_id = urllib.parse.quote_plus(id)
    url = f'https://api.finna.fi/v1/record?prettyPrint=1&id={urlencoded_id}'
    if full:
        url += add_finna_api_default_field_parameters()

    if lang:
        url += f'&lng={lang}'
    return url


# only two users for this wrapper?
def get_finna_record(id, full=False, lang=None):
    if not id:
        return None

    url = get_finna_record_url(id, full, lang)

    return get_json_response(s, url)


def get_summary_in_language(id, lang):
    if not id:
        return None

    urlencoded_id = urllib.parse.quote_plus(id)
    url = f'https://api.finna.fi/v1/record?prettyPrint=1&id={urlencoded_id}'
    url += finna_api_parameter('field[]', 'summary')
    url += f'&lng={lang}'
    
    json = get_json_response(s, url)
    if (is_valid_finna_record(json) == True):
        return json['records'][0]['summary']
    
    print("Finna API query failed: " + url)
    return None

def get_finna_id_from_url(url):
    if not url:
        return None
    if "finna.fi" in url:
        # Parse id from url
        patterns = [
                       r"finna\.fi/Record/([^?]+)",
                       r"finna\.fi/Cover/Show\?id=([^&]+)",
                       r"finna\.fi/thumbnail\.php\?id=([^&]+)",
                       r"finna\.fi/Cover/Download\?id=([^&]+)",
                   ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                id = match.group(1)
                return id

    if "kuvakokoelmat" in url:
        # Parse id from url
        patterns = [
              r"kuvakokoelmat\.fi/pictures/view/HK7155_([^?]+)",
              r"kuvakokoelmat\.fi/pictures/small/HK71/HK7155_([^?]+)\.jpg",
                   ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                matched_str = str(match.group(1)).replace('_', '-')
                id = f'musketti.M012:HK7155:{matched_str}'
                return id


# TODO: for categories, parse additional categories from the full record xml:
# classificationWrap><classification><term lang="fi" label="luokitus">
#
# TODO: parse original publication (newspaper, date, page):
# <relatedWorkSet><relatedWork><displayObject>Hufvudstadsbladet 16.6.1940, s. 4</displayObject>
#
# TODO: parse inscriptions:
# <inscriptionsWrap><inscriptions><inscriptionDescription><descriptiveNoteValue>Kirjoitus..
#
def parse_full_record(xml_data):
    # Parse the XML data
    root = ET.fromstring(xml_data)

    #descriptive_note_values = []
    #appellation_values = []
    try:
        # Find all 'descriptiveNoteValue' elements
        # and extract their text and attributes
        descriptive_notes = root.findall(".//descriptiveNoteValue")
        descriptive_note_values = [
            {
                'text': html.unescape(note.text) if note.text else '',
                'attributes': note.attrib
            }
            for note in descriptive_notes
        ]

        # Find all 'appellationValue' elements
        # and extract their text and attributes
        appellations = root.findall(".//appellationValue")
        appellation_values = [
            {
            'text': html.unescape(appellation.text) if appellation.text else '',
            'attributes': appellation.attrib
            }
            for appellation in appellations
        ]

        # <relatedWorkSet><relatedWork><displayObject>Hufvudstadsbladet 16.6.1940, s. 4</displayObject>
        #related_works = root.findall(".//displayObject")
        # classificationWrap><classification><term lang="fi" label="luokitus">
        #classifications = root.findall(".//term")

        return {'summary': descriptive_note_values, 'title': appellation_values}

    except:
        # give information where problem occurred
        print('Failed parsing full record XML')
        print(xml_data)
        pass

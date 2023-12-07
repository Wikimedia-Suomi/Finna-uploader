import requests
import urllib
import re
import json
import xml.etree.ElementTree as ET
import html

s = requests.Session()
s.headers.update({'User-Agent': 'FinnaUploader 0.1'})


def get_collection_names():
    collections = [
                  'Kuvasiskot',
                  'Studio Kuvasiskojen kokoelma',
                  'JOKA',
                  'JOKA Journalistinen kuva-arkisto',
                  'SA-kuva',
                  'Kansallisgalleria Ateneumin taidemuseo'
                  ]
    return collections


def get_collection_name_from_alias(name):
    aliases = {
             'Kuvasiskot': 'Studio Kuvasiskojen kokoelma',
             'JOKA': 'JOKA Journalistinen kuva-arkisto',
             'SA-kuva': '0/SA-kuva/',
             'Kansallisgalleria Ateneumin taidemuseo':
             '0/Kansallisgalleria Ateneumin taidemuseo/'
    }
    if name in aliases:
        return aliases[name]
    else:
        return name


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
    return url


def do_finna_search(page=1, lookfor=None, type='AllFields', collection=None, full=True): # noqa
    data = None
    url = "https://api.finna.fi/v1/search?"
    url += add_finna_api_free_images_only_parameters()
    if full:
        url += add_finna_api_default_field_parameters()
    url += finna_api_parameter('limit', '100')
    url += finna_api_parameter('page', str(page))

    collection = get_collection_name_from_alias(collection)
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
    with urllib.request.urlopen(url) as file:
        try:
            data = json.loads(file.read().decode())
        except Exception as e:
            print(e)
            data = None
    return data


# Get finna API record with most of the information
# Finna API documentation
# * https://api.finna.fi
# * https://www.kiwi.fi/pages/viewpage.action?pageId=53839221
def get_finna_record_url(id, full=False, lang=None):
    urlencoded_id = urllib.parse.quote_plus(id)
    url = f'https://api.finna.fi/v1/record?prettyPrint=1&id={urlencoded_id}'
    if full:
        url += add_finna_api_default_field_parameters()

    if lang:
        url += f'&lng={lang}'
    return url


def get_finna_record(id, full=False, lang=None):
    url = get_finna_record_url(id, full, lang)

    try:
        response = s.get(url)
        return response.json()
    except:
        print("Finna API query failed: " + url)
        exit(1)


def get_summary_in_language(id, lang):
    urlencoded_id = urllib.parse.quote_plus(id)
    url = f'https://api.finna.fi/v1/record?prettyPrint=1&id={urlencoded_id}'
    url += finna_api_parameter('field[]', 'summary')
    url += f'&lng={lang}'
    try:
        response = s.get(url)
        json = response.json()
        return json['records'][0]['summary']
    except:
        print("Finna API query failed: " + url)
        exit(1)


def get_finna_id_from_url(url):
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


def parse_full_record(xml_data):
    # Parse the XML data
    root = ET.fromstring(xml_data)

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

    return {'summary': descriptive_note_values, 'title': appellation_values}

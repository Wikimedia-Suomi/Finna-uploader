import requests
import urllib
import re
import html

from images.wikitext.wikidata_helpers import get_collection_names

from images.imagehash_helpers import isimageformatsupported

s = requests.Session()
s.headers.update({'User-Agent': 'FinnaUploader 0.2 (https://commons.wikimedia.org/wiki/User:FinnaUploadBot)'}) # noqa

# TODO: responses could be cached instead of possibly repeating
def get_json_response(session, url):
    if not url:
        print("empty url, cannot request")
        return None

    print("DEBUG: requesting with url:", url)
    
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


# Shortcut -> long-name translations
# for example, Helsingin kaupunginmuseo has only institution without collections
# there are also others
def get_collection_aliases():
    aliases = {
             'Kuvasiskot': 'Studio Kuvasiskojen kokoelma',
             'hkm': '0/HKM/',
             'Helsingin kaupunginmuseo': 'Helsingin kaupunginmuseo',
             'Vantaan' : '0/VANTAA/', # Vantaan kaupunginmuseo
             'Kymenlaakson' : '0/Kymenlaakson museo/',
             'Lahdenmuseo' : '0/LAHTIMUSEO/', # Lahden museot, myös 1\/LAHTIMUSEO\/Kuvakokoelmat kuva-arkisto\/
             'Varkauden' : '0/VARKAUDENMUSEOT/', # Varkauden museot
             'Kainuun' : '0/KainuunMuseo/',
             'Lapin' : '0/LMM/', # Lapin maakuntamuseo
             'Oulun' : '0/OULUNMUSEO/',
             'Tornion' : '0/Tornionlaakso/',
             'Lappeenrannan' : '0/LPRMUSEOT/', # myös 1\/LPRMUSEOT\/Wolkoffin museo\/
             'Mikkelin' : '0/mikkelinmuseot/',
             'Kuhmu' : '0/KUHMU/', # Kuopion kulttuurihistoriallinen museo
             'Ugin' : '0/Uudenkaupungin museo/',
             'HML' : '0/HMLMUSEO/', # Hämeenlinnan kaupunginmuseo
             'KHM' : '0/KHM/', # Kemin historiallinen museo
             'FMP': '0/FMP/', # Suomen valokuvataiteen museo
             'JOKA': 'JOKA Journalistinen kuva-arkisto',
             'SLS' : '0/SLS/', # Svenska litteraturs\u00e4llskapet i Finland
             'SA-kuva' : '0/SA-kuva/',
             'Forssan' : '0/FORSSANMUSEO/',
             'Heinolan' : '0/Heinolan museot/', 
             'Kamu' : '0/ESPOO_KAUPMUS/', # KAMU Espoon kaupunginmuseo
             'Taika' : '0/TAIKA/', # Hyvinkään
             'Tuusulan' : '0/Tuusulan museo/',
             'Imatran' : '0/imatranmuseot/',
             'Kouvolan' : '0/POIKILO/',
             'Loviisan' : '0/loviisankaupunginmuseo/',
             'SibeliusMuseum' : '0/Sibeliusmuseum/',
             'SibeliusArkiv' : '0/SibeliusmuseumsArkiv/',
             'Teatterimuseo' : '0/TEATTERIMUSEO/',
             'Lusto' : '0/Lusto/', # Suomen metsämuseo
             'Pielisen' : '0/PielisenMuseo/',
             'Marinum' : '0/Forum Marinum/',
             'Merimuseo' : '0/RAUMANMERIMUSEO/',
             'Ilmailu' : '0/ilmailumuseo/',
             'Yomuseo' : '0/yo-museo/', # Tiedemuseo Liekki
             'Tekniikanmuseo' : '0/tekniikan_museo/', # Tekniikan museo
             'Metsästysmuseo' : '0/Metsastysmuseo/', # Suomen Metsästysmuseo
             'Urheilumuseo' : '0/URHEILUMUSEO/',
             'Lottamuseo' : '0/Lottamuseo/', 
             'Satmuseo0' : "0/SATMUSEO/", # Satakunnan Museo
             'Satmuseo1' : "1/SATMUSEO/Kuvakokoelma/", # Kuvakokoelma
             'Rauman' : '0/RAUMANMUSEO/', 
             'Turunkm' : '0/Turun kaupunginmuseo/',
             'Turunmus' : '0/Turun museokeskus/',
             'Naantalin' : '0/Naantalin museo/',
             'Salon' : '0/Salon historiallinen museo/',
             'Nurmeksen' : '0/NurmeksenMuseo/',
             'Museovirasto' : '0/Museovirasto/',
             'Siiri': '0/Siiri/', # Tampereen historialliset museot
             'Vapriikki': '1/Siiri/Vapriikin kuva-arkisto/',
             'Valkeakosken' : '0/VISAVUORI/',
             'Werstas' : '0/Werstas/', # Työväenmuseo Werstas
             #'tvarkisto': '0/tyovaen_arkisto/', # työväen arkisto, ei vapaita kuvia
             'kansan' : '0/kansan_arkisto/', # Kansan Arkisto, Kansan uutisten?
             'Aaltoarkisto' : '0/AALTOARKISTO/', # Aalto-yliopiston arkisto
             'elka' : '0/elka/', # Suomen Elinkeinoelämän Keskusarkisto
             'Kustavin' : '0/Kustavin museo/',
             'Käsityö' : '0/SKM/',
             'Arkkitehtuurimuseo' : '0/MFA/',
             'WAM' : '0/WAM Turun kaupungin taidemuseo/',
             'Kansallismuseo' : '0/Suomen kansallismuseo/',
             'Kansallisgalleria' : '0/Kansallisgalleria Arkistokokoelmat/',
             'Ateneumin': '0/Kansallisgalleria Ateneumin taidemuseo/',
             'Sinebrychoffin' : '0/Kansallisgalleria Sinebrychoffin taidemuseo/'
    }
    return aliases

def get_collection_name_from_alias(name):
    aliases = get_collection_aliases()
    if name in aliases:
        return aliases[name]
    else:
        return name

def is_building_collection(name):
    collections = ['0/SA-kuva/',
                    '0/HKM/',
                    '0/VANTAA/',
                    '0/Kymenlaakson museo/',
                    '0/SATMUSEO/',
                    '1/SATMUSEO/Kuvakokoelma/',
                    '0/LAHTIMUSEO/',
                    '0/VARKAUDENMUSEOT/',
                    '0/KainuunMuseo/',
                    '0/LMM/',
                    '0/OULUNMUSEO/',
                    '0/Tornionlaakso/',
                    '0/LPRMUSEOT/',
                    '0/mikkelinmuseot/',
                    '0/KUHMU/',
                    '0/Uudenkaupungin museo/',
                    '0/HMLMUSEO/',
                    '0/KHM/',
                    '0/FMP/',
                    '0/SLS/',
                    '0/FORSSANMUSEO/',
                    '0/Heinolan museot/',
                    '0/ESPOO_KAUPMUS/',
                    '0/TAIKA/',
                    '0/Tuusulan museo/',
                    '0/imatranmuseot/',
                    '0/POIKILO/',
                    '0/loviisankaupunginmuseo/',
                    '0/SibeliusmuseumsArkiv/',
                    '0/TEATTERIMUSEO/',
                    '0/Lusto/',
                    '0/PielisenMuseo/',
                    '0/Forum Marinum/',
                    '0/RAUMANMERIMUSEO/',
                    '0/ilmailumuseo/',
                    '0/yo-museo/',
                    '0/tekniikan_museo/',
                    '0/Metsastysmuseo/',
                    '0/URHEILUMUSEO/',
                    '0/Lottamuseo/',
                    '0/RAUMANMUSEO/',
                    '0/Turun kaupunginmuseo/',
                    '0/Turun museokeskus/',
                    '0/Naantalin museo/',
                    '0/Salon historiallinen museo/',
                    '0/NurmeksenMuseo/',
                    '0/kansan_arkisto/',
                    '0/Siiri/',
                    '1/Siiri/Vapriikin kuva-arkisto/',
                    '0/VISAVUORI/',
                    '0/Werstas/',
                    '0/Museovirasto/',
                    '0/AALTOARKISTO/',
                    '0/elka',
                    '0/Kustavin museo/',
                    '0/SKM/',
                    '0/MFA/',
                    '0/WAM Turun kaupungin taidemuseo/',
                    '0/Suomen kansallismuseo/',
                    '0/Kansallisgalleria Arkistokokoelmat/',
                    '0/Kansallisgalleria Ateneumin taidemuseo/',
                    '0/Kansallisgalleria Sinebrychoffin taidemuseo/']
    if name in collections:
        return True
    return False

def do_finna_search(page=1, lookfor=None, type='AllFields', collection=None, full=True): # noqa

    url = "https://api.finna.fi/v1/search?"
    url += add_finna_api_free_images_only_parameters()
    if full:
        url += add_finna_api_default_field_parameters()

    # with limit=20 maximum page=5000 api returns 100 000 records, see last_indexed
    url += finna_api_parameter('limit', '100') # 0-100, use 0 to get number of results
    url += finna_api_parameter('page', str(page))
    
    if (is_building_collection(collection) == True):
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



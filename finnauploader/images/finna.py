import requests
import urllib
import re
import json
from images.imagehash_helpers import is_same_image

# urlencode Finna parameters
def finna_api_parameter(name, value):   
   return "&" + urllib.parse.quote_plus(name) + "=" + urllib.parse.quote_plus(value)


def add_finna_api_free_images_only_parameters():
    url=''
    url+= finna_api_parameter('filter[]', '~format_ext_str_mv:"0/Image/"')
    url+= finna_api_parameter('filter[]', 'free_online_boolean:"1"')
    url+= finna_api_parameter('filter[]', '~usage_rights_str_mv:"usage_B"')
    return url

def add_finna_api_default_field_parameters():
    url=''
    url+= finna_api_parameter('field[]', 'id')
    url+= finna_api_parameter('field[]', 'title')
    url+= finna_api_parameter('field[]', 'subTitle')
    url+= finna_api_parameter('field[]', 'shortTitle')
    url+= finna_api_parameter('field[]', 'summary')
    url+= finna_api_parameter('field[]', 'imageRights')
    url+= finna_api_parameter('field[]', 'images')
    url+= finna_api_parameter('field[]', 'imagesExtended')
    url+= finna_api_parameter('field[]', 'onlineUrls')
    url+= finna_api_parameter('field[]', 'openUrl')
    url+= finna_api_parameter('field[]', 'nonPresenterAuthors')
    url+= finna_api_parameter('field[]', 'onlineUrls')
    url+= finna_api_parameter('field[]', 'subjects')
    url+= finna_api_parameter('field[]', 'subjectsExtendet')
    url+= finna_api_parameter('field[]', 'subjectPlaces')
    url+= finna_api_parameter('field[]', 'subjectActors')
    url+= finna_api_parameter('field[]', 'subjectDetails')
    url+= finna_api_parameter('field[]', 'geoLocations')
    url+= finna_api_parameter('field[]', 'buildings')
    url+= finna_api_parameter('field[]', 'identifierString')
    url+= finna_api_parameter('field[]', 'collections')
    url+= finna_api_parameter('field[]', 'institutions')
    url+= finna_api_parameter('field[]', 'classifications')
    url+= finna_api_parameter('field[]', 'events')
    url+= finna_api_parameter('field[]', 'languages')
    url+= finna_api_parameter('field[]', 'originalLanguages')
    url+= finna_api_parameter('field[]', 'year')
    url+= finna_api_parameter('field[]', 'hierarchicalPlaceNames')
    url+= finna_api_parameter('field[]', 'formats')
    url+= finna_api_parameter('field[]', 'physicalDescriptions')
    url+= finna_api_parameter('field[]', 'measurements')
    return url

def do_finna_search(page=1, lookfor=None, type='AllFields', collection=None ):
    data = None
    url = "https://api.finna.fi/v1/search?"
    url += add_finna_api_free_images_only_parameters()
    url += add_finna_api_default_field_parameters()
    url += finna_api_parameter('limit','100')
    url += finna_api_parameter('page',str(page))

    if collection:
        url+= finna_api_parameter('filter[]', f'~hierarchy_parent_title:"{collection}"')

    # Example search value '"professorit"+"miesten+puvut"'
    if lookfor:
        url+= finna_api_parameter('lookfor',f'{lookfor}')     

    # Where lookfor is targeted. Known values 'AllFields', 'Subjects'
    if type:
        url+= finna_api_parameter('type',f'{type}') 

    print(url)
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

def get_finna_record(id, full=False):

    url="https://api.finna.fi/v1/record?id=" +  urllib.parse.quote_plus(id)
    if full:
        url+= add_finna_api_default_field_parameters()
                        
    try:
        response = requests.get(url)
        return response.json()
    except:
        print("Finna API query failed: " + url)
        exit(1)

def is_correct_finna_record(finna_id, image_url):
    finna_record = get_finna_record(finna_id, True)
    
    if finna_record['status']!='OK':
        print('Finna status not OK')
        return False    

    if finna_record['resultCount']!=1:
        print('Finna resultCount!=1')
        return False

    record_finna_id=finna_record['records'][0]['id']
    if record_finna_id!=finna_id:
        print(f'finna_id update: {finna_id} -> {record_finna_id}')
    
    for imageExtended in finna_record['records'][0]['imagesExtended']:
        # Test copyright
        allowed_copyrighs=['CC BY 4.0', 'CC0']
        if imageExtended['rights']['copyright'] not in allowed_copyrighs:
            print("Incorrect copyright: " + imageExtended['rights']['copyright'])
            return False
    
        # Confirm that images are same using imagehash
    
        finna_thumbnail_url="https://finna.fi" + imageExtended['urls']['large']
        
         if is_same_image(finna_thumbnail_url, image_url):
            return record_finna_id

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
                 id = 'musketti.M012:HK7155:' + str(match.group(1)).replace('_', '-')
                 return id
               



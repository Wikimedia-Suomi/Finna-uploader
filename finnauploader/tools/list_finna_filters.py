# Prints Finna facets and collections
#
# Usage: python list_finna_filters.py facet_name
# - python list_finna_filters.py building
#
# Usage: python list_finna_filters.py hierarchy_parent_title building"
# Example:
# - python list_finna_filters.py "hierarchy_parent_title" "0/Museovirasto/"
#
import requests
import json
import sys
from urllib.parse import urlparse, parse_qs, quote
from bs4 import BeautifulSoup

out = {}


def load_and_print_json(url, lang):
    headers = {
        'User-Agent': 'Finna-uploader to Wikimedia Commos/1.0'
    }

    # Language is defined using cookie
    cookies = {
        'language': lang
    }

    # Fetch the JSON data from the URL
    response = requests.get(url, headers=headers, cookies=cookies)
    response.raise_for_status()  # This will raise an exception for HTTP errors

    # Parse the JSON data
    data = response.json()
    return data


def handle_row(row, lang):
    try:
        keytext = row['value']
        labeltext = row['displayText']
    except:
        print("ERROR")
        print(json.dumps(row, indent=4))
        exit(1)
    if keytext not in out:
        out[keytext] = {}

    out[keytext][lang] = labeltext

#    print(f'{keytext} {labeltext}')
    if 'children' in row:
        for childrow in row['children']:
            handle_row(childrow, lang)


# Finna renders list dynamically from JSON
def get_data_from_json(facet_name, langs):
    # Finnan vakiohaku kuville.
    # - Rajattu tuloksiin jotka on kuvia ja niistä löytyy internetistä kuva
    url = "https://www.finna.fi/AJAX/JSON?"
    url += "filter%5B%5D=%7Eformat_ext_str_mv%3A%220%2FImage%2F%22"
    url += "&filter%5B%5D=free_online_boolean%3A%221%22"
    url += "&type=AllFields"
    url += "&method=getFacetData"
    url += "&source=Solr"
    url += f"&facetName={facet_name}"
    url += "&facetSort=top"
    url += "&facetOperator=OR&"
    url += "query=filter%255B%255D%3D%257Eformat_ext_str_mv%253A%25220%252FImage%252F%2522%26filter%255B%255D%3Dfree_online_boolean%253A%25221%2522%26type%3DAllFields" # noqa
    url += "&querySuppressed=0"
    url += "&extraFields=handler%2Climit%2CselectedShards%2Csort%2Cview"

    for lang in langs:
        data = load_and_print_json(url, lang)
        for row in data['data']['facets']:
            handle_row(row, lang)


def parse_data_from_html(content):
    # Parse the HTML content of the page
    soup = BeautifulSoup(content, 'html.parser')

    # Find the list by its id and extract all list items
    list_items = soup.find('ul', id='facet-list-index').find_all('li')

    # Iterate through each list item and extract the desired data
    for item in list_items:
        link = item.find('a')
        href = link.get('href')  # Extract the href attribute
        parsed_url = urlparse(href)
        query_params = parse_qs(parsed_url.query)
        # Extract the hierarchy_parent_title value

        filters = query_params.get('filter[]', [None])
        for filter in filters:
            if 'hierarchy_parent_title' in filter:
                hierarchy_parent_title = filter.split(":", 1)[1]\
                                               .replace('"', '')

        data_title = link.get('data-title')  # Extract the data-title attribute
#        print(f"Link: {href}, Title: {data_title}")
        if data_title != hierarchy_parent_title:
            print(hierarchy_parent_title)
            print("ERROR")
            exit(1)

        out.append(data_title)


# Finna renders list in server side as paged html
def get_data_from_html(facet_name, building_id):
    encoded_building_id = quote(building_id)

    url = 'https://www.finna.fi/Search/FacetList?'
    url += 'filter%5B0%5D=%7Eformat_ext_str_mv%3A%220%2FImage%2F%22'
    url += '&filter%5B1%5D=free_online_boolean%3A%221%22'
    url += f'&filter%5B2%5D=%7Ebuilding%3A%22{encoded_building_id}%22'
    url += '&type=AllFields'
    url += '&facet=hierarchy_parent_title'
    url += '&facetop=OR'
    url += '&facetexclude=0'
    url += '&facetsort=index'
    url += '&lng=en-gb'

    headers = {
        'User-Agent': 'Finna-uploader to Wikimedia Commos/1.0'
    }

    for facetpage in range(1, 100):
        paged_url = f'{url}&facetpage={facetpage}'

        # Fetch the JSON data from the URL
        response = requests.get(paged_url, headers=headers)
        # This will raise an exception for HTTP errors
        response.raise_for_status()
        parse_data_from_html(response.content)
        if 'more…' not in response.content.decode():
            break


def get_buildings_id(building_name, langs):
    ret = {}
    get_data_from_json('building', langs)
    if building_name:
        for rowname in out:
            if building_name in rowname:
                ret[rowname] = out[rowname]
            elif building_name in json.dumps(out[rowname]):
                ret[rowname] = out[rowname]

    if len(ret) == 1:
        # return first key
        return next(iter(ret))
    elif len(ret) > 1:
        print("Error: Multiple buildings found")
    else:
        print("Error: No buildings found")
        ret = out

    usage_msg = 'python list_finna_filters.py hierarchy_parent_title building'
    print(f'Usage: {usage_msg}')
    print("Available buildings:")
    print(json.dumps(ret, indent=4))
    exit(1)


# Key is keyword in Finna api, second is human readable label in web UI
# List is fetched using command
# wget -O - "https://finna.fi/Search/Results?lookfor=&type=AllFields&filter%5B0%5D=%7Eformat_ext_str_mv%3A%220%2FImage%2F%22&filter%5B1%5D=free_online_boolean%3A1&lng=en-gb"|grep data-facet # noqa
#
# Commented out ones doesn't work
facets = {
  'usage_rights_ext_str_mv': {'en-gb': 'Usage rights', 'fi': 'Käyttöoikeudet'},
  'format_ext_str_mv': {'en-gb': 'Content type', 'fi': 'Aineistotyyppi'},
  # 'free_online_boolean&#x3A;1' : { 'en-gb' : 'Available online',
  #                                  'fi' : 'Verkossa saatavilla', },
  # 'author_facet' : { 'en-gb' : 'Author', 'fi' : 'Tekijä', },
  # 'topic_facet' : { 'en-gb' : 'Topic', 'fi' : 'Aihe' },
  # 'geographic_facet' : { 'en-gb' : 'Region', 'fi' : 'Alue' },
  # 'search_daterange_mv' : { 'en-gb' : 'Year of manufacture',
  #                           'fi' : 'Valmistusvuosi' },
  # 'era_facet' : { 'en-gb' : 'Era', 'fi' : 'Aiheen aika' },
  'language': {'en-gb': 'Language', 'fi': 'Kieli'},
  'hierarchy_parent_title': {'en-gb': 'Contained in',
                             'fi': 'Sisältyy kokonaisuuteen'},
  'sector_str_mv': {'en-gb': 'Sector', 'fi': 'Toimiala'},
  'building': {'en-gb': 'Organization',
               'fi': 'Organisaatio'},
  'first_indexed': {'en-gb': 'New in Finna',
                    'fi': 'Uutta Finnassa'}
}

langs = ['fi', 'sv', 'en-gb']


# Handle command line arguments
facet_name = None
building_name = None
if len(sys.argv) == 2:
    facet_name = sys.argv[1]
elif len(sys.argv) == 3:
    facet_name = sys.argv[1]
    building_name = sys.argv[2]
else:
    facet_name = None

if not facet_name or facet_name not in facets:
    print("Usage: python list_finna_filters.py facet_name")
    print("")
    print("Available facets:")
    print(json.dumps(facets, indent=4))
    exit(1)

if facet_name == 'hierarchy_parent_title':
    building_id = get_buildings_id(building_name, langs)
    out = []
    get_data_from_html(facet_name, building_id)
else:
    get_data_from_json(facet_name, langs)

# Pretty-print the JSON data
print(json.dumps(out, indent=4))

import requests
import pywikibot
from pywikibot.data import sparql

from images.pywikibot_helpers import getCommonsite

# finna id query results: reduce queries
toolforgeFinnaId = {}
uploadsummary = None
sparql_finna_ids_data = None

# set into cache
def setToolforgeFinnaId(finna_id, exists):
    toolforgeFinnaId[finna_id] = exists

# lookup cache only
def isToolforgeFinnaId(finna_id):
    if (finna_id in toolforgeFinnaId):
        return toolforgeFinnaId[finna_id]
    return False

# try to search from server:
# also use cache if possible.
# this is only used for "slow" search?
def toolforge_finnasearch(finna_id):
    # use cache if possible
    if (isToolforgeFinnaId(finna_id) == True):
        return True
    
    # TODO: import whole dump instead?
    #url = 'https://imagehash.toolforge.org/static/commons_finna_imagehashes.json.gz'

    s = requests.Session()
    s.headers.update({'User-Agent': 'FinnaUploader 0.2 (https://commons.wikimedia.org/wiki/User:FinnaUploadBot)'}) # noqa
    
    url = f'https://imagehash.toolforge.org/finnasearch?finna_id={finna_id}'
    response = s.get(url)
    response.raise_for_status()  # Raise an exception for HTTP errors
    data = response.json()
    
    print("tf result:", data)

    if len(data):
        print("tf result:", data)
        setToolforgeFinnaId(finna_id, True)
        return True

    return False


def get_existing_finna_ids_from_sparql():
    print("Loading existing photo Finna ids using SPARQL")
    # Define the SPARQL query
    query = "SELECT ?item ?finna_id WHERE { ?item wdt:P9478 ?finna_id }"

    # Set up the SPARQL endpoint and entity URL
    # Note: https://commons-query.wikimedia.org requires user to be logged in

    entity_url = 'https://commons.wikimedia.org/entity/'
    endpoint = 'https://commons-query.wikimedia.org/sparql'

    # Create a SparqlQuery object
    query_object = sparql.SparqlQuery(endpoint=endpoint, entity_url=entity_url)

    # Execute the SPARQL query and retrieve the data
    data = query_object.select(query, full_data=True)
    if not data:
        print("SPARQL Failed. login BUG?")
        exit(1)

    # TODO: can we simplify to a set with unique instances only?
    # there are duplicates for various reasons

    #print("DEBUG: existing ids from sparql: ", str(data))
    return data


# edit summaries of last 1000 edits to check which files were already uploaded
def get_upload_summary(limit=1000):

    # maybe use set() for unique list (we don't really care how many times it exists)
    uploads = list()
    checked = list() # checked page list (filter)

    # ensure proper login
    commonssite = getCommonsite()

    current_user = commonssite.user()

    usual_uploaders = list()
    usual_uploaders.append(str(current_user)) # get own edits
    if (current_user != 'FinnaUploadBot'):
        usual_uploaders.append('FinnaUploadBot')
    if (current_user != 'FinnaUploadBot2'):
        usual_uploaders.append('FinnaUploadBot2')
    #usual_uploaders.append('Zache')


    for username in usual_uploaders:
            
        user = pywikibot.User(commonssite, username)
        contribs = user.contributions(total=limit)

        # list of tuples
        for contrib in contribs:
            page = contrib[0]
            # if (page.namespace == 0): does not work correctly ?
            # we don't care if user modifies something else
            if (page.title().startswith("File:") == False):
                continue
            if page.title() in checked:
                continue
            
            print("contrib: ", page.title())
            # only use on filepages instead of pages with lists of files..
            for url in page.extlinks():
                if (url.find("finna.fi") < 1):
                    continue
                #print("url in contrib: ", url)
                uploads.append(url)
            checked.append(page.title())

    return uploads

# only used from import helper during import
def is_already_in_commons(finna_id, fast=False):
    if (sparql_finna_ids_data == None):
        print("Loading existing ids by sparql")
        sparql_finna_ids_data = get_existing_finna_ids_from_sparql()

    if (uploadsummary == None):
        print("Loading 1000 most recent edit summaries for skipping uploaded files")
        uploadsummary = get_upload_summary(1000)

    #print("DEBUG: searching for existing finna id: ", finna_id)
    
    # Check if image is already uploaded
    if finna_id in sparql_finna_ids_data:
        print(f'Skipping 1: {finna_id} already uploaded based on sparql')
        return True

    if finna_id in uploadsummary:
        print(f'Skipping 2: {finna_id} already uploaded based on summaries')
        return True

    # use cache if possible
    if (isToolforgeFinnaId(finna_id) == True):
        return True

    # non-fast will try to search from toolforce by id:
    # we should use cached dump of data if possible
    if not fast:
        if toolforge_finnasearch(finna_id):
            msg = f'Skipping 3: {finna_id} already uploaded based on imagehash'
            print(msg)
            return True
    return False

# main ()

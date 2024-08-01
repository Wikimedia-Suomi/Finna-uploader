import requests
import pywikibot
from pywikibot.data import sparql

class UploadCache:
    def load_duplicates(self):
        self.uploadsummary = self.get_upload_summary(5000)
        self.sparql_finna_ids_data = self.get_existing_finna_ids_from_sparql()
        #self.sparql_finna_ids = str(self.sparql_finna_ids_data)


s = requests.Session()

# finna id query results: reduce queries
toolforgeFinnaId = {}

def setToolforgeFinnaId(finna_id, exists):
    toolforgeFinnaId[finna_id] = exists


def isToolforgeFinnaId(finna_id):
    if (finna_id in toolforgeFinnaId):
        return toolforgeFinnaId[finna_id]
    return False

def toolforge_finnasearch(finna_id):
    if (isToolforgeFinnaId(finna_id) == True):
        return True
    
    url = f'https://imagehash.toolforge.org/finnasearch?finna_id={finna_id}'
    response = s.get(url)
    response.raise_for_status()  # Raise an exception for HTTP errors
    data = response.json()

    if len(data):
        setToolforgeFinnaId(finna_id)
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

    #print("DEBUG: existing ids from sparql: ", str(data))
    return data


# edit summaries of last 1000 edits to check which files were already uploaded
def get_upload_summary(limit=1000):
    site = pywikibot.Site('commons', 'commons')
    site.login()

    # Get own edits
    current_user = site.user()  # The user whose edits we want to check
    user = pywikibot.User(site, str(current_user))
    contribs = user.contributions(total=limit)  # Get the user's last 5000 edits

    uploadsummary = ''
    for contrib in contribs:
        uploadsummary += str(contrib) + "\n"

    usual_uploaders = ['FinnaUploadBot', 'FinnaUploadBot2', 'Zache']
    for username in usual_uploaders:
        if (current_user != username):
            user = pywikibot.User(site, username)
            contribs = user.contributions(total=limit)

            for contrib in contribs:
                uploadsummary += str(contrib) + "\n"

    return uploadsummary


def is_already_in_commons(finna_id, fast=False):
    #if (sparql_finna_ids == None):
        #return False

    print("DEBUG: searching for existing finna id: ", finna_id)

    
    # Check if image is already uploaded
    #if finna_id in sparql_finna_ids:
    if finna_id in sparql_finna_ids_data:
        print(f'Skipping 1: {finna_id} already uploaded based on sparql')
        return True

    if finna_id in uploadsummary:
        print(f'Skipping 2: {finna_id} already uploaded based on summaries')
        return True

    if not fast:
        if toolforge_finnasearch(finna_id):
            msg = f'Skipping 3: {finna_id} already uploaded based on imagehash'
            print(msg)
            return True
    return False


#def search_from_sparql_finna_ids(needle):
    #if needle in sparql_finna_ids:
        #return True
    #return False

#def get_sparql_finna_id_list():
    #return sparql_finna_ids

# main ()
print("Loading 5000 most recent edit summaries for skipping uploaded files")
uploadsummary = get_upload_summary(5000)
sparql_finna_ids_data = get_existing_finna_ids_from_sparql()
#sparql_finna_ids = str(sparql_finna_ids_data)

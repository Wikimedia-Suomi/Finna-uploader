import requests
import pywikibot
from pywikibot.data import sparql

s = requests.Session()


def finna_exists(id):
    url = f'https://imagehash.toolforge.org/finnasearch?finna_id={id}'
    response = s.get(url)
    response.raise_for_status()  # Raise an exception for HTTP errors
    data = response.json()
    if len(data):
        return True
    else:
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
    # Check if image is already uploaded
    if finna_id in sparql_finna_ids:
        print(f'Skipping 1: {finna_id} already uploaded based on sparql')
        return True

    if finna_id in uploadsummary:
        print(f'Skipping 2: {finna_id} already uploaded based on summaries')
        return True

    if not fast:
        if finna_exists(finna_id):
            msg = f'Skipping 3: {finna_id} already uploaded based on imagehash'
            print(msg)
            return True
    return False


def search_from_sparql_finna_ids(needle):
    if needle in sparql_finna_ids:
        return True
    return False


def get_sparql_finna_ids():
    return sparql_finna_ids


print("Loading 1000 most recent edit summaries for skipping uploaded files")
uploadsummary = get_upload_summary()
sparql_finna_ids_data = get_existing_finna_ids_from_sparql()
sparql_finna_ids = str(sparql_finna_ids_data)

import pywikibot
from pywikibot.exceptions import NoPageError
import json
import re
from datetime import datetime
from pywikibot.data.sparql import SparqlQuery


# should do this here instead of in wikidata_helpers.py ?
pywikibot.config.socket_timeout = 240

dtstart = datetime.now()

g_wdsite = None
g_commonssite = None

def getWdsite():
    global g_wdsite
    if (g_wdsite == None):
        g_wdsite = pywikibot.Site("wikidata", "wikidata")
        g_wdsite.login() # ensure we have proper login
    
    return g_wdsite

def getCommonsite():
    global g_commonssite
    if (g_commonssite == None):
        g_commonssite = pywikibot.Site('commons', 'commons')
        g_commonssite.login() # ensure we have proper login
    
    return g_commonssite

def are_there_messages_for_bot_in_commons():

    commonssite = getCommonsite()
    
    # Check if the page exists
    if commonssite.userinfo['messages']:
        # talk_page = commonssite.user.getUserTalkPage()
        user = pywikibot.User(commonssite, commonssite.username())
        talk_page = user.getUserTalkPage()
        latestdt = talk_page.latest_revision.timestamp
        if (latestdt > dtstart):
            page_name = talk_page.title()
            msg = f'Warning: You have received a {page_name} message. Exiting.'
            print(msg)
            
            # abort upload
            exit()
            return True
    return False


def test_if_finna_id_exists_in_commons(finna_id, slow=False):
    query = """
SELECT DISTINCT ?media ?finna_id ?phash ?dhash WHERE {
    ?media wdt:P9478 __finna_id__ .
    OPTIONAL { ?media wdt:P9310 ?phash }
    OPTIONAL { ?media wdt:P12563 ?dhash }
} LIMIT 3
"""

    query = query.replace('__finna_id__', f'"{finna_id}"')
    endpoint = 'https://commons-query.wikimedia.org/sparql'
    entity_url = 'https://commons.wikimedia.org/entity/'
    sparql = SparqlQuery(endpoint=endpoint, entity_url=entity_url)
    data = sparql.select(query)
    return data

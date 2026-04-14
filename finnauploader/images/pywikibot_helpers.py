import pywikibot
from pywikibot.exceptions import NoPageError
import json
import re
from datetime import datetime


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



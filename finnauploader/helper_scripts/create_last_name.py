# Script creates wikidata item for last name.
#
# Usage:
# python3 create_last_name.py <lastname>
#
# 

import re
import sys
import pywikibot
from requests import get

import urllib
import urllib.request
import urllib.parse

# https://github.com/mpeel/wikicode/blob/master/wir_newpages.py#L42
def getURL(url, retry=True, timeout=30):
    raw = ''
    sleep = 10 # seconds
    maxsleep = 900
    #headers = {'User-Agent': 'pywikibot'}
    headers = { 'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:55.0) Gecko/20100101 Firefox/55.0' }
    req = urllib.request.Request(url, headers=headers)
    while retry and sleep <= maxsleep:
        try:
            return urllib.request.urlopen(req, timeout=timeout).read().strip().decode('utf-8')
        except:
            print('Error while retrieving: %s' % (url))
            print('Retry in %s seconds...' % (sleep))
            time.sleep(sleep)
            sleep = sleep * 2
    return raw

def checkqcode(title, itemqcode):
    wdsite = pywikibot.Site('wikidata', 'wikidata')
    wdsite.login()

    repo = wdsite.data_repository()
    
    itemfound = pywikibot.ItemPage(repo, itemqcode)
    dictionary = itemfound.get()

    print(dictionary)
    print(dictionary.keys())
    print(itemfound)
    
    return True

# https://github.com/mpeel/wikicode/blob/master/wir_newpages.py#L706
def searchname(par_name, lang='fi'):

    searchitemurl = 'https://www.wikidata.org/w/api.php?action=wbsearchentities&search=%s&language=%s&format=xml' % (urllib.parse.quote(par_name), lang)
    raw = getURL(searchitemurl)
    #print(searchitemurl.encode('utf-8'))

    if not '<search />' in raw:
        m = re.findall(r'id="(Q\d+)"', raw)
        
        numcandidates = '' #do not set to zero
        numcandidates = len(m)
        print("Found %s candidates" % (numcandidates))
        
        for itemfoundq in m:
            # NOTE! server gives suggestions, verify it matches!
            print("potential match exists ", str(itemfoundq))
            return checkqcode(par_name, itemfoundq)
    else:
        print("not found")
        return False

# see: https://www.wikidata.org/wiki/Wikidata:Pywikibot_-_Python_3_Tutorial/Labels
def addname(par_name):

    wdsite = pywikibot.Site('wikidata', 'wikidata')
    wdsite.login()

    repo = wdsite.data_repository()

    new_descr = {"fi": "sukunimi", "en": "family name"}
    newitemlabels = {'fi': par_name,'en': par_name}

    print('Creating a new item...')

    #create item
    newitem = pywikibot.ItemPage(repo)

    #for key in newitemlabels:
        #newitem.editLabels(labels={key: newitemlabels[key]},
            #summary="Setting label: {} = '{}'".format(key, newitemlabels[key]))
        
    #for key in new_descr:
        #newitem.editDescriptions({key: new_descr[key]},
            #summary="Setting description: {} = '{}'".format(key, new_descr[key]))
        
    data = {"labels": {"en": par_name, "fi": par_name},
    "descriptions": {"en": "family name", "fi": "sukunimi"}}
    newitem.editEntity(data, summary=u'Edited item: set labels, descriptions')

    newitem.get()

    print('Adding properties...')

    # instance of
    if not 'P31' in newitem.claims:
        print("Adding claim: family name")
        claim = pywikibot.Claim(repo, 'P31')
        target = pywikibot.ItemPage(repo, 'Q101352') # family name
        claim.setTarget(target)
        newitem.addClaim(claim)#, summary='Adding 1 claim')
        
    # writing system
    if not 'P282' in newitem.claims:
        print("Adding claim: writing system")
        claim = pywikibot.Claim(repo, 'P282')
        target = pywikibot.ItemPage(repo, 'Q8229') # latin alphabet
        claim.setTarget(target)
        newitem.addClaim(claim)#, summary='Adding 1 claim')
        
    # native label
    #if not 'P1705' in newitem.claims:
        #print("Adding claim: native label")
        #claim = pywikibot.Claim(repo, 'P1705')
        #claim.setTarget(wtitle) # + qualifer lang Q1412
        #newitem.addClaim(claim)#, summary='Adding 1 claim')

    #p_claim = pywikibot.Claim(wikidata_site, 'P459', is_reference=False, is_qualifier=True)
    #q_targetph = pywikibot.ItemPage(wikidata_site, hash_methodqcode)
    #p_claim.setTarget(q_targetph)
    #claim.addQualifier(p_claim)
    
    print('All done')

# main()

if __name__ == "__main__":
    if len(sys.argv) == 2:
        # just name
        expectedname = sys.argv[1]
        print(f"Expected name from parameter: {expectedname}")
        if (searchname(expectedname) == False):
            addname(expectedname)
    else:
        print("Script creates wikidata item for last name.")  # noqa
        print("Usage: python3 create_last_name.py <lastname> ")  # noqa
        exit(1)


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
import json

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
            return urllib.request.urlopen(req, timeout=timeout).read()
        except:
            print('Error while retrieving: %s' % (url))
            print('Retry in %s seconds...' % (sleep))
            time.sleep(sleep)
            sleep = sleep * 2
    return raw

def isItemLastName(item):
    isLastName = False
    instance_of = item.claims.get('P31', [])
    for claim in instance_of:
        
        # might have combinations of last name and disambiguation
        if (claim.getTarget().id == 'Q4167410'):
            print("disambiguation page")
            return False # skip for now

        # family name
        if (claim.getTarget().id == 'Q101352'):
            print("instance ok", claim.getTarget().id)
            isLastName = True

        # "von something"
        if (claim.getTarget().id == 'Q66480858'):
            print("instance affixed name", claim.getTarget().id)
            isLastName = True

        if (claim.getTarget().id == 'Q106319018'):
            print("instance hyphenated surname", claim.getTarget().id)
            isLastName = True

        if (claim.getTarget().id == 'Q60558422'):
            print("instance compound surname", claim.getTarget().id)
            isLastName = True

        if (claim.getTarget().id == 'Q121493679'):
            print("instance surname", claim.getTarget().id)
            isLastName = True

        if (claim.getTarget().id == 'Q29042997'):
            print("instance double family name", claim.getTarget().id)
            isLastName = True
    return isLastName

def checkqcode(wtitle, itemqcode, lang='fi'):
    wdsite = pywikibot.Site('wikidata', 'wikidata')
    wdsite.login()

    repo = wdsite.data_repository()
    
    itemfound = pywikibot.ItemPage(repo, itemqcode)
    dictionary = itemfound.get()

    isLastName = isItemLastName(itemfound)

    print("item id, ", itemfound.getID())
    if (lang in itemfound.labels):
        label = itemfound.labels[lang]
        if (label == wtitle and isLastName == True):
            print("found matching label, ", label)
            return True

    #print(dictionary)
    #print(dictionary.keys())
    #print(itemfound)
    
    return False

def getqcodesfromresponse(record):
    qcodes = list()
    if "search" in record:
        s = record["search"]
        if (len(s) > 0):
            for res in s:
                if "id" in res:
                    #print("id = ", res["id"])
                    qcodes.append(res["id"])
    return qcodes

# https://github.com/mpeel/wikicode/blob/master/wir_newpages.py#L706
def searchname(wtitle, lang='fi'):
    print(" ---------")
    print("searching for ", wtitle)

    ## check we have correct qcode for lastname
    #if (validatenamecode(repo, wtitle, nameqcode) == False):
        #print("title and code is not for name", wtitle, nameqcode)
        #return False

    qcodes = list()
    hasMoreItems = True
    contfrom = 0
    
    while (hasMoreItems == True):
        if (contfrom == 0):
            searchitemurl = 'https://www.wikidata.org/w/api.php?action=wbsearchentities&search=%s&language=%s&limit=50&format=json' % (urllib.parse.quote(wtitle), lang)
        else:
            searchitemurl = 'https://www.wikidata.org/w/api.php?action=wbsearchentities&search=%s&language=%s&continue=%s&limit=50&format=json' % (urllib.parse.quote(wtitle), lang, str(contfrom))
        #print(searchitemurl.encode('utf-8'))
        resp = getURL(searchitemurl).strip().decode('utf-8')

        record = json.loads(resp) #.json()

        if 'error' in record:
            print("error result: ", record['error'])
        if 'success' in record:
            if (record['success'] != 1):
                print("not successful")
                return None

        #elif (record['success'] == 1):
            #print("search returned success")
            
        # if there is search-continue="7" results are not complete..
        if "search-continue" in record:
            print("continue search from: ", record['search-continue'])
            contfrom = record['search-continue']
        else:
            hasMoreItems = False

        qcodestmp = getqcodesfromresponse(record)
        for qc in qcodestmp:
            qcodes.append(qc)

    if (len(qcodes) == 0):
        print("no codes found for", wtitle)
        return None
    return qcodes


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
    
    print('All done', newitem.getID())

# main()

if __name__ == "__main__":
    if len(sys.argv) == 2:
        # just name
        expectedname = sys.argv[1]
        print(f"Expected name from parameter: {expectedname}")

        qcodes = searchname(expectedname)
        for itemfoundq in qcodes:
            # NOTE! server gives suggestions, verify it matches!
            print("potential match exists ", str(itemfoundq))
            if (checkqcode(expectedname, itemfoundq) == True):
                print("found exact match.")  # noqa
                exit(1)
        
        addname(expectedname)
    else:
        print("Script creates wikidata item for last name.")  # noqa
        print("Usage: python3 create_last_name.py <lastname> ")  # noqa
        exit(1)


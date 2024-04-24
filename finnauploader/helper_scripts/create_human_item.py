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

def confirmsaving(completename):
    # Get the actual name from the Wikidata item
    #actual_name = item.labels.get('fi', '[No label]')
    #print("Actual name on Wikidata: "+ actual_name +", last name: "+ lastname +"")

    print("Complete name: "+ completename +"")

    # Confirm from the user if they want to continue
    confirmation = pywikibot.input_choice(
        "Do you want to continue with the edits?",
        [('Yes', 'y'), ('No', 'n')],
        default='n'
    )

    if confirmation == 'y':
        return True
    
    print("Operation cancelled.")
    return False

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

def isItemHuman(item):
    isHuman = False
    instance_of = item.claims.get('P31', [])
    for claim in instance_of:
        
        # family name
        if (claim.getTarget().id == 'Q5'):
            print("instance ok", claim.getTarget().id)
            isHuman = True
    return isHuman

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

        if (claim.getTarget().id == 'Q56219051'):
            print("instance Mac of Mc prefix", claim.getTarget().id)
            isLastName = True

    return isLastName

def isItemFirstName(item):
    isFirstName = False
    instance_of = item.claims.get('P31', [])
    for claim in instance_of:
        
        # might have combinations of last name and disambiguation
        if (claim.getTarget().id == 'Q4167410'):
            print("disambiguation page")
            return False # skip for now

        # given name
        if (claim.getTarget().id == 'Q202444'):
            print("instance ok", claim.getTarget().id)
            isFirstName = True

        # male first name
        if (claim.getTarget().id == 'Q12308941'):
            print("instance ok", claim.getTarget().id)
            isFirstName = True

        # female first name
        if (claim.getTarget().id == 'Q11879590'):
            print("instance ok", claim.getTarget().id)
            isFirstName = True

    return isFirstName

# skip some where translitteration might cause issues
def skipByWritingSystem(item):
    instance_of = item.claims.get('P31', [])
    for claim in instance_of:
        
        # Han-sukunimi
        if (claim.getTarget().id == 'Q1093580'):
            return True

    writingsystem = item.claims.get('P282', [])
    for claim in writingsystem:
        
        # kiinan kirjoitusjärjestelmä
        if (claim.getTarget().id == 'Q8201'):
            return True
        
        # not latin alphabet
        if (claim.getTarget().id != 'Q8229'):
            return True

    return False

def getlabelfromitem(item, lang='fi'):
    if lang in item.labels:
        label = item.labels[lang]
        return label
    return None

def getFirstNameQcode(qcodes, name):
    if (qcodes == None):
        print("No items")
        return ''
    if (len(qcodes) == 0):
        print("No items")
        return ''

    for itemqcode in qcodes:
        nameitem = pywikibot.ItemPage(repo, itemqcode)
        if (nameitem.isRedirectPage() == True):
            continue
        
        if (isItemFirstName(nameitem) == True):
            label = getlabelfromitem(nameitem)
            if (label == name):
                return itemqcode
    return ''

def getLastNameQcode(qcodes, name):
    if (qcodes == None):
        print("No items")
        return ''
    if (len(qcodes) == 0):
        print("No items")
        return ''

    for itemqcode in qcodes:
        nameitem = pywikibot.ItemPage(repo, itemqcode)
        if (nameitem.isRedirectPage() == True):
            continue
        
        if (isItemLastName(nameitem) == True):
            label = getlabelfromitem(nameitem)
            if (label == name):
                return itemqcode
    return ''

# check that given item matches with expected label:
# searches can give partial matches
def validatenametitle(repo, nametitle, nameqcode):
    if (len(nameqcode) == 0 or len(nametitle) == 0):
        return False
    
    nameitem = pywikibot.ItemPage(repo, nameqcode)
    if (nameitem.isRedirectPage() == True):
        return False

    dictionary = nameitem.get()
    # not support first or last name -> not valid name
    if (isItemLastName(nameitem) == False and isItemFirstName(nameitem) == False):
        return False
    
    label = getlabelfromitem(nameitem)
    if (label == nametitle):
        # exact match
        return True
    return False

def checkqcodesforhuman(repo, nametitle, firstname, lastname, qcodes):
    if (qcodes == None):
        print("No items")
        return False
    if (len(qcodes) == 0):
        print("No items")
        return False

    for itemqcode in qcodes:
        isMatchingFirstName = False
        isMatchingLastName = False
        
        humanitem = pywikibot.ItemPage(repo, itemqcode)
        if (humanitem.isRedirectPage() == True):
            continue

        print("checking item by code", itemqcode)
        dictionary = humanitem.get()
        
        # check instance
        if (isItemHuman(humanitem) == False):
            print("Not human", itemqcode)
            continue

        if (skipByWritingSystem(humanitem) == True):
            continue

        if 'P734' in humanitem.claims:
            #  check label if it matches to last name
            print("Already has property for last name")
            
            plist = humanitem.claims['P734']
            for p in plist:
                target = p.getTarget()
                if (validatenametitle(repo, lastname, target.id) == False):
                    continue
                else:
                    isMatchingLastName = True

        if 'P735' in humanitem.claims:
            #  check label if it matches to first name
            print("Already has property for given name")
            
            plist = humanitem.claims['P735']
            for p in plist:
                target = p.getTarget()
                if (validatenametitle(repo, firstname, target.id) == False):
                    continue
                else:
                    isMatchingFirstName = True

        if (isMatchingLastName == True and isMatchingFirstName == True):
            label = getlabelfromitem(humanitem)
            print("First and last name targets match", label)
            return True
        
        ## double check label for match
        label = getlabelfromitem(humanitem)
        if (label != None and label.find(nametitle) > 0):

            if (nametitle == label):
                print("Found exact matching label", label)
                return True
            
            # check that last name is last (not first) in the label
            indexlast = label.rfind(" ", 0, len(label)-1)
            if (indexlast < 0):
                print("Item does have first and last name", label)
                #continue
            firstfromlabel = label[:indexlast]
            if (firstfromlabel == firstname):
                print("Item has matching first name in label", firstfromlabel)
                isMatchingFirstName = True
                
            lastfromlabel = label[indexlast+1:]
            if (lastfromlabel == lastname):
                print("Item has matching last name in label", lastfromlabel)
                isMatchingLastName = True

            if (isMatchingLastName == True and isMatchingFirstName == True):
                print("First and last name in label matches", label)
                return True

        #else:
            #print("Label is not ok", itemqcode)
        
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
def searchbyname(repo, wtitle, lang='fi'):
    print(" ---------")
    print("searching for ", wtitle)

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


def addLastName(repo, humanitem, nameqcode):
    if not 'P734' in humanitem.claims:
        print("Adding claim: family name")
        claim = pywikibot.Claim(repo, 'P734')
        target = pywikibot.ItemPage(repo, nameqcode) # family name
        claim.setTarget(target)
        humanitem.addClaim(claim)#, summary='Adding 1 claim')

def addFirstName(repo, humanitem, nameqcode):
    if not 'P735' in humanitem.claims:
        print("Adding claim: given name")
        claim = pywikibot.Claim(repo, 'P735')
        target = pywikibot.ItemPage(repo, nameqcode) # given name
        claim.setTarget(target)
        humanitem.addClaim(claim)#, summary='Adding 1 claim')

# see: https://www.wikidata.org/wiki/Wikidata:Pywikibot_-_Python_3_Tutorial/Labels
def addhuman(repo, complete_name, given_name_qcode, last_name_qcode):

    print('Creating a new item...')

    #create item
    newitem = pywikibot.ItemPage(repo)

    newitemlabels = {'fi': complete_name,'en': complete_name}
    for key in newitemlabels:
        newitem.editLabels(labels={key: newitemlabels[key]},
            summary="Setting label: {} = '{}'".format(key, newitemlabels[key]))
        
    newitem.get()

    print('Adding properties...')

    # instance of
    if not 'P31' in newitem.claims:
        print("Adding claim: human")
        claim = pywikibot.Claim(repo, 'P31')
        target = pywikibot.ItemPage(repo, 'Q5') # 
        claim.setTarget(target)
        newitem.addClaim(claim)#, summary='Adding 1 claim')

    addLastName(repo, newitem, last_name_qcode)
    addFirstName(repo, newitem, given_name_qcode)
        
    # writing system
    #if not 'P282' in newitem.claims:
        #print("Adding claim: writing system")
        #claim = pywikibot.Claim(repo, 'P282')
        #target = pywikibot.ItemPage(repo, 'Q8229') # latin alphabet
        #claim.setTarget(target)
        #newitem.addClaim(claim)#, summary='Adding 1 claim')
        
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

# remove pre- and post-whitespaces when mwparser leaves them
def trimlr(string):
    string = string.lstrip()
    string = string.rstrip()
    return string

# main()

if __name__ == "__main__":
    if len(sys.argv) == 3:
        # just name
        expectedlastname = sys.argv[1]
        expectedfirstname = sys.argv[2]

        first_name = ""
        last_name = ""
        if (expectedlastname.endswith(",")):
            # last name given first
            first_name = expectedfirstname
            last_name = expectedlastname[:len(expectedlastname)-1]
        else:
            # first name given first
            first_name = expectedlastname
            last_name = expectedfirstname

        first_name = trimlr(first_name)
        last_name = trimlr(last_name)

        complete_name = first_name + " " + last_name
        print(f"Complete name from parameter: {complete_name}")

        wdsite = pywikibot.Site('wikidata', 'wikidata')
        wdsite.login()
        repo = wdsite.data_repository()

        qcodes = searchbyname(repo, complete_name)
        if (checkqcodesforhuman(repo, complete_name, first_name, last_name, qcodes) == True):
            print(f"Human already exists by same name: {complete_name}")
            exit(1)

        # locate qcodes for first and last name
        qcodesFirstname = searchbyname(repo, first_name)
        qcodeFirstName = getFirstNameQcode(qcodesFirstname, first_name)
        qcodesLastname = searchbyname(repo, last_name)
        qcodeLastName = getLastNameQcode(qcodesLastname, last_name)
        if (qcodeFirstName == '' or qcodeLastName == ''):
            print(f"Items for names missing")
            exit(1)

        # ask verification before modifying 
        if (confirmsaving(complete_name) == True):
            addhuman(repo, complete_name, qcodeFirstName, qcodeLastName)
            #print("Properties checked for ", itemqcode)

    else:
        print("Script creates wikidata item for human by name.")  # noqa
        print("Usage: python3 create_human_item.py <lastname>, <firstname> ")  # noqa
        exit(1)


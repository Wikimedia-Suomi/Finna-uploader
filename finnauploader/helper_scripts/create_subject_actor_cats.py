# Script creates commons category for person defined by wikidata item.
#
# Usage:
# python3 create_subject_actor_cats.py <Wikidata_ID> \"<Lastname, Firstname>\"

# TODO: this needs some improvements in case there exists a category for a different person:
# could get if sitelink to commons exists and use that in property for Commons-category to remove one potential conflict
# 

import sys
import pywikibot
import re


# Create a site object for Wikidata and Wikimedia Commons
wikidata_site = pywikibot.Site('wikidata', 'wikidata')
commons_site = pywikibot.Site('commons', 'commons')


# Function to check if the Wikidata item is a human
def is_human(item):
    human_qid = 'Q5'  # QID for human
    instance_of = item.claims.get('P31', [])
    
    for claim in instance_of:
        #qid = claim.getTarget().id
        if (claim.getTarget().id == human_qid):
            return True
    return False
    #return any(claim.getTarget().id == human_qid for claim in instance_of)


def get_name_from_label(wikidata_item, lang='fi'):
    for li in wikidata_item.labels:
        label = wikidata_item.labels[li]
        if (li == lang):
            return label
    return None

# Function to create a commons category and a subcategory for photographs
def create_commons_category(name):
    # Main category
    category_name = "Category:%s" % name
    category_page = pywikibot.Page(commons_site, category_name)
    if not category_page.exists():
        category_page.text = "{{Wikidata Infobox}}\n\n"
        category_page.save("Creating new category: %s" % category_name)
    return category_name


# Function to update the list on Wikimedia Commons
def update_commons_list(name, wikidata_id):
    page_title = "User:FinnaUploadBot/data/subjectActors"
    page = pywikibot.Page(commons_site, page_title)
    target_text = f"\n* {name} : {{{{Q|{wikidata_id}}}}}"
    if target_text not in page.text:
        page.text += f"\n* {name} : {{{{Q|{wikidata_id}}}}}"
        page.save("Adding new entry for %s" % name)

# check if there is sitelink in wikidata and return it if there is
def get_commons_sitelink(wikidata_item):

    # throws exception if link does not exist yet
    #sitelink = wikidata_item.getSitelink('commonswiki')

    if 'commonswiki' in wikidata_item.sitelinks:
        commonslink = wikidata_item.sitelinks['commonswiki']
        linktitle = commonslink.canonical_title()

        if (linktitle.find("Category:") == 0):
            l = len("Category:")
            return linktitle[l:]
        return linktitle
    return None

# check if there is commons-category property in wikidata and return it if there is
def get_commonscat_property(wikidata_item):
    if 'P373' in wikidata_item.claims:
        proplist = wikidata_item.claims['P373']
    return None

# are both defined? if so, is there a mismatch?
#def compare_commons_property(wikidata_item):
#    sitelink = get_commons_sitelink(wikidata_item)
#    commonprop = get_commonscat_property(wikidata_item)
    
# Main execution
def main(wikidata_id):
    # Access the Wikidata item
    wikidata_item = pywikibot.ItemPage(wikidata_site, wikidata_id)

    if not wikidata_item.exists():
        print("Item does not exist.")
        return

    # Check if the item is a human
    if not is_human(wikidata_item):
        print("Item is not a human.")
        return

    # Get the actual name from the Wikidata item
    actual_name = get_name_from_label(wikidata_item)
    if (actual_name == None):
        # wikidata item needs fixing first
        print("There is no Finnish label in Wikidata for:", wikidata_id )
        return
        
    print(f"Actual name on Wikidata: {actual_name}")

    # should not include namespace "Category:"
    oldsitelink = get_commons_sitelink(wikidata_item)
    if (oldsitelink != None):
        print("Sitelink already in Wikidata:", oldsitelink )

    commonscatprop = get_commonscat_property(wikidata_item)
    if (commonscatprop != None):
        print("Commons properties already in Wikidata:", commonscatprop )

    if (oldsitelink != None and commonscatprop != None):
        if (oldsitelink not in commonscatprop):
            print("WARN: Commons property different from commons sitelink:", oldsitelink )

    # by default, use name from label for category
    new_catname = actual_name
    if (oldsitelink != None):
        # if there is already sitelink, use that to avoid mismatches:
        # add this to property if it isn't there yet
        new_catname = oldsitelink

    print("Using Commons category name:", new_catname)

    # Confirm from the user if they want to continue
    confirmation = pywikibot.input_choice(
        "Do you want to continue with the edits?",
        [('Yes', 'y'), ('No', 'n')],
        default='n'
    )

    if confirmation == 'n':
        print("Operation cancelled.")
        return

    # Check for Commons category (P373)
    if 'P373' not in wikidata_item.claims:
        created_category_name = create_commons_category(new_catname)
        category_claim = pywikibot.Claim(wikidata_site, 'P373')
        category_claim.setTarget(new_catname)
        wikidata_item.addClaim(category_claim)

        if (oldsitelink == None):
            new_sitelink = {'site': 'commonswiki', 'title': created_category_name}
            summary = 'Add Commons category'
            wikidata_item.setSitelink(sitelink=new_sitelink, summary=summary)

        print("Property saved")

    #return wikidata_id


if __name__ == "__main__":
    #if len(sys.argv) == 1:
        #nonPresenterAuthorsCache = parse_cache_page('User:FinnaUploadBot/data/nonPresenterAuthors') # noqa
        # no need for "reversed name" here, just use what is in the page
        #if name in nonPresenterAuthorsCache:
            #print(f"Name from list: {name}")
            #wikidata_id = nonPresenterAuthorsCache[name]
            #main(wikidata_id)
    #elif len(sys.argv) == 2:
    if len(sys.argv) == 2:
        print(f"qcode only")
        # just qcode 
        wikidata_id = sys.argv[1]
        main(wikidata_id)
        # TODO get reversed name and update to page
        #update_commons_list(expected_name, wikidata_id)
    elif len(sys.argv) == 3:
        # qcode and name -> add name to list
        wikidata_id = sys.argv[1]
        expected_name = sys.argv[2]
        print(f"Expected name from parameter: {expected_name}")
        main(wikidata_id)
        update_commons_list(expected_name, wikidata_id)
    else:
        print("Script creates commons category for person defined by wikidata item.")  # noqa
        print("Usage: python3 create_subject_actor_cats.py <Wikidata_ID> \"<Lastname, Firstname>\"")  # noqa

# Script creates categories and Creator template for Wikidata id
# and adds wikidata_id to the
# https://commons.wikimedia.org/wiki/User:FinnaUploadBot/data/subjectActors
#
# Usage:
# python3 create_photographystudio_cats.py <Wikidata_ID> \"<Name>\"

import sys
import pywikibot

# Create a site object for Wikidata and Wikimedia Commons
wikidata_site = pywikibot.Site('wikidata', 'wikidata')
commons_site = pywikibot.Site('commons', 'commons')


# Function to update the list on Wikimedia Commons
def update_commons_list(name, wikidata_id):
    page_title = "User:FinnaUploadBot/data/nonPresenterAuthors"
    page = pywikibot.Page(commons_site, page_title)
    target_text = f"\n* {name} : {{{{Q|{wikidata_id}}}}}"
    if target_text not in page.text:
        page.text += f"\n* {name} : {{{{Q|{wikidata_id}}}}}"
        page.save("Adding new entry for %s" % name)


# Function to check if the Wikidata item is a human
def is_studio(item):
    instance_of = item.claims.get('P31', [])
    qid = 'Q672070'  # QID for photography studio
    return any(claim.getTarget().id == qid for claim in instance_of)

def get_name_from_label(wikidata_item, lang='fi'):
    for li in wikidata_item.labels:
        label = wikidata_item.labels[li]
        if (li == lang):
            return label
    return None

# Function to create a creator template in Wikimedia Commons
def create_creator_template(name, wikidata_id):
    template_text = "{{Creator\n"
    template_text += "| Linkback = Creator:%s\n" % name
    template_text += "| Alternative names =\n"
    template_text += "| Wikidata = %s\n" % wikidata_id
    template_text += "| Option = {{{1|}}}\n"
    template_text += "}}"
    page = pywikibot.Page(commons_site, 'Creator:%s' % name)
    page.text = template_text
    page.save("Creating new creator template for %s" % name)


# Function to create a commons category and a subcategory for photographs
def create_commons_category(name):
    # Main category
    category_name = "Category:%s" % name
    category_page = pywikibot.Page(commons_site, category_name)
    if not category_page.exists():
        category_page.text = "{{Wikidata Infobox}}\n\n"
        category_page.text += "[[Category:Photographic studios in Finland]]"
        category_page.save("Creating new category: %s" % category_name)
    return category_name


# Function to create a commons category and a subcategory for photographs
def create_photographs_commons_category(name):
    # Subcategory for photographs
    photographs_category = "Category:Photographs by %s" % name
    photo_cat_page = pywikibot.Page(commons_site, photographs_category)
    if not photo_cat_page.exists():
        photo_cat_page.text = "[[Category:%s]]\n\n" % name
        photo_cat_page.save("Creating Photographs subcategory for %s" % name)

    return photographs_category

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

# Main execution
def main(wikidata_id, expected_name):
    # Access the Wikidata item
    wikidata_item = pywikibot.ItemPage(wikidata_site, wikidata_id)

    if not wikidata_item.exists():
        print("Item does not exist.")
        return

    # Check if the item is a studio
    if not is_studio(wikidata_item):
        print("Item is not a photostudio.")
        return

    # Get the actual name from the Wikidata item
    actual_name = get_name_from_label(wikidata_item)
    if (actual_name == None):
        # wikidata item needs fixing first
        print("There is no Finnish label in Wikidata for:", wikidata_id )
        return

    print(f"Actual name on Wikidata: {actual_name}")
    print(f"Expected name from parameter: {expected_name}")

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

    # Check for Wikimedia Creator template (P1472)
    if 'P1472' not in wikidata_item.claims:
        create_creator_template(new_catname, wikidata_id)
        creator_claim = pywikibot.Claim(wikidata_site, 'P1472')
        creator_claim.setTarget(new_catname)
        wikidata_item.addClaim(creator_claim)

        print("Property for creator template saved")

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

        print("Property for sitelink saved")

    # check to only add when new?
    #if (oldsitelink == None and commonscatprop == None):

    photo_category_name = create_photographs_commons_category(new_catname)
    print(photo_category_name)
    update_commons_list(expected_name, wikidata_id)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        page_name = 'User:FinnaUploadBot/data/nonPresenterAuthors'
        usage = "python3 create_photographystudio_cats.py <Wikidata_ID> \"<Name>\"" # noqa
        print(f'Script creates a commons category for wikidata id and adds it to the {page_name}') # noqa
        print(f'Usage: {usage}')
    else:
        wikidata_id = sys.argv[1]
        expected_name = sys.argv[2]
        main(wikidata_id, expected_name)

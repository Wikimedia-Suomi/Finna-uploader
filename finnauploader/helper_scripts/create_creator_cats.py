# Script creates categories and Creator template for Wikidata id
# and adds wikidata_id to the
# https://commons.wikimedia.org/wiki/User:FinnaUploadBot/data/subjectActors
#
# Usage:
# python3 create_subject_actor_cats.py <Wikidata_ID> \"<Lastname, Firstname>\"

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

def is_instance_of(item, qid):
    instance_of = item.claims.get('P31', [])
    for claim in instance_of:
        if (claim.getTarget().id == qid):
            return True
    return False

def has_property_of(item, prop, qid):
    instance_of = item.claims.get(prop, [])
    for claim in instance_of:
        if (claim.getTarget().id == qid):
            return True
    return False

# Function to check if the Wikidata item is a human
def is_human(item):
    return is_instance_of(item, 'Q5')  # QID for human

def is_photographer(item):
    return has_property_of(item, 'P106', 'Q33231')  # QID for photographer

def is_architect(item):
    return has_property_of(item, 'P106', 'Q42973')  # QID for architect

def is_designer(item):
    return has_property_of(item, 'P106', 'Q5322166')  # QID for designer

def is_illustrator(item):
    return has_property_of(item, 'P106', 'Q644687')  # QID for illustrator
    #'Q15296811'  # piirtäjä


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
        category_page.text += "[[Category:Photographers from Finland]]"
        category_page.save("Creating new category: %s" % category_name)
    return category_name


# Function to create a commons category and a subcategory for photographs by photographer
def create_photographs_commons_category(name):
    # Subcategory for photographs
    photographs_category = "Category:Photographs by %s" % name
    photo_cat_page = pywikibot.Page(commons_site, photographs_category)
    if not photo_cat_page.exists():
        photo_cat_page.text = "[[Category:%s]]\n\n" % name
        photo_cat_page.text += "[[Category:Photographs by photographer from Finland]]" # noqa
        photo_cat_page.save("Creating Photographs subcategory for %s" % name)

    return photographs_category

# Function to create a commons category and a subcategory for buildings by architect
def create_buildings_commons_category(name):
    # Subcategory for photographs
    buildings_category = "Category:Buildings by %s" % name
    buildings_cat_page = pywikibot.Page(commons_site, buildings_category)
    if not buildings_cat_page.exists():
        buildings_cat_page.text = "[[Category:%s]]\n\n" % name
        # Buildings by architect (flat list)
        # Works by <architect>
        #photo_cat_page.text += "[[Category: <>]]" # noqa
        buildings_cat_page.save("Creating Buildings subcategory for %s" % name)

    return buildings_category

# Function to create a commons category and a subcategory for works by designer
# note: artist/designer works might not be free to upload..
# check date of death?
def create_works_commons_category(name):
    # Subcategory for photographs
    works_category = "Category:Works by %s" % name
    works_cat_page = pywikibot.Page(commons_site, works_category)
    if not works_cat_page.exists():
        works_cat_page.text = "[[Category:%s]]\n\n" % name
        # works by designer
        # Works by <architect>
        # Works by <illustrator> ?
        #photo_cat_page.text += "[[Category: <>]]" # noqa
        works_cat_page.save("Creating Works subcategory for %s" % name)

    return works_category

# Main execution
def main(wikidata_id, expected_name):
    # Access the Wikidata item
    wikidata_item = pywikibot.ItemPage(wikidata_site, wikidata_id)

    if not wikidata_item.exists():
        print("Item does not exist.")
        return

    if 'fi' not in wikidata_item.labels:
        print("Item label does not exist.")
        return

    # Check if the item is a human
    if not is_human(wikidata_item):
        print("Item is not a human.")
        return

    # Get the actual name from the Wikidata item
    actual_name = wikidata_item.labels.get('fi', '[No label]')
    print(f"Actual name on Wikidata: {actual_name}")
    print(f"Expected name from parameter: {expected_name}")

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
        name = wikidata_item.labels['fi']
        create_creator_template(name, wikidata_id)
        creator_claim = pywikibot.Claim(wikidata_site, 'P1472')
        creator_claim.setTarget(name)
        wikidata_item.addClaim(creator_claim)

    # Check for Commons category (P373)
    if 'P373' not in wikidata_item.claims:
        name = wikidata_item.labels['fi']
        category_name = create_commons_category(name)
        category_claim = pywikibot.Claim(wikidata_site, 'P373')
        category_claim.setTarget(name)
        wikidata_item.addClaim(category_claim)

        sitelink = {'site': 'commonswiki', 'title': category_name}
        summary = 'Add Commons category'
        wikidata_item.setSitelink(sitelink=sitelink, summary=summary)

    name = wikidata_item.labels['fi']
    
    # TODO: if creator is not photographer, don't create photography category:
    # if creator is architect, use create_buildings_commons_category()
    # check property P106 for appropriate category?
    #
    #if is_photographer(wikidata_item):
    photo_category_name = create_photographs_commons_category(name)
    print(photo_category_name)
    
    #if is_architect(wikidata_item):
        #building_category_name = create_buildings_commons_category(name)
        #print(building_category_name)
    
    # note: artist/designer works might not be free to upload..
    # check date of death?
    #if is_designer(wikidata_item) or is_illustrator(wikidata_item)
    #works_category_name = create_works_commons_category(name)
    #print(works_category_name)
    
    update_commons_list(expected_name, wikidata_id)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        page_name = 'User:FinnaUploadBot/data/nonPresenterAuthors'
        usage = "python3 create_subject_actor_cats.py <Wikidata_ID> \"<Lastname, Firstname>\"" # noqa
        print(f'Script creates a commons category for wikidata id and adds it to the {page_name}') # noqa
        print(f'Usage: {usage}')
    else:
        wikidata_id = sys.argv[1]
        expected_name = sys.argv[2]
        main(wikidata_id, expected_name)

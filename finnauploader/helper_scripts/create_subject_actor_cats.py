# Script creates commons category for person defined by wikidata item.
#
# Usage:
# python3 create_subject_actor_cats.py <Wikidata_ID> \"<Lastname, Firstname>\"

import sys
import pywikibot


# Create a site object for Wikidata and Wikimedia Commons
wikidata_site = pywikibot.Site('wikidata', 'wikidata')
commons_site = pywikibot.Site('commons', 'commons')


# Function to check if the Wikidata item is a human
def is_human(item):
    instance_of = item.claims.get('P31', [])
    human_qid = 'Q5'  # QID for human
    return any(claim.getTarget().id == human_qid for claim in instance_of)


# Function to create a commons category and a subcategory for photographs
def create_commons_category(name):
    # Main category
    category_name = "Category:%s" % name
    category_page = pywikibot.Page(commons_site, category_name)
    category_page.text = '{{Wikidata Infobox}}'
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


# Main execution
def main(wikidata_id, expected_name):
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

    update_commons_list(expected_name, wikidata_id)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Script creates commons category for person defined by wikidata item.")  # noqa
        print("Usage: python3 create_subject_actor_cats.py <Wikidata_ID> \"<Lastname, Firstname>\"")  # noqa
    else:
        wikidata_id = sys.argv[1]
        expected_name = sys.argv[2]
        main(wikidata_id, expected_name)

import mwparserfromhell
from images.wikitext.creator import get_creator_image_category_from_wikidata_id

def create_categories(r):
    # Create a new WikiCode object
    wikicode = mwparserfromhell.parse("")
        
    # Create the categories
    categories = set()
    
    creator_category=get_creator_image_category_from_wikidata_id(r['creator_wikidata_id'])
    creator_category=creator_category.replace('Category:', '')
    categories.add(creator_category)

    subject_categories = {
        'muotokuvat':'Portrait photographs',
        'henkilökuvat':'Portrait photographs',
        'professorit':'Professors from Finland',
        'miesten puvut':'Men wearing suits in Finland'
    }
      
    for subject_category in subject_categories.keys():
        if subject_category in str(r['subjects']):
            categories.add(subject_categories[subject_category])
      
    if 'year' in r:     
        if 'Category:Portrait photographs' in categories:
            categories.add('People of Finland in ' + r['year'])
        else:
            categories.add(r['year'] + ' in Finland')
   
    categories.add('Files uploaded by FinnaUploadBot')
    
    for category in categories:
        # Create the Wikilink
        wikilink = mwparserfromhell.nodes.Wikilink(title='Category:' + category)
       
        # Add the Wikilink to the WikiCode object
        wikicode.append(wikilink)

    flatten_wikicode=str(wikicode).replace('[[Category:', '\n[[Category:')
      
    # return the wikitext
    return flatten_wikicode

import mwparserfromhell
from images.wikitext.timestamps import parse_timestamp_string

def language_template_wrap(lang, text):
    if text:
        return '{{' + lang + '|' + text + '}}'
    else:
        return ''

def create_photographer_template(r):
    # Create a new WikiCode object
    wikicode = mwparserfromhell.parse("")
      
    # Create the template
    template = mwparserfromhell.nodes.Template(name='Photograph')
   
    # Add the parameters to the template
    template.add('photographer', r['creator_template'])
    template.add('title', '\n'.join(r['template_titles']))
    template.add('description', language_template_wrap('fi', '\n'.join(r['template_descriptions'])))
    template.add('depicted people', language_template_wrap('fi', r['subjectActors']))
    template.add('depicted place', language_template_wrap('fi', r['subjectPlaces']))
    template.add('date', parse_timestamp_string(r['date']))
    template.add('medium', '')
    template.add('dimensions', "\n".join(r['measurements']))
    template.add('institution', r['institution_template'])
    template.add('department', language_template_wrap('fi', "; ".join(r['collections'])))
    template.add('references', '')
    template.add('object history', '')
    template.add('exhibition history', '')
    template.add('credit line', '')
    template.add('inscriptions', '')
    template.add('notes', '')
    template.add('accession number', r['identifierString'])
    template.add('source', r['source'])
    template.add('permission',  language_template_wrap('fi', "\n".join([r['copyright'], r['copyright_description']])))
    template.add('other_versions', '')
    template.add('wikidata', '')
    template.add('camera coord', '')
     
    # Add the template to the WikiCode object
    wikicode.append(template)
    flatten_wikitext=str(wikicode)
            
    # Add newlines before parameter name
    params = ['photographer', 'title', 'description', 'depicted people', 'depicted place', 'date', 'medium', 'dimensions',
              'institution', 'department', 'references', 'object history', 'exhibition history', 'credit line', 'inscriptions',
              'notes', 'accession number', 'source', 'permission', 'other_versions', 'wikidata', 'camera coord']
            
    for param in params:
        flatten_wikitext=flatten_wikitext.replace('|' + param +'=', '\n|' +param +' = ')
   
    # return the wikitext
    return flatten_wikitext

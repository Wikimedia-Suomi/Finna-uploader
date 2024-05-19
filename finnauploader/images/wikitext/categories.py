import mwparserfromhell


def create_categories_new(finna_image):
    subject_places = finna_image.subject_places.values_list('name', flat=True)
    depicted_places = str(list(subject_places))

    # Create a new WikiCode object
    wikicode = mwparserfromhell.parse("")

    # Create the categories
    categories = set()

    for subject_actor in finna_image.subject_actors.all():
        category = subject_actor.get_commons_category()
        categories.add(category)

    authors = finna_image.non_presenter_authors.filter(role='kuvaaja')
    for author in authors:
        category = author.get_photos_category()
        categories.add(category)

    subject_categories = {
        'muotokuvat': 'Portrait photographs',
        'henkilökuvat': 'Portrait photographs',
        'professorit': 'Professors from Finland',
        'Osuusliike Elanto': 'Elanto',
        'Valmet Oy': 'Valmet',
        'Salora Oy': 'Salora',
        'Veljekset Åström Oy': 'Veljekset Åström'
    }

    for subject in finna_image.subjects.all():
        if subject.name in subject_categories:
            category = subject_categories[subject.name]
            categories.add(category)

        # needs more detailed reasoning for categories:
        # if image location is not from Finland, don't categorize under Finland..
        if subject.name == 'miesten puvut' and 'Suomi' in depicted_places:
            categories.add('Men wearing suits in Finland')

    for add_category in finna_image.add_categories.all():
        category_name = add_category.get_category_name()
        if category_name:
            categories.add(category_name)

    if finna_image.year:
        if 'Portrait photographs' in categories:
            categories.add(f'People of Finland in {finna_image.year}')

        if 'Helsinki' in depicted_places:
            categories.add(f'{finna_image.year} in Helsinki')
        elif 'Suomi' in depicted_places:
            categories.add(f'{finna_image.year} in Finland')

    categories.add('Files uploaded by FinnaUploadBot')

    for category in categories:
        # Create the Wikilink
        category_title = 'Category:' + category
        wikilink = mwparserfromhell.nodes.Wikilink(title=category_title)

        # Add the Wikilink to the WikiCode object
        wikicode.append(wikilink)

    flatten_wikicode = str(wikicode).replace('[[Category:', '\n[[Category:')

    # return the wikitext
    return flatten_wikicode

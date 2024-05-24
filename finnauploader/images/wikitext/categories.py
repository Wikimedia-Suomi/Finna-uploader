import mwparserfromhell

def get_category_place(subject_places, depicted_places):
    print("DEBUG: get_category_place, subject places: ", str(subject_places) )
    print("DEBUG: get_category_place, depicted places: ", str(depicted_places) )

    # may start with comma and space -> clean it
    if (depicted_places.startswith(",")):
        depicted_places = depicted_places[1:]
        depicted_places = depicted_places.lstrip()
    
    cat_place = {
        "Helsinki","Hamina","Hyvinkää","Hämeenlinna","Espoo","Forssa","Iisalmi","Imatra","Inari","Joensuu","Jyväskylä","Lahti","Lappajärvi","Lappeenranta","Loviisa","Kajaani","Kemi","Kokkola","Kotka","Kuopio","Kuusamo","Kouvola","Mikkeli","Naantali","Pietarsaari","Porvoo","Pori","Oulu","Raahe","Rauma","Rovaniemi","Savonlinna","Seinäjoki","Sipoo","Sotkamo","Turku","Tampere","Tornio","Uusikaupunki","Vantaa","Vaasa"
    }
    for p in cat_place:
        if p in depicted_places:
            return p
        # may need combination location (country, subdivision etc)
        tmp = "Suomi, " + p
        if (tmp in depicted_places):
            return p
        
    if 'Suomi' in depicted_places:
        return "Finland"
    return ""

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

    # Ssteamboats: non ocean-going
    # Steamships of Finland
    # Naval ships of Finland
    # Sailing ships of Finland
    subject_categories = {
        'muotokuvat': 'Portrait photographs',
        'henkilökuvat': 'Portrait photographs',
        'saamenpuvut' : 'Sami clothing',
        'Osuusliike Elanto': 'Elanto',
        'Valmet Oy': 'Valmet',
        'Salora Oy': 'Salora',
        'Veljekset Åström Oy': 'Veljekset Åström',
        'Yntyneet Paperitehtaat': 'Yntyneet Paperitehtaat',
        'Turun linna' : 'Turku Castle',
        'Hämeen linna' : 'Häme Castle',
        'Olavinlinna' : 'Olavinlinna',
        'Hvitträsk': 'Hvitträsk',
        'kiväärit' : 'Rifles'
    }
    
    # must have place 'Suomi' to generate ' in Finland'
    #
    # note: there are also "from" and "of" categories in Commons, 
    # can we guess the right one automatically?
    # aircraft may be "in" city or "at" airport..
    subject_categories_with_country = {
        'professorit': 'Professors from',
        'kauppaneuvokset' : 'Businesspeople from',
        'toimitusjohtajat' : 'Businesspeople from',
        'miesten puvut': 'Men wearing suits in',
        'muotinäytökset' : 'Fashion shows in',
        'lentonäytökset': 'Air shows in',
        'veturit' : 'Locomotives of',
        'junat' : 'Trains of',
        'laivat' : 'Ships in',
        'veneet' : 'Boats in',
        'matkustajalaivat' : 'Passenger ships in',
        'purjeveneet' : 'Sailboats in',
        'moottoriveneet' : 'Motorboats in',
        'lossit' : 'Cable ferries in',
        'lentokoneet' : 'Aircraft in',
        'linja-autot': 'Buses in',
        'kuorma-autot' : 'Trucks in',
        'henkilöautot' : 'Automobiles in',
        'autokilpailut' : 'Automobile races in',
        'auto-onnettomuudet' : 'Automobile accidents in',
        'hotellit' : 'Hotels in',
        'asuinrakennukset' : 'Houses in',
        'liikerakennukset' : 'Buildings in',
        'osuusliikkeet' : 'Consumers\' cooperatives in',
        'nosturit' : 'Cranes in',
        'kaivinkoneet' : 'Excavators in',
        'tehtaat' : 'Factories in',
        'teollisuusrakennukset' : 'Factories in',
        'konepajateollisuus' : 'Machinery industry in',
        'laulujuhlat' : 'Music festivals in',
        'rukit' : 'Spinning wheels in',
        'meijerit' : 'Dairies in',
        'mainoskuvat' : 'Advertisements in'
    }
    
    cat_place = get_category_place(subject_places, depicted_places)

    for subject in finna_image.subjects.all():
        if subject.name in subject_categories:
            category = subject_categories[subject.name]
            categories.add(category)

        if subject.name in subject_categories_with_country and 'Suomi' in depicted_places:
            category = subject_categories_with_country[subject.name] + " " + "Finland"
            categories.add(category)

        if (subject.name == 'kartanot' and 'Louhisaari' in depicted_places):
            categories.add('Louhisaari Manor')
    
    for add_category in finna_image.add_categories.all():
        category_name = add_category.get_category_name()
        if category_name:
            categories.add(category_name)

    if finna_image.year:
        if 'Portrait photographs' in categories and 'Suomi' in depicted_places:
            categories.add(f'People of Finland in {finna_image.year}')

        if (len(cat_place) > 0):
            categories.add(f'{finna_image.year} in {cat_place}')
    else:
        # if we can't determine year, use only location name
        # and only if it something other than country (at least a city)
        if (len(cat_place) > 0 and (cat_place != 'Suomi' and cat_place != 'Finland')):
            categories.add(cat_place)

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

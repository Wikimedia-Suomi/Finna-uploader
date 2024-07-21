import mwparserfromhell

from images.wikitext.wikidata_helpers import get_subject_image_category_from_wikidata_id, \
                                    get_creator_nane_by_wikidata_id


def get_category_by_wikidata_id(wikidata_id):
    if not wikidata_id:
        return None
    
    category = get_subject_image_category_from_wikidata_id(wikidata_id)
    if category:
        # this is error in the data if someone has added this way (unlikely, but check it anyway)
        if (category.find("Category:") >= 0):
            category = category.replace('Category:', '')
        return category
    return None


def get_photography_category_by_photographer_id(wikidata_id):
    if not wikidata_id:
        print('DEBUG: no wikidata id, unable to find photographer category')
        return None

    creatorName = get_subject_image_category_from_wikidata_id(wikidata_id)
    if (creatorName != None):
        print('DEBUG: creator name ', creatorName ,' for wikidata id: ', wikidata_id)
        
        if (creatorName.startswith("Photographs by") == True):
            category = creatorName
        else:
            category = "Photographs by " + creatorName

        #if (isCategoryExistingInCommons(category)):
            #return category
        print('DEBUG: using photography category', category)
        return category
        
    return None


# if picture is categorized under architecture
# and authors includes person with role "arkkitehti"
# categorize under "buildings by <architect>"
# subject should include "rakennukset"
def get_building_category_by_architect_id(wikidata_id):
    if not wikidata_id:
        print('DEBUG: no wikidata id, unable to find architect category')
        return None
    
    creatorName = get_subject_image_category_from_wikidata_id(wikidata_id)
    if (creatorName != None):
        print('DEBUG: creator name ', creatorName ,' for wikidata id: ', wikidata_id)

        if 'Buildings by' in creatorName:
            category = creatorName
        else:
            category = "Buildings by " + creatorName

        #if (isCategoryExistingInCommons(category)):
            #return category
        print('DEBUG: using photography category', category)
        return category

    return None


def get_subject_category(finna_subject):
    value = finna_subject.value.replace('category:', 'Category:')

    if 'https://commons.wikimedia.org/wiki/Category:' in value:
        return value.replace('https://commons.wikimedia.org/wiki/Category:', '')

    if 'http://commons.wikimedia.org/wiki/category:' in value:
        return value.replace('http://commons.wikimedia.org/wiki/Category:', '')

    if '^Category:' in value:
        return value.replace('Category:', '')

    wikidata_id = finna_subject.get_wikidata_id()
    return get_category_by_wikidata_id(wikidata_id)


def get_category_for_building(subject_name, depicted_places):
    
    manor_categories_by_location = {
        'Louhisaari' : 'Louhisaari Manor',
        'Piikkiö' : 'Pukkila Manor',
        'Kuusisto' : 'Kuusisto Manor',
        'Knuutila' : 'Knuutila Manor'
    }
    
    categories = set()

    #if (subject.name == 'kartanot' and 'Vesilahti' in depicted_places):
        #categories.add('Laukko Manor')
    if (subject_name == "Laukon kartano"):
        categories.add('Laukko Manor')

    # not in subjects like usual
    if ('Lamminahon talo' in depicted_places):
        categories.add('Lamminaho House')

    #Vuojoen kartano : Vuojoki Manor

    return categories


# for place names, we want full exact match, not partial:
# "Kotkaniemi" is not same as "Kotka"
def is_entry_in_list(name : str, subject_places : list):
    for p in subject_places:
        if (p == name):
            return True
        #elif (name == "Suomi, " + p):
            #return True
    return False


def get_category_place(subject_places):
    print("DEBUG: get_category_place, subject places: ", str(subject_places) )
    #print("DEBUG: get_category_place, depicted places: ", str(depicted_places) )

    if ('Helsingin maalaiskunta' in subject_places):
        return "Vantaa"
    if ('Espoon maalaiskunta' in subject_places):
        return "Espoo"

    # for now, use hack to translate into category
    if ('Nokia' in subject_places):
        return "Nokia, Finland"
    if ('Maarianhamina' in subject_places):
        return "Mariehamn"
    if ('Raasepori' in subject_places):
        #return "Raseborg"
        return "Raasepori"
    if ('Viipuri' in subject_places):
        return "Vyborg"
    #if ('Helsingin maalaiskunta' in subject_places):
        #return "Vantaa"
    if ('Pietarsaari' in subject_places):
        return "Jakobstad"
    if ('Tammisaari' in subject_places):
        return "Ekenäs"
    if ('Jääski' in subject_places):
        return "Lesogorsky"
    if ('Sortavala' in subject_places):
        return "Sortavala"
    if ('Petsamo'  in subject_places):
        return "Petsamo"

    cat_place = {
        "Helsinki","Hanko","Hamina","Heinola","Hyvinkää","Hämeenlinna","Espoo","Forssa","Iisalmi","Imatra","Inari","Joensuu","Joutseno","Juupajoki","Jyväskylä","Jämsä","Kaarina","Karkkila","Kajaani","Kauhajoki","Kerava","Kemi","Kitee","Kokkola","Kotka","Kuopio","Kuusamo","Kouvola","Lahti","Lappajärvi","Lappeenranta","Lohja","Loviisa","Mikkeli","Muhos","Naantali","Padasjoki","Perniö","Porvoo","Pori","Pornainen","Oulu","Raahe","Raisio","Rauma","Rovaniemi","Salo","Savonlinna","Seinäjoki","Siilinjärvi","Sipoo","Sotkamo","Turku","Tammela","Tampere","Tornio","Uusikaupunki","Vantaa","Vaasa","Vihti","Virolahti","Virrat"
    }
    for p in cat_place:
        # we want exact match: not partial name
        if (is_entry_in_list(p, subject_places) == True):
            return p
        # may need combination location (country, subdivision etc)
        #tmp = "Suomi, " + p
        #if (is_entry_in_list(tmp, subject_places) == True):
            #return p
    return ""


def get_category_for_subject_in_country(subject_name):
    
    # must have place 'Suomi' to generate ' in Finland'
    #
    # note: there are also "from" and "of" categories in Commons, 
    # can we guess the right one automatically?
    # aircraft may be "in" city or "at" airport..
    subject_categories_with_country = {
        'professorit': 'Professors from',
        'kauppaneuvokset' : 'Businesspeople from',
        'toimitusjohtajat' : 'Businesspeople from',
        'miehet' : 'Men of',
        'naiset' : 'Women of',
        'perheet' : 'Families of',
        'miesten puvut': 'Men wearing suits in',
        #'naisten puvut': 'Women wearing suits in',
        'univormut' : 'Uniforms of',
        #'kansallispuvut' : 'Traditional clothing of',
        'kengät' : 'Shoes of',
        'muotinäytökset' : 'Fashion shows in',
        'kampaukset' : 'Hair fashion in',
        'kampaamot' : 'Hair dressing shops in',
        'parturit' : 'Barber shops in',
        #'parturi-kampaamot' : 'Barber shops in',
        #'parturi-kampaamot' : 'Hair dressing shops in',
        'raitiovaunut' : 'Trams in',
        'veturit' : 'Locomotives of',
        'junat' : 'Trains of',
        'junanvaunut' : 'Railway coaches of',
        'rautatieasemat' : 'Train stations in',
        #'merimiesvaatteet' : '',
        'telakat' : 'Shipyards in',
        'laivat' : 'Ships in',
        'rahtilaivat' : 'Cargo ships in',
        'sotalaivat' : 'Naval ships in',
        'sota-alukset' : 'Naval ships in',
        'sukellusveneet' : 'Submarines in',
        #'panssarilaivat'
        'veneet' : 'Boats in',
        'jäänmurtajat' : 'Ice breakers in',
        'matkustajalaivat' : 'Passenger ships in',
        'purjeveneet' : 'Sailboats in',
        #'purjelaivat' : 'Sailing ships'
        'moottoriveneet' : 'Motorboats in',
        'lossit' : 'Cable ferries in',
        'traktorit' : 'Tractors in',
        'lentonäytökset': 'Air shows in',
        'lentokoneet' : 'Aircraft in',
        'helikopterit' : 'Helicopters in',
        'purjelento' : 'Gliding in',
        'mopot' : 'Mopeds in',
        'moottoripyörät' : 'Motorcycles in',
        'moottoripyöräurheilu' : 'Motorcycle racing in',
        'moottoriurheilu' : 'Motorsports in',
        'linja-autot': 'Buses in',
        'kuorma-autot' : 'Trucks in',
        'autot' : 'Automobiles in',
        'henkilöautot' : 'Automobiles in',
        'autourheilu' : 'Automobile racing in',
        'autokilpailut' : 'Automobile races in',
        'auto-onnettomuudet' : 'Automobile accidents in',
        'liikenneonnettomuudet' : 'Road accidents in',
        'taksit' : 'Taxis in',
        'taksiasemat' : 'Taxi stands in',
        'hotellit' : 'Hotels in',
        'kodit' : 'Accommodation buildings in',
        'asuinrakennukset' : 'Houses in',
        'liikerakennukset' : 'Buildings in',
        'kioskit' : 'Kiosks in',
        'virastotalot' : 'Government buildings in',
        'toimistorakennukset' : 'Office buildings in',
        'kerrostalot' : 'Apartment buildings in',
        'osuusliikkeet' : 'Consumers\' cooperatives in',
        'saunat' : 'Sauna buildings in',
        'alastomuus' : 'Nudity in',
        'nosturit' : 'Cranes in',
        'kaivinkoneet' : 'Excavators in',
        'tehtaat' : 'Factories in',
        'teollisuusrakennukset' : 'Factories in',
        'konepajateollisuus' : 'Machinery industry in',
        'paperiteollisuus' : 'Pulp and paper industry in',
        'sahateollisuus' : 'Sawmills in',
        'metsänhoito' : 'Forestry in',
        'aitta' : 'Granaries in',
        'aitat' : 'Granaries in',
        #'lato' : 'Barns in',
        #'ladot' : 'Barns in',
        'koulurakennukset' : 'School buildings in',
        'koululaiset' : 'School children of',
        'koulutus' : 'Education in',
        'opetus' : 'Teaching in',
        'opettajat' : 'Teachers from',
        'ammatit opettajat' : 'Teachers from',
        'sairaalat' : 'Hospitals in',
        'sairaanhoitajat' : 'Nurses from',
        'lääkärit' : 'Physicians from',
        'museot' : 'Museums in',
        'kirjat' : 'Books of',
        'kirjapainot' : 'Printing in',
        'kirjapainotekniikka' : 'Printing equipment in',
        #'kirjapainotyöntekijät'
        #'kirjapainajat'
        'kirjastorakennukset' : 'Libraries in',
        #'kirjastoautot': 'Bookmobiles in',
        'rakennushankkeet' : 'Construction in',
        'rakennustarvikkeet' : 'Construction equipment in',
        #'työvälineet'
        'sepät' : 'Blacksmiths from',
        'puutyöt' : 'Woodworking in',
        'puusepänteollisuus' : 'Carpentry in',
        'ompelukone' : 'Sewing machines in',
        'sängyt' : 'Beds in',
        'parisängyt' : 'Beds in',
        'pyykinpesu' : 'Laundry in‎',
        #'pyykinpesuvälineet' : '',
        'pesukoneet' : 'Washing machines in',
        'mankelit' : 'Mangles in',
        'huonekalut' : 'Furniture in',
        'sohvat' : 'Couches in',
        'tuolit' : 'Chairs in',
        'jääkaapit' : 'Refrigerators in‎',
        'sisustus' : 'Interior decoration in',
        'interiöörit' : 'Building interiors in',
        'sisätilat' : 'Building interiors in',
        #'asunnot'
        #'muusikot' : 'Musicians from', # who is playing?
        #'orkesterit' : 'Orchestras from', # who is playing?
        #'yhtyeet' : 'Musical groups from', # who is playing?
        #'piano'
        'laulujuhlat' : 'Music festivals in',
        'festivaalit' : 'Music festivals in',
        'neulonta' : 'Knitting in',
        'virkkaus' : 'Crochet in',
        'työvaatteet' : 'Work clothing in',
        'työkalut' : 'Tools in',
        'kirveet' : 'Axes of',
        'alasimet' : 'Anvils in',
        'rukit' : 'Spinning wheels in',
        'kehruu' : 'Spinning in',
        'kutojat' : 'Weavers in',
        'kudonta' : 'Weaving in',
        'kutominen' : 'Weaving in',
        #kudinpuut 
        'kangaspuut' : 'Looms in',
        'räsymatot' : 'Rugs and carpets of',
        'nuket' : 'Dolls in',
        'leikkikalut' : 'Toys in',
        'meijerit' : 'Dairies in',
        'elintarvikeliikkeet' : 'Grocery stores in',
        'elokuvateatterit' : 'Cinemas in',
        'myymälät' : 'Shops in',
        'ravintolat' : 'Restaurants in',
        'kahvilat' : 'Coffee shops in',
        'konditoriat' : 'Konditoreien in',
        'leipomoteollisuus' : 'Bread industry in',
        #'leipomotuotteet' : '',
        #'leipomotyöntekijät' : '',
        'leipominen' : 'Baking in',
        'leivinuunit' : 'Baking ovens in',
        'musiikkiliikkeet' : 'Music stores in',
        #'laulajat' : 'Vocalists from',
        'vaateliikkeet' : 'Clothing shops in',
        'mainoskuvat' : 'Advertisements in',
        'näyteikkunat' : 'Shop windows in',
        'koira' : 'Dogs of',
        'koiranäyttelyt' : 'Dog shows in',
        'hevosajoneuvot' : 'Horse-drawn vehicles in',
        'ravit' : 'Harness racing in',
        'raviurheilu' : 'Harness racing in',
        'polkupyörät' : 'Bicycles in',
        'aikakauslehdet' : 'Magazines of',
        # sanomalehtipaperi
        'sanomalehdet' : 'Newspapers of',
        'ammattikoulutus' : 'Vocational schools in',
        'salmet' : 'Straits of',
        'uimarannat' : 'Beaches of',
        'uimapuvut' : 'Swimwear in',
        'kylvö' : 'Agriculture in',
        'peltoviljely' : 'Agriculture in',
        'maanviljely' : 'Agriculture in',
        'maatalous' : 'Agriculture in',
        'tukinuitto' : 'Timber floating in',
        'uitto' : 'Timber floating in',
        'uittorännit' : 'Timber floating in',
        'kalastus' : 'Fishing in',
        'pilkintä' : 'Ice fishing in',
        'kalanviljely' : 'Fish farming in',
        'kalanviljelylaitokset' : 'Fish farming in',
        'luonnonmaisema' : 'Landscapes of',
        #'maisemavalokuvaus' : '',
        # retkeilyalueet, retkeilyvarusteet
        'retkeily' : 'Camping in',
        'keittiöt' : 'Kitchens in',
        'ruoanvalmistus' : 'Cooking in',
        'kylpyhuoneet' : 'Bathrooms in',
        'näyttelyt' : 'Exhibitions in',
        'messut' : 'Trade fairs in',
        'messut (tapahtumat)' : 'Trade fairs in',
        'pikaluistelu' : 'Speed skating in',
        'talviurheilulajit' : 'Winter sports in',
        'talviurheilu' : 'Winter sports in',
        'kilpaurheilu' : 'Sports competitions in',
        'autokorjaamot' : 'Automobile repair shops in',
        'huoltamot' : 'Petrol stations in',
        'huoltoasemat' : 'Petrol stations in',
        'paloautot' : 'Fire engines of',
        'takka' : 'Fireplaces in',
        'takat' : 'Fireplaces in',
        'kattaukset' : 'Table settings in',
        'pöydät' : 'Tables in',
        'äitienpäivä' : 'Mother\'s Day in',
        'häät' : 'Marriage in',
        'hääkuvat' : 'Marriage in',
        'hääpuvut' : 'Wedding clothes in',
        'hautajaiset' : 'Funerals in'
        #'maaottelut' : ''
        #'turkikset'
    }

    # in some cases they are in upper case..
    subject_name = subject_name.lower()

    if (subject_name in subject_categories_with_country):
        category = subject_categories_with_country[subject_name] + " " + "Finland"
        return category
    return None


# filter some possible errors in names:
# extra spaces, commas etc.
def places_cleaner(finna_image):
    places = list()
    subject_places = finna_image.subject_places.values_list('name', flat=True)
    print("DEBUG: input places: ", str(subject_places) )

    for p in subject_places:
        
        # if it is plain comma -> skip
        if (p == ","):
            continue
        
        # if it only begins with a comma -> strip it
        if (p.startswith(",")):
            p = p[1:]
        
        # remove leading/trailing whitespaces if any
        p = p.lstrip()
        p = p.rstrip()

        # if it is comma-separate location -> split into components
        if (p.find(",") > 0):
            tmp = p.split(",")
            for t in tmp:
                #print("DEBUG: t in places: ", str(t) )
                
                # if it only begins with a comma -> strip it
                if (t.startswith(",")):
                    t = t[1:]
                    
                # remove leading/trailing whitespaces if any
                t = t.lstrip()
                t = t.rstrip()

                # avoid duplicates
                if (t not in places):
                    places.append(t)
        else:
            if (p not in places):
                places.append(p)

    print("DEBUG: output places: ", str(places) )
    return places


def create_categories_new(finna_image):
    subject_names = finna_image.subjects.values_list('name', flat=True)
    subject_places = places_cleaner(finna_image) # clean some issues in data
    depicted_places = str(list(subject_places))

    # pre-parsed wikidata ids from subject_place string
    best_wikidata_locations = finna_image.best_wikidata_location

    # may start with comma and space -> clean it
    if (depicted_places.startswith(",")):
        depicted_places = depicted_places[1:]
    depicted_places = depicted_places.lstrip()

    # Create a new WikiCode object
    wikicode = mwparserfromhell.parse("")

    # Create the categories
    categories = set()

    for subject_actor in finna_image.subject_actors.all():
        wikidata_id = subject_actor.get_wikidata_id()
        category = get_category_by_wikidata_id(wikidata_id)
        if category:
            categories.add(category)

    authors = finna_image.non_presenter_authors.all()
    for author in authors:
        if (author.is_photographer()):
            # "photographs by" category under photographer
            wikidata_id = author.get_wikidata_id()
            category = get_photography_category_by_photographer_id(wikidata_id)
            if (category != None):
                categories.add(category)

        if (author.is_architect()):
            # is image about a building?
            if (finna_image.is_entry_in_subjects("rakennukset") or finna_image.is_entry_in_subjects("kirkkorakennukset")):
                # "buildings by" category under architect
                wikidata_id = author.get_wikidata_id()
                category = get_building_category_by_architect_id(wikidata_id)
                if (category != None):
                    categories.add(category)
            

    # Ssteamboats: non ocean-going
    # Steamships of Finland
    # Naval ships of Finland
    # Sailing ships of Finland
    subject_categories = {
        'muotokuvat': 'Portrait photographs',
        'henkilökuvat': 'Portrait photographs',
        'henkilövalokuvaus': 'Portrait photographs',
        'ryhmäkuvat' : 'Group photographs',
        'saamenpuvut' : 'Sami clothing',
        'Osuusliike Elanto': 'Elanto',
        'Valmet Oy': 'Valmet',
        'Salora Oy': 'Salora',
        'Veljekset Åström Oy': 'Veljekset Åström',
        'Yntyneet Paperitehtaat': 'Yntyneet Paperitehtaat',
        'Turun linna' : 'Turku Castle',
        'Hämeen linna' : 'Häme Castle',
        'Olavinlinna' : 'Olavinlinna',
        'Raaseporin linna' : 'Raseborg castle',
        'Hvitträsk': 'Hvitträsk',
        'Lamminahon talo' : 'Lamminaho House',
        'taksinkuljettajat' : 'Taxi drivers',
        'kronometrit' : 'Chronometers',
        'kahvimyllyt' : 'Coffee grinders',
        'keinuhevoset' : 'Rocking horses',
        #'mikroskoopit' : 'Microscopes'
        #'aseet' : 'weapons'
        #'ampuma-aseet' : 'Firearms',
        #'käsiaseet' : 'Handguns'
        #'kiväärit' : 'Rifles'
        'pistoolit' : 'Pistols',
        #'revolverit' : 'Revolvers'
        'panssarivaunut' : 'Tanks'
    }
    
    # categories by type of photograph (portrait, nature..)
    # luontokuvat
    
    
    # iron works
    # metal industry
    # Metalworkers

    # categories from 
    for best_wikidata_location in best_wikidata_locations.all():
        wikidata_id = best_wikidata_location.uri.replace('http://www.wikidata.org/entity/', '')
        print(f'FOOBAR {wikidata_id}')
        category_name = get_category_by_wikidata_id(wikidata_id)
        if category_name:
            categories.add(category_name)

    # lentokentät ja satamat ?
    # aircraft at ...
    # Sailing ships in port of ...

    isInFinland = False
    cat_place = get_category_place(subject_places)
    if (len(cat_place) == 0):
        # TODO: try to cache the lookups
        # if we didn't have fast recognizing, try slow one
        #for place in reversed(subject_places):
            #location_id = get_location_by_name(place)
            #if (location_id != None):
        
        # fallback, if all else fails, at least try to detect counry
        if (depicted_places.find('Suomi') >= 0):
            cat_place = "Finland"
            isInFinland = True
            print("Place recognized as Finland, no further")
        #if 'Suomen entinen kunta/pitäjä' in depicted_places:
            #cat_place = "Finland"
    else:
        # for now, we recognize mostly places in finland..
        # these places that we recognize are no longer part of finland, if not one of them -> assume in finland
        if ('Viipuri' not in depicted_places and 'Petsamo' not in depicted_places and 'Sortavala' not in depicted_places and 'Jääski' not in depicted_places):
            isInFinland = True

    # not in subjects like usual
    if ('Lamminahon talo' in subject_places):
        categories.add('Lamminaho House')

    # Luumäki; Kotkaniemi
    if ('Kotkaniemi' in subject_places):
        categories.add('Kotkaniemi')

    if ('Kotka' in subject_places and 'Varissaari' in subject_places):
        categories.add('Varissaari')

    if ('Kaukas OY' in subject_places and 'Lappeenranta' in subject_places):
        categories.add('Kaukas mill site')

    isInPortraits = False
    for subject in finna_image.subjects.all():
        if subject.name in subject_categories:
            category = subject_categories[subject.name]
            if (category == "Portrait photographs" and isInFinland == True):
                if 'miehet' in subject_names:
                    categories.add("Portrait photographs of men of Finland")
                    isInPortraits = True
                if 'naiset' in subject_names:
                    categories.add("Portrait photographs of women of Finland")
                    isInPortraits = True
                    
                if ('Portrait photographs of men of Finland' not in categories and 'Portrait photographs of women of Finland' not in categories):
                    categories.add("Portrait photographs of Finland")
                    isInPortraits = True
            elif (category == "Portrait photographs"):
                categories.add(category)
                isInPortraits = True
            else:
                categories.add(category)

        if (subject.name == "työ" and isInFinland == True):
            isGenderedWork = False
            if 'miehet' in subject_names:
                categories.add("Men at work in Finland")
                isGenderedWork = True
            if 'naiset' in subject_names:
                categories.add("Women at work in Finland")
                isGenderedWork = True
            if (isGenderedWork == False):
                # working in finland but no tag for gender
                categories.add("People at work in Finland")

        if (isInFinland == True):
            category = get_category_for_subject_in_country(subject.name)
            if (category != None):
                categories.add(category)
            
        # or Askainen
        if (subject.name == 'kartanot' and 'Louhisaari' in subject_places):
            categories.add('Louhisaari Manor')

        if (subject.name == 'kartanot' and 'Piikkiö' in subject_places):
            categories.add('Pukkila Manor')

        #if (subject.name == 'kartanot' and 'Vesilahti' in subject_places):
            #categories.add('Laukko Manor')
        if (subject.name == "Laukon kartano"):
            categories.add('Laukko Manor')

        # Kuusisto, Kaarina
        if (subject.name == 'kartanot' and 'Kuusisto' in subject_places):
            categories.add('Kuusisto Manor')

        # Knuutila, Nokia
        if (subject.name == 'kartanot' and 'Knuutila' in subject_places):
            categories.add('Knuutila Manor')


        if (subject.name == 'parlamentit' and 'Helsinki' in subject_places):
            categories.add('Parliament House, Helsinki')

        if (subject.name == 'linnat' and 'Turun linna' in subject_places):
            categories.add('Turku Castle')

        if (subject.name == 'linnat' and 'Hämeen linna' in subject_places):
            categories.add('Häme Castle')

        if (subject.name == 'linnat' and 'Olavinlinna' in subject_places):
            categories.add('Olavinlinna')

        # or Snappertuna
        if (subject.name == 'linnat' and 'Raaseporin linna' in subject_places):
            categories.add('Raseborg castle')

        # Svartholma, Loviisa
        if (subject.name == 'linnakkeet' and 'Svartholma' in subject_places):
            categories.add('Svartholm Fortress')
        elif (subject.name == 'linnakkeet' and isInFinland == True):
            categories.add('Fortresses in Finland')

        if (subject.name == 'linnoitukset' and 'Kyminlinna' in subject_places):
            categories.add('Kyminlinna')

        if (subject.name == 'kanavat' and 'Kimolan kanava' in subject_places):
            categories.add('Kimola Canal')
        if (subject.name == 'kanavat' and 'Vääksyn Vesijärven kanava' in subject_places):
            categories.add('Vääksy Canal')

        #if (subject.name == "teatterirakennukset" and 'Turku' in subject_places):
            #categories.add('Turku City Theatre')

        # categorize by location if in finland
        if (subject.name == 'luontokuvat' and len(cat_place) > 0 and isInFinland == True):
            cattext = 'Nature of ' + cat_place
            categories.add(cattext)

        # categorize by city if in Finland
        if (subject.name == 'kirkot' or subject.name == 'kirkkorakennukset'):
            if (len(cat_place) > 0 and isInFinland == True):
                cattext = 'Churches in ' + cat_place
                categories.add(cattext)

    
    for add_category in finna_image.add_categories.all():
        wikidata_id = finna_subject.get_wikidata_id()
        category_name = get_category_by_wikidata_id(wikidata_id)
        if category_name:
            categories.add(category_name)

    if finna_image.year:
        if (isInPortraits == True and isInFinland == True):
            categories.add(f'People of Finland in {finna_image.year}')
        if (isInPortraits == True):
            categories.add(f'{finna_image.year} portrait photographs')

        if (len(cat_place) > 0):
            categories.add(f'{finna_image.year} in {cat_place}')
    else:
        # if we can't determine year, use only location name
        # and only if it something other than country (at least a city)
#        if (len(cat_place) > 0 and (cat_place != 'Suomi' and cat_place != 'Finland') and isInFinland == True):
#            categories.add(cat_place)
       pass

    # TODO: to categorize under "Black and white photographs of Finland",
    # see models about parsing the full record xml from Finna for more terms

    categories.add('Files uploaded by FinnaUploadBot')

    for category in categories:
        # is it possible to get this somehow?
        if '^Category:' in category:
            print("Should strip category")
            exit(1)
        # is it possible to get this somehow?
        if 'http' in category:
            print("Should strip url from category")
            exit(1)
        
        # Create the Wikilink
        category_title = 'Category:' + category
        wikilink = mwparserfromhell.nodes.Wikilink(title=category_title)

        # Add the Wikilink to the WikiCode object
        wikicode.append(wikilink)

    flatten_wikicode = str(wikicode).replace('[[Category:', '\n[[Category:')

    # return the wikitext
    return flatten_wikicode

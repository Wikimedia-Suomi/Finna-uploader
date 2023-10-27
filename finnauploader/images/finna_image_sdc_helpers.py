def get_structured_data_for_new_image(finna_image):
    labels = finna_image.get_sdc_labels()
    claims = []

    claim = finna_image.get_source_of_file_claim()
    claims.append(claim)

    claim = finna_image.get_finna_id_claim()
    claims.append(claim)

    claim = finna_image.get_inception_claim()
    claims.append(claim)

    # Handle image rights

    claim = finna_image.image_right.get_licence_claim()
    claims.append(claim)

    claim = finna_image.image_right.get_copyright_state_claim()
    claims.append(claim)

    # Handle non presenter authors (photographers)

    known_roles = ['kuvaaja', 'reprokuvaaja']
    non_presenter_authors = finna_image.non_presenter_authors.all()

    for author in non_presenter_authors:
        if author.role not in known_roles:
            print(f'{author.role} is not known role')

        if author.role == 'kuvaaja':
            claim = author.get_photographer_author_claim()
            claims.append(claim)

    # Handle collections

    collections = finna_image.collections.all()
    identifier = finna_image.identifier_string

    for collection in collections:
        claim = collection.get_collection_claim(identifier)
        claims.append(claim)

    # Handle subject actors

    subject_actors = finna_image.subject_actors.all()
    for subject_actor in subject_actors:
        claim = subject_actor.get_depict_claim()
        claims.append(claim)

    # Handle local subjects

    for add_depict in finna_image.add_depicts.all():
        claim = add_depict.get_depict_claim()
        claims.append(claim)

    json_claims = []
    for claim in claims:
        if claim:
            claim = claim.toJSON()
            json_claims.append(claim)

    ret = {
        'labels': labels,
        'claims': json_claims
    }

    return ret

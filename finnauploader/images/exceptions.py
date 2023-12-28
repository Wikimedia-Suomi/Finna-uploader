class MissingCollectionError(Exception):
    """ Collection is missing at
    https://commons.wikimedia.org/wiki/User:FinnaUploadBot/data/collections.
    """
    pass


class MissingInstitutionError(Exception):
    """ Institution is missing at
    https://commons.wikimedia.org/wiki/User:FinnaUploadBot/data/institutions.
    """
    pass


class MissingNonPresenterAuthorError(Exception):
    """ Institution is missing at
    https://commons.wikimedia.org/wiki/User:FinnaUploadBot/data/nonPresenterAuthors.
    """
    pass


class MultipleNonPresenterAuthorError(Exception):
    """ Institution is missing at
    https://commons.wikimedia.org/wiki/User:FinnaUploadBot/data/nonPresenterAuthors.
    """
    pass


class MissingSubjectActorError(Exception):
    """ Institution is missing at
    https://commons.wikimedia.org/wiki/User:FinnaUploadBot/data/subjectActors.
    """
    pass


class MissingLocationKeywordError(Exception):
    """ Institution is missing at
    https://commons.wikimedia.org/wiki/User:FinnaUploadBot/data/locationKeywords.
    """
    pass

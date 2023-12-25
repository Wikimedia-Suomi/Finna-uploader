from rest_framework import serializers
from .models import FinnaImage, FinnaImageRight, FinnaNonPresenterAuthor, \
                    FinnaSummary, FinnaSubject, FinnaSubjectPlace, \
                    FinnaSubjectActor, FinnaSubjectDetail, FinnaCollection, \
                    FinnaBuilding, FinnaAlternativeTitle, FinnaInstitution


class FinnaCollectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinnaCollection
        fields = '__all__'


class FinnaSubjectDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinnaSubjectDetail
        fields = '__all__'


class FinnaSubjectActorSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinnaSubjectActor
        fields = '__all__'


class FinnaSubjectPlaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinnaSubjectPlace
        fields = '__all__'


class FinnaSubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinnaSubject
        fields = '__all__'


class FinnaSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = FinnaSummary
        fields = '__all__'


class FinnaBuildingSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinnaBuilding
        fields = '__all__'


class FinnaImageRightSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinnaImageRight
        fields = '__all__'


class FinnaNonPresenterAuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinnaNonPresenterAuthor
        fields = '__all__'


class FinnaAlternativeTitleSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinnaAlternativeTitle
        fields = '__all__'


class FinnaInstitutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinnaInstitution
        fields = '__all__'


class FinnaImageSerializer(serializers.ModelSerializer):
    non_presenter_authors = FinnaNonPresenterAuthorSerializer(many=True)
    buildings = FinnaBuildingSerializer(many=True)
    subjects = FinnaSubjectSerializer(many=True)
    subject_places = FinnaSubjectPlaceSerializer(many=True)
    subject_actors = FinnaSubjectActorSerializer(many=True)
    subject_details = FinnaSubjectDetailSerializer(many=True)
    collections = FinnaCollectionSerializer(many=True)
    image_right = FinnaImageRightSerializer()
    summaries = FinnaSummarySerializer(many=True)
    alternative_titles = FinnaAlternativeTitleSerializer(many=True)
    institutions = FinnaInstitutionSerializer(many=True)

    class Meta:
        model = FinnaImage
        fields = ['finna_id', 'title', 'year', 'number_of_images',
                  'non_presenter_authors', 'summaries', 'subjects',
                  'subject_places', 'subject_actors', 'subject_details',
                  'collections', 'buildings', 'image_right', 'identifier_string',
                  'short_title', 'alternative_titles', 'date_string',
                  'measurements', 'institutions']

#    finna_id = models.CharField(max_length=200, null=False, blank=False, db_index=True, unique=True)
#    title = models.CharField(max_length=200)
#    alternative_titles = models.ManyToManyField(FinnaAlternativeTitle)
#    year = models.PositiveIntegerField(unique=False, null=True, blank=True)
#    date_string = models.CharField(max_length=200, null=True, blank=True)
#    number_of_images = models.PositiveIntegerField(unique=False, null=True, blank=True)
##    master_url = models.URLField(max_length=500)
##    master_format = models.CharField(max_length=16)
#    measurements = models.CharField(max_length=32)
#    non_presenter_authors = models.ManyToManyField(FinnaNonPresenterAuthor)
#    summaries = models.ManyToManyField(FinnaSummary)
#    subjects = models.ManyToManyField(FinnaSubject)
#    subject_places = models.ManyToManyField(FinnaSubjectPlace)
#    subject_actors = models.ManyToManyField(FinnaSubjectActor)
#    subject_details = models.ManyToManyField(FinnaSubjectDetail)
#    collections = models.ManyToManyField(FinnaCollection)
#    buildings = models.ManyToManyField(FinnaBuilding)
#    institutions = models.ManyToManyField(FinnaInstitution)
#    image_right = models.ForeignKey(FinnaImageRight, on_delete=models.RESTRICT)
##    add_categories = models.ManyToManyField(FinnaLocalSubject, related_name="category_images")
##    add_depicts = models.ManyToManyField(FinnaLocalSubject, related_name="depict_images")
##    best_wikidata_location = models.ManyToManyField(FinnaSubjectWikidataPlace)

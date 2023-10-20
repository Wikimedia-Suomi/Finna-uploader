from rest_framework import serializers
from .models import FinnaImage, FinnaImageRight, FinnaNonPresenterAuthor, \
                    FinnaSummary, FinnaSubject, FinnaSubjectPlace, \
                    FinnaSubjectActor, FinnaSubjectDetail, FinnaCollection, \
                    FinnaBuilding


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


class FinnaImageSerializer(serializers.ModelSerializer):
    non_presenter_authors = FinnaNonPresenterAuthorSerializer(many=True)
    buildings = FinnaBuildingSerializer(many=True)
    subjects = FinnaSubjectSerializer(many=True)
    subject_places = FinnaSubjectPlaceSerializer(many=True)
    subject_actors = FinnaSubjectActorSerializer(many=True)
    subject_details = FinnaSubjectDetailSerializer(many=True)
    collections = FinnaCollectionSerializer(many=True)
    image_right = FinnaImageRightSerializer()
    summary = FinnaSummarySerializer()

    class Meta:
        model = FinnaImage
        fields = ['finna_id', 'title', 'year', 'number_of_images',
                  'non_presenter_authors', 'summary', 'subjects',
                  'subject_places', 'subject_actors', 'subject_details',
                  'collections', 'buildings', 'image_right', 'identifier_string',
                  'short_title']

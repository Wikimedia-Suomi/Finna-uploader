from images.models import FinnaImage, FinnaRecordSearchIndex
from images.serializers import FinnaImageSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import status, viewsets
from django.shortcuts import get_object_or_404
from watson import search as watson

from images.finna_record_api import get_finna_record_by_id
from images.wikitext.photographer import get_wikitext_for_new_image
from images.sdc_helpers import get_structured_data_for_new_image
from images.pywikibot_helpers import are_there_messages_for_bot_in_commons, \
                                    edit_commons_mediaitem, \
                                    upload_file_to_commons, \
                                    get_comment_text


class FinnaImageViewSet(viewsets.ReadOnlyModelViewSet):
    # TODO: selection for collection would be nice
    
    queryset = FinnaImage.objects.filter(
                                         identifier_string__contains='JOKA',
                                         )
    serializer_class = FinnaImageSerializer

    # http://127.0.0.1:8000/finna/14526/upload
    @action(detail=True, methods=['get'])
    def upload(self, request, pk=None):
        if (are_there_messages_for_bot_in_commons() == True):
            exit(1)

        # Fetch the instance with the given primary key (pk)
        old_finna_image = get_object_or_404(FinnaImage, pk=pk)

        print("Fetching image record:", old_finna_image.finna_id)

        # Update to latest finna_record
        new_record = get_finna_record_by_id(old_finna_image.finna_id)
        finna_image = FinnaImage.objects.create_from_data(new_record)

        filename = finna_image.pseudo_filename
        image_url = finna_image.master_url

        # if we store incomplete url -> needs fixing
        if (image_url.find("http://") < 0 and image_url.find("https://") < 0):
            print("URL is not complete:", image_url)
            exit(1)

        # can't upload from redirector with copy-upload:
        # must handle differently
        if (image_url.find("siiri.urn") > 0 or image_url.find("profium.com") > 0):
            print("Cannot use copy-upload from URL:", image_url)
            exit(1)

        structured_data = get_structured_data_for_new_image(finna_image)
        wikitext = get_wikitext_for_new_image(finna_image)
        comment = get_comment_text(finna_image)

        # Debug log
        print('')
        print(wikitext)
        print('')
        print(comment)
        print(filename)

        print('uploading from:', image_url)

        page = upload_file_to_commons(image_url, filename,
                                      wikitext, comment)
        ret = edit_commons_mediaitem(page, structured_data)
        print(ret)
        finna_image.already_in_commons = True
        finna_image.save()

        return Response({"status": "OK",
                         "filename": filename,
                         "message": f'{pk} uploaded to commons'},
                        status=status.HTTP_200_OK)

    # TODO: add action to call the helper script for creating subject if it is missing..

    # http://127.0.0.1:8000/finna/14526/skip/
    @action(detail=True, methods=['get'])
    def skip(self, request, pk=None):
        # Your logic for removing an item
        # 'pk' is the 'external_id' in your URL

        # Fetch the instance with the given primary key (pk)
        instance = get_object_or_404(FinnaImage, pk=pk)

        # Set the 'deleted' attribute to True
        instance.skipped = True

        # Save the instance to apply the changes
        instance.save()

        return Response({"status": "OK",
                        "message": f'{pk} will be skipped'},
                        status=status.HTTP_200_OK)

    # http://127.0.0.1:8000/finna/random
    @action(detail=False, methods=['get'])
    def random(self, request):
        # Get the 'limit' parameter from the request,
        # default to 10 if not provided
        try:
            limit = int(request.query_params.get('limit', 10))
        except ValueError:
            limit = 10

        # You can also add a maximum limit to prevent too large requests
        max_limit = 100
        limit = min(limit, max_limit)

        search_query = request.query_params.get('searchkey', '')

        q = self.get_queryset()
        q = q.filter(already_in_commons=False,
                     skipped=False)

        if search_query:
            plus_words = []
            minus_words = []
            search_keys = search_query.split(" ")
            for search_key in search_keys:
                if search_key[0] == '-':
                    sk = search_key[1:]
                    minus_words.append(sk)
                else:
                    sk = search_key
                    plus_words.append(sk)

            if len(plus_words):
                plus_query = " ".join(plus_words)
                plus_results = watson.search(plus_query,
                                             models=[FinnaRecordSearchIndex])
                plus_ids = [result.object.id for result in plus_results]
                q = q.filter(data__in=plus_ids)

            if len(minus_words):
                minus_query = " ".join(minus_words)
                minus_results = watson.search(minus_query,
                                              models=[FinnaRecordSearchIndex])
                minus_ids = [result.object.id for result in minus_results]
                q = q.exclude(data__in=minus_ids)

            elif len(plus_words) == 0:
                q = q.filter(data=-1)

        random_records = q.order_by('?')[:limit]
        serializer = self.get_serializer(random_records, many=True)
        return Response(serializer.data)


class HelloWorldAPI(APIView):
    def get(self, request):
        return Response({"message": "Hello from Django REST API!"})

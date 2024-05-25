from images.models import FinnaImage, FinnaRecordSearchIndex
from images.serializers import FinnaImageSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import status, viewsets
from django.shortcuts import get_object_or_404
from watson import search as watson
from images.finna import get_finna_record

from images.wikitext.photographer import get_wikitext_for_new_image
from images.finna_image_sdc_helpers import get_structured_data_for_new_image
from images.pywikibot_helpers import edit_commons_mediaitem, \
                                     upload_file_to_commons, \
                                     get_comment_text


class FinnaImageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FinnaImage.objects.filter(
                                         identifier_string__contains='JOKA',
                                         )
    serializer_class = FinnaImageSerializer

    # http://127.0.0.1:8000/finna/14526/upload
    @action(detail=True, methods=['get'])
    def upload(self, request, pk=None):

        # Fetch the instance with the given primary key (pk)
        finna_image = get_object_or_404(FinnaImage, pk=pk)

        # Update to latest finna_record
        record = get_finna_record(finna_image.finna_id, True)
        record = record['records'][0]
        finna_image = FinnaImage.objects.create_from_data(record)

        filename = finna_image.pseudo_filename
        image_url = finna_image.master_url

        # if we store incomplete url -> needs fixing
        if (image_url.find("http://") < 0 and image_url.find("https://") < 0):
            print("URL is not complete:", image_url)
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
                    minus_words.append(search_key[1:])
                else:
                    plus_words.append(search_key)

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

from .serializers import FinnaImageSerializer
import json

def finna_image_to_json(instance):
    serializer = FinnaImageSerializer(instance)
    return json.dumps(serializer.data, indent=4)

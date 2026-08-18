from django.http import JsonResponse


def health(request):
    response = JsonResponse({"status": "ok", "service": "domaintwin-api"})
    response["Access-Control-Allow-Origin"] = "*"
    return response

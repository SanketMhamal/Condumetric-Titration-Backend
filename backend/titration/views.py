from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
import csv
import json

from .serializers import TitrationInputSerializer
from .calculation import find_equivalence


@api_view(["GET"])
def health(request):
    """GET /api/health/ — lightweight ping to wake up the Render server."""
    return Response({"status": "ok"})


@api_view(["POST"])
def calculate(request):
    """POST /api/calculate/ — run conductometric titration analysis."""
    serializer = TitrationInputSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    try:
        result = find_equivalence(
            volumes=data["volumes"],
            conductivities=data["conductivities"],
            acid_type=data["acid_type"],
            v0=data["v0"],
            apply_dilution_flag=data["apply_dilution"],
        )
    except Exception as exc:
        return Response(
            {"error": str(exc)},
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    return Response(result, status=status.HTTP_200_OK)


@csrf_exempt
def download_input(request):
    """POST /api/download-input/ — download input data as CSV.
    Accepts form-encoded POST with a 'json_data' field containing JSON.
    """
    if request.method != "POST":
        return HttpResponse("Method not allowed", status=405)

    raw = request.POST.get("json_data", "{}")
    data = json.loads(raw)
    volumes = data.get("volumes", [])
    conductivities = data.get("conductivities", [])

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="titration_input_data.csv"'
    response["Access-Control-Allow-Origin"] = "*"

    writer = csv.writer(response)
    writer.writerow(["Volume", "Conductivity"])
    for v, c in zip(volumes, conductivities):
        writer.writerow([v, c])

    return response


@csrf_exempt
def download_results(request):
    """POST /api/download-results/ — download analysis results as CSV.
    Accepts form-encoded POST with a 'json_data' field containing JSON.
    """
    if request.method != "POST":
        return HttpResponse("Method not allowed", status=405)

    raw = request.POST.get("json_data", "{}")
    data = json.loads(raw)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="titration_results.csv"'
    response["Access-Control-Allow-Origin"] = "*"

    writer = csv.writer(response)
    writer.writerow(["Conductometric Titration Analysis - Results Report"])
    writer.writerow([])

    ep = data.get("equivalence_point", {})
    writer.writerow(["Equivalence Point"])
    writer.writerow(["Volume (mL)", ep.get("volume", "")])
    writer.writerow(["Conductivity", ep.get("conductivity", "")])
    writer.writerow([])

    writer.writerow(["Angle Between Lines (degrees)", data.get("angle", "")])
    writer.writerow(["Acid Type", data.get("acid_type", "")])
    writer.writerow([])

    ra = data.get("region_A", {})
    writer.writerow(["Region A (Before Equivalence)"])
    writer.writerow(["Slope", ra.get("slope", "")])
    writer.writerow(["Intercept", ra.get("intercept", "")])
    writer.writerow(["R-squared", ra.get("r_squared", "")])
    writer.writerow([])

    rb = data.get("region_B", {})
    writer.writerow(["Region B (After Equivalence)"])
    writer.writerow(["Slope", rb.get("slope", "")])
    writer.writerow(["Intercept", rb.get("intercept", "")])
    writer.writerow(["R-squared", rb.get("r_squared", "")])
    writer.writerow([])

    writer.writerow(["Corrected Data"])
    writer.writerow(["Volume", "Conductivity"])
    for pair in data.get("corrected_data", []):
        if isinstance(pair, list) and len(pair) == 2:
            writer.writerow(pair)

    return response

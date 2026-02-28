from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .serializers import TitrationInputSerializer
from .calculation import find_equivalence


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

from rest_framework import serializers


class TitrationInputSerializer(serializers.Serializer):
    volumes = serializers.ListField(
        child=serializers.FloatField(),
        min_length=3,
        help_text="List of titrant volumes (mL)",
    )
    conductivities = serializers.ListField(
        child=serializers.FloatField(),
        min_length=3,
        help_text="List of measured conductivity values",
    )
    acid_type = serializers.ChoiceField(
        choices=["strong", "weak"],
        help_text="Type of acid: 'strong' or 'weak'",
    )
    v0 = serializers.FloatField(
        min_value=0.01,
        help_text="Initial volume of the acid solution (mL)",
    )
    apply_dilution = serializers.BooleanField(
        default=True,
        help_text="Whether to apply dilution correction",
    )

    def validate(self, data):
        if len(data["volumes"]) != len(data["conductivities"]):
            raise serializers.ValidationError(
                "volumes and conductivities must have the same length."
            )
        return data

from rest_framework import serializers
from .models import QueryLog
from .models import FinancialMetric
from .models import FinancialUpload



class QueryLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = QueryLog
        fields = '__all__'

from .models import Task


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = "__all__"

class AskAgentSerializer(serializers.Serializer):

    question = serializers.CharField(
        required=True,
        max_length=500,
        allow_blank=False,
    )
    specialist = serializers.CharField(required=False, max_length=100, allow_blank=False)
    conversation_id = serializers.IntegerField(required=False, min_value=1)
    companion_mode = serializers.BooleanField(required=False, default=False)



class FinancialMetricSerializer(serializers.ModelSerializer):

    class Meta:
        model = FinancialMetric
        fields = "__all__"



class FinancialUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialUpload
        fields = "__all__"

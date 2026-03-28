from rest_framework import serializers
from .models import TicketProgress

class TicketProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketProgress
        fields = '__all__'

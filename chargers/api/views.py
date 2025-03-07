from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from ..models import Charger, Transaction
from .serializers import ChargerSerializer, TransactionSerializer

class ChargerViewSet(viewsets.ModelViewSet):
    queryset = Charger.objects.all()
    serializer_class = ChargerSerializer

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        charger = self.get_object()
        if charger.status != 'Available':
            return Response(
                {'error': 'Charger is not available'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # In a real implementation, you would send a RemoteStartTransaction request to the charger
        return Response({'status': 'Request sent to charger'})

    @action(detail=True, methods=['post'])
    def stop(self, request, pk=None):
        charger = self.get_object()
        if charger.status != 'Charging':
            return Response(
                {'error': 'Charger is not charging'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # In a real implementation, you would send a RemoteStopTransaction request to the charger
        return Response({'status': 'Request sent to charger'})

class TransactionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer

    def get_queryset(self):
        queryset = Transaction.objects.all()
        charger_id = self.request.query_params.get('charger_id', None)
        if charger_id is not None:
            queryset = queryset.filter(charger_id=charger_id)
        return queryset.order_by('-start_time')

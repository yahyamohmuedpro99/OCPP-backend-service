from django.shortcuts import render
from .models import Charger
def test_interface(request):
    chargers= Charger.objects.all()
    return render(request, 'test.html', {'chargers': chargers})

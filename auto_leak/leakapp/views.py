from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate,login,logout 
from django.urls import reverse
from django.views import View
from django.http import JsonResponse
from leakapp.forms import LeakAppMasterDataForm
from leakapp.models import LeakAppMasterData
# Create your views here.

def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('leakapp_list')
        else:
            messages.error(request, 'Invalid username or password')
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect(reverse('login'))


class LeakAppMasterDataView(View):
    def get(self, request, pk=None):
        if pk:
            instance = get_object_or_404(LeakAppMasterData, pk=pk)
            form = LeakAppMasterDataForm(instance=instance)
        else:
            form = LeakAppMasterDataForm()

        data = LeakAppMasterData.objects.all()
        return render(request, 'master.html', {'form': form, 'data': data})

    def post(self, request, pk=None):
        part_number = request.POST.get("part_number", "").strip()

        if LeakAppMasterData.objects.filter(part_number=part_number).exists():
            return JsonResponse({"error": "Part number already exists."}, status=400)

        form = LeakAppMasterDataForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({"message": "Record added successfully!"}, status=201)

        return JsonResponse({"error": "Invalid data."}, status=400)

    def delete(self, request, pk):
        instance = get_object_or_404(LeakAppMasterData, pk=pk)
        instance.delete()
        return JsonResponse({"message": "Record deleted successfully!"}, status=200)

def search_part_numbers(request):
    query = request.GET.get("query", "").strip()
    if query:
        results = LeakAppMasterData.objects.filter(part_number__icontains=query).values("id", "part_number")
        return JsonResponse({"results": list(results)})
    return JsonResponse({"results": []})

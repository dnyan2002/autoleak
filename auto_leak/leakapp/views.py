from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate,login,logout 
from django.urls import reverse
from django.views import View
from django.db import connection
from django.contrib.auth.decorators import login_required
from datetime import datetime
from django.http import JsonResponse
from django.db.models import Max
from leakapp.forms import LeakAppMasterDataForm, LeakAppTestForm
from leakapp.models import LeakAppMasterData, LeakAppTest, LeakAppShowReport
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


def get_leak_test_data(request):
    part_no = request.GET.get("part_number", "").strip()
    form = LeakAppTestForm()
    part_numbers = LeakAppMasterData.objects.all()

    filter_values = {}
    highest_values = {}
    results = {}

    # Always include AI1 to AI16 filter names
    filter_names = [f"AI{i}" for i in range(1, 17)]

    if part_no:
        # Only populate the latest filter values
        for filter_name in filter_names:
            latest_entry = LeakAppTest.objects.filter(
                part_number__part_number=part_no, filter_no=filter_name
            ).order_by('-date_field').first()
            
            # Save the values directly in separate dictionaries
            if latest_entry:
                filter_values[filter_name] = latest_entry.filter_values
                highest_values[filter_name] = latest_entry.iot_value
                results[filter_name] = "ok" if latest_entry.filter_values <= latest_entry.iot_value else "not ok"
            else:
                filter_values[filter_name] = None
                highest_values[filter_name] = None
                results[filter_name] = None

    return render(request, "leak_test.html", {
        "form": form,
        "part_numbers": part_numbers,
        "filter_values": filter_values,
        "highest_values": highest_values,
        "results": results,
        "selected_part_no": part_no,
        "filter_names": filter_names,  # Send static filter names
    })


def get_latest_filter_values(request):
    part_no = request.GET.get("part_number", "").strip()
    latest_filters = {}

    if part_no:
        for i in range(1, 17):
            filter_no = f"AI{i}"
            latest_entry = LeakAppTest.objects.filter(
                part_number__part_number=part_no, filter_no=filter_no
            ).order_by('-date_field').first()
            if latest_entry:
                latest_filters[filter_no] = latest_entry.filter_values

    return JsonResponse({"latest_filters": latest_filters})


def get_highest_filter_value(request):
    part_no = request.GET.get("part_number", "").strip()
    highest_values = {}

    if part_no:
        for i in range(1, 17):
            filter_name = f"AI{i}"
            filters_data = LeakAppTest.objects.filter(
                part_number__part_number=part_no, filter_no=filter_name
            ).order_by('date_field')
            if filters_data:
                highest_value = filters_data.aggregate(Max('filter_values'))['filter_values__max']
                highest_values[filter_name] = highest_value

    return JsonResponse({"highest_values": highest_values})


def search_part_numbers_for_leak_test(request):
    query = request.GET.get("query", "").strip()
    if query:
        results = LeakAppMasterData.objects.filter(part_number__icontains=query).values("id", "part_number")
        return JsonResponse({"results": list(results)})
    return JsonResponse({"results": []})


def dictfetchall(cursor):
    """Helper function to convert cursor results into a dictionary."""
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

@login_required(login_url="login")
def report_screen(request):
    # Get filter parameters from request
    selected_date = request.GET.get("date", "")
    selected_month = request.GET.get("month", "")
    selected_year = request.GET.get("year", "")
    selected_batch_counter = request.GET.get("batch_counter", "")
    selected_part_number = request.GET.get("part_number", "")
    selected_status = request.GET.get("status", "")

    # Construct SQL Query
    sql_query = "SELECT * FROM leakapp_show_report WHERE 1=1"
    sql_params = []

    if selected_date:
        try:
            selected_date = datetime.strptime(selected_date, "%Y-%m-%d").date()
            sql_query += " AND DATE(data) = %s"
            sql_params.append(selected_date)
        except ValueError:
            pass

    elif selected_month and selected_year:
        try:
            selected_month = int(selected_month)
            selected_year = int(selected_year)
            sql_query += " AND YEAR(data) = %s AND MONTH(data) = %s"
            sql_params.extend([selected_year, selected_month])
        except ValueError:
            pass

    elif selected_year:
        try:
            selected_year = int(selected_year)
            sql_query += " AND YEAR(data) = %s"
            sql_params.append(selected_year)
        except ValueError:
            pass

    # Apply batch filter
    if selected_batch_counter:
        sql_query += " AND batch_counter = %s"
        sql_params.append(selected_batch_counter)

    # Apply part number filter
    if selected_part_number:
        try:
            part = LeakAppMasterData.objects.get(id=selected_part_number)
            sql_query += " AND part_number_id = %s"
            sql_params.append(part.id)
        except LeakAppMasterData.DoesNotExist:
            sql_query += " AND 1=0"  # Forces an empty result

    # Apply status filter
    if selected_status:
        sql_query += " AND status = %s"
        sql_params.append(selected_status)

    # Execute the raw SQL query
    with connection.cursor() as cursor:
        cursor.execute(sql_query, sql_params)
        report_data = dictfetchall(cursor)

    # Get first record if only one result exists
    single_data = report_data[0] if len(report_data) == 1 else None

    # Populate dropdowns
    batch_counters = LeakAppShowReport.objects.values_list("batch_counter", flat=True).distinct()
    part_numbers = LeakAppMasterData.objects.all()
    statuses = LeakAppShowReport.objects.values_list("status", flat=True).distinct()
    years = list(range(2000, 2099))

    # Pass selected values properly
    context = {
        "report_data": report_data,
        "single_data": single_data,
        "date": selected_date.strftime("%Y-%m-%d") if selected_date else "",
        "month": selected_month if selected_month else "",
        "year": selected_year if selected_year else "",
        "selected_batch_counter": selected_batch_counter,
        "selected_part_number": selected_part_number,
        "selected_status": selected_status,
        "batch_counters": batch_counters,
        "part_numbers": part_numbers,
        "statuses": statuses,
        "years": years,
    }

    return render(request, "report_screen.html", context)

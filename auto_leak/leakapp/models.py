from django.db import models
from datetime import timedelta


class User(models.Model):
    username = models.CharField(max_length=255, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'


class LeakAppMasterData(models.Model):
    part_number = models.CharField(max_length=255)
    greater_less = models.CharField(max_length=10, blank=True, null=True)
    setpoint1 = models.IntegerField(default=18, blank=True, null=True)
    value = models.FloatField(null=True, blank=True)
    setpoint2 = models.IntegerField(default=70, blank=True, null=True)
    timer1 = models.DurationField(default=timedelta(seconds=5), blank=True, null=True)
    timer2 = models.DurationField(default=timedelta(seconds=15), blank=True, null=True)

    def __str__(self):
        return f"{self.part_number}"
    
    class Meta:
        verbose_name = "Parts"
        verbose_name_plural = "Parts"
        db_table = "leakapp_masterdata"


class FOI(models.Model):
    part_number = models.ForeignKey(LeakAppMasterData, on_delete=models.CASCADE, verbose_name="Part Number")
    filter_counter = models.IntegerField()
    filterno = models.CharField(max_length=255)
    filter_values = models.FloatField()
    date_field = models.DateField()
    iot_value = models.IntegerField()
    result = models.CharField(max_length=25)
    shift = models.CharField(max_length=25)

    # def __str__(self):
    #     return f"{self.PartNumber} - {self.FilterNo} ({self.Date_Field})"

    class Meta:
        db_table = "foi_tbl"
        verbose_name = "FOI"
        verbose_name_plural = "FOI"


class LeakAppTest(models.Model):
    part_number = models.ForeignKey(LeakAppMasterData, on_delete=models.CASCADE, verbose_name="Part Number")
    batch_counter = models.IntegerField()
    filter_no = models.CharField(max_length=50)
    digital_input = models.CharField(max_length=20)
    filter_values = models.FloatField()
    date_field = models.DateTimeField(auto_now = True)
    iot_value = models.FloatField()
    class Meta:
        db_table = "leakapp_test"
        verbose_name = "Leak Test"
        verbose_name_plural = "Leak Tests"


class Shift(models.Model):
    shift_name = models.CharField(max_length=50)
    start_time = models.DurationField()
    end_time = models.DurationField()

    def __str__(self):
        return self.shift_name
    class Meta:
        db_table = "shift_tbl"
        verbose_name = "Shift"
        verbose_name_plural = "Shifts"


class LeakAppShowReport(models.Model):
    batch_counter = models.IntegerField()
    part_number = models.ForeignKey(LeakAppMasterData, on_delete= models.CASCADE)
    filter_values = models.FloatField()
    filter_no = models.CharField(max_length=50, verbose_name="Filter No")
    status = models.CharField(max_length=30)
    shift = models.ForeignKey(Shift, on_delete=models.CASCADE)
    highest_value = models.FloatField()
    date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "leakapp_show_report"
        verbose_name = "Leak Report"
        verbose_name_plural = "Leak Report"


class LeakAppResult(models.Model):
    batch_counter = models.IntegerField(default=0, verbose_name="Batch Counter")
    part_number = models.ForeignKey(LeakAppMasterData, on_delete=models.CASCADE)
    filter_no = models.CharField(max_length=50)
    filter_values = models.FloatField()
    status = models.CharField(max_length=30)
    shift = models.ForeignKey(Shift, on_delete=models.CASCADE)
    highest_value = models.FloatField()
    date = models.DateTimeField(auto_now=True)
    filter_counter_by_system = models.IntegerField()
    iot_value = models.IntegerField()

    class Meta:
        db_table = "leakapp_result_tbl"
        verbose_name = "Leak Result"
        verbose_name_plural = "Leak Results"
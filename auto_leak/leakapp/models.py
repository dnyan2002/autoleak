from django.db import models

class User(models.Model):
    username = models.CharField(max_length=255, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)

class LeakAppMasterData(models.Model):
    part_number = models.CharField(max_length=255)
    greater_less = models.CharField(max_length=10, blank=True, null=True)
    setpoint1 = models.IntegerField(default=18, blank=True, null=True)
    value = models.FloatField(null=True, blank=True)
    setpoint2 = models.IntegerField(default=70, blank=True, null=True)
    timer1 = models.DurationField(default="00:00:05", blank=True, null=True)
    timer2 = models.DurationField(default="00:00:15", blank=True, null=True)

    def __str__(self):
        return f"{self.part_number}"
    
    class Meta:
        verbose_name = "Leak App Master Data"
        verbose_name_plural = "Leak App Master Data"
        db_table = "leakapp_masterdata"


# class DateRecord(models.Model):
#     dt = models.DateTimeField()
#     dt_display = models.CharField(max_length=20)
#     created_by = models.CharField(max_length=15)
#     created_date = models.DateField(auto_now_add=True)
#     created_ip = models.CharField(max_length=20)
    
#     def __str__(self):
#         return f"{self.dt_display} ({self.dt})"
    
#     class Meta:
#         verbose_name = "Date Record"
#         verbose_name_plural = "Date Records"
#         db_table = "365dates"


# class AccessRight(models.Model):
#     node = models.CharField(max_length=100)
#     action = models.CharField(max_length=100)
#     profile = models.IntegerField()
    
#     def __str__(self):
#         return f"{self.node} - {self.action} ({self.profile})"

#     class Meta:
#         db_table = "accessright"
#         verbose_name = "Access Right"
#         verbose_name_plural = "Access Rights"


# class ATKExportCriteria(models.Model):
#     nodetype = models.CharField(max_length=100)
#     name = models.CharField(max_length=100)
#     criteria = models.TextField()
#     user_id = models.IntegerField()
#     visibility = models.IntegerField()
    
#     def __str__(self):
#         return f"{self.name} - {self.nodetype} ({self.user_id})"

#     class Meta:
#         db_table = "atk_exportcriteria"
#         verbose_name = "ATK Export Criteria"
#         verbose_name_plural = "ATK Export Criterias"


# class FOIHighest(models.Model):
#     batchcounter = models.IntegerField()
#     partnumber = models.CharField(max_length=25)
#     filter_values = models.FloatField()
#     filterno = models.CharField(max_length=25)
#     result = models.CharField(max_length=25)
#     shift = models.CharField(max_length=50)
#     highest_value = models.CharField(max_length=10)
#     date_field = models.DateField()

#     def __str__(self):
#         return f"{self.PartNumber} - {self.BatchCounter} ({self.Date_Field})"

#     class Meta:
#         db_table = "foi_highest_tbl"
#         verbose_name = "FOI Highest"
#         verbose_name_plural = "FOI Highest"
    

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

class Shift(models.Model):
    shift_name = models.CharField(max_length=50)
    start_time = models.DurationField()
    end_time = models.DurationField()

    class Meta:
        db_table = "shift_tbl"

class LeakAppShowReport(models.Model):
    batch_counter = models.IntegerField()
    part_number = models.ForeignKey(LeakAppMasterData, on_delete= models.CASCADE)
    filter_values = models.FloatField()
    filter_no = models.CharField(max_length=50, verbose_name="Filter No")
    status = models.CharField(max_length=30)
    shift = models.ForeignKey(Shift, on_delete=models.CASCADE)
    highest_value = models.FloatField()
    data = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "leakapp_show_report"
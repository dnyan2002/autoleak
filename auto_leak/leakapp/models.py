from django.db import models

class User(models.Model):
    username = models.CharField(max_length=255, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)


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
    

# class FOI(models.Model):
#     partnumber = models.CharField(max_length=255)
#     filter_counter = models.IntegerField()
#     filterno = models.CharField(max_length=255)
#     filter_values = models.FloatField()
#     date_field = models.DateField()
#     iot_value = models.IntegerField()
#     result = models.CharField(max_length=25)
#     shift = models.CharField(max_length=25)
    
#     def __str__(self):
#         return f"{self.PartNumber} - {self.FilterNo} ({self.Date_Field})"

#     class Meta:
#         db_table = "foi_tbl"
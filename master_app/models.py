from django.db import models
from App.models import *
from admin_app.models import AdminModel

# Create your models here.

class MastrModel(models.Model):
    master_user = models.OneToOneField(MyUser, on_delete=models.CASCADE, related_name="master_user")
    admin_user = models.ForeignKey(AdminModel, on_delete=models.CASCADE, related_name="admin_user")
    master_link = models.ForeignKey('self', on_delete=models.CASCADE, related_name="linked_masters", null=True, blank=True)
    
    limit = models.BooleanField(default=False)
    master_limit = models.PositiveIntegerField("Master Limit",default=0,blank=True,null=True)
    client_limit = models.PositiveIntegerField("Client Limit",default=0,blank=True,null=True)
    
    
    
    def __str__(self):
        return str(self.master_user)
    
    class Meta:
        verbose_name = "Master Model" 
        verbose_name_plural = "Master Model"  
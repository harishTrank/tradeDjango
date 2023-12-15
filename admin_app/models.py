from django.db import models
from App.models import *
from master_app.models import *

class AdminModel(models.Model):
    user = models.OneToOneField(MyUser, on_delete=models.CASCADE, related_name="admin_user")
    
    def __str__(self):
        return str(self.user)


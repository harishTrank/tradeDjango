from django.db import models
from App.models import *
from master_app.models import *

class AdminModel(models.Model):
    user = models.OneToOneField(MyUser, on_delete=models.CASCADE, related_name="admin_user")
    nse_brk = models.PositiveIntegerField("NSE Brk", default=0)
    mcx_brk = models.PositiveIntegerField("MCX Brk", default=0)
    mini_brk = models.PositiveIntegerField("MINI Brk", default=0)
    
    def __str__(self):
        return str(self.user)


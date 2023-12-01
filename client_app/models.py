from django.db import models
from App.models import *
from master_app.models import *
from admin_app.models import *


class ClientModel(models.Model):
    client = models.OneToOneField(MyUser, on_delete=models.CASCADE, related_name="client")
    master_user_link = models.ForeignKey(MastrModel, on_delete=models.CASCADE, related_name="master_user_link")
    admin_create_client = models.ForeignKey(AdminModel, on_delete=models.CASCADE, related_name="admin_create_client", null=True, blank=True)
    
    def __str__(self):
        return str(self.client)


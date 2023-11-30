from django.db import models
from App.models import *
from master_app.models import *


class ClientModel(models.Model):
    client = models.OneToOneField(MyUser, on_delete=models.CASCADE, related_name="client")
    master_user_link = models.ForeignKey(MastrModel, on_delete=models.CASCADE, related_name="master_user_link")
    
    def __str__(self):
        return str(self.client)


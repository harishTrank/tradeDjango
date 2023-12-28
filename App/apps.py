from django.apps import AppConfig
from django.conf import settings
from App.scheduler import send_hello  
from apscheduler.schedulers.background import BackgroundScheduler


class AppConfigTest(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'App'
    
    
    
    def ready(self):
        scheduler = BackgroundScheduler()
        scheduler.add_job(send_hello, 'cron', hour=11, minute=42) 
        # scheduler.add_job(send_hello, 'interval', seconds=5)
        scheduler.start()

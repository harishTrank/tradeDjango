from django.apps import AppConfig
from django.conf import settings
from App.scheduler import *  
from apscheduler.schedulers.background import BackgroundScheduler


class AppConfigTest(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'App'
    
    def ready(self):
        scheduler = BackgroundScheduler()
        scheduler.add_job(nse_squareoff, 'cron', args=["NSE"], hour=15, minute=29)
        scheduler.add_job(mini_mcx_squareoff, 'cron', args=["MINI"], hour=23, minute=29)
        scheduler.add_job(delete_expire, 'cron', hour=23, minute=59)
        # scheduler.start()

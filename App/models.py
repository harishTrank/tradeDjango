from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser
import random
from App.chocies import *
from django.utils import timezone
import uuid

class CommonTimePicker(models.Model):
    created_at = models.DateTimeField("Created At", auto_now_add=True)
    updated_at = models.DateTimeField("Updated At", auto_now_add=True)

    class Meta:
        abstract = True
        
        
class MyUserManager(BaseUserManager):
    def create_user(self, user_name, password=None):
        if not user_name:
            raise ValueError('Users must have an user_name')

        user = self.model(
            user_name=self.user_name,
        )

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, user_name, password=None):
        user = self.model(
            user_name=user_name,
        )
        user.set_password(password)
        user.is_superuser = True
        if user.is_superuser: user.user_type = "SuperAdmin"
        user.is_staff = True
        user.save(using=self._db)
        return user



class MyUser(AbstractBaseUser,CommonTimePicker):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4, editable=False)
    user_type = models.CharField("User Type", max_length=20, choices=USER_TYPE_CHOICES, blank=True, null=True)
    role = models.CharField("Role", max_length=20, choices=ROLE_CHOICES, blank=True, null=True)
    full_name = models.CharField("Full Name", max_length=255, blank=True, null=True)
    user_name = models.CharField("User Name", max_length=255, blank=True, null=True,unique=True)
    phone_number = models.CharField("Phone Number",max_length=10,default=0)
    email = models.EmailField("Email", max_length=255, blank=True, null=True)
    city = models.CharField("City",max_length=200,blank=True,null=True)
    credit = models.PositiveIntegerField("Credit",default=0)    
    balance = models.IntegerField("Balance",default=0)
    remark=models.CharField("Remark",max_length=200,blank=True,null=True)
    avatar = models.ImageField("Avatar", upload_to="Profile/%Y/%m/%d/", blank=True, null=True)
    dob = models.DateField("Date of Birth", max_length=20, blank=True, null=True)
    address = models.TextField("Address", blank=True, null=True, default="")
    mcx = models.BooleanField("MCX", default=False)
    sgx = models.BooleanField("SGX", default=False)
    mini = models.BooleanField("MINI", default=False)
    nse = models.BooleanField("NSE", default=False)
    others = models.BooleanField("Others", default=False)
    add_master = models.BooleanField("Add Master", default=False)
    change_password = models.BooleanField("Change Password", default=False)
    bet = models.BooleanField("Bet", default=False)
    close_only = models.BooleanField("Close Only", default=False)
    margin_sq = models.BooleanField("Margin Sq", default=False)
    status = models.BooleanField("Status", default=True)
    auto_square_off = models.BooleanField("Auto Square off", default=False)
    
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField("Super User", default=False)

    nse_brk = models.PositiveIntegerField("NSE Brk", default=0, null=True, blank=True)
    mcx_brk = models.PositiveIntegerField("MCX Brk", default=0, null=True, blank=True)
    mini_brk = models.PositiveIntegerField("MINI Brk", default=0, null=True, blank=True)

    objects = MyUserManager()

    USERNAME_FIELD = 'user_name'
 

    def __str__(self):
        return self.user_name

    def has_perm(self, perm, obj=None):
        "Does the user have a specific permission?"
     
        return True

    def has_module_perms(self, app_label):
        "Does the user have permissions to view the app `app_label`?"
        return True
    
    def create_otp(self):
        otp = random.randint(1000, 9999)
        self.otp = otp
        self.otp_varify = False
        self.save()
        return otp
    
    def save(self, *args, **kwargs):
        if not self.id:
            self.id = str(uuid.uuid4())
        super().save(*args, **kwargs)
        
    class Meta:
        verbose_name_plural = 'My User'
        ordering = ('-created_at',)   
        
        


class LoginHistoryModel(CommonTimePicker):
    user_history = models.ForeignKey(MyUser, on_delete=models.CASCADE, related_name="user_history")
    ip_address = models.CharField("Ip address", max_length=200,null=True, blank=True)
    method = models.CharField("Method", max_length=200,null=True, blank=True)
    action = models.CharField("action", max_length=20, choices=ACTIONLOGIN, blank=True, null=True)

    def __str__(self):
        return self.method + " " + self.user_history.user_name


class ExchangeModel(CommonTimePicker):
    user = models.ForeignKey(MyUser, on_delete=models.CASCADE, related_name='user')
    symbol_name = models.CharField("Symbol Name", max_length=200, blank=True)
    exchange = models.BooleanField("Exchange", default=False)
    symbols = models.BooleanField("Symbols", default=False)
    turnover = models.BooleanField("Turnover", default=False)

    def __str__(self):
        return self.symbol_name + " " + self.user.user_name



class MarketWatchModel(CommonTimePicker):
    market_user = models.ForeignKey(MyUser,on_delete=models.CASCADE, related_name='market_user')    
    trade_coin_id = models.CharField("Trade Coin Id", max_length=200,null=True, blank=True)
    
    def __str__(self):
        return self.trade_coin_id 
    class Meta:
        ordering = ('-trade_coin_id',)   
    
    
class TradHistoryModel(CommonTimePicker):
    trade_user = models.ForeignKey(MyUser, on_delete=models.CASCADE, related_name='trade_user')  
    status = models.BooleanField("Status",default=False)
    
    def __str__(self):
        return self.state
    
     
class BuyAndSellModel(CommonTimePicker):
    buy_sell_user = models.ForeignKey(MyUser, on_delete=models.CASCADE, related_name='buy_sell_user')  
    quantity = models.IntegerField("Quantity",default=0)
    trade_type = models.CharField("Trade Type",max_length=20, choices=TRADE_TYPE, blank=True, null=True)
    action = models.CharField("Action",max_length=20, choices=ACTION, blank=True, null=True)
    price = models.FloatField("Price",default=0)
    coin_name = models.CharField("Coin Name",max_length=200, blank=True, null=True)
    ex_change = models.CharField("Exchange",max_length=200, blank=True, null=True)
    is_pending = models.BooleanField("Is Pending", default=False)
    identifer = models.CharField("Identifer",max_length=200, null=True, blank=True)
    ip_address = models.CharField("Ip Address", max_length=200, default="", null=True, blank=True)
    order_method = models.CharField("Order Method", max_length=200, default="", null=True, blank=True)
    trade_status = models.BooleanField("Trade Status", default=True)
    is_cancel = models.BooleanField("Is Cancel", default=False)
    sl_flag = models.BooleanField("Sl Flag", default=False,null=True, blank=True)
    message = models.CharField("Message",max_length=200, default="", null=True, blank=True)
    stop_loss = models.IntegerField("Quantity",default=0, null=True, blank=True)
    
    
    class Meta:
        abstract = True

    
    def __str__(self):
        return self.trade_type
    
    class Meta:
        ordering = ('-id',)


class AccountSummaryModal(CommonTimePicker):
    user_summary = models.ForeignKey(MyUser, on_delete=models.CASCADE, related_name="user_summary")
    particular = models.CharField("Particular", max_length=200)
    quantity = models.PositiveIntegerField("Quantity", default=0)
    buy_sell_type = models.CharField("Buy Sell Type", max_length=200)
    price = models.FloatField("Price", default=0)
    average = models.FloatField("Average", default=0)
    summary_flg = models.CharField("Type", max_length=200,choices=SUMMARYFLAG, blank=True, null=True)
    amount = models.FloatField("Amount", default=0)
    closing = models.IntegerField("closing", default=0)
    open_qty = models.IntegerField("Opening", default=0)
    
    def __str__(self):
        return self.user_summary.user_name
     
    class Meta:
        ordering = ('-created_at',)   
     
        
class GroupSettingsModel(CommonTimePicker):
    group = models.CharField("Group", max_length=200, null=True, blank=True)
    
    def __str__(self):
        return self.group    

class ScriptModel(CommonTimePicker):
    group_user = models.ForeignKey(GroupSettingsModel, on_delete=models.CASCADE, related_name="group_user")
    script = models.CharField("Script", max_length=200, null=True, blank=True)
    lot_size = models.IntegerField("Lot Size",default=0)
    qty_max = models.IntegerField("Qty Max",default=0)
    lot_max = models.IntegerField("Lot Max",default=0)
    breakup_qty = models.IntegerField("Breakup Qty",default=0)
    breakup_lot = models.IntegerField("Break Lot",default=0)
    
    def __str__(self) -> str:
        return self.script


class AdminCoinWithCaseModal(CommonTimePicker):
    master_coins = models.ForeignKey(MyUser, on_delete=models.CASCADE, related_name="admin_coins")
    ex_change = models.CharField("ExChange", max_length=200)
    identifier = models.CharField("Identifier", max_length=200)
    breakup_qty = models.FloatField("Break Up Quantity", default=0)
    max_qty = models.FloatField("Max Quantity", default=0)
    breakup_lot = models.FloatField("Breakup Lot", default=0)
    max_lot = models.FloatField("Max Lot", default=0)
    lot_size = models.FloatField("Lot Size", default=0)


    def __str__(self):     
        return self.master_coins.user_name + " " + self.ex_change + " " + self.identifier
    

    
    
class UserCreditModal(CommonTimePicker):
    user_credit = models.ForeignKey(MyUser, on_delete=models.CASCADE, related_name="user_credit")
    opening = models.FloatField(default=0)
    credit = models.FloatField(default=0)
    debit = models.FloatField(default=0)
    closing = models.FloatField(default=0)
    message = models.CharField("Message", max_length=200, null=True, blank=True, default="")
    transection = models.ForeignKey(MyUser, on_delete=models.CASCADE, related_name="transection")

    def __str__(self):
        return f"{self.user_credit.user_name} {self.closing}"
    

class TradeMarginModel(CommonTimePicker):
    exchange = models.CharField("Exchange", max_length=200, null=True, blank=True)
    script = models.CharField("script", max_length=200, null=True, blank=True)
    trade_margin = models.FloatField("Trade Margin", default=0)
    disc = models.CharField("Description", max_length=200, null=True, blank=True)
    
    def __str__(self):
        return str(self.exchange) + " "+ str(self.script)
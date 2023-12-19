from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth import authenticate, login
from App.models import *
from client_app.models import *
from django.contrib.auth.hashers import make_password
from django.contrib.auth import authenticate,login,logout
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.db.models import Sum, Avg , Q ,F
import csv
from django.http import HttpResponse
from datetime import datetime, timedelta

class LoginView(View):
    def get(self, request):
        if request.user.is_authenticated:
            if request.user is not None and request.user.user_type == "SuperAdmin":
                return redirect("Admin:list-user")
            elif request.user is not None and request.user.user_type == "Admin":
                return redirect("Admin:dashboard")
            elif request.user is not None and request.user.user_type == "Master":
                return redirect("Admin:dashboard")
            elif request.user is not None and request.user.user_type == "Client":
                return redirect("Admin:dashboard")
        return render(request, "register/login.html")
    
    def post(self, request):
        user_name = request.POST.get("user_name")
        password = request.POST.get("password")
        user = authenticate(user_name=user_name, password=password)
        
        if user is not None:
            if user.user_type in ["SuperAdmin", "Admin", "Master", "Client"]:
                login(request, user)
                if user.user_type == "SuperAdmin":
                    return redirect("Admin:dashboard")
                else:
                    return redirect("Admin:dashboard")
            else:
                messages.error(request, "Invalid user type")
        return redirect("Admin:login")



class LogoutView(View):
    def get(self, request):
        logout(request)
        return redirect("Admin:login")
    



    
    
    
class Dashboard(View):
    def get(self, request):
        if request.user.is_authenticated:
            user = request.user
            exchange_obj = ExchangeModel.objects.filter(user=user).values("symbol_name","exchange")
            return render(request, "dashboard/dashboard.html",{"symbols":exchange_obj})
        return redirect("Admin:login")
        
    
  
class AddUserView(View):
    def get(self, request):
        return render(request, "User/add-user.html")
       
    def post(self, request):
        limit = request.user.master_user.limit if request.user.user_type == "Master" else False
        master_limit = request.user.master_user.master_limit if request.user.user_type == "Master" else None
        client_limit = request.user.master_user.client_limit if request.user.user_type == "Master" else None
        
        user_data = {
            "full_name": request.POST.get("full_name"),
            "user_name": request.POST.get("user_name"),
            "phone_number": request.POST.get("phone_number"),
            "city": request.POST.get("city"),
            "credit": request.POST.get("credit") if request.POST.get("credit") else 0,
            "remark": request.POST.get("remark"),
            "password": make_password(request.POST.get("password")),
            "mcx": True if request.POST.get("mcx") and request.POST.get("mcx").lower() == 'on' else False,
            "nse": True if request.POST.get("nse") and request.POST.get("nse").lower() == 'on' else False,
            "sgx": True if request.POST.get("sgx") and request.POST.get("sgx").lower() == 'on' else False,
            "others": True if request.POST.get("others") and request.POST.get("others").lower() == 'on' else False,
            "mini": True if request.POST.get("mini") and request.POST.get("mini").lower() == 'on' else False,
            "change_password": True if request.POST.get("change_password") and request.POST.get("change_password").lower() == 'on' else False,
            "add_master": True if request.POST.get("add_master") and request.POST.get("add_master").lower() == 'on' else False,
            "auto_square_off": True if request.POST.get("auto_square") and request.POST.get("auto_square").lower() == 'on' else False,
        }
        exchanges = [
            {
                "name": "MCX",
                "exchange": request.POST.get("mcx_exchange") == 'on',
                "symbols": request.POST.get("mcx_symbol") == 'on',
                "turnover": request.POST.get("mcx_turnover") == 'on',
            },
            {
                "name": "NSE",
                "exchange": request.POST.get("nse_exchange") == 'on',
                "symbols": request.POST.get("nse_symbol") == 'on',
                "turnover": request.POST.get("nse_turnover") == 'on',
            },
          
            {
                "name": "MINI",
                "exchange": request.POST.get("mini_exchange") == 'on',
                "symbols": request.POST.get("mini_symbol") == 'on',
                "turnover": request.POST.get("mini_turnover") == 'on',
            },
        ]
        user_name = request.POST.get("user_name")
        if MyUser.objects.filter(user_name=user_name).exists():
            messages.error(request, f"Username '{user_name}' already exists. Please choose a different one.")
            return redirect("Admin:add-user") 

        if request.user.user_type == "SuperAdmin":
            if (not request.POST.get("accountUser") == 'on'):
                create_user = MyUser.objects.create(user_type="Admin", **user_data)
                AdminModel.objects.create(user=create_user)
                messages.success(request, f"Admin create successfully.")
            elif request.POST.get("add_master") == 'on':
                selected_admin = AdminModel.objects.get(user__id=request.POST.get("selectedAdminName"))
                selected_admin.user.balance -=int(request.POST.get("credit"))
                selected_admin.user.save()
                create_user = MyUser.objects.create(user_type="Master", **user_data)
                try:
                    self_master = MyUser.objects.get(id=request.POST.get("selectedMasterName")).master_user
                    MastrModel.objects.create(master_user=create_user, admin_user=selected_admin,master_link=self_master)
                    self_master.master_user.balance -=int(request.POST.get("credit"))
                    self_master.master_user.save()
                    messages.success(request, f"Master create successfully.")
                except:
                    MastrModel.objects.create(master_user=create_user, admin_user=selected_admin)
                    messages.success(request, f"Master create successfully.")
            else:
                selected_admin = AdminModel.objects.get(user__id=request.POST.get("selectedAdminName"))
                create_user = MyUser.objects.create(user_type="Client", **user_data)
                try:
                    selected_master = MyUser.objects.get(id=request.POST.get("selectedMasterName")).master_user
                    ClientModel.objects.create(client=create_user, admin_create_client=selected_admin,master_user_link=selected_master)
                    selected_master.master_user.balance -=int(request.POST.get("credit"))
                    selected_master.master_user.save()
                    messages.success(request, f"Client create successfully.")   
                except:
                    ClientModel.objects.create(client=create_user, admin_create_client=selected_admin)
                    selected_admin.user.balance -=int(request.POST.get("credit"))
                    selected_admin.user.save()
                    messages.success(request, f"Client create successfully.")   
                    
                    
        elif request.user.user_type == "Admin":
            selected_admin = AdminModel.objects.get(user__id=request.user.id)
            if (request.POST.get("add_master") == 'on'):
                credit_amount = request.POST.get("credit")
                if credit_amount is not None and credit_amount.isdigit():
                    credit_amount = int(credit_amount)
                    if hasattr(request.user, 'balance') and request.user.balance <= credit_amount:
                        messages.error(request, f"Insufficient balance")
                        return redirect("Admin:add-user")
                request.user.balance -= credit_amount
                request.user.save() 
                create_user = MyUser.objects.create(user_type="Master", **user_data)
                MastrModel.objects.create(master_user=create_user, admin_user=selected_admin)
                messages.success(request, f"Master added successfully")
                return redirect("Admin:add-user")
            else:
                create_user = MyUser.objects.create(user_type="Client", **user_data)
                if (request.POST.get("selectedMasterName") == None or request.POST.get("selectedMasterName") == ""):
                    credit_amount = request.POST.get("credit")
                    if credit_amount is not None and credit_amount.isdigit():
                        credit_amount = int(credit_amount)
                        if hasattr(request.user, 'balance') and request.user.balance <= credit_amount:
                            messages.error(request, f"Insufficient balance")
                            return redirect("Admin:add-user")
                    request.user.balance -= credit_amount
                    request.user.save() 
                    ClientModel.objects.create(client=create_user, admin_create_client=selected_admin)
                    messages.success(request, f"Client added successfully")
                else:
                    user = MyUser.objects.get(id=request.POST.get("selectedMasterName"))
                    user.user_name
                    print("----===----",user)
                    selected_master = MastrModel.objects.get(master_user__id=request.POST.get("selectedMasterName"))
                    ClientModel.objects.create(client=create_user, master_user_link=selected_master, admin_create_client=selected_admin)
        elif request.user.user_type == "Master":
            credit_amount = request.POST.get("credit")
            if credit_amount is not None and credit_amount.isdigit():
                credit_amount = int(credit_amount)
                if hasattr(request.user, 'balance') and request.user.balance <= credit_amount:
                    messages.error(request, f"Insufficient balance")
                    return redirect("Admin:add-user")
                
            request.user.balance -= credit_amount
            request.user.save() 
            
            if limit == False:
                messages.error(request, f"Cannot create more users.")
                return redirect("Admin:add-user") 
            if limit:
                master_users_count = MastrModel.objects.filter(master_link=request.user.master_user).count()
                if master_users_count >= master_limit:
                    messages.error(request, f"Cannot create more Master users. Limit reached ({master_limit}).")
                    return redirect("Admin:add-user")
                client_users_count = ClientModel.objects.filter(master_user_link=request.user.master_user).count()
                if client_users_count >= client_limit:
                    messages.error(request, f"Cannot create more Client users. Limit reached ({client_limit}).")
                    return redirect("Admin:add-user")
            
            if (request.POST.get("add_master") == 'on'):
                current_master = MyUser.objects.get(id=request.user.id).master_user
                create_user = MyUser.objects.create(user_type="Master", **user_data)
                MastrModel.objects.create(master_user=create_user, admin_user=request.user.master_user.admin_user,master_link=current_master)
                messages.success(request, f"Master added successfully.")
            else:
                create_user = MyUser.objects.create(user_type="Client", **user_data)
                ClientModel.objects.create(client=create_user,master_user_link=request.user.master_user,admin_create_client=request.user.master_user.admin_user)
                messages.success(request, f"Client added successfully.")
     
        for exchange_data in exchanges:
            ExchangeModel.objects.create(
                user=create_user,
                symbol_name=exchange_data['name'],
                exchange=exchange_data['exchange'],
                symbols=exchange_data['symbols'],
                turnover=exchange_data['turnover']
            )
        return render(request, "User/add-user.html")
   

        
        
        
class ListUserView(View):
    def get(self , request):
        user = request.user
        if request.user.user_type == "Master":
            response_user = MyUser.objects.filter(id__in=set(ClientModel.objects.filter(master_user_link=user.master_user).values_list("client__id", flat=True)) | set(MastrModel.objects.filter(master_link=user.master_user).values_list("master_user__id", flat=True))).order_by("full_name")
        elif request.user.user_type == "Admin":
            master_ids = MastrModel.objects.filter(admin_user=user.admin_user).values_list("master_user__id", flat=True)
            client_ids = ClientModel.objects.filter(master_user_link__master_user__id__in=master_ids).values_list("client__id", flat=True)
            response_user = MyUser.objects.filter(id__in=set(master_ids) | set(client_ids))
        elif request.user.user_type == "SuperAdmin":
            response_user = MyUser.objects.exclude(id=request.user.id).order_by("full_name")
        return render(request, "User/list-user.html",{"client":response_user})
    

class DownloadCSVView(View):
    def get(self, request):
        user = request.user
        if request.user.user_type == "Master":
            user_clients = MyUser.objects.filter(id__in=set(ClientModel.objects.filter(master_user_link=user.master_user).values_list("client__id", flat=True)) | set(MastrModel.objects.filter(master_link=user.master_user).values_list("master_user__id", flat=True)))
        elif request.user.user_type == "Admin":
            master_ids = MastrModel.objects.filter(admin_user=user.admin_user).values_list("master_user__id", flat=True)
            client_ids = ClientModel.objects.filter(master_user_link__master_user__id__in=master_ids).values_list("client__id", flat=True)
            user_clients = MyUser.objects.filter(id__in=set(master_ids) | set(client_ids))
        elif request.user.user_type == "SuperAdmin":
            user_clients = MyUser.objects.exclude(id=request.user.id)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="user_data.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'Username', 'Name', 'Type', 'Parent', 'Credit', 'Balance', 'Bet', 'Close Only', 'Margin Sq', 'Status', 'Created Date', 'Last Login'])

        for client in user_clients:
            writer.writerow([
                client.user_name,
                client.full_name,
                client.user_type,
                client.user_name,
                client.credit,
                client.balance,
                client.bet,
                client.close_only,
                client.margin_sq,
                client.status,
                client.created_at,
                client.last_login])

        return response
    

    

class SearchUserView(View):
    def get(self, request):
        user = request.user
        if request.user.user_type == "Master":
            user_res = MyUser.objects.filter(id__in=set(ClientModel.objects.filter(master_user_link=user.master_user).values_list("client__id", flat=True)) | set(MastrModel.objects.filter(master_link=user.master_user).values_list("master_user__id", flat=True)))
        elif request.user.user_type == "Admin":
            master_ids = MastrModel.objects.filter(admin_user=user.admin_user).values_list("master_user__id", flat=True)
            client_ids = ClientModel.objects.filter(master_user_link__master_user__id__in=master_ids).values_list("client__id", flat=True)
            user_res = MyUser.objects.filter(id__in=set(master_ids) | set(client_ids))
        elif request.user.user_type == "SuperAdmin":
            user_res = MyUser.objects.exclude(id=request.user.id)
        return render(request, "User/search-user.html",{"user":user_res})
    
    
    
from django.http import JsonResponse

class SearchUsersView(View):
    def get(self, request):
        search_text = request.GET.get('search_text', '')
        current_user = request.user 
        
        if request.user.user_type == "Master":
            user_res = MyUser.objects.filter(id__in=set(ClientModel.objects.filter(master_user_link=user.master_user).values_list("client__id", flat=True)) | set(MastrModel.objects.filter(master_link=user.master_user).values_list("master_user__id", flat=True)))
        elif request.user.user_type == "Admin":
            master_ids = MastrModel.objects.filter(admin_user=user.admin_user).values_list("master_user__id", flat=True)
            client_ids = ClientModel.objects.filter(master_user_link__master_user__id__in=master_ids).values_list("client__id", flat=True)
            user_res = MyUser.objects.filter(id__in=set(master_ids) | set(client_ids))
        elif request.user.user_type == "SuperAdmin":
            user_res = MyUser.objects.exclude(id=request.user.id)
            
        matching_users = MyUser.objects.filter(
            user_name__icontains=search_text
        ).exclude(id=request.user.id)
        user_data = [{'user_name': user.user_name, 'user_id': user.id} for user in matching_users]
        return JsonResponse(user_data, safe=False)
    
    
    
    
    
    
#=============================User deatils New Window =======================#



class UserDeatilsViewById(View):
    def get(self, request, id):
        user = MyUser.objects.get(id=id)
        exchange_obj = ExchangeModel.objects.filter(user=user).values("symbol_name","exchange")
        return render(request, "components/user/user-deatils.html", {"id":id,"user":user, "exchange_obj":exchange_obj})

class UserDeatilsView(View):
    def get(self, request):
        return render(request, "components/user/user-deatils.html")

class TabTrades(View):
    def get(self, request, id):
        response = BuyAndSellModel.objects.filter(buy_sell_user__id=id).values("id","buy_sell_user__user_name", "quantity", "trade_type", "action", "price", "coin_name", "ex_change","created_at","is_pending","identifer", "order_method", "ip_address") 
        # if request.user.user_type == "SuperAdmin":
        #     response = BuyAndSellModel.objects.exclude(buy_sell_user__id=request.user.id).values("id","buy_sell_user__user_name", "quantity", "trade_type", "action", "price", "coin_name", "ex_change","created_at","is_pending","identifer", "order_method", "ip_address") 
        # if request.user.user_type == "Admin":
        #     user_keys = [request.user.id]
        #     child_clients = request.user.admin_user.admin_create_client.all().values_list("client__id", flat=True)
        #     user_keys += list(child_clients)
        #     response = BuyAndSellModel.objects.filter(buy_sell_user__id__in=user_keys).values("id","buy_sell_user__user_name", "quantity","trade_type","action","price","coin_name","ex_change","created_at","is_pending","identifer","order_method","ip_address")
        # if request.user.user_type == "Client":
        #     response = request.user.buy_sell_user.all().values("id","buy_sell_user__user_name", "quantity", "trade_type", "action", "price", "coin_name", "ex_change","created_at","is_pending","identifer", "order_method", "ip_address") 
        # elif request.user.user_type == "Master":
        #     user_keys = [request.user.id]
        #     child_clients = request.user.master_user.master_user_link.all().values_list("client__id", flat=True)
        #     user_keys += list(child_clients)
        #     response = BuyAndSellModel.objects.filter(buy_sell_user__id__in=user_keys).values("id","buy_sell_user__user_name", "quantity", "trade_type", "action", "price", "coin_name", "ex_change", "created_at","is_pending","identifer","order_method", "ip_address")
        return render(request, "components/user/trade.html",{"response":response})
    
    

    
    
class UserScriptMaster(View):
    def get(self, request, id):
        print("user_id", id)
        return render(request, "components/user/script-master.html")


class GropuSettingView(View):
    def get(self, request):
        return render(request, "components/user/group-setting.html")
    
    
class QuantitySettingView(View):
    def get(self, request):
        return render(request, "components/user/quantity-setting.html")
    

class BrkView(View):
    def get(self, request, id):
        
        return render(request, "components/user/brk.html",{"user":MyUser.objects.get(id=id)})
    
    
class TradeMargin(View):
    def get(self, request):
        return render(request, "components/user/trade-margin.html")
    

class CreditView(View):
    def get(self, request):
        return render(request, "components/user/")
    
class TabAccountSummary(View):
    def get(self, request):
        return render(request, "components/user/account-summary.html")
    
class TabSettlement(View):
    def get(self, request):
        return render(request, "components/user/settlement.html")
    
class RejectionLogView(View):
    def get(self, request, id):
        from_date = request.GET.get('from_date')
        to_date = request.GET.get('to_date')
        exchange = request.GET.get('exchange')
        symbol = request.GET.get('symbol')
        user = MyUser.objects.get(id=id)
        exchange_obj = ExchangeModel.objects.filter(user=user).values("symbol_name","exchange")
        rejection = user.buy_sell_user.filter(is_cancel=True).values("id","buy_sell_user__user_name", "quantity", "trade_type", "action", "price", "coin_name", "ex_change","created_at","is_pending","identifer", "message") 
        response = user.buy_sell_user.order_by('-coin_name').values('coin_name').distinct()
        if from_date:
            if to_date:
                rejection = rejection.filter(created_at__gte=from_date,created_at__lte=to_date,is_cancel=True)
        if exchange:
            rejection = rejection.filter(ex_change=exchange,is_cancel=True)
        
        if symbol:
            rejection = rejection.filter(coin_name=symbol,is_cancel=True)
            
        return render(request, "components/user/rejection-log.html",{"rejection":rejection,"exchange_obj":exchange_obj,"response":response})
    
class ShareDetailsView(View):
    def get(self, request):
        return render(request, "components/user/share-deatils.html")
    
    
class UserInfoView(View):
    def get(self , request):
        return render(request, "components/user/")
    
#==================================================#
class ChangePasswordView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return render(request, "register/change-password.html")
        return redirect("Admin:dashboard")
    
    def post(self, request):
        user_name = request.POST.get("user_name")
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")
        try:
            user = MyUser.objects.get(user_name=user_name)
        except MyUser.DoesNotExist:
            messages.error(request, "User does not exist!")
            return redirect("Admin:change-password")
        
        if new_password == confirm_password:
            user.set_password(new_password)
            user.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Password change succesfully")
            return redirect("Admin:dashboard")
        else:
            messages.error(request, "New passwords do not match!")
            return redirect("Admin:change-password")
        
       
    
    
class MarketWatchView(View):
    def get(self, request):
        user = request.user
        trade_coin_id = user.market_user.filter(trade_coin_id__isnull=False).values_list('trade_coin_id', flat=True)
        print("===>",trade_coin_id)
        return render(request, "view/market-watch.html",{'identifiers': list(set(list(trade_coin_id)))})
    

class TradesView(View):
    def get(self, request):
        params = request.GET
        user_keys = []
        user = request.user
        from_date = params.get('from_date')
        to_date = params.get('to_date')
        ex_change = params.get('ex_change')
        coin_name = params.get('coin_name')
        is_pending = params.get("is_pending")
        user_name = params.get("user_name")
        if request.user.user_type == "SuperAdmin":
            response = BuyAndSellModel.objects.exclude(buy_sell_user__id=request.user.id).values("id","buy_sell_user__user_name", "quantity", "trade_type", "action", "price", "coin_name", "ex_change", "created_at","updated_at","is_pending","identifer") 
        elif request.user.user_type == "Admin":
            user_keys = [request.user.id]
            child_clients = request.user.admin_user.admin_create_client.all().values_list("client__id", flat=True)
            user_keys += list(child_clients)
            response = BuyAndSellModel.objects.filter(buy_sell_user__id__in=user_keys).values("id","buy_sell_user__user_name", "quantity", "trade_type", "action", "price", "coin_name", "ex_change", "created_at","updated_at","is_pending","identifer")
        elif request.user.user_type == "Client":
            response = request.user.buy_sell_user.all().values("id","buy_sell_user__user_name", "quantity", "trade_type", "action", "price", "coin_name", "ex_change", "created_at","updated_at","is_pending","identifer") 
        else:
            user_keys = [request.user.id]
            child_clients = request.user.master_user.master_user_link.all().values_list("client__id", flat=True)
            user_keys += list(child_clients)
            response = BuyAndSellModel.objects.filter(buy_sell_user__id__in=user_keys).values("id","buy_sell_user__user_name", "quantity", "trade_type", "action", "price", "coin_name", "ex_change", "created_at","updated_at","is_pending","identifer")
        
        if from_date and to_date:
            from_date_obj = timezone.datetime.strptime(from_date, '%Y-%m-%d').replace(hour=0, minute=0, second=0, microsecond=0)
            to_date_obj = timezone.datetime.strptime(to_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59, microsecond=999999)
            response = response.filter(created_at__gte=from_date_obj, created_at__lte=to_date_obj)
            
        if ex_change:
            response = response.filter(ex_change=ex_change)
        if coin_name:
            response = response.filter(coin_name__icontains=coin_name)
        if user_name:
            response = response.filter(buy_sell_user__user_name=user_name)
            
        if is_pending:
            is_pending_bool = is_pending.lower() == 'true'
            response = response.filter(is_pending=is_pending_bool)
            
        user_coin_names = BuyAndSellModel.objects.filter(
            buy_sell_user__id__in=user_keys
        ).values_list('coin_name', flat=True).distinct()
        
        return render(request, "view/trades.html",{"response": response,"user_coin_names": user_coin_names,})
    
    
class OrdersView(View):
    def get(self, request):
        return render(request, "view/order.html")
    
from django.db.models import Avg, F, Subquery, OuterRef

class PositionsView(View):
    def get(self, request):
        params = request.GET
        user = request.user
        ex_change = params.get('ex_change')
        coin_name = params.get('coin_name')
        is_pending = params.get("is_pending")
        user_name = params.get("user_name")
        
        results = (
                user.buy_sell_user.all()
                .filter(is_pending=False, trade_status=True)
                .values('identifer','coin_name')
                .annotate(total_quantity=Sum('quantity'), avg_price=Avg('price'))
                .exclude(total_quantity=0)
            )
        
        if ex_change:
            results = results.filter(ex_change=ex_change)
        if coin_name:
            results = results.filter(coin_name__icontains=coin_name)
        if user_name:
            results = results.filter(buy_sell_user__user_name=user_name)
            
        user_coin_names = list(set(list(user.buy_sell_user.filter(
            buy_sell_user__id__in=[request.user.id] 
        ).values_list('coin_name', flat=True).distinct())))
        
        identifer = list(set(list(user.buy_sell_user.filter(
            buy_sell_user__id__in=[request.user.id] 
        ).values_list('identifer', flat=True).distinct())))
        print(user_coin_names)
        return render(request, "view/positions.html",{"response": list(results),"user_coin_names": user_coin_names, "identifer": identifer})
    
    
class ProfitAndLoss(View):
    def get(self, request):
        return render(request, "view/profit-loss.html")
    
    
    
class M2MProfitAndLoss(View):
    def get(self, request):
        return render(request, "view/M2Mprofit-loss.html")
    

class IntradayHistory(View):
    def get(self, request):
        return render(request, "view/intraday-history.html")
    

class RejectionLogTab(View):
    def get(self, request):
        user = request.user
        from_date = request.GET.get('from_date')
        to_date = request.GET.get('to_date')
        exchange = request.GET.get('exchange')
        symbol = request.GET.get('symbol')
        response = BuyAndSellModel.objects.exclude(buy_sell_user=user).order_by('-coin_name').values('coin_name').distinct()
        print("==",response)
        
        
        if request.user.user_type == "SuperAdmin":
            rejection = BuyAndSellModel.objects.exclude(buy_sell_user=user, is_cancel=True).values("id", "buy_sell_user__user_name", "quantity", "trade_type", "action", "price", "coin_name", "ex_change", "created_at", "is_pending", "identifer", "message","ip_address")
           
        elif request.user.user_type == "Admin":
            rejection = BuyAndSellModel.objects.exclude(buy_sell_user=user, is_cancel=True).values("id", "buy_sell_user__user_name", "quantity", "trade_type", "action", "price", "coin_name", "ex_change", "created_at", "is_pending", "identifer", "message","ip_address")

        elif request.user.user_type == "Master":
            user_keys = [request.user.id]
            child_clients = request.user.master_user.master_user_link.all().values_list("client__id", flat=True)
            user_keys += list(child_clients)
            rejection = BuyAndSellModel.objects.filter(buy_sell_user__id__in=user_keys).values("id", "buy_sell_user__user_name", "quantity", "trade_type", "action", "price", "coin_name", "ex_change", "created_at", "is_pending", "identifer", "message","ip_address")
        
        elif request.user.user_type == "Client":
            rejection = user.buy_sell_user.filter(is_cancel=True).values("id","buy_sell_user__user_name", "quantity", "trade_type", "action", "price", "coin_name", "ex_change","created_at","is_pending","identifer", "message") 
        
        if from_date:
            if to_date:
                rejection = rejection.filter(created_at__gte=from_date,created_at__lte=to_date,is_cancel=True)
        if exchange:
            rejection = rejection.filter(ex_change=exchange,is_cancel=True)
        
        if symbol:
            rejection = rejection.filter(coin_name=symbol,is_cancel=True)
       
        return render(request, "view/rejection-log.html",{"rejection":rejection, "response":response})
    
    
    
class LoginHistory(View):
    def get(self, request):
        user = request.user
        from_date = request.GET.get('from_date')
        to_date = request.GET.get('to_date')
        user_name = request.GET.get("user_name")
        
        if request.user.user_type == "SuperAdmin" or request.user.user_type == "Admin":
            user_obj = LoginHistoryModel.objects.exclude(user_history=request.user).values("ip_address", "method", "action", "user_history__user_name", "user_history__user_type", "user_history__id", "id","created_at")
        elif request.user.user_type == "Master":
            user_keys = [request.user.id]
            child_clients = request.user.master_user.master_user_link.all().values_list("client__id", flat=True)
            user_keys += list(child_clients)
            user_obj = LoginHistoryModel.objects.filter(user_history__id__in=user_keys).values("ip_address", "method", "action", "user_history__user_name", "user_history__user_type", "user_history__id", "id","created_at")
            
        elif request.user.user_type == "Client":
            user_obj = LoginHistoryModel.objects.filter(user_history__id=request.user.id).values("ip_address", "method", "action", "user_history__user_name", "user_history__user_type", "user_history__id", "id","created_at")
        if from_date and to_date:
            user_obj = user_obj.filter(created_at__gte=from_date, created_at__lte=to_date)
            
        if user_name:
            user_obj = user_obj.filter(user_history__user_name=user_name)

        user_obj = user_obj.filter(ip_address__icontains="")
        all_users = LoginHistoryModel.objects.filter(user_history__id=request.user.id).values("user_history__user_name").distinct()
        
        return render(request, "view/login-history.html",{"login_data":user_obj, "all_users":all_users})
    
       
    
    
    
class OpenPosition(View):
    def get(self, request):
        return render(request, "report/open-position.html")
    
    
    
class ManageTrades(View):
    def get(self, request):
        return render(request, "report/manage-trades.html")
    
    
    
class TradeAccount(View):
    def get(self, request):
        return render(request, "report/trade-account.html")
    
    

class SettlementView(View):
    def get(self, request):
        return render(request, "report/settlement.html")
    
    
    
class AccountSummary(View):
    def get(self, request):
        return render(request, "report/account-summary.html")
    
    
class BillGenerate(View):
    def get(self, request):
        return render(request, "report/bill-generate.html")
    

class LogsHistory(View):
    def get(self, request):
        return render(request, "report/logs-history.html")
    
    
class UserLogsNew(View):
    def get(self, request):
        return render(request, "report/user-logs-new.html")
    
    
class UserScriptPositionTrack(View):
    def get(self, request):
        return render(request, "report/user-script-position-track.html")
    
    
class UserScriptPositionTrackPl(View):
    def get(self, request):
        return render(request, "report/user-script-position-track-pl.html")
    
    
    
class ScriptQuantity(View):
    def get(self, request):
        return render(request, "report/script-quantity.html")
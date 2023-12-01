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



class LoginView(View):
    def get(self, request):
        if request.user.is_authenticated:
            if request.user is not None and request.user.user_type == "SuperAdmin":
                return redirect("Admin:dashboard")
            elif request.user is not None and request.user.user_type == "Admin":
                return redirect("Admin:dashboard")
            elif request.user is not None and request.user.user_type == "Master":
                return redirect("Admin:dashboard")
            elif request.user is not None and request.user.user_type == "Client":
                return redirect("Admin:dashboard")
        return render(request, "register/login.html")
    
    def post(self, request):
        params = request.POST
        user = authenticate(user_name=params["user_name"], password=params["password"])
        if user is not None and user.user_type == "SuperAdmin":
            login(request,user)
            return redirect("Admin:dashboard")
        elif user is not None and user.user_type == "Admin":
            login(request, user)
            return redirect("Admin:dashboard")
        elif user is not None and user.user_type == "Master":
            login(request, user)
            return redirect("Admin:dashboard")
        elif user is not None and user.user_type == "Client":
            login(request, user)
            return redirect("Admin:dashboard")
        else:
            messages.error(request, "Invalid credentials")
            return redirect("Admin:login")



class LogoutView(View):
    def get(self, request):
        logout(request)
        return redirect("Admin:login")
    
    
    
class Dashboard(View):
    def get(self, request):
        if request.user.is_authenticated:
            return render(request, "dashboard/dashboard.html")
        return redirect("Admin:login")
        
    
    
   
class AddUserView(View):
    def get(self, request):
        return render(request, "User/add-user.html")
    
    def post(self, request):
        user_name = request.POST.get("user_name")
        if MyUser.objects.filter(user_name=user_name).exists():
            messages.error(request, "User name already exists.")
            return redirect("Admin:add-user")
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
        }
        user_id = request.user.id
        print("sdfsdfksdfkdfkkdf",request.user.user_name)
        current_master = MyUser.objects.get(id=user_id).master_user
        if request.POST.get("add_master") == "on":
            admin_belongs = current_master.admin_user
            create_user = MyUser.objects.create(user_type="Master", **user_data)
            new_mastr_model = MastrModel.objects.create(master_user=create_user,
                admin_user=admin_belongs,
                master_link=current_master)
            new_mastr_model.save()
        else:
            create_user = MyUser.objects.create(user_type="Client",**user_data)
            ClientModel.objects.create(client=create_user, master_user_link=current_master)
            
        
        mcx_exchange = request.POST.get("mcx_exchange") == 'on'
        mcx_turnover = request.POST.get("mcx_turnover") == 'on'
        mcx_symbol = request.POST.get("mcx_symbol") == 'on'

        nse_exchange = request.POST.get("nse_exchange") == 'on'
        nse_turnover = request.POST.get("nse_turnover") == 'on'
        nse_symbol = request.POST.get("nse_symbol") == 'on'
        
        sgx_exchange = request.POST.get("sgx_exchange") == 'on'
        sgx_turnover = request.POST.get("sgx_turnover") == 'on'
        sgx_symbol = request.POST.get("sgx_symbol") == 'on'

        others_exchange = request.POST.get("others_exchange") == 'on'
        others_turnover = request.POST.get("others_turnover") == 'on'
        others_symbol = request.POST.get("others_symbol") == 'on'
        exchanges = [
        {
            "name": "MCX",
            "exchange": mcx_exchange,
            "symbols": mcx_symbol,
            "turnover": mcx_turnover,
        },
        {
            "name": "NSE",
            "exchange": nse_exchange,
            "symbols": nse_symbol,
            "turnover": nse_turnover,
        },
        {
            "name": "SGX",
            "exchange": sgx_exchange,
            "symbols": sgx_symbol,
            "turnover": sgx_turnover,
        },
        {
            "name": "OTHERS",
            "exchange": others_exchange,
            "symbols": others_symbol,
            "turnover": others_turnover,
        },]
        try:
            for exchange_data in exchanges:
                ExchangeModel.objects.create(
                    user=create_user,
                    symbol_name=exchange_data['name'],
                    exchange=exchange_data['exchange'],
                    symbols=exchange_data['symbols'],
                    turnover=exchange_data['turnover']
                )
            messages.success(request,"User added successfully")
            return redirect("Admin:dashboard")
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            return redirect("Admin:add-user")
        
       
        
        
        
class ListUserView(View):
    def get(self , request):
        user = request.user
        if request.user.user_type == "Master":
            response_user = MyUser.objects.filter(id__in=set(ClientModel.objects.filter(master_user_link=user.master_user).values_list("client__id", flat=True)) | set(MastrModel.objects.filter(master_link=user.master_user).values_list("master_user__id", flat=True)))
        elif request.user.user_type == "Admin":
            master_ids = MastrModel.objects.filter(admin_user=user.admin_user).values_list("master_user__id", flat=True)
            client_ids = ClientModel.objects.filter(master_user_link__master_user__id__in=master_ids).values_list("client__id", flat=True)
            response_user = MyUser.objects.filter(id__in=set(master_ids) | set(client_ids))
        return render(request, "User/list-user.html",{"client":response_user})
    

class DownloadCSVView(View):
    def get(self, request):
        user = request.user
        user_clients = MyUser.objects.filter(id__in=list(ClientModel.objects.filter(master_user_link=user.master_user).values_list("client__id", flat=True)) + list(MastrModel.objects.filter(master_link=user.master_user).values_list("master_user__id", flat=True)))
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="user_data.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'Username', 'Name', 'Type', 'Parent','Credit', 'Balance', 'Created Date', 'Last Login'
        ])
        for client in user_clients:
            writer.writerow([
                client.client.user_name,
                client.client.full_name,
                client.client.user_type,
                client.master_user_link.master_user.user_name,
                client.client.credit,
                client.client.balance,
                client.client.created_at,
                client.client.last_login,
            ])

        return response
    

class SearchUserView(View):
    def get(self, request):
        user = request.user
        all_user = ClientModel.objects.filter(master_user_link__master_user=user)
        return render(request, "User/search-user.html",{"user":all_user})
    
    
    
from django.http import JsonResponse

class SearchUsersView(View):
    def get(self, request):
        search_text = request.GET.get('search_text', '')
        current_user = request.user  # Get the current logged-in user
        try:
            master_model = MastrModel.objects.get(master_user=current_user)
        except MastrModel.DoesNotExist:
            return JsonResponse([], safe=False)  # No MasterModel found, return an empty response
        client_models = ClientModel.objects.filter(master_user_link=master_model)
        matching_users = MyUser.objects.filter(
            client__in=client_models,
            user_name__icontains=search_text
        )
        user_data = [{'user_name': user.user_name} for user in matching_users]
        return JsonResponse(user_data, safe=False)



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
        user = request.user
        from_date = params.get('from_date')
        to_date = params.get('to_date')
        ex_change = params.get('ex_change')
        coin_name = params.get('coin_name')
        is_pending = params.get("is_pending")
        user_name = params.get("user_name")
        
        user_keys = [request.user.id]
        child_clients = request.user.master_user.master_user_link.all().values_list("client__id", flat=True)
        user_keys += list(child_clients)
        response = BuyAndSellModel.objects.filter(buy_sell_user__id__in=user_keys).values("id","buy_sell_user__user_name", "quantity", "trade_type", "action", "price", "coin_name", "ex_change", "created_at","updated_at","is_pending","identifer")
        
        if from_date and to_date:
            from_date_obj = timezone.datetime.strptime(from_date, '%Y-%m-%d').replace(hour=0, minute=0, second=0, microsecond=0)
            to_date_obj = timezone.datetime.strptime(to_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59, microsecond=999999)
            response = response.filter(created_at__range=(from_date_obj, to_date_obj))
            
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
    

class RejectionLog(View):
    def get(self, request):
        return render(request, "view/rejection-log.html")
    
    
    
class LoginHistory(View):
    def get(self, request):
        return render(request, "view/login-history.html")
    
    
    
    
    
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
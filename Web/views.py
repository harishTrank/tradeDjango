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
import requests
from django.db.models import Avg, F, Subquery, OuterRef
from App.scheduler import NODEIP
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
        role = request.POST.get("selectServer")
        user = authenticate(username=user_name, password=password)
        try:
            if user.role != role:
                messages.error(request, "Invalid user role.")
                return redirect("Admin:login")
        except:
            pass
        
        if user is not None:
            if user.user_type in ["SuperAdmin", "Admin", "Master", "Client"]:
                login(request, user)
                if not user.status:
                    messages.error(request, "This user is deactivated.")
                else:
                    historyGenerator = LoginHistoryModel(user_history=user, ip_address=request.META.get('REMOTE_ADDR'), method='WEB', action='LOGIN')
                    historyGenerator.save()
                    if user.change_password == True:
                        return redirect("Admin:first-login")
                    return redirect("Admin:dashboard")
            else:
                messages.error(request, "Invalid user type")
                return redirect("Admin:login")
        messages.error(request, "Invalid username or password")
        return redirect("Admin:login")
    

class FirstLogin(View):
    def get(self, request):
        return render(request, "register/first-login.html")
    def post(self, request):
        user = request.user
        current_password = request.POST.get("current_password")
        new_password = request.POST.get("new_password")
        if not user.check_password(current_password):
            messages.error(request,"Invalid Old Password")
            return redirect("Admin:first-login")
        user.set_password(new_password)
        user.change_password = False
        user.save()
        update_session_auth_hash(request, user)
        return redirect("Admin:dashboard")
    

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
            "role":"AREX",
            "phone_number": request.POST.get("phone_number"),
            "city": request.POST.get("city"),
            "credit": request.POST.get("credit") if request.POST.get("credit") else 0,
            "balance": request.POST.get("credit") if request.POST.get("credit") else 0,
            "remark": request.POST.get("remark"),
            "password": make_password(request.POST.get("password")),
            "mcx": True if request.POST.get("mcx") and request.POST.get("mcx").lower() == 'on' else False,
            "nse": True if request.POST.get("nse") and request.POST.get("nse").lower() == 'on' else False,
            "sgx": True if request.POST.get("sgx") and request.POST.get("sgx").lower() == 'on' else False,
            "others": True if request.POST.get("others") and request.POST.get("others").lower() == 'on' else False,
            "mini": True if request.POST.get("mini") and request.POST.get("mini").lower() == 'on' else False,
            "change_password": True if request.POST.get("change_password") and request.POST.get("change_password").lower() == 'on' else False,
            "add_master": True if request.POST.get("add_master") and request.POST.get("add_master").lower() == 'on' else False,
            "margin_sq": True if request.POST.get("auto_square") and request.POST.get("auto_square").lower() == 'on' else False,
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
            if (request.POST.get("currentUserType") == 'Admin'):
                create_user = MyUser.objects.create(user_type="Admin", **user_data)
                AdminModel.objects.create(user=create_user)
                messages.success(request, f"Admin create successfully.")
            elif request.POST.get("currentUserType") == 'Master':
                selected_admin = AdminModel.objects.get(user__id=request.POST.get("selectedAdminName"))
                if selected_admin.user.balance <= int(request.POST.get("credit")):
                    messages.error(request, f"Insufficient balance.")
                    return redirect("Admin:add-user")
                selected_admin.user.balance -=int(request.POST.get("credit"))
                selected_admin.user.save()
                create_user = MyUser.objects.create(user_type="Master", **user_data, parent=selected_admin.user.user_name)
                try:
                    self_master = MyUser.objects.get(id=request.POST.get("selectedMasterName")).master_user
                    MastrModel.objects.create(master_user=create_user, admin_user=selected_admin,master_link=self_master)
                    if self_master.master_user.balance <= int(request.POST.get("credit")):
                        messages.error(request, f"Insufficient balance.")
                        return redirect("Admin:add-user")
                    self_master.master_user.balance -=int(request.POST.get("credit"))
                    self_master.master_user.save()
                    messages.success(request, f"Master create successfully.")
                except:
                    MastrModel.objects.create(master_user=create_user, admin_user=selected_admin)
                    UserCreditModal.objects.create(user_credit=selected_admin.user, opening=selected_admin.user.balance + int(request.POST.get("credit")), credit=0, debit=int(request.POST.get("credit")), closing=request.user.balance, transection=create_user, message="New master opening credit refrenece.")
                    messages.success(request, f"Master create successfully.")
            else:
                selected_admin = AdminModel.objects.get(user__id=request.POST.get("selectedAdminName"))
                try:
                    selected_master = MyUser.objects.get(id=request.POST.get("selectedMasterName")).master_user
                    create_user = MyUser.objects.create(user_type="Client", **user_data, parent=selected_master)
                    ClientModel.objects.create(client=create_user, admin_create_client=selected_admin,master_user_link=selected_master)
                    if selected_master.master_user.balance <= int(request.POST.get("credit")):
                        messages.error(request, f"Insufficient balance.")
                        return redirect("Admin:add-user")
                    selected_master.master_user.balance -=int(request.POST.get("credit"))
                    UserCreditModal.objects.create(user_credit=selected_master.master_user, opening=selected_master.master_user.balance + int(request.POST.get("credit")), credit=0, debit=int(request.POST.get("credit")), closing=selected_master.master_user.balance, transection=create_user, message="New client opening credit refrenece.")
                    selected_master.master_user.save()
                    messages.success(request, f"Client create successfully.")   
                except:
                    create_user = MyUser.objects.create(user_type="Client", **user_data, parent=selected_admin.user.user_name)
                    ClientModel.objects.create(client=create_user, admin_create_client=selected_admin)
                    if selected_admin.user.balance <= int(request.POST.get("credit")):
                        messages.error(request, f"Insufficient balance.")
                        return redirect(request, "Admin:add-user")
                    selected_admin.user.balance -=int(request.POST.get("credit"))
                    UserCreditModal.objects.create(user_credit=selected_admin.user, opening=selected_admin.user.balance + int(request.POST.get("credit")), credit=0, debit=int(request.POST.get("credit")), closing=selected_admin.user.balance, transection=create_user, message="New client opening credit refrenece.")
                    selected_admin.user.save()
                    messages.success(request, f"Client create successfully.")   
                    
                    
        elif request.user.user_type == "Admin":
            selected_admin = AdminModel.objects.get(user__id=request.user.id)
            if (request.POST.get("currentUserType") == 'Master'):
                credit_amount = request.POST.get("credit")
                if credit_amount is not None and credit_amount.isdigit():
                    credit_amount = int(credit_amount)
                    if hasattr(request.user, 'balance') and request.user.balance <= credit_amount:
                        messages.error(request, f"Insufficient balance")
                        return redirect("Admin:add-user")
                if request.user.balance <= int(request.POST.get("credit")):
                    messages.error(request, f"Insufficient balance.")
                    return redirect(request, "Admin:add-user")
                request.user.balance -= credit_amount
                request.user.save() 
                create_user = MyUser.objects.create(user_type="Master", **user_data, parent=selected_admin)
                MastrModel.objects.create(master_user=create_user, admin_user=selected_admin)
                messages.success(request, f"Master added successfully")
                return redirect("Admin:add-user")
            else:
                create_user = MyUser.objects.create(user_type="Client", **user_data, parent=selected_admin)
                if (request.POST.get("selectedMasterName") == None or request.POST.get("selectedMasterName") == ""):
                    credit_amount = request.POST.get("credit")
                    if credit_amount is not None and credit_amount.isdigit():
                        credit_amount = int(credit_amount)
                        if hasattr(request.user, 'balance') and request.user.balance <= credit_amount:
                            messages.error(request, f"Insufficient balance")
                            return redirect("Admin:add-user")
                        
                    if request.user.balance <= int(request.POST.get("credit")):
                        messages.error(request, f"Insufficient balance.")
                        return redirect(request, "Admin:add-user")
                    request.user.balance -= credit_amount
                    request.user.save() 
                    ClientModel.objects.create(client=create_user, admin_create_client=selected_admin)
                    messages.success(request, f"Client added successfully")
                else:
                    # user = MyUser.objects.get(id=request.POST.get("selectedMasterName"))
                    selected_master = MastrModel.objects.get(master_user__id=request.POST.get("selectedMasterName"))
                    ClientModel.objects.create(client=create_user, master_user_link=selected_master, admin_create_client=selected_admin)
                    
        elif request.user.user_type == "Master":
            credit_amount = request.POST.get("credit")
            if credit_amount is not None and credit_amount.isdigit():
                credit_amount = int(credit_amount)
                if hasattr(request.user, 'balance') and request.user.balance <= credit_amount:
                    messages.error(request, f"Insufficient balance")
                    return redirect("Admin:add-user")
            if request.user.balance <= int(request.POST.get("credit")):
                messages.error(request, f"Insufficient balance.")
                return redirect(request, "Admin:add-user")
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
            current_master = ""
            if (request.POST.get("currentUserType") == 'Master'):
                current_master = MyUser.objects.get(id=request.user.id).master_user
                create_user = MyUser.objects.create(user_type="Master", **user_data, parent=current_master)
                MastrModel.objects.create(master_user=create_user, admin_user=request.user.master_user.admin_user,master_link=current_master)
                messages.success(request, f"Master added successfully.")
            else:
                create_user = MyUser.objects.create(user_type="Client", **user_data, parent=current_master)
                ClientModel.objects.create(client=create_user,master_user_link=request.user.master_user,admin_create_client=request.user.master_user.admin_user)
                messages.success(request, f"Client added successfully.")
       
        exchangeList = []
        for exchange_data in exchanges:
            exchangeList.append(exchange_data['name'].upper())
            ExchangeModel.objects.create(
                user=create_user,
                symbol_name=exchange_data['name'],
                exchange=exchange_data['exchange'],
                symbols=exchange_data['symbols'],
                turnover=exchange_data['turnover']
            )
        
        if create_user.user_type == "Master" or create_user.user_type == "Client":
                    response = requests.post(f"http://{NODEIP}/api/tradeCoin/coins", json={
                        "coinList": exchangeList
                    })
                    if response.status_code // 100 == 2 and response.json()['success']:
                        for obj in response.json()['response']:
                            if "_" in obj['InstrumentIdentifier']:
                                obj['InstrumentIdentifier'] = obj['InstrumentIdentifier'].split("_")[1]
                                
                            if AdminCoinWithCaseModal.objects.filter(master_coins=create_user, identifier=obj['InstrumentIdentifier'], ex_change=obj['Exchange']).count() == 0:
                                AdminCoinWithCaseModal.objects.create(master_coins=create_user, ex_change=obj['Exchange'], identifier=obj['InstrumentIdentifier'], lot_size=obj["QuotationLot"])
        return render(request, "User/add-user.html")




class EditUserView(View):
    def get(self, request, id):
        user = MyUser.objects.get(id=id)
        exchange = ExchangeModel.objects.filter(user=user)
        mcx, nse, mini = False, False, False
        symbols_mcx, symbols_nse, symbols_mini = False, False, False
        turnover_mcx, turnover_nse, turnover_mini = False, False, False
        
        for entry in exchange:
            if entry.symbol_name == "MCX" and entry.exchange:
                mcx = True
            elif entry.symbol_name == "NSE" and entry.exchange:
                nse = True
            elif entry.symbol_name == "MINI" and entry.exchange:
                mini = True
                
        for entry in exchange:
            if entry.symbol_name == "MCX" and entry.symbols:
                symbols_mcx = True
            elif entry.symbol_name == "NSE" and entry.symbols:
                symbols_nse = True
            elif entry.symbol_name == "MINI" and entry.symbols:
                symbols_mini = True
                
        for entry in exchange:
            if entry.symbol_name == "MCX" and entry.turnover:
                turnover_mcx = True
            elif entry.symbol_name == "NSE" and entry.turnover:
                turnover_nse = True
            elif entry.symbol_name == "MINI" and entry.turnover:
                turnover_mini = True
        
        return render(request, "User/edit-user.html", { "user": user,
            "exchange": exchange,
            "mini": mini,
            "nse": nse,
            "mcx": mcx,
            "symbols_mcx":symbols_mcx,
            "symbols_nse":symbols_nse,
            "symbols_mini":symbols_mini,
            "turnover_mcx":turnover_mcx,
            "turnover_nse":turnover_nse,
            "turnover_mini":turnover_mini
        })

    def post(self, request, id):
        user = MyUser.objects.get(id=id)
        user_data = {
            "full_name": request.POST.get("full_name"),
            "user_name": request.POST.get("user_name"),
            "phone_number": request.POST.get("phone_number"),
            "parent": request.user.user_name,
            "city": request.POST.get("city"),
            "credit": request.POST.get("credit") if request.POST.get("credit") else 0,
            "remark": request.POST.get("remark"),
            "mcx": True if request.POST.get("mcx") and request.POST.get("mcx").lower() == 'on' else False,
            "nse": True if request.POST.get("nse") and request.POST.get("nse").lower() == 'on' else False,
            "sgx": True if request.POST.get("sgx") and request.POST.get("sgx").lower() == 'on' else False,
            "others": True if request.POST.get("others") and request.POST.get("others").lower() == 'on' else False,
            "mini": True if request.POST.get("mini") and request.POST.get("mini").lower() == 'on' else False,
            "change_password": True if request.POST.get("change_password") and request.POST.get("change_password").lower() == 'on' else False,
            "add_master": True if request.POST.get("add_master") and request.POST.get("add_master").lower() == 'on' else False,
            "margin_sq": True if request.POST.get("auto_square") and request.POST.get("auto_square").lower() == 'on' else False,
        }
        if request.POST.get("password") != "":
            user_data["password"]= make_password(request.POST.get("password"))
        
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
        if MyUser.objects.exclude(id=user.id).filter(user_name=user_name).exists():
            messages.error(request, f"Username '{user_name}' already exists for another user. Please choose a different one.")
            return redirect("Admin:list-user") 


        for key, value in user_data.items():
            setattr(user, key, value)
        user.save()
        
           
        for exchange_data in exchanges:
            exchange = ExchangeModel.objects.get(user=user, symbol_name=exchange_data['name'])
            exchange.exchange = exchange_data['exchange']
            exchange.symbols = exchange_data['symbols']
            exchange.turnover = exchange_data['turnover']
            exchange.save()
        messages.success(request , f"'{user_name}' edit successfully")
        return redirect("Admin:list-user")
   

        
        
class ListUserView(View):
    def get(self, request):
        filter_type = request.GET.get('filter_type')
        user = request.user
        requested_user_type = request.GET.get('user_type')
        user_status = request.GET.get('user_status')

        if user.user_type == "Master":
            master_clients = ClientModel.objects.filter(master_user_link=user.master_user).values_list("client__id", flat=True)
            master_users = MastrModel.objects.filter(master_link=user.master_user).values_list("master_user__id", flat=True)
            response_user = MyUser.objects.filter(id__in=list(master_clients) + list(master_users)).order_by("user_name")
        elif user.user_type == "Admin":
            master_ids = MastrModel.objects.filter(admin_user=user.admin_user).values_list("master_user__id", flat=True)
            client_ids = ClientModel.objects.filter(master_user_link__master_user__id__in=master_ids).values_list("client__id", flat=True)
            response_user = MyUser.objects.filter(id__in=list(master_ids) + list(client_ids))
        elif user.user_type == "SuperAdmin":
            response_user = MyUser.objects.exclude(id=user.id).order_by("user_name")
        if user.user_type == "Client":
            response_user = MyUser.objects.filter(id=request.user.id).order_by("user_name")

        if requested_user_type == "Master":
            response_user = response_user.filter(user_type="Master")
        elif requested_user_type == "Client":
            response_user = response_user.filter(user_type="Client")

        if user_status == "In Active":
            response_user = response_user.filter(status=False)
        elif user_status == "Active":
            response_user = response_user.filter(status=True)

        return render(request, "User/list-user.html", {"client": response_user})
    

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
        user = request.user
        
        if user.user_type == "Master":
            user_res = MyUser.objects.filter(id__in=set(ClientModel.objects.filter(master_user_link=user.master_user).values_list("client__id", flat=True)) | set(
                    MastrModel.objects.filter(
                        master_link=user.master_user
                    ).values_list("master_user__id", flat=True)
                )
            )
        elif user.user_type == "Admin":
            master_ids = MastrModel.objects.filter(admin_user=user.admin_user).values_list("master_user__id", flat=True)
            client_ids = ClientModel.objects.filter(
                master_user_link__master_user__id__in=master_ids
            ).values_list("client__id", flat=True)
            user_res = MyUser.objects.filter(
                id__in=set(master_ids) | set(client_ids)
            )
        elif user.user_type == "SuperAdmin":
            user_res = MyUser.objects.exclude(id=user.id)
            
        matching_users = user_res.filter(
            user_name__icontains=search_text
        ).exclude(id=user.id)
        
        user_data = [
            {'user_name': user.user_name, 'user_id': user.id} 
            for user in matching_users
        ]
        
        return JsonResponse(user_data, safe=False)


#=============================User deatils New Window =======================#



class UserDeatilsViewById(View):
    def get(self, request, id):
        user = MyUser.objects.get(id=id)
        exchange_obj = ExchangeModel.objects.filter(user=user).values("symbol_name","exchange")
        return render(request, "components/user/user-deatils.html", {"id":id,"user":user, "exchange_obj":exchange_obj})


class OpenPositionView(View):
    def get(self, request):
        result = (
                AccountSummaryModal.objects.filter(user_summary__id=request.GET.get("id"), particular=request.GET.get("coin"))
                .values('particular','quantity', 'buy_sell_type','price','average','summary_flg','amount','closing','open_qty','user_summary__user_name')
        )
        print(result)
        return render(request, "components/user/open-position.html")

 
class UserDeatilsView(View):
    def get(self, request):
        return render(request, "components/user/user-deatils.html")

class TabTrades(View):
    def get(self, request, id):
        from_date = request.GET.get('from_date')
        to_date = request.GET.get('to_date')
        status = request.GET.get('status')
        exchange = request.GET.get('exchange')
        symbol = request.GET.get('symbol')
        user = MyUser.objects.get(id=id)
        symbol_name = user.user.values("symbol_name")
        response = BuyAndSellModel.objects.filter(buy_sell_user__id=id).values("id","buy_sell_user__user_name", "quantity", "trade_type", "action", "price", "coin_name", "ex_change","created_at","is_pending","identifer", "order_method", "ip_address","is_cancel") 
        if from_date:
            if to_date:
                to_date = datetime.strptime(to_date, '%Y-%m-%d') + timedelta(days=1)
                response = response.filter(created_at__gte=from_date,created_at__lte=to_date)
        if exchange:
            response = response.filter(ex_change=exchange)
        if status == "Successful":
            response = response.filter(is_cancel=False)
        if status == "Pending":
            response = response.filter(is_pending=True)
        if status == "Cancelled":
            response = response.filter(is_cancel=True)
        return render(request, "components/user/trade.html",{"response":response,"symbol_name":symbol_name,"user":user.user_name,"id":id})
    

class TradeDownloadCsv(View):
    def get(self, request, id):
        user = MyUser.objects.get(id=id)
        buy_and_sell_instances = BuyAndSellModel.objects.filter(buy_sell_user=user)
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="trade.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'UserName', 'OrderTime', 'Symbol', 'Order Type', 'Price', 'Quantity','Ip address','Order Method','Trade Status'])
        for instance in buy_and_sell_instances:
            if instance.trade_status == True:
                trade_status = "Complete"
            else:
                trade_status = "Not Complete"
            writer.writerow([
                user.user_name,
                instance.created_at,
                instance.coin_name,
                instance.action,
                instance.price,
                instance.quantity,
                instance.ip_address,
                instance.order_method,
                trade_status])
        return response 

    
    
class UserScriptMaster(View):
    def get(self, request, id):
        return render(request, "components/user/script-master.html")


class GropuSettingView(View):
    def get(self, request):
        group = GroupSettingsModel.objects.all()
        return render(request, "components/user/group-setting.html",{"group":group})
    
class ScriptQuantitySetting(View):
    def get(self, request):
        
        group_settings = GroupSettingsModel.objects.get(id=1)  
        related_scripts = group_settings.group_user.all() 
        return render(request, "components/user/script-quantity-setting.html",{"script":related_scripts})
    
class QuantitySettingView(View):
    def get(self, request, id):
        user = MyUser.objects.get(id=id)
        exchange = ExchangeModel.objects.filter(user=user)
        return render(request, "components/user/quantity-setting.html",{"exchange":exchange,"id":id})
    

class BrkView(View):
    def get(self, request, id):
        user = MyUser.objects.get(id=id)
        exchange = user.user.values("symbol_name")
        return render(request, "components/user/brk.html",{"user":user, "exchange":exchange, "first":exchange.first()["symbol_name"]})
    
    
class TradeMarginTab(View):
    def get(self, request, id):
        user = MyUser.objects.get(id=id)
        exchange_obj = user.user.values("symbol_name")
        exchange = request.GET.get('exchange')
        trade_margin = request.GET.get('price')
        trade = user.admin_coins.all()
        if exchange:
            trade = trade.filter(ex_change=exchange)
        # if trade_margin:
        #     trade = trade.filter(trade_margin=trade_margin)
            
        return render(request, "components/user/trade-margin.html",{"trade_margin":trade,"exchange_obj":exchange_obj,"user":user,"first":exchange_obj.first()["symbol_name"]})
    

class CreditView(View):
    def get(self, request,id):
        user = MyUser.objects.get(id=id)
        from_date = request.GET.get('from_date')
        to_date = request.GET.get('to_date')
        coin_name = request.GET.get('coin_name')
        
        account_summary = user.user_credit.all().values('id','opening', 'credit', 'debit', 'closing', 'transection__user_name', "created_at", 'message')
        if from_date and to_date:
            from_date_obj = timezone.datetime.strptime(from_date, '%Y-%m-%d').replace(hour=0, minute=0, second=0, microsecond=0)
            to_date_obj = timezone.datetime.strptime(to_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59, microsecond=999999)
            account_summary = account_summary.filter(created_at__gte=from_date_obj, created_at__lte=to_date_obj)
        if coin_name:
            account_summary = account_summary.filter(particular__icontains=coin_name)
        return render(request, "components/user/credit.html",{"account_summary":account_summary,"id":user.id})





class CreditDownloadCSVView(View):
    def get(self, request, id):
        user = MyUser.objects.get(id=id)
        user_credit_instances = UserCreditModal.objects.filter(user_credit=user)
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="credit.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'Date Time', 'Opening', 'Credit', 'Debit', 'Closing', 'Comment','Transaction'])
        for instance in user_credit_instances:
            writer.writerow([
                instance.created_at,
                instance.opening,
                instance.credit,
                instance.debit,
                instance.closing,
                instance.message,
                instance.transection])
        return response
    
    


    
class TabAccountSummary(View):
    def get(self, request, id):
        from_date = request.GET.get('from_date')
        to_date = request.GET.get('to_date')
        user_name = request.GET.get('user_name')
        p_and_l = request.GET.get('p_and_l')
        brk = request.GET.get('brk')
        credit = request.GET.get('credit')
        user = MyUser.objects.get(id=id)
        account_summary = user.user_summary.all().values('id','user_summary__user_name', 'particular', 'quantity', 'buy_sell_type', 'price', 'average', 'summary_flg', 'amount', 'closing', 'open_qty','created_at')
        if from_date:
            if to_date:
                to_date = datetime.strptime(to_date, '%Y-%m-%d') + timedelta(days=1)
                account_summary = account_summary.filter(created_at__gte=from_date,created_at__lte=to_date)
        
        if p_and_l == 'on' and brk == 'on':   
            account_summary = account_summary.filter(Q(summary_flg__icontains='Profit/Loss') | Q(summary_flg__icontains='Brokerage'))
       
        elif p_and_l == 'on':
            account_summary = account_summary.filter(summary_flg__icontains='Profit/Loss')
        elif brk == 'on':
            account_summary = account_summary.filter(summary_flg__icontains='Brokerage')
        return render(request, "components/user/account-summary.html",{"account_summary":account_summary,"id":user.id})
  
  
  
class AccountSummaryTabDownloadCSV(View):
    def get(self, request, id):
        user = MyUser.objects.get(id=id)
        user_summary_instances = AccountSummaryModal.objects.filter(user_summary=user)
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="account-summary.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'Date', 'Username', 'Particular', 'Qty', 'Buy/Sell', 'Price','Average Price','Type','Amount'])
        for instance in user_summary_instances:
            writer.writerow([
                instance.created_at,
                user.user_name,
                instance.particular,
                instance.quantity,
                instance.buy_sell_type,
                instance.price,
                instance.average,
                instance.summary_flg,
                instance.amount])
        return response
  
  
  
    
class TabSettlement(View):
    def get(self, request ,id):
        user = MyUser.objects.get(id=id)
        return render(request, "components/user/settlement.html",{"user_id":id,"user":user})
    
class RejectionLogView(View):
    def get(self, request, id):
        print("sdsddsdd")
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
            
        return render(request, "components/user/rejection-log.html",{"rejection":rejection,"exchange_obj":exchange_obj,"response":response, "id":id})


class RejectionDownloadCSVView(View):
    def get(self, request, id):
        user = MyUser.objects.get(id=id)
        buy_and_sell_instances = BuyAndSellModel.objects.filter(buy_sell_user=user,is_cancel=True)
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="rejection.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'Date', 'Message', 'Username', 'Symbol', 'Type', 'Quantity','Price'])
        for instance in buy_and_sell_instances:
            writer.writerow([
                instance.created_at,
                instance.message,
                user.user_name,
                instance.coin_name,
                instance.trade_type,
                instance.quantity,
                instance.price])
        return response





class ShareDetailsView(View):
    def get(self, request):
        return render(request, "components/user/share-deatils.html")
    
    
class UserInfoView(View):
    def get(self , request, id):
        user = MyUser.objects.get(id=id)
        return render(request, "components/user/user-info.html",{"user":user})
    
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
        coin_type = user.user.filter(exchange=True).values_list("symbol_name", flat=True)
        return render(request, "view/market-watch.html",{'identifiers': list(set(list(trade_coin_id))), "coin_type":list(coin_type)})
    

class SybolsView(View):
    def get(self, request):
        user = request.user
        coin_type = user.user.filter(exchange=True).values_list("symbol_name", flat=True)
        return render(request, "view/market-picture.html",{"coin_type":list(coin_type)})


    

class TradesView(View):
    def get(self, request):
        params = request.GET
        user_keys = []
        from_date = params.get('from_date')
        to_date = params.get('to_date')
        ex_change = params.get('ex_change')
        coin_name = params.get('coin_name')
        is_pending = params.get("is_pending")
        user_name = params.get("user_name")
        if request.user.user_type == "SuperAdmin":
            response = BuyAndSellModel.objects.exclude(buy_sell_user__id=request.user.id).filter(is_cancel=False).values("id","buy_sell_user__user_name", "quantity", "trade_type", "action", "price", "coin_name", "ex_change", "created_at","updated_at","is_pending","identifer","order_method","ip_address") 
            user_list = MyUser.objects.exclude(id=request.user.id).filter(role=request.user.role)

        elif request.user.user_type == "Admin":
            user_keys = [request.user.id]
            child_clients = request.user.admin_user.admin_create_client.all().values_list("client__id", flat=True)
            relative_master = MastrModel.objects.filter(admin_user__user__id=request.user.id).values_list("master_user__id", flat=True)
            user_keys += list(child_clients) + list(relative_master)
            user_list = MyUser.objects.filter(id__in=user_keys)
            response = BuyAndSellModel.objects.filter(buy_sell_user__id__in=user_keys, is_cancel=False).values("id","buy_sell_user__user_name", "quantity", "trade_type", "action", "price", "coin_name", "ex_change", "created_at","updated_at","is_pending","identifer","order_method","ip_address")
        elif request.user.user_type == "Client":
            user_list = []
            response = request.user.buy_sell_user.all().values("id","buy_sell_user__user_name", "quantity", "trade_type", "action", "price", "coin_name", "ex_change", "created_at","updated_at","is_pending","identifer","order_method","ip_address") 
        else:
            user_keys = [request.user.id]
            child_clients = request.user.master_user.master_user_link.all().values_list("client__id", flat=True)
            user_keys += list(child_clients)
            user_list = MyUser.objects.filter(id__in=user_keys)
            response = BuyAndSellModel.objects.filter(buy_sell_user__id__in=user_keys, is_cancel=False).values("id","buy_sell_user__user_name", "quantity", "trade_type", "action", "price", "coin_name", "ex_change", "created_at","updated_at","is_pending","identifer","order_method","ip_address")
        
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

        if request.user.user_type == "SuperAdmin":
            user_coin_names = BuyAndSellModel.objects.filter(is_cancel=False).order_by('coin_name').values('coin_name').distinct()
        else:
            user_coin_names = BuyAndSellModel.objects.filter(
                buy_sell_user__id__in=user_keys, is_cancel=False
            ).order_by('coin_name').values('coin_name').distinct()
        return render(request, "view/trades.html",{"response": list(response),"user_coin_names": user_coin_names,"filter_data":list({'buy_sell_user__user_name' }), "user_list": user_list})
    

class ViewTradesDownloadCSV(View):
     def get(self, request):
        user = request.user
        if request.user.user_type == "SuperAdmin":
            buy_and_sell_records = BuyAndSellModel.objects.filter(buy_sell_user__user_type="Client")
        elif request.user.user_type == "Admin":
            buy_and_sell_records = BuyAndSellModel.objects.filter(buy_sell_user__client__admin_create_client=user.admin_user)
        elif request.user.user_type == "Master":
            buy_and_sell_records = BuyAndSellModel.objects.filter(buy_sell_user__client__master_user_link=user.master_user)
        elif request.user.user_type == "Client":
            buy_and_sell_records = BuyAndSellModel.objects.filter(buy_sell_user=user)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="trades.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'Execution Time', 'Username', 'Symbol', 'Type','Quantity', 'Price', 'Order Time', 'IPAddress', 'Order Method'])

        for record in buy_and_sell_records:
            writer.writerow([
                record.created_at,
                record.buy_sell_user.user_name,
                record.coin_name,
                record.action,
                record.quantity,
                record.price,
                record.created_at,
                record.ip_address,
                record.order_method,
            ])
        return response

    
    
class OrdersView(View):
    def get(self, request):
        params = request.GET
        user_keys = []
        from_date = params.get('from_date')
        to_date = params.get('to_date')
        ex_change = params.get('ex_change')
        coin_name = params.get('coin_name')
        is_pending = params.get("is_pending")
        user_name = params.get("user_name")
        if request.user.user_type == "SuperAdmin":
            response = BuyAndSellModel.objects.exclude(buy_sell_user__id=request.user.id).values("id","buy_sell_user__user_name", "quantity", "trade_type", "action", "price", "coin_name", "ex_change", "created_at","updated_at","is_pending","identifer","order_method","ip_address") 
            user_list = MyUser.objects.exclude(id=request.user.id).filter(role=request.user.role)

        elif request.user.user_type == "Admin":
            user_keys = [request.user.id]
            child_clients = request.user.admin_user.admin_create_client.all().values_list("client__id", flat=True)
            relative_master = MastrModel.objects.filter(admin_user__user__id=request.user.id).values_list("master_user__id", flat=True)
            user_keys += list(child_clients) + list(relative_master)
            user_list = MyUser.objects.filter(id__in=user_keys)
            response = BuyAndSellModel.objects.filter(buy_sell_user__id__in=user_keys).values("id","buy_sell_user__user_name", "quantity", "trade_type", "action", "price", "coin_name", "ex_change", "created_at","updated_at","is_pending","identifer","order_method","ip_address")
        elif request.user.user_type == "Client":
            user_list = []
            response = request.user.buy_sell_user.all().values("id","buy_sell_user__user_name", "quantity", "trade_type", "action", "price", "coin_name", "ex_change", "created_at","updated_at","is_pending","identifer","order_method","ip_address") 
        else:
            user_keys = [request.user.id]
            child_clients = request.user.master_user.master_user_link.all().values_list("client__id", flat=True)
            user_keys += list(child_clients)
            user_list = MyUser.objects.filter(id__in=user_keys)
            response = BuyAndSellModel.objects.filter(buy_sell_user__id__in=user_keys).values("id","buy_sell_user__user_name", "quantity", "trade_type", "action", "price", "coin_name", "ex_change", "created_at","updated_at","is_pending","identifer","order_method","ip_address")
        
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

        if request.user.user_type == "SuperAdmin":
            user_coin_names = BuyAndSellModel.objects.all().order_by('coin_name').values('coin_name').distinct()
        else:
            user_coin_names = BuyAndSellModel.objects.filter(
                buy_sell_user__id__in=user_keys
            ).order_by('coin_name').values('coin_name').distinct()
            
        return render(request, "view/order.html", {"response": list(response),"user_coin_names": user_coin_names,"filter_data":list({'buy_sell_user__user_name' }), "user_list": user_list})
    
    
    
class OrderDownloadCSVView(View):
    def get(self, request):
        user = request.user
        if request.user.user_type == "SuperAdmin":
            buy_and_sell_records = BuyAndSellModel.objects.filter(buy_sell_user__user_type="Client")
        elif request.user.user_type == "Admin":
            buy_and_sell_records = BuyAndSellModel.objects.filter(buy_sell_user__client__admin_create_client=user.admin_user)
        elif request.user.user_type == "Master":
            buy_and_sell_records = BuyAndSellModel.objects.filter(buy_sell_user__client__master_user_link=user.master_user)
        elif request.user.user_type == "Client":
            buy_and_sell_records = BuyAndSellModel.objects.filter(buy_sell_user=user)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="orders.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'Username', 'Symbol', 'Type','Quantity', 'Price', 'Order Time', 'IPAddress', 'Order Method'])

        for record in buy_and_sell_records:
            writer.writerow([
                record.buy_sell_user.user_name,
                record.coin_name,
                record.action,
                record.quantity,
                record.price,
                record.created_at,
                record.ip_address,
                record.order_method,
            ])
        return response
    
    
    
from django.db.models.functions import Coalesce
from django.db.models import Sum, Avg, Case, When, F, Value, FloatField

class PositionsView(View):
    def get(self, request):
        params = request.GET
        ex_change = params.get('ex_change')
        coin_name = params.get('coin_name')
        user_name = params.get("user_name")

        response = (
            BuyAndSellModel.objects.filter(trade_status=True, is_pending=False, is_cancel=False)
            .values('identifer','coin_name', 'buy_sell_user__user_name')
            .annotate(
                total_quantity=Sum('quantity'),
                avg_buy_price=Coalesce(
                    Avg(Case(When(quantity__gt=0, then='price'), output_field=FloatField())),
                    Value(0.0)
                ),
                avg_sell_price=Coalesce(
                    Avg(Case(When(quantity__lt=0, then='price'), output_field=FloatField())),
                    Value(0.0)
                )
            ).exclude(total_quantity=0)
        )

        if request.user.user_type == "SuperAdmin":
            response = response.exclude(buy_sell_user__id=request.user.id)
            user_list = MyUser.objects.exclude(id=request.user.id).filter(role=request.user.role)

        elif request.user.user_type == "Admin":
            user_keys = [request.user.id]
            child_clients = request.user.admin_user.admin_create_client.all().values_list("client__id", flat=True)
            relative_master = MastrModel.objects.filter(admin_user__user__id=request.user.id).values_list("master_user__id", flat=True)
            user_keys += list(child_clients) + list(relative_master)
            user_list = MyUser.objects.filter(id__in=user_keys)
            response = response.filter(buy_sell_user__id__in=user_keys)
        elif request.user.user_type == "Client":
            user_list = []
            user_keys = []
            response = response.filter(buy_sell_user__id=request.user.id)
        else:
            user_keys = [request.user.id]
            child_clients = request.user.master_user.master_user_link.all().values_list("client__id", flat=True)
            user_keys += list(child_clients)
            user_list = MyUser.objects.filter(id__in=user_keys)
            response = response.filter(buy_sell_user__id__in=user_keys)
        
        if ex_change:
            response = response.filter(ex_change=ex_change)
        if coin_name:
            response = response.filter(coin_name__icontains=coin_name)
        if user_name:
            response = response.filter(buy_sell_user__user_name=user_name)
            
        identifer = list(set(list(response.values_list('identifer', flat=True))))

        if request.user.user_type == "SuperAdmin":
            user_coin_names = BuyAndSellModel.objects.all().order_by('coin_name').values('coin_name').distinct()
        else:
            user_coin_names = BuyAndSellModel.objects.filter(
                buy_sell_user__id__in=user_keys
            ).order_by('coin_name').values('coin_name').distinct()
        
        return render(request, "view/positions.html",{"response": list(response),"user_coin_names": user_coin_names, "identifer": identifer, "user_list": user_list})
    
    
class ProfitAndLoss(View):
    def get(self, request):
        params = request.GET
        user_name = params.get("user_name")
        if request.user.user_type == "SuperAdmin":
            user_list = MyUser.objects.exclude(id=request.user.id).filter(role=request.user.role)

        elif request.user.user_type == "Admin":
            user_keys = [request.user.id]
            child_clients = request.user.admin_user.admin_create_client.all().values_list("client__id", flat=True)
            relative_master = MastrModel.objects.filter(admin_user__user__id=request.user.id).values_list("master_user__id", flat=True)
            user_keys += list(child_clients) + list(relative_master)
            user_list = MyUser.objects.filter(id__in=user_keys)
        elif request.user.user_type == "Client":
            user_list = []
        else:
            user_keys = [request.user.id]
            child_clients = request.user.master_user.master_user_link.all().values_list("client__id", flat=True)
            user_keys += list(child_clients)
            user_list = MyUser.objects.filter(id__in=user_keys)

        if user_name:
            response = response.filter(buy_sell_user__user_name=user_name)
        return render(request, "view/profit-loss.html", {"user_list": user_list})
    
    
class M2MProfitAndLoss(View):
    def get(self, request):
        user = request.user
        user_name = request.GET.get("user_name")
        if request.user.user_type == "SuperAdmin":
            user_obj = MyUser.objects.filter(user_type="Client")
        elif request.user.user_type == "Admin":
            admin_obj = user.admin_user.admin_create_client.all().values_list("client__id",flat=True)
            user_obj = MyUser.objects.filter(id__in=admin_obj)
        elif request.user.user_type == "Master":
            master_obj = user.master_user.master_user_link.all().values_list("client__id",flat=True)
            user_obj = MyUser.objects.filter(id__in=master_obj)
        else:
            client_obj = [request.user.id]
            user_obj = [request.user]
        if user_name:
            user_obj = user_obj.filter(user_name=user_name)
        return render(request, "view/M2Mprofit-loss.html",{"user":user,"user_obj":user_obj})
    

class IntradayHistory(View):
    def get(self, request):
        return render(request, "view/intraday-history.html")
    

class RejectionLogTab(View):
    def get(self, request):
        user = request.user
        from_date = request.GET.get('from_date')
        to_date = request.GET.get('to_date')
        exchange = request.GET.get('exchange')
        user_name = request.GET.get('user_name')
        symbol = request.GET.get('symbol')
        response = BuyAndSellModel.objects.exclude(buy_sell_user=user).order_by('-coin_name').values('coin_name').distinct()
        
        rejection = BuyAndSellModel.objects.filter(is_cancel=True)
        if request.user.user_type == "SuperAdmin":
            rejection = BuyAndSellModel.objects.exclude(buy_sell_user=user).values("id", "buy_sell_user__user_name", "quantity", "trade_type", "action", "price", "coin_name", "ex_change", "created_at", "is_pending", "identifer", "message","ip_address")
            rejection = rejection.filter(is_cancel=True)
            user = MyUser.objects.exclude(id=request.user.id).filter(role=request.user.role)

        elif request.user.user_type == "Admin":
            user_keys = [request.user.id]
            child_clients = request.user.admin_user.admin_create_client.all().values_list("client__id", flat=True)
            user_keys += list(child_clients)
            
            rejection = BuyAndSellModel.objects.exclude(buy_sell_user__id__in=user_keys).values("id", "buy_sell_user__user_name", "quantity", "trade_type", "action", "price", "coin_name", "ex_change", "created_at", "is_pending", "identifer", "message","ip_address")
            rejection = rejection.filter(is_cancel=True)
            user = MyUser.objects.filter(id__in=user_keys)
        elif request.user.user_type == "Master":
            user_keys = [request.user.id]
            child_clients = request.user.master_user.master_user_link.all().values_list("client__id", flat=True)
            user_keys += list(child_clients)
            rejection = BuyAndSellModel.objects.filter(buy_sell_user__id__in=user_keys, is_cancel=True).values("id", "buy_sell_user__user_name", "quantity", "trade_type", "action", "price", "coin_name", "ex_change", "created_at", "is_pending", "identifer", "message","ip_address")
            user = BuyAndSellModel.objects.exclude(buy_sell_user=user, is_cancel=True).values_list("buy_sell_user__user_name", flat=True)

        elif request.user.user_type == "Client":
            rejection = user.buy_sell_user.filter(is_cancel=True).values("id","buy_sell_user__user_name", "quantity", "trade_type", "action", "price", "coin_name", "ex_change","created_at","is_pending","identifer", "message") 
            user = BuyAndSellModel.objects.filter(buy_sell_user=user, is_cancel=True).values_list("buy_sell_user__user_name", flat=True)

        if from_date:
            if to_date:
                to_date = datetime.strptime(to_date, '%Y-%m-%d') + timedelta(days=1)
                rejection = rejection.filter(created_at__gte=from_date,created_at__lte=to_date)
        if exchange:
            rejection = rejection.filter(ex_change=exchange)
        
        if symbol:
            rejection = rejection.filter(coin_name__icontains=symbol)
        
        if user_name:
            rejection = rejection.filter(buy_sell_user__user_name=user_name)
        if 'download_csv' in request.GET:
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="rejection-log.csv"'
            writer = csv.writer(response)
            
            writer.writerow([
                'Date', 'Message', 'Username', 'Symbol', 'Type Quantity', 'Price','IP Address'])
            for reject in rejection:
                writer.writerow([
                    reject['created_at'],
                    reject['message'],
                    reject['buy_sell_user__user_name'],
                    reject['coin_name'],
                    reject['action'],
                    reject['quantity'],
                    reject['price'],
                    reject['ip_address']
                ])
            return response

        return render(request, "view/rejection-log.html",{"rejection":rejection, "response":response, "user":list(set(user))})
    
    
    
class LoginHistory(View):
    def get(self, request):
        user = request.user
        from_date = request.GET.get('from_date')
        to_date = request.GET.get('to_date')
        user_name = request.GET.get("user_name")
        
        if request.user.user_type == "SuperAdmin" or request.user.user_type == "Admin":
            user_obj = LoginHistoryModel.objects.exclude(user_history=request.user).values("ip_address", "method", "action", "user_history__user_name", "user_history__user_type", "user_history__id", "id","created_at")
            user_names = MyUser.objects.exclude(id=request.user.id).filter(role=request.user.role)
            
        elif request.user.user_type == "Master":
            user_keys = [request.user.id]
            child_clients = request.user.master_user.master_user_link.all().values_list("client__id", flat=True)
            user_keys += list(child_clients)
            user_obj = LoginHistoryModel.objects.filter(user_history__id__in=user_keys).values("ip_address", "method", "action", "user_history__user_name", "user_history__user_type", "user_history__id", "id","created_at")
            user_names = MyUser.objects.filter(id__in=user_keys)
            
        elif request.user.user_type == "Client":
            user_names = []
            user_obj = LoginHistoryModel.objects.filter(user_history__id=request.user.id).values("ip_address", "method", "action", "user_history__user_name", "user_history__user_type", "user_history__id", "id","created_at")
        if from_date:
            if to_date:
                to_date = datetime.strptime(to_date, '%Y-%m-%d') + timedelta(days=1)
                user_obj = user_obj.filter(created_at__gte=from_date,created_at__lte=to_date)
            
        if user_name:
            user_obj = user_obj.filter(user_history__user_name=user_name)

        user_obj = user_obj.filter(ip_address__icontains="")
        # all_users = LoginHistoryModel.objects.filter(user_history__id=request.user.id).values("user_history__user_name").distinct()
        
        if 'download_csv' in request.GET:
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="user_data.csv"'
            writer = csv.writer(response)
            writer.writerow([
                'Login Date', 'Logout Date', 'Username', 'User Type', 'IP Address', 'Device ID'])
            for user in user_obj:
                writer.writerow([
                    user['created_at'],
                    user['action'],
                    user['user_history__user_name'],
                    user['user_history__user_type'],
                    user['ip_address'],
                    user['method']
                ])
            return response
        return render(request, "view/login-history.html",{"login_data":user_obj, "user_names":user_names})
    
       
    
    
    
class OpenPosition(View):
    def get(self, request):
        if request.user.user_type == "Master":
            master_child = MastrModel.objects.filter(master_link=request.user.master_user).values_list('master_user__user_name', flat=True)
            client_child = ClientModel.objects.filter(master_user_link=request.user.master_user).values_list('client__user_name', flat=True)
            user_names = list(master_child) + list(client_child)
            user_names.append(request.user.user_name)
        elif request.user.user_type == "SuperAdmin":
            user_names = MyUser.objects.filter(role=request.user.role).exclude(id=request.user.id).values_list("user_name", flat=True)
        elif request.user.user_type == "Admin":
            masters = request.user.admin_user.admin_user.all().values_list('master_user__user_name', flat=True)
            clients = request.user.admin_user.admin_create_client.all().values_list('client__user_name', flat=True)
            user_names = list(masters) + list(clients)
        else:
            user_names = [request.user.user_name]
        exchange = request.user.user.filter(exchange=True).values_list("symbol_name", flat=True)
        return render(request, "report/open-position.html", {"user_names": user_names, "exchange": exchange})
    
    
class ManageTrades(View):
    def get(self, request):
        user = request.user
        from_date = request.GET.get('from_date')
        to_date = request.GET.get('to_date')
        status = request.GET.get('status')
        exchange = request.GET.get('exchange')
        user_name = request.GET.get('user_name')
        user_obj = MyUser.objects.get(id=user.id)
        
        if request.user.user_type == "SuperAdmin":
            client = ClientModel.objects.all().values_list("client__id",flat=True)
            user = MyUser.objects.filter(user_type="Client")
        elif request.user.user_type == "Admin":
            client = user.admin_user.admin_create_client.all().values_list("client__id",flat=True)
            user = MyUser.objects.filter(id__in=client)
        elif request.user.user_type == "Master":
            client = user.master_user.master_user_link.all().values_list("client__id",flat=True)
            user = MyUser.objects.filter(id__in=client)
        elif request.user.user_type == "Client":
            client = [request.user.id]
            user = [request.user]
        
        manage_trades = BuyAndSellModel.objects.filter(
           buy_sell_user__id__in=client
        ).values(
            "id", "buy_sell_user__user_name", "quantity", "trade_type", "action", "price", 
            "coin_name", "ex_change", "created_at", "is_pending", "identifer", 
            "order_method", "ip_address", "is_cancel"
        )
        symbol_name = user_obj.user.values("symbol_name")
        
        if from_date and to_date:
            to_date = datetime.strptime(to_date, '%Y-%m-%d') + timedelta(days=1)
            manage_trades = manage_trades.filter(created_at__gte=from_date, created_at__lte=to_date)
                
        if status == "Pending":
            manage_trades = manage_trades.filter(trade_status=True)
        else:
            manage_trades = manage_trades.filter(trade_status=False)
            
        if exchange:
            manage_trades = manage_trades.filter(ex_change=exchange)
        if user_name:
            manage_trades = manage_trades.filter(buy_sell_user__user_name=user_name)

        return render(request, "report/manage-trades.html", {"manage_trades": manage_trades, "symbol_name": symbol_name, "user": user})

    
    
    
class TradesDownloadCSVView(View):
    def get(self, request):
        user = request.user
        if request.user.user_type == "SuperAdmin":
            buy_and_sell_records = BuyAndSellModel.objects.filter(buy_sell_user__user_type="Client")
        elif request.user.user_type == "Admin":
            buy_and_sell_records = BuyAndSellModel.objects.filter(buy_sell_user__client__admin_create_client=user.admin_user)
        elif request.user.user_type == "Master":
            buy_and_sell_records = BuyAndSellModel.objects.filter(buy_sell_user__client__master_user_link=user.master_user)
        elif request.user.user_type == "Client":
            buy_and_sell_records = BuyAndSellModel.objects.filter(buy_sell_user=user)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="trades.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'Username', 'Symbol', 'Type', 'Quantity', 'Price', 'Status', 'Order Time', 'IPAddress', 'Reference Price'])

        for record in buy_and_sell_records:
            writer.writerow([
                record.buy_sell_user.user_name,
                record.coin_name,
                record.action,
                record.quantity,
                record.price,
                record.trade_status,
                record.order_method,
            ])
        return response

    
    
    
class TradeAccount(View):
    def get(self, request):
        user = request.user
        user_name = request.GET.get("user_name")
        if request.user.user_type == "SuperAdmin":
            user_obj = MyUser.objects.filter(user_type="Client")
        elif request.user.user_type == "Admin":
            admin_obj = user.admin_user.admin_create_client.all().values_list("client__id",flat=True)
            user_obj = MyUser.objects.filter(id__in=admin_obj)
        elif request.user.user_type == "Master":
            master_obj = user.master_user.master_user_link.all().values_list("client__id",flat=True)
            user_obj = MyUser.objects.filter(id__in=master_obj)
        else:
            client_obj = [request.user.id]
            user_obj = [request.user]
        if user_name:
            user_obj = user_obj.filter(user_name=user_name)
            
        return render(request, "report/trade-account.html",{"user":user,"user_obj":user_obj})
    
    

class SettlementView(View):
    def get(self, request):
        user = request.user.id
        return render(request, "report/settlement.html", {"user_id":user})
    
    
    
class AccountSummary(View):
    def get(self, request):
        from_date = request.GET.get('from_date')
        to_date = request.GET.get('to_date')
        p_and_l = request.GET.get('p_and_l')
        brk = request.GET.get('brk')
        credit = request.GET.get('credit')
        user = request.user
        account_summary = user.user_summary.all().values('id','user_summary__user_name', 'particular', 'quantity', 'buy_sell_type', 'price', 'average', 'summary_flg', 'amount', 'closing', 'open_qty','created_at')
        if from_date:
            if to_date:
                to_date = datetime.strptime(to_date, '%Y-%m-%d') + timedelta(days=1)
                account_summary = account_summary.filter(created_at__gte=from_date,created_at__lte=to_date)
        
        if p_and_l == 'on' and brk == 'on':   
            account_summary = account_summary.filter(Q(summary_flg='Profit/Loss') | Q(summary_flg='Brokerage'))
       
        elif p_and_l == 'on':
            account_summary = account_summary.filter(summary_flg='Profit/Loss')
        elif brk == 'on':
            account_summary = account_summary.filter(summary_flg='Brokerage')
        if credit == "on":
            account_summary = account_summary.filter(summary_flg="Credit")

        return render(request, "report/account-summary.html",{"account_summary":account_summary,"id":user.id})





class AccountSummaryDownloadCSV(View):
    def get(self, request, id):
        user = MyUser.objects.get(id=id)
        user_summary_instances = AccountSummaryModal.objects.filter(user_summary=user)
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="account-summary.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'Date', 'Username', 'Particular', 'Qty', 'Buy/Sell', 'Price','Average Price','Type','Amount','Closing','Open Qty'])
        for instance in user_summary_instances:
            writer.writerow([
                instance.created_at,
                user.user_name,
                instance.particular,
                instance.quantity,
                instance.buy_sell_type,
                instance.price,
                instance.average,
                instance.summary_flg,
                instance.amount,
                instance.closing,
                instance.open_qty
                ])
        return response
    
class BillGenerate(View):
    def get(self, request):
        return render(request, "report/bill-generate.html")
    

class TradeMargin(View):
    def get(self, request):
        user = MyUser.objects.get(id=request.user.id)
        exchange_obj = user.user.values("symbol_name")
        exchange = request.GET.get('exchange')
        trade_margin = request.GET.get('price')
        trade = user.admin_coins.all()
        first_symbol_name = exchange_obj.first()["symbol_name"] if exchange_obj.first() else None
        if exchange:
            trade = trade.filter(ex_change=exchange)
        return render(request, "report/trade-margin.html", {"trade_margin": trade, "exchange_obj": exchange_obj, "user": user, "first": first_symbol_name})



class ScriptMaster(View):
    def get(self, request):
        return render(request, "report/script-master.html")
    
    
    
class LogsHistory(View):
    def get(self, request):
        return render(request, "report/logs-history.html")
    
    
class UserLogsNew(View):
    def get(self, request):
        return render(request, "report/user-logs-new.html")
    
    
class UserScriptPositionTrack(View):
    def get(self, request):
        return render(request, "report/user-script-position-track.html")


class PositionTrackViewOrders(View):
    def get(self, request):
        coin_name = request.GET.get("coin").replace("_", " ")
        user_id = request.GET.get("id")
        result = (
                BuyAndSellModel.objects.filter(buy_sell_user__id=user_id, trade_status=True, is_pending=False, is_cancel=False, coin_name=coin_name)
                .values('identifer','coin_name', 'action','buy_sell_user__user_name','created_at','quantity','price','trade_status','ip_address','order_method')
                .annotate(
                    total_quantity=Sum('quantity'),
                    avg_buy_price=Coalesce(
                        Avg(Case(When(quantity__gt=0, then='price'), output_field=FloatField())),
                        Value(0.0)
                    ),
                    avg_sell_price=Coalesce(
                        Avg(Case(When(quantity__lt=0, then='price'), output_field=FloatField())),
                        Value(0.0)
                    )
                ).exclude(total_quantity=0).order_by("created_at")
            )
        return render(request, "report/position-track-view-orders.html", {"result":result})
    
    
class UserScriptPositionTrackPl(View):
    def get(self, request):
        return render(request, "report/user-script-position-track-pl.html")
    
    
    
class ScriptQuantity(View):
    def get(self, request):
        user = request.user
        # group_settings = GroupSettingsModel.objects.get(id=1)  
        # related_scripts = group_settings.group_user.all() 
        return render(request, "report/script-quantity.html",{"id":user.id})
    
    
    
    
class ExchangeTimeSchedule(View):
    def get(self, request):
        return render(request, "tools/exchange-time.html")
    
    

class MassageView(View):
    def get(self, request):
        message = MessageModel.objects.all()
        return render(request, "tools/message.html",{"message":message})
    def post(self, request):
        message  = MessageModel.objects.create(message=request.POST.get("message"))
        messages.success(request, f"Message add successfully.")
        return redirect("Admin:message")
    
    
    
class WeeklyAdminView(View):
    def get(self, request):
        user = request.user
        user_obj = request.GET.get('user_name')
        check = MyUser.objects.filter(user_name=user_obj).values("id")

        if request.user.user_type == "SuperAdmin":
            user = request.user
            user_names = MyUser.objects.filter(user_type__in=["Master", "Client"]).values_list("user_name",flat=True)
        elif request.user.user_type == "Admin": 
            user = request.user
            admin_child = AdminModel.objects.filter(user=user).values_list("user__user_name", flat=True)
            master_child = MastrModel.objects.filter(admin_user=user.admin_user)
            client_child = ClientModel.objects.filter(master_user_link__in=master_child).values_list('client__user_name', flat=True)
            user_names = list(master_child) + list(client_child)
           
        elif request.user.user_type == "Master":
            user = request.user
            master_child = MastrModel.objects.filter(master_link=user.master_user).values_list('master_user__user_name', flat=True)
            client_child = ClientModel.objects.filter(master_user_link=user.master_user).values_list('client__user_name', flat=True)
            user_names = list(master_child) + list(client_child)
            user_names.append(user.user_name)
        else:
            user = request.user
            user_names = [user.user_name]
        if user_obj:
            pass
            
        return render(request, "report/weekly-admin.html",{"user":user,"user_names":user_names})
    
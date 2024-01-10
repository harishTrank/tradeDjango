from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import *
from .serializers import *
from client_app.models import *
from master_app.models import *
from rest_framework.exceptions import APIException
from django.http import Http404
from django.contrib.auth.hashers import make_password
from rest_framework.pagination import PageNumberPagination
from django.contrib.auth import update_session_auth_hash
from django.db.models import Sum, F, Value, IntegerField, Case, When, Avg, Q
from django.http import JsonResponse
from django.db.models.functions import Coalesce
from django.db.models import Sum, Avg, Case, When, F, Value, FloatField
import requests

NODEIP = '52.66.205.199'
class LoginApi(APIView):
    def post(self, request):
        try:
            current_user = MyUser.objects.filter(user_name__iexact=request.data["user_name"]).first()
            print("current_user.status", current_user.status, current_user)
            if not current_user or not current_user.check_password(request.data["password"]) or request.data["user_type"] != current_user.role:
                return Response({"success": False, "message": "Invalid credentials."}, status=status.HTTP_404_NOT_FOUND)
            elif not current_user.status:
                return Response({"success": False, "message": "This user has been disabled."}, status=status.HTTP_404_NOT_FOUND)
            elif current_user.user_type == "Admin" or current_user.user_type =="SuperAdmin":
                return Response({"success": False, "message": "Invaild user."}, status=status.HTTP_404_NOT_FOUND)
            else:
                refresh = RefreshToken.for_user(current_user)
                token = {
                    'access': str(refresh.access_token),
                }
                historyGenerator = LoginHistoryModel(user_history=current_user, ip_address=request.data['current_ip'], method=request.data['method'], action='LOGIN')
                historyGenerator.save()
                return Response({'responsecode':status.HTTP_200_OK,
                                    'userid': current_user.id,
                                    'role':current_user.role,
                                    'token': token,
                                    'responsemessage': 'User logged in successfully.'}
                                , status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            return Response({"success": False, "message": "Something went wrong."}, status=status.HTTP_404_NOT_FOUND)
        
        
class LogoutUserAPIView(APIView):
    def post(self, request):
        current_user = MyUser.objects.filter(id__iexact=request.data["user_id"]).first()
        historyGenerator = LoginHistoryModel(user_history=current_user, ip_address=request.data['current_ip'], method=request.data['method'], action='LOGOUT')
        historyGenerator.save()
        return Response({"success": True, "message": "Logout user successfully"}, status=status.HTTP_200_OK)
    

class ResetPasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():

            user = request.user
            if "user_id" in request.data and request.data["user_id"] != "":
                user = MyUser.objects.filter(id=request.data["user_id"]).first()
            current_password = serializer.validated_data.get('current_password')
            new_password = serializer.validated_data.get('new_password')

            if not user.check_password(current_password):
                raise APIException("Current password is incorrect.", code=status.HTTP_400_BAD_REQUEST)

            user.set_password(new_password)
            user.save()

            return Response({'responsecode': status.HTTP_200_OK, 'responsemessage': 'Password changed successfully'},)
        else:
            responcemessage = ""
            for item in serializer.errors.items():
                responcemessage += " " + f"error in {item[0]}:-{item[1][0]}"
            response = {
                "responsecode": status.HTTP_400_BAD_REQUEST,
                "responcemessage": responcemessage
            }
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
     
                



class AddUserAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        limit = request.user.master_user.limit if request.user.user_type == "Master" else False
        master_limit = request.user.master_user.master_limit if request.user.user_type == "Master" else None
        client_limit = request.user.master_user.client_limit if request.user.user_type == "Master" else None
        
        credit_amount = request.data.get("credit")
        if credit_amount is not None and credit_amount.isdigit():
            credit_amount = int(credit_amount)
            if hasattr(request.user, 'balance') and request.user.balance <= credit_amount:
                return Response({"status":False, "message":"Insufficient balance."},status=401)

            request.user.balance -= credit_amount
            request.user.save() 
            
        master_users_count = MastrModel.objects.filter(master_link=request.user.master_user).count()
        if request.data.get("add_master") == True:
            if master_users_count >= master_limit:
                return Response({"status":False, "message":"Cannot create more master. Limit reached."},status=401)
        else:
            client_users_count = ClientModel.objects.filter(master_user_link=request.user.master_user).count()
            if client_users_count >= client_limit:
                return Response({"status":False, "message":"Cannot create client users. Limit reached."},status=401)
        try:
            if MyUser.objects.filter(user_name=request.data.get("user_name")).exists():
                return Response({"status": False, "message": "This User Already exists."}, status=status.HTTP_400_BAD_REQUEST)
            
            user_id = request.user.id
            current_master = MyUser.objects.get(id=user_id).master_user
            
            createUs = request.data.pop("exchange_data")
            password=request.data.pop("password")
            request.data.pop("role")
            
            if request.data.get("add_master"):
                admin_belongs = current_master.admin_user
                create_user = MyUser.objects.create(user_type="Master", **request.data, password=make_password(password), role=request.user.role)
                current_master = MyUser.objects.get(id=request.user.id).master_user
                MastrModel.objects.create(master_user=create_user, admin_user=admin_belongs, master_link=current_master)
                UserCreditModal.objects.create(user_credit=request.user, opening=request.user.balance + credit_amount, credit=0, debit=credit_amount, closing=request.user.balance, transection=create_user, message="New master opening credit refrenece.")
            else:
                create_user = MyUser.objects.create(user_type="Client", **request.data, password=make_password(password), role=request.user.role)
                ClientModel.objects.create(client=create_user, master_user_link=current_master)
                UserCreditModal.objects.create(user_credit=request.user, opening=request.user.balance + credit_amount, credit=0, debit=credit_amount, closing=request.user.balance, transection=create_user, message="New client opening credit refrenece.")
            try: 
                exchangeList = []
                for exchange_item in createUs:
                    if exchange_item['exchange']:
                        exchangeList.append(exchange_item['symbol_name'].upper())

                    ExchangeModel.objects.create(
                        user=create_user,
                        symbol_name=exchange_item['symbol_name'].upper(),
                        exchange=exchange_item['exchange'],
                        symbols=exchange_item['symbols'],
                        turnover=exchange_item['turnover']
                    )

                if create_user.user_type == "Master" or create_user.user_type == "Client":
                    response = requests.post(f"http://{NODEIP}:5000/api/tradeCoin/coins", json={
                        "coinList": exchangeList
                    })
                    if response.status_code // 100 == 2 and response.json()['success']:
                        for obj in response.json()['response']:
                            if "_" in obj['InstrumentIdentifier']:
                                obj['InstrumentIdentifier'] = obj['InstrumentIdentifier'].split("_")[1]

                            if AdminCoinWithCaseModal.objects.filter(master_coins=create_user, identifier=obj['InstrumentIdentifier'], ex_change=obj['Exchange']).count() == 0:
                                AdminCoinWithCaseModal.objects.create(master_coins=create_user, ex_change=obj['Exchange'], identifier=obj['InstrumentIdentifier'], lot_size=obj["QuotationLot"])
                    else:
                        print("Response:", response.text)
            except Exception as e:
                print("e",e)
            return Response({"status":True,"message":"User created Successfully"}, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            print("e",e)
            return Response({"error": "User not found"}, status=status.HTTP_400_BAD_REQUEST)
    


class EditUserApi(APIView):
    def post(self, request):
        user_id = request.GET.get("user_id")
        user = MyUser.objects.get(id=user_id)
            
        user_data = {
            "full_name": request.data.get("full_name"),
            "user_name": request.data.get("user_name"),
            "phone_number": request.data.get("phone_number"),
            "city": request.data.get("city"),
            "credit": request.data.get("credit") if request.data.get("credit") else 0,
            "remark": request.data.get("remark"),
            "mcx": True if request.data.get("mcx") and request.data.get("mcx") == True else False,
            "nse": True if request.data.get("nse") and request.data.get("nse") == True else False,
            "mini": True if request.data.get("mini") and request.data.get("mini") == True else False,
            "change_password": True if request.data.get("change_password") and request.data.get("change_password") == True else False,
            "add_master": True if request.data.get("add_master") and request.data.get("add_master") == True else False,
            "margin_sq": True if request.data.get("auto_square") and request.data.get("auto_square") == True else False,
        }
        if request.data.get("password") != "":
            print("===",request.data.get("password"))
            user_data["password"]= make_password(request.data.get("password"))
        
        exchanges = [
            {
                "name": "MCX",
                "exchange": request.data.get("mcx_exchange"),
                "symbols": request.data.get("mcx_symbol"),
                "turnover": request.data.get("mcx_turnover"),
            },
            {
                "name": "NSE",
                "exchange": request.data.get("nse_exchange"),
                "symbols": request.data.get("nse_symbol"),
                "turnover": request.data.get("nse_turnover"),
            },
          
            {
                "name": "MINI",
                "exchange": request.data.get("mini_exchange"),
                "symbols": request.data.get("mini_symbol"),
                "turnover": request.data.get("mini_turnover"),
            },
        ]
        user_name = request.data.get("user_name")
        if MyUser.objects.exclude(id=user.id).filter(user_name=user_name).exists():
            return Response({"status":False, "message":"already exists for another user. Please choose a different one."},status=404)

        for key, value in user_data.items():
            setattr(user, key, value)
        user.save()
        
        for exchange_data in exchanges:
            exchange = ExchangeModel.objects.get(user=user, symbol_name=exchange_data['name'])
            exchange.exchange = exchange_data['exchange']
            exchange.symbols = exchange_data['symbols']
            exchange.turnover = exchange_data['turnover']
            exchange.save()
        return Response({"status":True,"message":"User edit succesfully"})
    
    
class UserProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user = request.user
        if request.GET.get("user_id") and request.GET.get("user_id") != "":
            user = MyUser.objects.get(id=request.GET.get("user_id"))
        if (request.query_params.get("user_id") and request.query_params.get("user_id") != ""):
            user = MyUser.objects.filter(id=request.query_params.get("user_id")).first()
        exchange = ExchangeModel.objects.filter(user=user.id).values_list('symbol_name', flat=True)
        serializer = GetMyUserSerializer(user)
        tradeCoinData = MarketWatchModel.objects.filter(market_user=user).values_list("trade_coin_id", flat=True) 
        data_to_send = {
            "responsecode":status.HTTP_200_OK,
            "responsemessage":"data getting sucessfully",
            "data":{**serializer.data, "exchange": list(exchange)},
            "tradeCoinData":list(tradeCoinData),
            "ip_address": user.user_history.first().ip_address if user.user_history.first() else ""
        }
        if (not user.status):
            return Response({"message": "This user has been disabled.", "success": False}, status=status.HTTP_404_NOT_FOUND)
        else:
            return Response(data_to_send, status=status.HTTP_200_OK)

class UserDetailsAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user = request.user
        
        if (request.query_params.get("user_id") and request.query_params.get("user_id") != ""):
            user = MyUser.objects.filter(id=request.query_params.get("user_id")).first()
        exchange = ExchangeModel.objects.filter(user=user.id).values_list('symbol_name', flat=True)
        la_lodu = ExchangeModel.objects.filter(user=user.id).values('symbol_name','exchange','symbols','turnover')
        serializer = GetMyUserSerializer(user)
        data_to_send = {
            "responsecode":status.HTTP_200_OK,
            "responsemessage":"data getting sucessfully",
            "data":{**serializer.data, "exchange": list(exchange), "la_lodu":la_lodu},
            "ip_address": user.user_history.first().ip_address if user.user_history.first() else ""
        }
        return Response(data_to_send, status=status.HTTP_200_OK)


class MaketWatchScreenApi(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            tradeCoinData = MarketWatchModel.objects.filter(market_user=request.user).values_list("trade_coin_id", flat=True) 
            return Response({"result": tradeCoinData }, status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            return Response({"message": "Something went wrong, Try Again"}, status=status.HTTP_404_NOT_FOUND)
        

    def post(self, request):
        serializer = TradeCoinSerializer(data=request.data)

        if serializer.is_valid():
            user = request.user
            trade_coin_id = serializer.validated_data.get('trade_coin_id')
            existing_entry = MarketWatchModel.objects.filter(
                market_user=user,
                trade_coin_id=trade_coin_id
            ).first()

            if existing_entry:
                existing_entry.trade_coin_id = trade_coin_id
                existing_entry.save()
            else:
                MarketWatchModel.objects.create(market_user=user, trade_coin_id=trade_coin_id)
            return Response({
                'responsecode': status.HTTP_200_OK,
                'responsemessage': 'Trade coin added successfully'
            })

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    
    def delete(self, request):
        user = request.user
        trade_coin_id_to_delete = request.query_params.get('trade_coin_id')  # Get the ID from URL parameters

        if trade_coin_id_to_delete:
            try:
                market_watch_instance = MarketWatchModel.objects.get(
                    market_user=user,
                    trade_coin_id=trade_coin_id_to_delete
                )
                market_watch_instance.delete()

                return Response({
                    'responsecode': status.HTTP_200_OK,
                    'responsemessage': f'Trade coin {trade_coin_id_to_delete} deleted successfully'
                })
            except MarketWatchModel.DoesNotExist:
                raise Http404("No matching trade coin found for deletion")
        else:
            return Response({
                'responsecode': status.HTTP_400_BAD_REQUEST,
                'responsemessage': 'No trade coin ID provided to delete'
            })

def accountSummaryService(data, user, pandL, summary_flag, admin=""):
    if (pandL != 0):
        result = (
            user.buy_sell_user.filter(trade_status=True, is_pending=False, is_cancel=False, identifer=data["identifer"])
            .values('identifer','coin_name')
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
        if (result and len(list(result)) > 0):
            if summary_flag == "Profit/Loss":
                AccountSummaryModal.objects.create(user_summary=user if admin == "" else admin, particular=data["coin_name"], quantity=abs(data["quantity"]), buy_sell_type=data["action"], price=data['price'], average= list(result)[0]['avg_sell_price'] if data["action"] == 'BUY' else list(result)[0]['avg_buy_price'], summary_flg=summary_flag, amount=pandL, closing=user.balance)
            else:
                AccountSummaryModal.objects.create(user_summary=user if admin == "" else admin, particular=data["coin_name"], quantity=abs(data["quantity"]), buy_sell_type=data["action"], price=data['price'], average= list(result)[0]['avg_buy_price'] if data["action"] == 'BUY' else list(result)[0]['avg_sell_price'], summary_flg=summary_flag, amount=pandL, closing=user.balance)
            
class BuySellSellApi(APIView):
    # permission_classes = [IsAuthenticated]
    def post(self, request):
        if (request.data.get("type") == "WEB"):
            user = MyUser.objects.get(id=request.data.get("userId"))
        else:
            user = request.user
        action = request.data.get('action')
        quantity = request.data.get('quantity')
        lot_size = request.data.get("lot_size")
        is_cancel = request.data.get("is_cancel")
        if user.user_type != "Client":
            return Response({"success": False, "message": "Not Allowed For Trade"}, status=status.HTTP_404_NOT_FOUND)
        
        totalCount = BuyAndSellModel.objects.filter(identifer=request.data.get("identifer"),is_pending=False, trade_status=True,is_cancel=False).values('identifer').annotate(total_quantity=Sum('quantity'), avg_price=Avg('price'))
        try:
            total_quantity = (-totalCount[0]["total_quantity"] if action == 'BUY' else totalCount[0]["total_quantity"])
        except:
            total_quantity = 0
        if totalCount.count() > 0 and (total_quantity < quantity)  and not is_cancel:
            current_coin = TradeMarginModel.objects.filter(exchange=request.data.get('ex_change'), script__icontains=request.data.get("identifer") if request.data.get('ex_change') == "NSE" else request.data.get("identifer").split("_")[1]).first()
            currentProfitLoss = total_quantity * quantity * lot_size - current_coin.trade_margin * quantity
            user.balance += currentProfitLoss
            accountSummaryService(request.data, user, currentProfitLoss, "Profit/Loss")
            quantity -= total_quantity
            
        total_cost = lot_size * quantity * request.data.get('price')
        if (totalCount.count() > 0 and (total_quantity == quantity)) and not is_cancel:
            if action == "SELL":
                currentProfitLoss = ( request.data.get('price') -totalCount[0]["avg_price"] ) * quantity * lot_size
            else:
                currentProfitLoss = ( totalCount[0]["avg_price"] -  request.data.get('price') ) * quantity * lot_size
                
            user.balance += currentProfitLoss
            accountSummaryService(request.data, user, currentProfitLoss, "Profit/Loss")
        
        elif action == 'BUY' and user.balance >= total_cost and not is_cancel:  
            user.balance -= total_cost
        elif action == 'SELL' and user.balance >= total_cost and not is_cancel:
            user.balance += total_cost
        else:
            buy_sell_instance = BuyAndSellModel(
                buy_sell_user=user,
                quantity=request.data.get('quantity') if action == 'BUY' else -request.data.get('quantity'),
                trade_type=request.data.get('trade_type'),
                action=request.data.get('action'),
                price=request.data.get('price'),
                coin_name=request.data.get('coin_name'),
                ex_change=request.data.get('ex_change'),
                is_pending=request.data.get('is_pending'),
                identifer=request.data.get("identifer"),
                ip_address=request.data.get("ip_address"),
                order_method=request.data.get("order_method"),
                stop_loss=request.data.get("stop_loss"),
                message='Market is closed. Please try again later!' if is_cancel else 'Insufficient balance/quantity',
                is_cancel=True
            )
            buy_sell_instance.save()
            return Response({'message': 'Market is closed. Please try again later!' if is_cancel else 'Insufficient balance/quantity'}, status=status.HTTP_400_BAD_REQUEST)
        user.save()
        buy_sell_instance = BuyAndSellModel(
            buy_sell_user=user,
            quantity=request.data.get('quantity') if action == 'BUY' else -request.data.get('quantity'),
            trade_type=request.data.get('trade_type'),
            action=request.data.get('action'),
            price=request.data.get('price'),
            coin_name=request.data.get('coin_name'),
            ex_change=request.data.get('ex_change'),
            is_pending=request.data.get('is_pending'),
            identifer=request.data.get("identifer"),
            ip_address=request.data.get("ip_address"),
            order_method=request.data.get("order_method"),
            stop_loss=request.data.get("stop_loss"),
            message= 'Buy order successfully' if action =="BUY" else 'Sell order successfully'
        )
        buy_sell_instance.save()
        if total_cost > 100000:
            if request.data.get('ex_change') == "MINI":
                brk_value = user.mini_brk
            elif request.data.get('ex_change') == "MCX":
                brk_value = user.mcx_brk
            else:
                brk_value = user.nse_brk
            admin_brk = total_cost/100000 * brk_value
            if (admin_brk != 0):
                accountSummaryService(request.data, user, -(abs(admin_brk)), "Brokerage")
                user.balance -= admin_brk
                user.save()
                if (user.user_type == "Master"):
                    current_admin = user.master_user.admin_user.user
                elif (user.user_type == "Client"):
                    current_admin = user.client.admin_create_client.user
                current_admin.balance += admin_brk
                current_admin.save()
                accountSummaryService(request.data, user, abs(admin_brk), "Brokerage", current_admin)
        if  (totalCount.count() > 0 and totalCount[0]["total_quantity"]== 0):
            BuyAndSellModel.objects.filter(identifer=request.data.get("identifer")).update(trade_status=False)
        return Response({'user_balance':user.balance,'message': 'Buy order successfully' if action =="BUY" else 'Sell order successfully'}, status=status.HTTP_200_OK)    
        
        
        
class AccountSummaryApi(APIView):
    pagination_class = PageNumberPagination
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user = request.user
        from_date = request.query_params.get('from_date')
        to_date = request.query_params.get('to_date')
        coin_name = request.query_params.get('coin_name')
        p_and_l = request.query_params.get('p_and_l')
        brk = request.query_params.get('brk')
        user_name = request.query_params.get('user_name')

        if user.user_type == "Master":
            master_child = MastrModel.objects.filter(master_link=request.user.master_user).values_list('master_user__user_name', flat=True)
            client_child = ClientModel.objects.filter(master_user_link=request.user.master_user).values_list('client__user_name', flat=True)
            user_ids = list(master_child) + list(client_child)
            user_ids.append(request.user.user_name)
            account_summary = AccountSummaryModal.objects.filter(user_summary__user_name__in=user_ids).values('id','user_summary__user_name', 'particular', 'quantity', 'buy_sell_type', 'price', 'average', 'summary_flg', 'amount', 'closing', 'open_qty','created_at')
        else:
            account_summary = user.user_summary.all().values('id','user_summary__user_name', 'particular', 'quantity', 'buy_sell_type', 'price', 'average', 'summary_flg', 'amount', 'closing', 'open_qty','created_at')
        if from_date and to_date:
            from_date_obj = timezone.datetime.strptime(from_date, '%Y-%m-%d').replace(hour=0, minute=0, second=0, microsecond=0)
            to_date_obj = timezone.datetime.strptime(to_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59, microsecond=999999)
            account_summary = account_summary.filter(created_at__gte=from_date_obj, created_at__lte=to_date_obj)
        if coin_name:
            account_summary = account_summary.filter(particular__icontains=coin_name)
        
        if p_and_l == 'true' and brk == 'true':   
            account_summary = account_summary.filter(Q(summary_flg__icontains='Profit/Loss') | Q(summary_flg__icontains='Brokerage'))
        elif p_and_l == 'true':
            account_summary = account_summary.filter(summary_flg__icontains='Profit/Loss')
        elif brk == 'true':
            account_summary = account_summary.filter(summary_flg__icontains='Brokerage')

        if user_name:
            account_summary = account_summary.filter(user_summary__user_name=user_name)

        paginator = self.pagination_class()
        paginated_trade = paginator.paginate_queryset(account_summary, request)
        response = paginator.get_paginated_response(paginated_trade)
        response.data['current_page'] = paginator.page.number  
        response.data['total'] = paginator.page.paginator.num_pages
        return response

class AccountSummaryCreditAPI(APIView):
    pagination_class = PageNumberPagination
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user = request.user
        from_date = request.query_params.get('from_date')
        to_date = request.query_params.get('to_date')
        coin_name = request.query_params.get('coin_name')
        user_name = request.query_params.get('user_name')
        
        if user.user_type == "Master":
            master_child = MastrModel.objects.filter(master_link=request.user.master_user).values_list('master_user__user_name', flat=True)
            client_child = ClientModel.objects.filter(master_user_link=request.user.master_user).values_list('client__user_name', flat=True)
            user_ids = list(master_child) + list(client_child)
            user_ids.append(request.user.user_name)
            account_summary = UserCreditModal.objects.filter(user_credit__user_name__in=user_ids).values('id','opening', 'credit', 'debit', 'closing', 'transection__user_name', "created_at", 'message')
        else:
            account_summary = user.user_credit.all().values('id','opening', 'credit', 'debit', 'closing', 'transection__user_name', "created_at", 'message')
        if from_date and to_date:
            from_date_obj = timezone.datetime.strptime(from_date, '%Y-%m-%d').replace(hour=0, minute=0, second=0, microsecond=0)
            to_date_obj = timezone.datetime.strptime(to_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59, microsecond=999999)
            account_summary = account_summary.filter(created_at__gte=from_date_obj, created_at__lte=to_date_obj)
        if coin_name:
            account_summary = account_summary.filter(particular__icontains=coin_name)

        if user_name:
            account_summary = account_summary.filter(user_credit__user_name=user_name)
        
        paginator = self.pagination_class()
        paginated_trade = paginator.paginate_queryset(account_summary, request)
        response = paginator.get_paginated_response(paginated_trade)
        response.data['current_page'] = paginator.page.number  
        response.data['total'] = paginator.page.paginator.num_pages
        return response    
    
class MasterChildApi(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        try:
            master_child = MastrModel.objects.filter(master_link=request.user.master_user).values_list('master_user__user_name', flat=True)
            client_child = ClientModel.objects.filter(master_user_link=request.user.master_user).values_list('client__user_name', flat=True)
            user_names = list(master_child) + list(client_child)
            user_names.append(request.user.user_name)
            return Response({"success": True, "message": "Data getting successfully.", "data": user_names}, status=status.HTTP_200_OK)
        except:
            return Response({"success": False, "message": "Something went wrong."}, status=status.HTTP_404_NOT_FOUND)


class PositionManager(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        try:
            if (request.GET.get("type") == "WEB"):
                user = MyUser.objects.get(id = request.GET.get("id"))
            else:
                user = request.user
            if (request.query_params.get("user_id") and request.query_params.get("user_id") != ""):
                user = MyUser.objects.filter(id=request.query_params.get("user_id")).first()

            result = (
                user.buy_sell_user.filter(trade_status=True, is_pending=False, is_cancel=False)
                .values('identifer','coin_name')
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
            return Response({"status": True, "response": result}, status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            return Response({"status": False}, status=status.HTTP_404_NOT_FOUND)
        
        

class PositionCoinsManager(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        try:
            user = request.user 
            if (request.query_params.get("user_id") and request.query_params.get("user_id") != ""):
                user = MyUser.objects.filter(id=request.query_params.get("user_id")).first()
            results = (
                user.buy_sell_user.all()
                .filter(is_pending=False, trade_status=True,is_cancel=False)
                .values('identifer')
                .annotate(total_quantity=Sum('quantity'), avg_price=Avg('price'))
                .exclude(total_quantity=0)
                .values_list('identifer',flat=True)
            )
            return Response({"status": True, "response": results}, status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            return Response({"status": False}, status=status.HTTP_404_NOT_FOUND)        


     
    
class TradeHistoryApi(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = PageNumberPagination
    def get(self, request):
        user = request.user
        if (request.query_params.get("user_id") and request.query_params.get("user_id") != ""):
            user = MyUser.objects.filter(id=request.query_params.get("user_id")).first()

        from_date = request.query_params.get('from_date')
        to_date = request.query_params.get('to_date')
        ex_change = request.query_params.get('ex_change')
        coin_name = request.query_params.get('coin_name')
        is_pending = request.query_params.get("is_pending")
        is_cancel = request.query_params.get("is_cancel")
        user_name = request.query_params.get("user_name")
        print("user.user_type", user.user_type)
        if user.user_type == "Client":          
            exchange_data = user.buy_sell_user.values("id","buy_sell_user__user_name", "quantity", "trade_type", "action", "price", "coin_name", "ex_change","created_at","is_pending","identifer", "message") 
            
            if from_date and to_date:
                from_date_obj = timezone.datetime.strptime(from_date, '%Y-%m-%d').replace(hour=0, minute=0, second=0, microsecond=0)
                to_date_obj = timezone.datetime.strptime(to_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59, microsecond=999999)
                exchange_data = exchange_data.filter(created_at__gte=from_date_obj, created_at__lte=to_date_obj)

            exchange_data = exchange_data.filter(is_cancel=False) if not is_cancel else exchange_data.filter(is_cancel=True)

            if ex_change:
                exchange_data = exchange_data.filter(ex_change=ex_change)
            if coin_name:
                exchange_data = exchange_data.filter(coin_name__icontains=coin_name)
            if is_pending:
                is_pending_bool = is_pending.lower() == 'true'
                exchange_data = exchange_data.filter(is_pending=is_pending_bool)

            paginator = self.pagination_class()
            paginated_trade = paginator.paginate_queryset(exchange_data, request)
            response = paginator.get_paginated_response(paginated_trade)
            response.data['current_page'] = paginator.page.number  
            response.data['total'] = paginator.page.paginator.num_pages
            return response
        
        elif user.user_type == "Master":
            user_keys = [user.id]
            child_clients = user.master_user.master_user_link.all().values_list("client__id", flat=True)
            master_child = MastrModel.objects.filter(master_link=user.master_user).values_list('master_user__user_name', flat=True)
            user_keys += list(child_clients) + list(master_child)
            response = BuyAndSellModel.objects.filter(buy_sell_user__id__in=user_keys).values("id","buy_sell_user__user_name", "quantity", "trade_type", "action", "price", "coin_name", "ex_change", "created_at","is_pending","identifer", "message")
            response = response.filter(is_cancel=False) if not is_cancel else response.filter(is_cancel=True)
            
            if from_date and to_date:
                from_date_obj = timezone.datetime.strptime(from_date, '%Y-%m-%d').replace(hour=0, minute=0, second=0, microsecond=0)
                to_date_obj = timezone.datetime.strptime(to_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59, microsecond=999999)
                response = response.filter(created_at__gte=from_date_obj, created_at__lte=to_date_obj)
                
            if ex_change:
                response = response.filter(ex_change=ex_change)
            if coin_name:
                response = response.filter(coin_name__icontains=coin_name)
                
            if is_pending:
                is_pending_bool = is_pending.lower() == 'true'
                response = response.filter(is_pending=is_pending_bool)

            if user_name:
                response = response.filter(buy_sell_user__user_name=user_name)
            
            paginator = self.pagination_class()
            paginated_trade = paginator.paginate_queryset(response, request)
            response = paginator.get_paginated_response(paginated_trade)
            response.data['current_page'] = paginator.page.number  
            response.data['total'] = paginator.page.paginator.num_pages
            return response
        return Response({"message":"data not found"}, status=status.HTTP_404_NOT_FOUND)  
    


class TradeParticularViewApi(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, id):
        try:
            buy_obj = BuyAndSellModel.objects.filter(id=id)
            return Response({"response":buy_obj.values()[0],"user":buy_obj[0].buy_sell_user.user_name}, status=status.HTTP_200_OK)
        except:
            return Response({"response":"Oops"}, status=status.HTTP_400_BAD_REQUEST)



class CoinNameApi(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user = request.user
        if (request.query_params.get('user_id') and request.query_params.get('user_id') != ""):
            user = MyUser.objects.filter(id=request.query_params.get('user_id')).first()
        if user.user_type == "Master":
            master_child = MastrModel.objects.filter(master_link=user.master_user).values_list('master_user__user_name', flat=True)
            client_child = ClientModel.objects.filter(master_user_link=user.master_user).values_list('client__user_name', flat=True)
            user_names = list(master_child) + list(client_child)
            user_names.append(user.user_name)
            response = BuyAndSellModel.objects.filter(buy_sell_user__user_name__in=user_names).order_by('-coin_name').values('coin_name').distinct()
        else:
            response = user.buy_sell_user.order_by('-coin_name').values('coin_name').distinct()
        return Response({"response":response,"status":status.HTTP_200_OK},status=status.HTTP_200_OK) 
    
    


class UserListApiView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = PageNumberPagination
    def get(self, request):
        user = request.user
        if (request.query_params.get("user_id") and request.query_params.get("user_id") != ""):
            user = MyUser.objects.filter(id=request.query_params.get("user_id")).first()
        own_user = request.query_params.get("own_user")
        select_user = request.query_params.get("select_user")
        select_status = request.query_params.get("select_status")
        if user.user_type == "Client":
            users = MyUser.objects.filter(id=user.id).values("id","user_name", "user_type","full_name","role","credit","balance")
            return JsonResponse(list(users), safe=False)
        else:
            if own_user == "OWN":
                users = MyUser.objects.filter(id=user.id).values("id","user_name", "user_type", "full_name","role","credit","balance")
                return JsonResponse({"results": list(users)}, safe=False)
            elif select_user == "MASTER":
                users = MyUser.objects.filter(id__in=set(MastrModel.objects.filter(master_link=user.master_user).values_list("master_user__id", flat=True)))
            elif select_status == "Active":
                users = MyUser.objects.filter(status=True if select_status else False,id__in=set(MastrModel.objects.filter(master_link=user.master_user).values_list("master_user__id", flat=True)))
            elif select_status == "InActive":
                users = MyUser.objects.filter(status=False,id__in=set(MastrModel.objects.filter(master_link=user.master_user).values_list("master_user__id", flat=True)))
            else:
                users = MyUser.objects.filter(id__in=set(ClientModel.objects.filter(master_user_link=user.master_user).values_list("client__id", flat=True))
                | set(
                    MastrModel.objects.filter(master_link=user.master_user).values_list("master_user__id", flat=True)))
        serialized_users = [{
            "id":user.id,
            "user_name": user.user_name,
             "user_type":user.user_type,
             "full_name":user.full_name,
             "role":user.role, 
             "credit":user.credit,
             "balance":user.balance}
            for user in users ]
        paginator = self.pagination_class()
        paginated_users = paginator.paginate_queryset(serialized_users, request)
        return paginator.get_paginated_response(paginated_users)



class LoginHistoryApi(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = PageNumberPagination
    def get(self, request):
        from_date = request.GET.get('from_date')
        to_date = request.GET.get('to_date')
        searchInput = request.GET.get('searchInput')
        user_obj = LoginHistoryModel.objects.filter(user_history__id=request.user.id).values("ip_address", "method", "action", "user_history__user_name", "user_history__user_type", "user_history__id", "id", "created_at").order_by("-id")
        if from_date and to_date:
            from_date_obj = timezone.datetime.strptime(from_date, '%Y-%m-%d').replace(hour=0, minute=0, second=0, microsecond=0)
            to_date_obj = timezone.datetime.strptime(to_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59, microsecond=999999)
            user_obj = user_obj.filter(created_at__gte=from_date_obj, created_at__lte=to_date_obj)

        user_obj = user_obj.filter(ip_address__icontains=searchInput)
        paginator = self.pagination_class()
        paginated_users = paginator.paginate_queryset(user_obj, request)
        return paginator.get_paginated_response(paginated_users)


class SearchUserAPI(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        if request.user.user_type == "Master":
            total_parent_master = MastrModel.objects.filter(master_link=request.user.master_user).values_list('id', flat=True)
            all_masters = [request.user.master_user.id] + list(total_parent_master) + list(MastrModel.objects.filter(master_link__id__in=list(total_parent_master)).values_list('id', flat=True))
            master_models = MastrModel.objects.filter(id__in=all_masters)
            serializer = MasterSerializer(master_models, many=True)
        elif request.user.user_type == "Admin":
            admin_models = AdminModel.objects.get(user=request.user)
            all_masters = admin_models.admin_user.all().values_list('id', flat=True)
            admin_master_models = MastrModel.objects.filter(id__in=all_masters)
            serializer = MasterSerializer(admin_master_models, many=True)
            
        elif request.user.user_type == "SuperAdmin":
            super_admin_users = MyUser.objects.filter(user_type='Admin', role=request.user.role)
            print("super_admin_users", super_admin_users)
            # Fetch associated AdminModel objects for each SuperAdmin
            super_admin_admin_models = AdminModel.objects.filter(user__in=super_admin_users)

            # Serialize the related AdminModel objects
            serializer = AdminSerializer(super_admin_admin_models, many=True)
        return Response({"success":True, "message": "Data getting successfully.", "data": serializer.data}, status=status.HTTP_200_OK)


class ScriptQuantityAPI(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        try:
            user_id = request.user.user_name
            if request.query_params.get("user_id") and request.query_params.get("user_id") != "":
                user_id = request.query_params.get("user_id")
            response = list(AdminCoinWithCaseModal.objects.filter(master_coins__user_name=user_id,ex_change=request.GET.get('searchInput')).values())
            return Response({"success": True, "response": response}, status=status.HTTP_200_OK)
        except:
            return Response({"success": False, "message": "Something went wrong."}, status=status.HTTP_404_NOT_FOUND)


class SettlementReportApi(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        try:
            user = request.user
            if request.query_params.get('id'):
                user = MyUser.objects.get(id=request.query_params.get('id'))
            if request.query_params.get('user_name'):
                user = MyUser.objects.get(user_name=request.query_params.get('user_name'))
            from_date = request.query_params.get('from_date')
            to_date = request.query_params.get('to_date')
            
            if from_date and to_date:
                from_date_obj = timezone.datetime.strptime(from_date, '%Y-%m-%d').replace(hour=0, minute=0, second=0, microsecond=0)
                to_date_obj = timezone.datetime.strptime(to_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59, microsecond=999999)
                total_profit = (
                    AccountSummaryModal.objects
                    .filter(user_summary= user.id, amount__gt=0, created_at__gte=from_date_obj, created_at__lte=to_date_obj, summary_flg="Profit/Loss")
                    .values('summary_flg')
                    .annotate(total_amount=Sum('amount'))
                )
                total_loss = (
                    AccountSummaryModal.objects
                    .filter(user_summary= user.id, amount__lt=0, created_at__gte=from_date_obj, created_at__lte=to_date_obj)
                    .values('summary_flg')
                    .annotate(total_amount=Sum('amount'))
                )
            else:
                total_profit = (
                    AccountSummaryModal.objects
                    .filter(user_summary= user.id, amount__gt=0, summary_flg="Profit/Loss")
                    .values('summary_flg')
                    .annotate(total_amount=Sum('amount'))
                )
                total_loss = (
                    AccountSummaryModal.objects
                    .filter(user_summary= user.id, amount__lt=0)
                    .values('summary_flg')
                    .annotate(total_amount=Sum('amount'))
                )
            return Response({"success": True, "message": "Data getting successfuly.", "total_profit": total_profit, "total_loss": total_loss}, status=status.HTTP_200_OK)
        except Exception as e:
            print("error from settlement",e)
            return Response({"success": False, "message": "From and to date is required."}, status=status.HTTP_404_NOT_FOUND)
        
class PositionTopHeader(APIView):
    def get(self, request):
        try:
            user = request.user
            if(request.GET.get("user_id") and request.GET.get("user_id") != ""):
                user = MyUser.objects.get(id=request.GET.get("user_id"))
            if (request.query_params.get("user_id") and request.query_params.get("user_id") != ""):
                user = MyUser.objects.filter(id=request.query_params.get("user_id")).first()
            margin_user = (
                user.buy_sell_user.filter(trade_status=True, is_pending=False, is_cancel=False)
                .values('identifer','coin_name', 'ex_change')
                .annotate(
                    total_quantity=Sum('quantity'),
                ).exclude(total_quantity=0)
            )
            release_p_and_l = (
                AccountSummaryModal.objects
                .filter(user_summary=user, summary_flg='Profit/Loss')
                .aggregate(total_amount=Sum('amount'))
            )
            margin_used_value = 0
            for obj in margin_user:
                current_coin = TradeMarginModel.objects.filter(exchange=obj['ex_change'], script__icontains=obj['identifer'] if obj['ex_change'] == "NSE" else obj["identifer"].split("_")[1]).first()
                margin_used_value += abs(obj["total_quantity"]) * current_coin.trade_margin if current_coin else 100
            return Response({"success": True, "message": "Data getting successfully.", "credit": user.credit, "balance": user.balance, "release_p_and_l": release_p_and_l['total_amount'] if release_p_and_l['total_amount'] else 0, "margin_used_value": margin_used_value}, status=status.HTTP_202_ACCEPTED)
        except Exception as e:
            print("error from position top", e)
            return Response({"success": False, "message": "Something went wrong."}, status=status.HTTP_404_NOT_FOUND)


class BrokrageSettings(APIView):
    def get(self, request):
        try:
            user = request.user
            if (request.GET.get("user_id") and request.GET.get("user_id") != ""):
                user = MyUser.objects.filter(id=request.GET.get("user_id")).first()
            response = AdminCoinWithCaseModal.objects.filter(master_coins=user, ex_change=request.GET.get("ex_change")).values("id", "turnover_brk", "lot_brk", "ex_change", "identifier", "lot_size")
            return Response({"status": True, "message": "Data getting successfully", "response": response})
        except Exception as e:
            print(e)
            return Response({"status": False, "message" :"Something went wrong."}, status=status.HTTP_404_NOT_FOUND)
        
    def post(self, request):
        try:
            brk_type = request.data.get("brk_type")
            amount = request.data.get("amount")
            object_list = request.data.get("object_list")
            records = AdminCoinWithCaseModal.objects.filter(id__in=object_list)

            if brk_type == "TURNOVER WISE":
                records.update(turnover_brk=float(amount))
            else:
                records.update(lot_brk=float(amount))
            return Response({"status": True, "message": "Data update successfully."})
        except Exception as e:
            print(e)
            return Response({"status": False, "message": "Something went wrong."}, status=status.HTTP_404_NOT_FOUND)
        

class TradeMarginSetting(APIView):
    def get(self, request):
        try:
            user = request.user
            if (request.GET.get("user_id") and request.GET.get("user_id") != ""):
                user = MyUser.objects.filter(id=request.GET.get("user_id")).first()
            response = AdminCoinWithCaseModal.objects.filter(master_coins=user, ex_change=request.GET.get("ex_change")).values("id", "trademargin_amount", "trademargin_percentage", "ex_change", "identifier","updated_at")
            return Response({"status": True, "message": "Data getting successfully", "response": response})
        except Exception as e:
            print(e)
            return Response({"status": False, "message": "Something went wrong."}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request):
        try:
            exchange = request.data.get("exchange")
            amount = request.data.get("amount")
            object_list = request.data.get("object_list")
            records = AdminCoinWithCaseModal.objects.filter(id__in=object_list)

            if exchange != "NSE":
                records.update(trademargin_amount=float(amount))
            else:
                records.update(trademargin_percentage=float(amount))
            return Response({"status": True, "message": "Data update successfully."})
        except Exception as e:
            print(e)
            return Response({"status": False, "message": "Something went wrong."}, status=status.HTTP_404_NOT_FOUND)
        
class TradeMarginUpdateAllApi(APIView):
    def post(self, request):
        try:
            exchange = request.data.get("exchange")
            amount = request.data.get("amount")
            identifier_list = request.data.get("identifier_list")
            user = request.user
            users = MyUser.objects.filter(id__in=set(ClientModel.objects.filter(master_user_link=user.master_user).values_list("client__id", flat=True))
                | set(
                    MastrModel.objects.filter(master_link=user.master_user).values_list("master_user__id", flat=True)))
            records = AdminCoinWithCaseModal.objects.filter(identifier__in=identifier_list, master_coins__in=users, ex_change=exchange)
            if exchange != "NSE":
                records.update(trademargin_amount=float(amount))
            else:
                records.update(trademargin_percentage=float(amount))
            return Response({"status": True, "message": "Data update successfully."})
        except Exception as e:
            print(e)
            return Response({"status": False, "message": "Something went wrong."}, status=status.HTTP_404_NOT_FOUND)

# web api ----------------------------------
class WebScriptQuantityAPI(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        try:
            response = list(AdminCoinWithCaseModal.objects.filter(master_coins__id=request.GET.get('id'),ex_change=request.GET.get('searchInput')).values())
            return Response({"success": True, "response": response}, status=status.HTTP_200_OK)
        except Exception as e:
            print("eeee", e)
            return Response({"success": False, "message": "Something went wrong."}, status=status.HTTP_404_NOT_FOUND)

class ChildUserFetchAPI(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        try:
            user = request.user
            if user.user_type == "Master":
                response_user = MyUser.objects.filter(id__in=set(ClientModel.objects.filter(master_user_link=user.master_user).values_list("client__id", flat=True)) | set(MastrModel.objects.filter(master_link=user.master_user).values_list("master_user__id", flat=True))).values("user_name", "id")
            elif user.user_type == "Admin":
                master_ids = MastrModel.objects.filter(admin_user=user.admin_user).values_list("master_user__id", flat=True)
                client_ids = ClientModel.objects.filter(master_user_link__master_user__id__in=master_ids).values_list("client__id", flat=True)
                response_user = MyUser.objects.filter(id__in=set(master_ids) | set(client_ids)).values("user_name", "id")
            elif request.user.user_type == "SuperAdmin":
                response_user = MyUser.objects.exclude(id=request.user.id).values("user_name", "id")
            return Response({"success": True, "message": "Fetch user record successfully.", "users": list(response_user)}, status=status.HTTP_200_OK)
        except:
            return Response({"success": False, "message": "This api only for admin and master user type."}, status=status.HTTP_404_NOT_FOUND)
        
class MyUserPerissionToggle(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        try:
            key = request.data["key"]
            user_obj = MyUser.objects.get(id=request.data["id"])
            current_value = getattr(user_obj, key)
            if "value" in request.data:
                setattr(user_obj, key, request.data["value"])
            else:
                setattr(user_obj, key, not current_value)
            user_obj.save()
            return Response({"success": True}, status=status.HTTP_200_OK)
        except:
            return Response({"success": False}, status=status.HTTP_404_NOT_FOUND)
        



class ChangePasswordWebAPI(APIView):
    def post(self, request):
        user_name = request.data["user_name"]
        new_password = request.data["new_password"]
        confirm_password = request.data["confirm_password"]
        try:
            user = MyUser.objects.get(user_name=user_name)
        except MyUser.DoesNotExist:
            return Response({"success": False, "message": "User Doesn't exist"}, status=status.HTTP_404_NOT_FOUND)
        
        if new_password == confirm_password:
            user.set_password(new_password)
            user.save()
            update_session_auth_hash(request, user)
            return Response({"success": True, "message": "Password change succesfully"}, status=status.HTTP_200_OK)
        else:
            return Response({"success": False, "message": "New passwords do not match!"}, status=status.HTTP_404_NOT_FOUND)
        

class GetAllAdminApiView(APIView):
    def get(self, request):
        try:
            response = MyUser.objects.filter(user_type="Admin").exclude(id=request.user.id).values("user_name", "id")
            return Response({"success": True, "response": list(response)}, status=status.HTTP_200_OK)
        except:
            return Response({"success": False}, status=status.HTTP_404_NOT_FOUND)
        
class GetMasterApiView(APIView):
    def get(self, request):
        try:
            response = MyUser.objects.get(id=request.GET.get("adminId")).admin_user.admin_user.all().values("master_user__user_name", "master_user__id")
            return Response({"success": True, "response": list(response)}, status=status.HTTP_200_OK)
        except:
            return Response({"success": False}, status=status.HTTP_404_NOT_FOUND)
        
        
        
        
class LimitUserCreation(APIView):
    def post(self, request):
        user_id = request.GET.get("id")
        limit_data = request.data 
        try:
            if user_id and user_id != "":
                user = MyUser.objects.get(id=user_id)
        except MyUser.DoesNotExist as e:
            print("error error", e)
            return Response({"status": False, "message": "User does not exist."}, status=404)
        master_user_data = user.master_user
        master_limit = master_user_data.master_limit
        limit = int(limit_data['master_limit'])
        if master_limit >= limit:
            return Response({"message":"Cannot downgrade more limit"},status=404)
        
        if 'limit' in limit_data:
            master_user_data.limit = limit_data['limit'] == "true" if True else False
        if 'master_limit' in limit_data:
            master_user_data.master_limit = limit_data['master_limit']
        if 'client_limit' in limit_data:
            master_user_data.client_limit = limit_data['client_limit']

        master_user_data.save()
        return Response({"status": True, "message": "Limits updated successfully"})
    
    
    
class AdminRightApi(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        user_id = request.GET.get("user_id")
        admin_Right = request.data
        try:
            user = MyUser.objects.get(id=user_id)
        except MyUser.DoesNotExist:
            return Response({"status": False, "message": "User does not exist."}, status=400)
        if admin_Right.get('user_rights'):
            masters = MastrModel.objects.filter(master_link=user.master_user) 
            for master in masters:
                master.master_user.add_order = admin_Right['add_order']  
                master.master_user.delete_trade = admin_Right['delete_trade']  
                master.master_user.execute_pending_order = admin_Right['execute_pending_order']  
                master.master_user.save()
            client_obj = ClientModel.objects.filter(master_user_link=user.master_user)
            if client_obj and len(client_obj)> 0:
                for cleint in client_obj:
                    cleint.client.add_order = admin_Right['add_order']  
                    cleint.client.delete_trade = admin_Right['delete_trade']  
                    cleint.client.execute_pending_order = admin_Right['execute_pending_order']  
                    cleint.client.save()
                
        if 'add_order' in admin_Right:
            print(admin_Right['add_order'])
            user.add_order = admin_Right['add_order']
        
        if 'delete_trade' in admin_Right:
            user.delete_trade = admin_Right['delete_trade'] 
            
        if 'execute_pending_order' in admin_Right:
            user.execute_pending_order = admin_Right['execute_pending_order'] 
            
        if 'by_manual' in admin_Right:
            user.by_manual = admin_Right['by_manual']
        
        user.save() 
        return Response({"status":True, "message":"Admin Right update Sucessfully"}, status=status.HTTP_200_OK)
    
class AdminRigthsGetApi(APIView):
    def get(self, request):
        user_id = request.GET.get("user_id")
        user = MyUser.objects.filter(id=user_id).values("add_order", "delete_trade", "execute_pending_order", "by_manual", "trade_right").first()
        return Response({"status":True,"data":user})
    
class MarketTradeRight(APIView):
    def post(self, request):
        user_id = request.GET.get("id")
        try:
            user = MyUser.objects.get(id=user_id)
        except MyUser.DoesNotExist:
            return Response({"status": False, "message": "User does not exist."}, status=400)
        trade_right = request.data.get("trade_right") 
        if request.data.get("trade_right")  is None:
            return Response({"status": False, "message": "Trade right is required."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            user.trade_right = trade_right
            user.save()
            return Response({"status":True,"message":"Trade right added sucessfully"}, status=status.HTTP_200_OK)
        

class MarketTradeGetApi(APIView):
    def get(self, request):
        user = MyUser.objects.filter(id=request.GET.get("user_id")).values("trade_right").first()
        return Response({"status":True,"data":user})

class BrkApi(APIView):
    def post(self, request):
        data = request.data
        currentAdmin = MyUser.objects.get(id=request.GET.get("id"))
        if data["price"] != 0:
            if data["exchange"].lower() == "mcx":
                currentAdmin.mcx_brk = data["price"]
            elif data["exchange"].lower() == "nse":
                currentAdmin.nse_brk = data["price"]
            else:
                currentAdmin.mini_brk = data["price"]
        currentAdmin.save()
        return Response({"status":True,"status":"Brk added succesfully"}, status=status.HTTP_200_OK)      

from django.db.models import Count
from datetime import datetime, timedelta
from django.utils import timezone

class TableChartAPi(APIView):
    def post(self, request):
        user = MyUser.objects.get(id=request.data["user_id"])
        currentCoins = request.data["currentCoin"]
        date_array , cancelArray, successArray = [] , [] , [] 
        
        if request.data["type"] == "day":
            four_days_ago = timezone.now().date() - timedelta(days=3)
            current_date = four_days_ago
            while current_date <= timezone.now().date():
                date_array.append(current_date)
                cancel_query = BuyAndSellModel.objects.filter(ex_change__in=currentCoins, buy_sell_user=user, is_cancel=True, created_at__date=current_date).values('created_at__date').annotate(count=Count('id'))
                cancelArray.append(0) if len(cancel_query) == 0 else cancelArray.append(cancel_query[0]["count"])
                success_query = BuyAndSellModel.objects.filter(ex_change__in=currentCoins, buy_sell_user=user, is_cancel=False, created_at__date=current_date).values('created_at__date').annotate(count=Count('id'))
                successArray.append(0) if len(success_query) == 0 else successArray.append(success_query[0]["count"])
                current_date += timedelta(days=1)
                
        elif  request.data["type"] == "week":
            current_date = timezone.now()
            for i in range(4):
                end_of_week = current_date - timedelta(days=current_date.weekday())
                start_of_week = end_of_week - timedelta(days=6)
                date_array.append((start_of_week.strftime('%Y-%m-%d'), end_of_week.strftime('%Y-%m-%d')))
                
                cancel_query = BuyAndSellModel.objects.filter(ex_change__in=currentCoins, buy_sell_user=user, is_cancel=True, created_at__range=(start_of_week, end_of_week)).count()
                cancelArray.append(cancel_query)
                
                success_query = BuyAndSellModel.objects.filter(ex_change__in=currentCoins, buy_sell_user=user, is_cancel=False, created_at__range=(start_of_week, end_of_week)).count()
                successArray.append(success_query)
                
                current_date = start_of_week - timedelta(days=1)
        else:
            current_date = timezone.now()
            for i in range (0, 4):
                month_year = current_date.strftime("%B %Y")
                date_array.append(month_year)
                cancel_query = BuyAndSellModel.objects.filter(ex_change__in=currentCoins, buy_sell_user=user, is_cancel=True, created_at__month=current_date.month, created_at__year=current_date.year).values('created_at__month').annotate(count=Count('id'))
                cancelArray.append(0) if len(cancel_query) == 0 else cancelArray.append(cancel_query[0]["count"])
                success_query = BuyAndSellModel.objects.filter(ex_change__in=currentCoins, buy_sell_user=user, is_cancel=False, created_at__month=current_date.month, created_at__year=current_date.year).values('created_at__month').annotate(count=Count('id'))
                successArray.append(0) if len(success_query) == 0 else successArray.append(success_query[0]["count"])
                current_date = current_date - timedelta(days=current_date.day)
                
        tableResponse = [{"trade": date_array[i], "cancel": cancelArray[i], "success" : successArray[i]} for i in range(4)]
        return Response({"status":True, "date_array": date_array, "cancel": cancelArray, "success": successArray, "tableResponse": tableResponse})


class PieChartHandlerApi(APIView):
    def post(self, request):
        try:
            filterType = request.data["type"]
            limit = int(request.data["limit"])
            currentUser = MyUser.objects.get(id=request.data["user_id"])
            
            currentResult = (
                BuyAndSellModel.objects
                .filter(
                    buy_sell_user=currentUser,
                    is_cancel=False,
                    ex_change__in=request.data["currentCoin"],
                    created_at__date__gte=request.data["fromDate"],
                    created_at__date__lte=request.data["toDate"]
                )
            )
            
            totalQuantity = currentResult.values('coin_name').annotate(total_quantity=Sum(Case(
                When(quantity__lt=0, then=F('quantity') * Value(-1)),
                default=F('quantity'),
                output_field=IntegerField(),
            )))
            
            if filterType == "top":
                totalQuantity = totalQuantity[:limit]
            else:
                totalQuantity = totalQuantity.order_by('-coin_name')[:limit]
            
            tableResult = []
            for obj in totalQuantity:
                currentRow = {}
                currentRow["coin_name"] = obj["coin_name"]
                currentRow["total"] = obj["total_quantity"]
                buyRecord = currentResult.filter(coin_name=obj["coin_name"], action="BUY").values('coin_name').annotate(total_quantity=Sum('quantity'))
                currentRow["buy"] = buyRecord[0]["total_quantity"] if len(buyRecord) > 0 else  0
                sellRecord = currentResult.filter(coin_name=obj["coin_name"], action="SELL").values('coin_name').annotate(total_quantity=Sum('quantity'))
                currentRow["sell"] = -sellRecord[0]["total_quantity"] if len(sellRecord) > 0 else  0
                tableResult.append(currentRow)
                
            return Response({"success": True, "message": "Pie chart data fetch successfully.", "labels": totalQuantity.values_list("coin_name", flat=True), "chartValue": totalQuantity.values_list("total_quantity", flat=True), "tableResult": tableResult}, status=status.HTTP_200_OK)
        except Exception as e:
            print(e, "eeeeee")
            return Response({"success": False, "message": "No record found"}, status=status.HTTP_404_NOT_FOUND)
        



class AccountLimitApi(APIView):
    def get(self, request):
        try:
            print("==============",request.GET.get("user_id"))
            user = request.user
            if (request.GET.get("user_id") and request.GET.get("user_id") != ""):
                user = MyUser.objects.get(id=request.GET.get("user_id"))
        except:
            return Response({"status":False, "message":"you dont have a right to set limit"},status=status.HTTP_400_BAD_REQUEST)
        
        if user.user_type == "Master":
            master_limit = user.master_user.master_limit
            created_master = MastrModel.objects.filter(master_link=user.master_user)
            master_created = 0
            master_occupied = 0
            for obj in created_master:
                if (obj.master_user.user_history.first()):
                    master_created += 1
                else:
                    master_occupied += 1
            master_remaining = master_limit - (master_created + master_occupied)

            client_limit = user.master_user.client_limit
            created_client = user.master_user.master_user_link.all()
            client_created = 0
            client_occupied = 0
            for obj in created_client:
                if (obj.client.user_history.first()):
                    client_created += 1
                else:
                    client_occupied += 1
            client_remaining = client_limit - (client_created + client_occupied)
        else:
            return Response({
                "status": True
            })
        return Response({
            "status": True,
            "master_limit": master_limit,
            "master_created": master_created,
            "master_occupied": master_occupied,
            "master_remaining": master_remaining,
            "client_limit": client_limit,
            "client_created": client_created,
            "client_occupied": client_occupied,
            "client_remaining": client_remaining,
            "user_name": user.user_name
        }, status=status.HTTP_200_OK)

# ------------------------------------------------

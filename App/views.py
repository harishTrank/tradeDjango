from django.shortcuts import render
from django.contrib.auth import login
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from .models import *
from .serializers import *
from client_app.models import *
from master_app.models import *
from rest_framework.exceptions import APIException
from rest_framework.generics import get_object_or_404
from django.http import Http404
from django.contrib.auth.hashers import make_password
from rest_framework.pagination import PageNumberPagination
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.db.models import Sum, F, Value, IntegerField, Case, When, Avg, Q
from django.http import JsonResponse
from django.db.models.functions import Coalesce
from django.db.models import Sum, Avg, Case, When, F, Value, FloatField

class LoginApi(APIView):
    def post(self, request):
        try:
            current_user = MyUser.objects.filter(user_name__iexact=request.data["user_name"]).first()
            if not current_user or not current_user.check_password(request.data["password"]):
                return Response({"success": False, "message": "Invalid credentials."}, status=status.HTTP_404_NOT_FOUND)
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
            
        if limit == False:
            return Response({"status":False, "message":"Cannot create more users."},status=401)
        
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
            
            if request.data.get("add_master"):
                admin_belongs = current_master.admin_user
                create_user = MyUser.objects.create(user_type="Master", **request.data, password=make_password(password))
                current_master = MyUser.objects.get(id=request.user.id).master_user
                MastrModel.objects.create(master_user=create_user, admin_user=admin_belongs, master_link=current_master)
            else:
                create_user = MyUser.objects.create(user_type="Client", **request.data, password=make_password(password))
                ClientModel.objects.create(client=create_user, master_user_link=current_master)
            try:     
                for exchange_item in createUs:
                    ExchangeModel.objects.create(
                        user=create_user,
                        symbol_name=exchange_item['symbol_name'],
                        exchange=exchange_item['exchange'],
                        symbols=exchange_item['symbols'],
                        turnover=exchange_item['turnover']
                    )
            except Exception as e:
                print("e",e)
            
            return Response({"status":True,"message":"User created Successfully"}, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            print("e",e)
            return Response({"error": "User not found"}, status=status.HTTP_400_BAD_REQUEST)
    

class UserProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user = request.user
        exchange = ExchangeModel.objects.filter(user=user.id).values_list('symbol_name', flat=True)
        serializer = GetMyUserSerializer(user)
        tradeCoinData = MarketWatchModel.objects.filter(market_user=request.user).values_list("trade_coin_id", flat=True) 
        data_to_send = {
            "responsecode":status.HTTP_200_OK,
            "responsemessage":"data getting sucessfully",
            "data":{**serializer.data, "exchange": exchange},
            "tradeCoinData":tradeCoinData ,
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

def accountSummaryService(data, user, pandL):
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
            create_summary = AccountSummaryModal(user_summary=user, particular=data["coin_name"], quantity=abs(data["quantity"]), buy_sell_type=data["action"], price=f"{data['price']}", average= f"{list(result)[0]['avg_buy_price']}" if data["action"] == 'BUY' else f"{list(result)[0]['avg_sell_price']}", summary_flg="Profit/Loss", amount=pandL, closing=user.balance)
            create_summary.save()
            
            
class BuySellSellApi(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        if (request.data.get("type") == "WEB"):
            user = MyUser.objects.get(id=request.data.get("userId"))
        else:
            user = request.user
        action = request.data.get('action')
        quantity = request.data.get('quantity')
        lot_size = request.data.get("lot_size")
        is_cancel = request.data.get("is_cancel")
        currentProfitLoss = 0
        
        totalCount = BuyAndSellModel.objects.filter(identifer=request.data.get("identifer"),is_pending=False, trade_status=True,is_cancel=False).values('identifer').annotate(total_quantity=Sum('quantity'), avg_price=Avg('price'))
        try:
            total_quantity = (-totalCount[0]["total_quantity"] if action == 'BUY' else totalCount[0]["total_quantity"])
        except:
            total_quantity = 0
        if totalCount.count() > 0 and (total_quantity < quantity)  and not is_cancel:
            currentProfitLoss = total_quantity * quantity * lot_size
            user.balance += currentProfitLoss
            quantity -= total_quantity
            
        total_cost = lot_size * quantity * request.data.get('price')
        if (totalCount.count() > 0 and (total_quantity == quantity)) and not is_cancel:
            if action == "SELL":
                currentProfitLoss = ( request.data.get('price') -totalCount[0]["avg_price"] ) * quantity * lot_size
            else:
                currentProfitLoss = ( totalCount[0]["avg_price"] -  request.data.get('price') ) * quantity * lot_size
                
            user.balance += currentProfitLoss
        
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
        accountSummaryService(request.data, user, currentProfitLoss)
        if  (totalCount.count() > 0 and totalCount[0]["total_quantity"]== 0):
            BuyAndSellModel.objects.filter(identifer=request.data.get("identifer")).update(trade_status=False)
        return Response({'user_balance':user.balance,'message': 'Buy order successfully' if action =="BUY" else 'Sell order successfully'}, status=status.HTTP_200_OK)    
        
        


class PositionManager(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        try:
            if (request.GET.get("type") == "WEB"):
                user = MyUser.objects.get(id = request.GET.get("id"))
            else:
                user = request.user 
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
            data = request.data  
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
        from_date = request.query_params.get('from_date')
        to_date = request.query_params.get('to_date')
        ex_change = request.query_params.get('ex_change')
        coin_name = request.query_params.get('coin_name')
        is_pending = request.query_params.get("is_pending")
        is_cancel = request.query_params.get("is_cancel")
        
        if user.user_type == "Client":          
            exchange_data = request.user.buy_sell_user.values("id","buy_sell_user__user_name", "quantity", "trade_type", "action", "price", "coin_name", "ex_change","created_at","is_pending","identifer", "message") 
            
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
            user_keys = [request.user.id]
            child_clients = request.user.master_user.master_user_link.all().values_list("client__id", flat=True)
            user_keys += list(child_clients)
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
        response = request.user.buy_sell_user.order_by('-coin_name').values('coin_name').distinct()
        return Response({"response":response,"status":status.HTTP_200_OK},status=status.HTTP_200_OK) 
    
    


class UserListApiView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = PageNumberPagination
    def get(self, request):
        user = request.user
        own_user = request.query_params.get("own_user")
        select_user = request.query_params.get("select_user")
        select_status = request.query_params.get("select_status")
        print("----",select_status)
        print("dfdfdfdf",request.user.user_type)
        if request.user.user_type == "Client":
            users = MyUser.objects.filter(id=request.user.id).values("id","user_name", "user_type","full_name","role","credit","balance")
            return JsonResponse(list(users), safe=False)
        else:
            if own_user == "OWN":
                users = MyUser.objects.filter(id=request.user.id).values("id","user_name", "user_type", "full_name","role","credit","balance")
                return JsonResponse({"results": list(users)}, safe=False)
            elif select_user == "MASTER":
                users = MyUser.objects.filter(id__in=set(MastrModel.objects.filter(master_link=user.master_user).values_list("master_user__id", flat=True)))
            elif select_status == "Active":
                users = MyUser.objects.filter(status=True if select_status else False,id__in=set(MastrModel.objects.filter(master_link=user.master_user).values_list("master_user__id", flat=True)))
                print("==========",users)
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
            serializer = AdminSerializer(admin_models)
        return Response({"success":True, "message": "Data getting successfully.", "data": serializer.data}, status=status.HTTP_200_OK)


# web api ----------------------------------
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
            setattr(user_obj, key, not current_value)
            user_obj.save()
            return Response({"success": True}, status=status.HTTP_200_OK)
        except:
            return Response({"success": False}, status=status.HTTP_404_NOT_FOUND)
        



class ChangePasswordWebAPI(APIView):
    def post(self, request):
        if request.user.user_type == "Master" or request.user.user_type == "Client" and request.user.user_name == request.data["user_name"]:
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
        return Response({"success": False, "message": "Invalid user name."}, status=status.HTTP_404_NOT_FOUND)
        

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
            user = MyUser.objects.get(id=user_id)
        except MyUser.DoesNotExist:
            return Response({"status": False, "message": "User does not exist."}, status=404)
        master_user_data, created = MastrModel.objects.get_or_create(master_user=user)
        
        if 'limit' in limit_data:
            master_user_data.limit = limit_data['limit'] == "true" if True else False
        if 'master_limit' in limit_data:
            master_user_data.master_limit = limit_data['master_limit']
        if 'client_limit' in limit_data:
            master_user_data.client_limit = limit_data['client_limit']

        master_user_data.save()
        return Response({"status": True, "message": "Limits updated successfully"})
    
    
    
class AdminRightApi(APIView):
    def post(self, request):
        user_id = request.GET.get("id")
        admin_Right = request.data
        try:
            user = MyUser.objects.get(id=user_id)
        except MyUser.DoesNotExist:
            return Response({"status": False, "message": "User does not exist."}, status=400)
        master_user_data , created = MastrModel.objects.get_or_create(master_user=user)
        
        if 'add_order' in admin_Right:
            master_user_data.add_order = admin_Right['add_order']
        
        if 'delete_trade' in admin_Right:
            master_user_data.delete_trade = admin_Right['delete_trade'] 
            
        if 'execute_pending_order' in admin_Right:
            master_user_data.execute_pending_order = admin_Right['execute_pending_order'] 
            
        if 'by_manual' in admin_Right:
            master_user_data.by_manual = admin_Right['by_manual']
        master_user_data.save() 
        return Response({"status":True, "message":"Admin Right Add Sucessfully"}, status=status.HTTP_200_OK)
    
    
class MarketTradeRight(APIView):
    def post(self, request):
        user_id = request.GET.get("id")
        try:
            user = MyUser.objects.get(id=user_id)
        except MyUser.DoesNotExist:
            return Response({"status": False, "message": "User does not exist."}, status=400)
        master_user_data , created = MastrModel.objects.get_or_create(master_user=user)
        print("master_user_data",master_user_data.trade_right)
        trade_right = request.data.get("trade_right") 
        if request.data.get("trade_right")  is None:
            return Response({"status": False, "message": "Trade right is required."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            master_user_data.trade_right = trade_right
            master_user_data.save()
            return Response({"status":True,"message":"Trade right added sucessfully"}, status=status.HTTP_200_OK)

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
        params = request.data
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

# ------------------------------------------------

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
from django.db.models import Sum, Avg , Q
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages


class LoginApi(APIView):
    permission_classes = [AllowAny,]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            response = serializer.create(serializer.validated_data)
            return Response(response)
        else:
            responcemessage = ""
            for item in serializer.errors.items():
                responcemessage += " " + f"error in {item[0]}:-{item[1][0]}"
            response = {
                "responsecode": status.HTTP_400_BAD_REQUEST,
                "responcemessage": responcemessage
            }
            return Response(response, status=status.HTTP_400_BAD_REQUEST)




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
                MastrModel.objects.create(master_user=create_user, admin_user=admin_belongs)
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
        serializer = GetMyUserSerializer(user)
        tradeCoinData = MarketWatchModel.objects.filter(market_user=request.user).values_list("trade_coin_id", flat=True) 
        data_to_send = {
            "responsecode":status.HTTP_200_OK,
            "responsemessage":"data getting sucessfully",
            "data":serializer.data,
            "tradeCoinData":tradeCoinData      
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
            
            
            

class BuySellSellApi(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        user = request.user 
        action = request.data.get('action')
        quantity = request.data.get('quantity')
        lot_size = request.data.get("lot_size")
        
        total_cost = lot_size * quantity * request.data.get('price')
        if user.balance < total_cost:
            return Response({'message': 'Insufficient balance/quantity'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            totalCount = BuyAndSellModel.objects.filter(identifer=request.data.get("identifer")).values('identifer').annotate(total_quantity=Sum('quantity'))
            if (len(totalCount) > 0):
                totalCount = totalCount[0]["total_quantity"] + (quantity if action == 'BUY' else -quantity)
                
            if action == 'BUY' and user.balance >= total_cost:  
                user.balance -= total_cost
            else:
                user.balance += total_cost
            user.save()
            buy_sell_instance = BuyAndSellModel(
                buy_sell_user=user,
                quantity=quantity if action == 'BUY' else -quantity,
                trade_type=request.data.get('trade_type'),
                action=request.data.get('action'),
                price=request.data.get('price'),
                coin_name=request.data.get('coin_name'),
                ex_change=request.data.get('ex_change'),
                is_pending=request.data.get('is_pending'),
                identifer=request.data.get("identifer"),
                ip_address=request.data.get("ip_address"),
                order_method=request.data.get("order_method"),)
            buy_sell_instance.save()
            if (totalCount == 0):
                BuyAndSellModel.objects.filter(identifer=request.data.get("identifer")).update(trade_status=False)
            
            return Response({'user_balance':user.balance,'message': 'Buy order successfully' if action =="BUY" else 'Sell order successfully'}, status=status.HTTP_200_OK)    
           


class PositionManager(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        try:
            user = request.user 
            data = request.data  
            results = (
                user.buy_sell_user.all()
                .filter(is_pending=False, trade_status=True)
                .values('identifer','coin_name')
                .annotate(total_quantity=Sum('quantity'), avg_price=Avg('price'))
                .exclude(total_quantity=0)
            )
            return Response({"status": True, "response": results}, status=status.HTTP_200_OK)
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
                .filter(is_pending=False, trade_status=True)
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
        identifer = request.query_params.get("identifer")
        ip_address = request.query_params.get("ip_address")
        order_method = request.query_params.get("order_method")
        
        if user.user_type == "Client":          
            exchange_data = request.user.buy_sell_user.all().values("id","buy_sell_user__user_name", "quantity", "trade_type", "action", "price", "coin_name", "ex_change","created_at","is_pending","identifer") 
            
            if from_date and to_date:
                
                from_date_obj = timezone.datetime.strptime(from_date, '%Y-%m-%d').replace(hour=0, minute=0, second=0, microsecond=0)
                to_date_obj = timezone.datetime.strptime(to_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59, microsecond=999999)
                
                exchange_data = exchange_data.filter(created_at__range=(from_date_obj, to_date_obj))
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
            response = BuyAndSellModel.objects.filter(buy_sell_user__id__in=user_keys).values("id","buy_sell_user__user_name", "quantity", "trade_type", "action", "price", "coin_name", "ex_change", "created_at","is_pending","identifer")
            
            if from_date and to_date:
                from_date_obj = timezone.datetime.strptime(from_date, '%Y-%m-%d').replace(hour=0, minute=0, second=0, microsecond=0)
                to_date_obj = timezone.datetime.strptime(to_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59, microsecond=999999)
                response = response.filter(created_at__range=(from_date_obj, to_date_obj))
                
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
           
        users = user.master_user.master_user_link.all()

        if own_user:
            users = users.filter(id=user.id)
        
        if select_user:
            users = users.filter(user_type=select_user)
        
        if select_status:
            users = users.filter(status=select_status)
        paginator = self.pagination_class()
        paginated_goals = paginator.paginate_queryset(users, request)
        serializer = MyUserSerializer(paginated_goals, many=True)
        
        return Response({"data":"comming soon...."},status=status.HTTP_200_OK)


# web api
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
        
# --------
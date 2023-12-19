from rest_framework import serializers
from rest_framework import status
from .models import *
from rest_framework_simplejwt.tokens import RefreshToken
from client_app.models import *
from master_app.models import *


class LoginSerializer(serializers.Serializer):
    user_name = serializers.CharField(required=True, allow_blank=False)
    password = serializers.CharField(required=True, allow_blank=False)
    user_type = serializers.CharField(required=True, allow_blank=False)
    def validate_password(self, value):
        if not value:
            raise serializers.ValidationError("Password is required")
    
        # Password validation
        if len(value) < 6 or len(value) > 50:
            raise serializers.ValidationError("The length should be between 6 and 50 characters.")
        return value
    
        

    def validate(self, attrs):
        user_name = attrs.get('user_name')
        password = attrs.get('password')
        user_type = attrs.get('user_type')

        user = MyUser.objects.filter(user_name__iexact=user_name).first()
        print("this 29 ======",user)
        if not user:
            raise serializers.ValidationError("User does not exist.")

        if not user.check_password(password):
            raise serializers.ValidationError("Incorrect password.")
        
        # user = MyUser.objects.filter(user_type=user_type).first()
        # print("this 38 ======",user)
        
        if not user:
            raise serializers.ValidationError("User role not exist.")
        
        unknown_fields = set(self.initial_data) - set(self.fields)
        if unknown_fields:
            raise serializers.ValidationError(f"Unknown field: {', '.join(unknown_fields)}")

        print("this 47 ======",attrs)
        
        return attrs
    def create(self, validated_data):
        user = validated_data['user']
        print("this 52 ======",user)

        refresh = RefreshToken.for_user(user)
        token = {
            # 'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
        # Return response with token and success message
        response = {
            'responsecode':status.HTTP_200_OK,
            'userid': user.id,
            'role':user.role,
            'token': token,
            'responsemessage': 'User logged in successfully.',
        }
        return response
    
    
    
class ResetPasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
    confirm_password = serializers.CharField(required=True)

    def validate(self, attrs):
        new_password = attrs.get('new_password')
        confirm_password = attrs.get('confirm_password')

        if new_password != confirm_password:
            raise serializers.ValidationError("New password and confirm password do not match.")

        if not new_password:
            raise serializers.ValidationError("New password is required.")

        if not confirm_password:
            raise serializers.ValidationError("Confirm password is required.")

        # Password validation
        if len(new_password) < 6 or len(new_password) > 50:
            raise serializers.ValidationError("The length of the new password should be between 6 and 50 characters.")

        return attrs
    
    
    
    
class GetMyUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyUser
        fields = "__all__"
        read_only_fields = ['id', 'email']
        
        

class TradeCoinSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketWatchModel
        fields = ['trade_coin_id'] 
        
    def validate(self, attrs):
        trade_coin_id = attrs.get('trade_coin_id')
        if not trade_coin_id:
            raise serializers.ValidationError("trade_coin_id is required")
        return attrs
    
 
    
class TradeHistorySerialzer(serializers.ModelSerializer):
    class Meta:
        model = BuyAndSellModel
        fields = "__all__"
        
        
class MyUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyUser
        fields = '__all__'


class MyUserSerializerParticularDetails(serializers.ModelSerializer):
    class Meta:
        model = MyUser
        fields = ("user_name", "user_type", "full_name", "role", "phone_number", "email", "city", "credit", "balance", "address")

class ClientSerializer(serializers.ModelSerializer):
    client_user_details = MyUserSerializerParticularDetails(source="client")
    class Meta:
        model = ClientModel
        fields = '__all__'

class MasterSerializer(serializers.ModelSerializer):
    clients = ClientSerializer(many=True, read_only=True, source='master_user_link')
    master_user_details = MyUserSerializerParticularDetails(source="master_user")
    class Meta:
        model = MastrModel
        fields = '__all__'


class AdminSerializer(serializers.ModelSerializer):
    user_details = MyUserSerializerParticularDetails(source="user")
    masters = MasterSerializer(many=True, read_only=True, source='admin_user')
    clients = ClientSerializer(many=True, read_only=True, source='admin_create_client')
    class Meta:
        model = AdminModel
        fields = '__all__'
from django.urls import path
from App.views import *
urlpatterns = [
    path("login/",LoginApi.as_view(),name="login"),
    path("add-user/",AddUserAPIView.as_view(),name="add-user"),
    path('update-password/', ResetPasswordView.as_view(), name='change-password'),
    path('user-profile/', UserProfileAPIView.as_view(), name='user-profile'),
    path('market-coin/', MaketWatchScreenApi.as_view(), name='add-market-coin'),
    path('buy-sell-coin/', BuySellSellApi.as_view(), name='buy-sell-coin'),
    path('trade-history/', TradeHistoryApi.as_view(), name='trade-history'),
    path('user-coin-list/', CoinNameApi.as_view(), name='user-coin-list'),
    path('user-list/', UserListApiView.as_view(), name='user-list'),
    path("position/", PositionManager.as_view(), name="position"),
    path("position-coins/", PositionCoinsManager.as_view(), name="position-coins"),
    path("trade-particular-view/<int:id>", TradeParticularViewApi.as_view(), name="trade-particular-view/"),
    path("permission-toggle/", MyUserPerissionToggle.as_view(), name="permission-toggle")
]

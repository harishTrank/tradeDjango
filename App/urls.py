from django.urls import path
from App.views import *
urlpatterns = [
    path("login/",LoginApi.as_view(),name="login"),
    path("logout/",LogoutUserAPIView.as_view(),name="login"),
    path("add-user/",AddUserAPIView.as_view(),name="add-user"),
    path('update-password/', ResetPasswordView.as_view(), name='change-password'),
    path('user-profile/', UserProfileAPIView.as_view(), name='user-profile'),
    path('market-coin/', MaketWatchScreenApi.as_view(), name='add-market-coin'),
    path('buy-sell-coin/', BuySellSellApi.as_view(), name='buy-sell-coin'),
    path('trade-history/', TradeHistoryApi.as_view(), name='trade-history'),
    path('user-coin-list/', CoinNameApi.as_view(), name='user-coin-list'),
    path('user-list/', UserListApiView.as_view(), name='user-list'),
    path("position/", PositionManager.as_view(), name="position"),
    path("account-summary/", AccountSummaryApi.as_view(), name="account-summary"),
    path("position-coins/", PositionCoinsManager.as_view(), name="position-coins"),
    path("trade-particular-view/<str:id>", TradeParticularViewApi.as_view(), name="trade-particular-view/"),
    path("permission-toggle/", MyUserPerissionToggle.as_view(), name="permission-toggle"),
    path("change-passwordweb-api/", ChangePasswordWebAPI.as_view(), name="change-passwordweb-api"),
    path("get-admin-api/", GetAllAdminApiView.as_view(), name="get-admin-api"),
    path("get-master-api/", GetMasterApiView.as_view(), name="get-master-api"),
    path("limit-user-creation/", LimitUserCreation.as_view(), name="limit-user-creation"),
    path("admin-right/", AdminRightApi.as_view(), name="admin-right"),
    path("admin-trade-right/", MarketTradeRight.as_view(), name="admin-trade-right"),
    path("brk/", BrkApi.as_view(), name="brk"),
    path("table-chart/", TableChartAPi.as_view(), name="table-chart"),
    path("pie-chart-api/", PieChartHandlerApi.as_view(), name="pie-chart-api"),
    path("child-user-api/", ChildUserFetchAPI.as_view(), name="child-user-api"),
    path("login-history/", LoginHistoryApi.as_view(), name="login-history"),
    # path("user-list/", UserListApi.as_view(), name="user-list"),
    path("search-user-api/", SearchUserAPI.as_view(), name="search-user-api"),
    path("script-quantity-api/", ScriptQuantityAPI.as_view(), name="script-quantity-api")
    
]

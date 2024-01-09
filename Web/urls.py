from django.contrib import admin
from django.urls import path, include
from Web.views import *

urlpatterns = [
    path("",LoginView.as_view(),name="login"),
    path("logout", LogoutView.as_view(), name="logout"),
    path("change-password",ChangePasswordView.as_view(),name="change-password"),
    path("dashboard",Dashboard.as_view(),name="dashboard"),
    
    
    path("add-user",AddUserView.as_view(),name="add-user"),
    path("list-user",ListUserView.as_view(),name="list-user"),
    path("edit-user/<str:id>",EditUserView.as_view(),name="edit-user"),
    # path("account-limit",AccountLimitView.as_view(),name="account-limit"),
    
    
    path("download-csv",DownloadCSVView.as_view(),name="download-csv"),
    path("search-user",SearchUserView.as_view(),name="search-user"),
    path("search-all-user",SearchUsersView.as_view(),name="search-all-user"),
    
    
    path("user-deatils",UserDeatilsView.as_view(),name="user-deatils"),
    path("user-deatils-by-id/<str:id>",UserDeatilsViewById.as_view(),name="user-deatils-by-id"),
    path("user-script/<str:id>",UserScriptMaster.as_view(),name="user-script"),
    
    path("group-setting",GropuSettingView.as_view(),name="group-setting"),
    path("script-quantity-setting",ScriptQuantitySetting.as_view(),name="script-quantity-setting"),
    path("tab-trade/<str:id>",TabTrades.as_view(),name="tab-trade"),
    
    
    path("quantity-setting/<str:id>",QuantitySettingView.as_view(),name="quantity-setting"),
    path("brk/<str:id>",BrkView.as_view(),name="brk"),
    path("trade-margin/<str:id>",TradeMargin.as_view(),name="trade-margin"),
    path("credit/<str:id>",CreditView.as_view(),name="credit"),
    path("tab-account-summary/<str:id>",TabAccountSummary.as_view(),name="tab-account-summary"),
    path("tab-settlement/<str:id>",TabSettlement.as_view(),name="tab-settlement"),
    path("rejection-log/<str:id>",RejectionLogView.as_view(),name="rejection-log"),
    path("share-deatils",ShareDetailsView.as_view(),name="share-deatils"),
    path("user-info/<str:id>",UserInfoView.as_view(),name="user-info"),
    
    
    path("market-watch",MarketWatchView.as_view(),name="market-watch"),
    path("trades",TradesView.as_view(),name="trades"),
    path("orders",OrdersView.as_view(),name="orders"),
    path("positions",PositionsView.as_view(),name="positions"),
    path("profit-and-loss",ProfitAndLoss.as_view(),name="profit-and-loss"),
    path("m2m-profit-and-loss",M2MProfitAndLoss.as_view(),name="m2m-profit-and-loss"),
    path("intraday-history",IntradayHistory.as_view(),name="intraday-history"),
    path("rejection-log",RejectionLogTab.as_view(),name="rejection-log"),
    path("login-history",LoginHistory.as_view(),name="login-history"),
    
    
    path("open-position",OpenPosition.as_view(),name="open-position"),
    path("manage-trades",ManageTrades.as_view(),name="manage-trades"),
    path("trade-account",TradeAccount.as_view(),name="trade-account"),
    path("settlement",SettlementView.as_view(),name="settlement"),
    path("account-summary",AccountSummary.as_view(),name="account-summary"),
    path("bill-generate",BillGenerate.as_view(),name="bill-generate"),
    path("logs-history",LogsHistory.as_view(),name="logs-history"),
    path("user-logs-new",UserLogsNew.as_view(),name="user-logs-new"),
    path("user-script-position-track",UserScriptPositionTrack.as_view(),name="user-script-position-track"),
    path("user-script-position-trac-pl",UserScriptPositionTrackPl.as_view(),name="user-script-position-trac-pl"),
    path("script-quantity",ScriptQuantity.as_view(),name="script-quantity"),
    
#----------------------csv download ---------------------#

    path('rejection-csv/<str:id>/', RejectionDownloadCSVView.as_view(), name='Admin:rejection-csv'),
    # path('order-csv/', OrderDownloadCSVView.as_view(), name='order-csv')

]

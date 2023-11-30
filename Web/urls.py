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
    path("download-csv",DownloadCSVView.as_view(),name="download-csv"),
    path("search-user",SearchUserView.as_view(),name="search-user"),
    path("search-all-user",SearchUsersView.as_view(),name="search-all-user"),
    
    path("market-watch",MarketWatchView.as_view(),name="market-watch"),
    path("trades",TradesView.as_view(),name="trades"),
    path("orders",OrdersView.as_view(),name="orders"),
    path("positions",PositionsView.as_view(),name="positions"),
    path("profit-and-loss",ProfitAndLoss.as_view(),name="profit-and-loss"),
    path("m2m-profit-and-loss",M2MProfitAndLoss.as_view(),name="m2m-profit-and-loss"),
    path("intraday-history",IntradayHistory.as_view(),name="intraday-history"),
    path("rejection-log",RejectionLog.as_view(),name="rejection-log"),
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
    
]

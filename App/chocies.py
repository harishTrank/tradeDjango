USER_TYPE_CHOICES = (
        ('SuperAdmin', 'SuperAdmin'),
        ('Admin', 'Admin'),
        ('Master', 'Master'),
        ('Client', 'Client'),
    )

ROLE_CHOICES = (
        ('AREX', 'AREX'),
        ('DEMO', 'DEMO'),
    )

TRADE_TYPE = (
    ('MARKET','MARKET'),
    ('LIMIT','LIMIT'),
    ('SL','SL')
)


ACTION = (
    ('BUY','BUY'),
    ('SELL','SELL')
)

ACTIONLOGIN = (
    ('LOGIN','LOGIN'),
    ('LOGOUT','LOGOUT')
)

SUMMARYFLAG = (
    ('Profit/Loss', 'Profit/Loss'),
    ('Brokerage', 'Brokerage'),
    ('Credit', 'Credit'),
)
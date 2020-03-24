"""
Gateway for FTX Crypto Exchange.
"""
from logging import DEBUG
import urllib
import hashlib
import hmac
import time
from copy import copy
from datetime import datetime, timedelta
from enum import Enum
from threading import Lock

from myApi.rest import RestClient, Request
from myApi.websocket import WebsocketClient
from myConstant import (
    Direction,
    Exchange,
    Product,
    Status,
    Offset,
    OrderType,
    Interval,
    EVENT_ACCOUNT_MARGIN,
    EVENT_BORROW_MONEY,
    EVENT_REPAY_MONEY
)
from myGateway import BaseGateway
from myObject import (
    TickData,
    OrderData,
    TradeData,
    AccountData,
    ContractData,
    BarData,
    OrderRequest,
    CancelRequest,
    SubscribeRequest,
    HistoryRequest,
    MarginAccountData
)
from myEvent import Event, EVENT_TIMER

REST_HOST = "https://ftx.com/api"
WEBSOCKET_HOST = "wss://ftx.com/ws/"
WEBSOCKET_TRADE_HOST = "wss://ftx.com/ws/"
WEBSOCKET_DATA_HOST = " tcp+ssl://fix.ftx.com:4363"


class FtxGateway(BaseGateway):
    """"""
    def __init__(self, event_engine):
        """Constructor"""
        super().__init__()
        
        self.rest_api = FtxRestApi(self)
        self.market_ws_api = FtxDataWebsocketApi(self)
        self.trade_ws_api = FtxTradeWebsocketApi(self)

    def connect(self, setting: dict):
        pass

    def subscribe(self, req: SubscribeRequest):
        pass

    def send_order(self, req: OrderRequest):
        pass

    def cancel_order(self, req:CancelRequest):
        pass

    def query_account(self):
        pass

    def query_position(self):
        pass

    def stop(self):
        pass

    def process_timer_event(self, event: Event):
        pass

class FtxRestApi(RestClient):
    """"""
    def __init__(self, gateway:FtxGateway):
        """"""
        super().__init__()
        
        self.gateway = gateway
        self.gateway_name = gateway.gateway_name

    def sign(self, request):
        """
        Generate FTX signature
        """

        # Add headers

        return request

    def connect(
        self, 
        key: str,
        secret: str,
        session_number: int,
        proxy_host: str,
        proxy_port: int
    ):
        pass

    def query_time(self):
        pass
    def query_account(self):
        pass
    def query_order(self):
        pass
    def query_contract(self):
        pass
    def send_order(self):
        pass
    def cancel_order(self):
        pass

    def on_query_time(self, data, request):
        pass
    def on_query_account(self, data, request):
        pass
    def on_query_order(self, data, request):
        pass
    def on_query_contract(self, data, request):
        pass
    def on_send_order(self, data, request):
        pass
    def on_cancel_order(self, data, request):
        pass

class FtxTradeWebsocketApi(WebsocketClient):
    """"""
    def __init__(self, gateway:FtxGateway):
        """"""
        super().__init__()

        self.gateway = gateway
        self.gateway_name = gateway.gateway_name

    def connect(self, url, proxy_host, proxy_port):
        self.init(url, proxy_host, proxy_port)
        self.start()

    def on_connected(self):
        pass

    def on_packet(self, packet):
        pass

    def on_account(self, packet):
        pass

    def on_order(self, packet):
        pass

class FtxDataWebsocketApi(WebsocketClient):
    """"""
    def __init__(self, gateway:FtxGateway):
        """"""
        super().__init__()
    
        self.gateway = gateway
        self.gateway_name = gateway.gateway_name

        self.ticks = {}

    def connect(self, proxy_port, proxy_port):
        pass

    def subscribe(self, req:SubscribeRequest):
        pass

    def on_packet(self, packet):
        pass
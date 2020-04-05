"""
Gateway for Binance Crypto Exchange.
"""
from logging import DEBUG, INFO, CRITICAL
import urllib
import hashlib
import hmac
import time
import numpy as np
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
    Interval
)
from myGateway import BaseGateway
from myObject import (
    TickData,
    DepthTickData,
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
from myEvent import (
    Event, 
    EVENT_TIMER,     
    EVENT_ACCOUNT_MARGIN,
    EVENT_BORROW_MONEY,
    EVENT_REPAY_MONEY
)

REST_HOST = "https://api.binance.com"
WEBSOCKET_TRADE_HOST = "wss://stream.binance.com:9443/ws/"
WEBSOCKET_DATA_HOST = "wss://stream.binance.com:9443/stream?streams="

STATUS_BINANCE2VT = {
    "NEW": Status.NOTTRADED,
    "PARTIALLY_FILLED": Status.PARTTRADED,
    "FILLED": Status.ALLTRADED,
    "CANCELED": Status.CANCELLED,
    "EXPIRED": Status.CANCELLED,
    "REJECTED": Status.REJECTED
}

ORDERTYPE_VT2BINANCE = {
    OrderType.LIMIT: "LIMIT",
    OrderType.MARKET: "MARKET"
}
ORDERTYPE_BINANCE2VT = {v: k for k, v in ORDERTYPE_VT2BINANCE.items()}

DIRECTION_VT2BINANCE = {
    Direction.LONG: "BUY",
    Direction.SHORT: "SELL"
}
DIRECTION_BINANCE2VT = {v: k for k, v in DIRECTION_VT2BINANCE.items()}

INTERVAL_VT2BINANCE = {
    Interval.MINUTE: "1m",
    Interval.HOUR: "1h",
    Interval.DAILY: "1d",
}

TIMEDELTA_MAP = {
    Interval.MINUTE: timedelta(minutes=1),
    Interval.HOUR: timedelta(hours=1),
    Interval.DAILY: timedelta(days=1),
}


class Security(Enum):
    NONE = 0
    SIGNED = 1
    API_KEY = 2


symbol_name_map = {}


class BinanceDepthGateway(BaseGateway):
    """
    VN Trader Gateway for Binance connection.
    """

    default_setting = {
        "key": "",
        "secret": "",
        "session_number": 3,
        "proxy_host": "",
        "proxy_port": 0,
    }

    exchanges = [Exchange.BINANCE]

    def __init__(self, event_engine):
        """Constructor"""
        super().__init__(event_engine, "BINANCE")

        self.trade_ws_api = BinanceTradeWebsocketApi(self)
        self.market_ws_api = BinanceDataWebsocketApi(self)
        self.rest_api = BinanceRestApi(self)
        self.query_account_margin_count = 0
    def connect(self, setting: dict):
        """"""
        key = setting["key"]
        secret = setting["secret"]
        session_number = setting["session_number"]
        proxy_host = setting["proxy_host"]
        proxy_port = setting["proxy_port"]

        self.rest_api.connect(key, secret, session_number,
                              proxy_host, proxy_port)
        self.market_ws_api.connect(proxy_host, proxy_port)

        self.event_engine.register(EVENT_TIMER, self.process_timer_event)

    def subscribe(self, req: SubscribeRequest):
        """"""
        self.market_ws_api.subscribe(req)

    # def send_order(self, req: OrderRequest):
    #     """"""
    #     return self.rest_api.send_order(req)

    def send_order(self, req: OrderRequest):
        """"""
        return self.rest_api.send_order_margin(req)

    def borrow_money(self, asset, amount):
        """"""
        return self.rest_api.borrow_money(asset, amount)
    def repay_money(self, req):
        """"""
        return self.rest_api.repay_money(req)

    def cancel_order(self, req: CancelRequest):
        """"""
        self.rest_api.cancel_order_margin(req)

    def query_account(self):
        """"""
        pass
    def query_account_margin(self):
        """"""
        pass

    def query_position(self):
        """"""
        pass

    def query_history(self, req: HistoryRequest):
        """"""
        return self.rest_api.query_history(req)

    def close(self):
        """"""
        self.rest_api.stop()
        self.trade_ws_api.stop()
        self.market_ws_api.stop()

    def process_timer_event(self, event: Event):
        """"""
        # self.rest_api.keep_user_stream()
        self.rest_api.keep_user_stream_margin()

        self.query_account_margin_count += 1
        if self.query_account_margin_count > 300:
            self.query_account_margin_count = 0
            self.rest_api.query_latest_price()

        self.rest_api.query_account_margin()

    def on_account_margin(self, account: MarginAccountData):
        """
        Account event push.
        Account event of a specific vt_accountid is also pushed.
        """
        self.on_event(EVENT_ACCOUNT_MARGIN, account)

    def on_borrow_money(self, data):
        self.on_event(EVENT_BORROW_MONEY, data)
        
    def on_repay_money(self, data):
        self.on_event(EVENT_REPAY_MONEY, data)


class BinanceRestApi(RestClient):
    """
    BINANCE REST API
    """

    def __init__(self, gateway: BinanceDepthGateway):
        """"""
        super().__init__()

        self.gateway = gateway
        self.gateway_name = gateway.gateway_name

        self.trade_ws_api = self.gateway.trade_ws_api

        self.key = ""
        self.secret = ""

        self.user_stream_key = ""
        self.user_stream_key_margin = ""
        self.keep_alive_count = 0
        self.keep_alive_count_margin = 0
        self.recv_window = 5000
        self.time_offset = 0

        self.order_count = 1_000_000
        self.order_count_lock = Lock()
        self.connect_time = 0
        self.latest_price = {}

    def sign(self, request):
        """
        Generate BINANCE signature.
        """
        security = request.data["security"]
        if security == Security.NONE:
            request.data = None
            return request

        if request.params:
            path = request.path + "?" + urllib.parse.urlencode(request.params)
        else:
            request.params = dict()
            path = request.path

        if security == Security.SIGNED:
            timestamp = int(time.time() * 1000)

            if self.time_offset > 0:
                timestamp -= abs(self.time_offset)
            elif self.time_offset < 0:
                timestamp += abs(self.time_offset)

            request.params["timestamp"] = timestamp

            query = urllib.parse.urlencode(sorted(request.params.items()))
            signature = hmac.new(self.secret, query.encode(
                "utf-8"), hashlib.sha256).hexdigest()

            query += "&signature={}".format(signature)
            path = request.path + "?" + query

        request.path = path
        request.params = {}
        request.data = {}

        # Add headers
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "X-MBX-APIKEY": self.key
        }

        if security in [Security.SIGNED, Security.API_KEY]:
            request.headers = headers

        return request

    def connect(
        self,
        key: str,
        secret: str,
        session_number: int,
        proxy_host: str,
        proxy_port: int
    ):
        """
        Initialize connection to REST server.
        """
        self.key = key
        self.secret = secret.encode()
        self.proxy_port = proxy_port
        self.proxy_host = proxy_host

        self.connect_time = (
            int(datetime.now().strftime("%y%m%d%H%M%S")) * self.order_count
        )

        self.init(REST_HOST, proxy_host, proxy_port)
        self.start(session_number)

        self.gateway.write_log("REST API启动成功")

        self.query_time()
        # self.query_account()
        self.query_latest_price()
        time.sleep(2)
        self.query_account_margin()
        # self.query_order()
        self.query_contract()
        # self.start_user_stream()
        self.start_user_stream_margin()

    def query_time(self):
        """"""
        data = {
            "security": Security.NONE
        }
        path = "/api/v1/time"

        return self.add_request(
            "GET",
            path,
            callback=self.on_query_time,
            data=data
        )

    def query_latest_price(self):
        """"""
        data = {"security": Security.NONE}

        self.add_request(
            method="GET",
            path="/api/v3/ticker/price",
            callback=self.on_query_latest_price,
            data=data
        )

    def query_account(self):
        """"""
        data = {"security": Security.SIGNED}

        self.add_request(
            method="GET",
            path="/api/v3/account",
            callback=self.on_query_account,
            data=data
        )

    def query_account_margin(self):
        """"""
        data = {"security": Security.SIGNED}

        self.add_request(
            method="GET",
            path="/sapi/v1/margin/account",
            callback=self.on_query_account_margin,
            data=data
        )
        # print("query_account_margin")
    
    def query_order(self):
        """"""
        data = {"security": Security.SIGNED}

        self.add_request(
            method="GET",
            path="/api/v3/openOrders",
            callback=self.on_query_order,
            data=data
        )

    def query_contract(self):
        """"""
        data = {
            "security": Security.NONE
        }
        self.add_request(
            method="GET",
            path="/api/v1/exchangeInfo",
            callback=self.on_query_contract,
            data=data
        )

    def _new_order_id(self):
        """"""
        with self.order_count_lock:
            self.order_count += 1
            return self.order_count

    def send_order(self, req: OrderRequest):
        """"""
        orderid = str(self.connect_time + self._new_order_id())
        order = req.create_order_data(
            orderid,
            self.gateway_name
        )
        self.gateway.on_order(order)

        data = {
            "security": Security.SIGNED
        }

        params = {
            "symbol": req.symbol,
            "timeInForce": "GTC",
            "side": DIRECTION_VT2BINANCE[req.direction],
            "type": ORDERTYPE_VT2BINANCE[req.type],
            "price": str(req.price),
            "quantity": str(req.volume),
            "newClientOrderId": orderid,
            "newOrderRespType": "ACK"
        }

        self.add_request(
            method="POST",
            path="/api/v3/order",
            callback=self.on_send_order,
            data=data,
            params=params,
            extra=order,
            on_error=self.on_send_order_error,
            on_failed=self.on_send_order_failed
        )

        return order.vt_orderid

    def send_order_margin(self, req: OrderRequest):
        """"""
        orderid = str(self.connect_time + self._new_order_id())
        order = req.create_order_data(
            orderid,
            self.gateway_name
        )
        self.gateway.on_order(order)

        data = {
            "security": Security.SIGNED
        }

        params = {
            "symbol": req.symbol,
            "side": DIRECTION_VT2BINANCE[req.direction],
            "type": ORDERTYPE_VT2BINANCE[req.type],
            "price": str(req.price),
            "quantity": str(req.volume),
            "newClientOrderId": orderid,
            "timeInForce": 'GTC'
        }
        if req.borrowmoney:
            params["sideEffectType"] = "MARGIN_BUY"
            params["timeInForce"] = "IOC"

        self.add_request(
            method="POST",
            path="/sapi/v1/margin/order",
            callback=self.on_send_order,
            data=data,
            params=params,
            extra=order,
            on_error=self.on_send_order_error,
            on_failed=self.on_send_order_failed
        )
        msg = f'Rest send order:{order.vt_orderid}'
        self.gateway.write_log(msg, level=DEBUG)
        return order.vt_orderid

    def cancel_order(self, req: CancelRequest):
        """"""
        data = {
            "security": Security.SIGNED
        }

        params = {
            "symbol": req.symbol,
            "origClientOrderId": req.orderid
        }

        self.add_request(
            method="DELETE",
            path="/api/v3/order",
            callback=self.on_cancel_order,
            params=params,
            data=data,
            extra=req
        )

    def cancel_order_margin(self, req: CancelRequest):
        """"""
        data = {
            "security": Security.SIGNED
        }

        params = {
            "symbol": req.symbol,
            "origClientOrderId": req.orderid
        }

        self.add_request(
            method="DELETE",
            path="/sapi/v1/margin/order",
            callback=self.on_cancel_order,
            params=params,
            data=data,
            extra=req
        )

    def borrow_money(self, asset, amount):
        """"""
        data = {
            "security": Security.SIGNED
        }

        params = {
            "asset": asset,
            "amount": amount
        }

        self.add_request(
            method="POST",
            path="/sapi/v1/margin/loan",
            callback=self.on_borrow_money,
            params=params,
            data=data
        )
        
    def repay_money(self, req):
        """"""
        data = {
            "security": Security.SIGNED
        }

        params = {
            "asset": req.asset,
            "amount": req.amount
        }

        self.add_request(
            method="POST",
            path="/sapi/v1/margin/repay",
            callback=self.on_repay_money,
            params=params,
            data=data
        )

    def start_user_stream(self):
        """"""
        data = {
            "security": Security.API_KEY
        }

        self.add_request(
            method="POST",
            path="/api/v1/userDataStream",
            callback=self.on_start_user_stream,
            data=data
        )

    def keep_user_stream(self):
        """"""
        self.keep_alive_count += 1
        if self.keep_alive_count < 1800:
            return

        data = {
            "security": Security.API_KEY
        }

        params = {
            "listenKey": self.user_stream_key
        }

        self.add_request(
            method="PUT",
            path="/sapi/v1/userDataStream",
            callback=self.on_keep_user_stream,
            params=params,
            data=data
        )

    def start_user_stream_margin(self):
        """"""
        data = {
            "security": Security.API_KEY
        }

        self.add_request(
            method="POST",
            path="/sapi/v1/userDataStream",
            callback=self.on_start_user_stream_margin,
            data=data
        )

    def keep_user_stream_margin(self):
        """"""
        self.keep_alive_count_margin += 1
        if self.keep_alive_count_margin < 600:
            return
        else:
            self.keep_alive_count_margin = 0

        data = {
            "security": Security.API_KEY
        }

        params = {
            "listenKey": self.user_stream_key_margin
        }

        self.add_request(
            method="PUT",
            path="/sapi/v1/userDataStream",
            callback=self.on_keep_user_stream_margin,
            params=params,
            data=data
        )

    def on_query_time(self, data, request):
        """"""
        local_time = int(time.time() * 1000)
        server_time = int(data["serverTime"])
        self.time_offset = local_time - server_time

    def on_query_latest_price(self, data, request):
        """"""
        for d in data:
            self.latest_price[d['symbol']] = float(d['price'])

    def on_query_account(self, data, request):
        """"""
        for account_data in data["balances"]:
            account = AccountData(
                accountid=account_data["asset"],
                balance=float(account_data["free"]) + float(account_data["locked"]),
                frozen=float(account_data["locked"]),
                gateway_name=self.gateway_name
            )

            if account.balance:
                self.gateway.on_account(account)

        self.gateway.write_log("<现货>账户资金查询成功")

    def on_query_account_margin(self, data, request):
        """"""
        max_borrow_btc = max(float(data['totalNetAssetOfBtc'])*2 - float(data['totalLiabilityOfBtc']), 0)
        account_net_based_USDT = 0
        for account_data in data["userAssets"]:
            if account_data["asset"] == "USDT":
                price_based_BTC = self.latest_price.get("BTC" + account_data["asset"], 1)
                max_borrow = max_borrow_btc * price_based_BTC
                price_based_USDT = 1
            else:
                price_based_BTC = self.latest_price.get(account_data["asset"]+"BTC", 1)
                max_borrow = max_borrow_btc/price_based_BTC
                price_based_USDT = self.latest_price.get(account_data["asset"]+"USDT", 0)
            
            account = MarginAccountData(
                accountid=account_data["asset"],
                exchange=Exchange.BINANCE,
                borrowed=float(account_data["borrowed"]),
                interest=float(account_data["interest"]),
                free=float(account_data["free"]),
                locked=float(account_data["locked"]),
                netAsset=float(account_data["netAsset"]),
                max_borrow=max_borrow,
                gateway_name=self.gateway_name
            )

            # if account.netAsset or account.borrowed:
            # print(f'{account_data["asset"]} based on BTC price: {price_based_BTC}, max_borrow:{account.max_borrow}')
            self.gateway.on_account_margin(account)
            
            account_net_based_USDT += account.netAsset * price_based_USDT
        # self.gateway.write_log(f"<杠杆>账户资金查询成功,based USDT: {account_net_based_USDT}")

    def on_query_order(self, data, request):
        """"""
        for d in data:
            dt = datetime.fromtimestamp(d["time"] / 1000)
            time = dt.strftime("%Y-%m-%d %H:%M:%S")

            order = OrderData(
                orderid=d["clientOrderId"],
                symbol=d["symbol"],
                exchange=Exchange.BINANCE,
                price=float(d["price"]),
                volume=float(d["origQty"]),
                type=ORDERTYPE_BINANCE2VT[d["type"]],
                direction=DIRECTION_BINANCE2VT[d["side"]],
                traded=float(d["executedQty"]),
                status=STATUS_BINANCE2VT.get(d["status"], None),
                time=time,
                gateway_name=self.gateway_name,
            )
            self.gateway.on_order(order)

        self.gateway.write_log("委托信息查询成功")

    def on_query_contract(self, data, request):
        """"""
        for d in data["symbols"]:
            base_currency = d["baseAsset"]
            quote_currency = d["quoteAsset"]
            name = f"{base_currency.upper()}/{quote_currency.upper()}"

            pricetick = 1
            min_volume = 1

            for f in d["filters"]:
                if f["filterType"] == "PRICE_FILTER":
                    pricetick = float(f["tickSize"])
                elif f["filterType"] == "LOT_SIZE":
                    min_volume = float(f["stepSize"])

            contract = ContractData(
                symbol=d["symbol"],
                exchange=Exchange.BINANCE,
                name=name,
                pricetick=pricetick,
                size=1,
                min_volume=min_volume,
                product=Product.SPOT,
                history_data=True,
                net_position=True,
                gateway_name=self.gateway_name,
            )
            self.gateway.on_contract(contract)

            symbol_name_map[contract.symbol] = contract.name
        self.gateway.write_log("合约信息查询成功")

    def on_send_order(self, data, request):
        """"""
        # try:
        #     print(f'rest api callback on_send_order:{data}, datetime: {datetime.now()}')
        # except:
        #     print('rest api on_send_order failed')
        # if 'marginBuyBorrowAsset' in data:
        #     # print(">>>>>>>there is a borrowmoney callback")
        #     # print(data)
        #     dt1 = datetime.fromtimestamp(data['transactTime'] / 1000)
        #     borrow_amount = float(data['marginBuyBorrowAmount'])
        #     borrow_asset = data['marginBuyBorrowAsset']
        #     borrow_exchange = Exchange.BINANCE
        #     borrow_dict = {}
        #     borrow_dict['borrow_asset'] = borrow_asset
        #     borrow_dict['borrow_amount'] = borrow_amount
        #     borrow_dict['datetime'] = dt1
        #     borrow_dict['borrow_exchange'] = borrow_exchange

        #     self.gateway.on_borrow_money(borrow_dict)
        pass

    def on_send_order_failed(self, status_code: str, request: Request):
        """
        Callback when sending order failed on server.
        """
        order = request.extra
        order.status = Status.REJECTED
        self.gateway.on_order(order)

        msg = f"委托失败，状态码：{status_code}，信息：{request.response.text}"
        self.gateway.write_log(msg, level=CRITICAL)

    def on_send_order_error(
        self, exception_type: type, exception_value: Exception, tb, request: Request
    ):
        """
        Callback when sending order caused exception.
        """
        order = request.extra
        order.status = Status.REJECTED
        self.gateway.on_order(order)

        # Record exception if not ConnectionError
        if not issubclass(exception_type, ConnectionError):
            self.on_error(exception_type, exception_value, tb, request)

    def on_cancel_order(self, data, request):
        """"""
        pass

    def on_start_user_stream(self, data, request):
        """"""
        self.user_stream_key = data["listenKey"]
        self.keep_alive_count = 0
        url = WEBSOCKET_TRADE_HOST + self.user_stream_key

        self.trade_ws_api.connect(url, self.proxy_host, self.proxy_port)

    def on_keep_user_stream(self, data, request):
        """"""
        pass

    def on_start_user_stream_margin(self, data, request):
        """"""
        self.user_stream_key_margin = data["listenKey"]
        self.keep_alive_count_margin = 0
        url = WEBSOCKET_TRADE_HOST + self.user_stream_key_margin

        self.trade_ws_api.connect(url, self.proxy_host, self.proxy_port)

    def on_keep_user_stream_margin(self, data, request):
        """"""
        pass

    def query_history(self, req: HistoryRequest):
        """"""
        history = []
        limit = 1000
        start_time = int(datetime.timestamp(req.start))

        while True:
            # Create query params
            params = {
                "symbol": req.symbol,
                "interval": INTERVAL_VT2BINANCE[req.interval],
                "limit": limit,
                "startTime": start_time * 1000,         # convert to millisecond
            }

            # Add end time if specified
            if req.end:
                end_time = int(datetime.timestamp(req.end))
                params["endTime"] = end_time * 1000     # convert to millisecond

            # Get response from server
            resp = self.request(
                "GET",
                "/api/v3/klines",
                data={"security": Security.NONE},
                params=params
            )

            # Break if request failed with other status code
            if resp.status_code // 100 != 2:
                msg = f"获取历史数据失败，状态码：{resp.status_code}，信息：{resp.text}"
                self.gateway.write_log(msg)
                break
            else:
                data = resp.json()
                if not data:
                    msg = f"获取历史数据为空，开始时间：{start_time}"
                    self.gateway.write_log(msg)
                    break

                buf = []

                for l in data:
                    dt = datetime.fromtimestamp(l[0] / 1000)    # convert to second

                    bar = BarData(
                        symbol=req.symbol,
                        exchange=req.exchange,
                        datetime=dt,
                        interval=req.interval,
                        volume=float(l[5]),
                        open_price=float(l[1]),
                        high_price=float(l[2]),
                        low_price=float(l[3]),
                        close_price=float(l[4]),
                        gateway_name=self.gateway_name
                    )
                    buf.append(bar)

                history.extend(buf)

                begin = buf[0].datetime
                end = buf[-1].datetime
                msg = f"获取历史数据成功，{req.symbol} - {req.interval.value}，{begin} - {end}"
                self.gateway.write_log(msg)

                # Break if total data count less than limit (latest date collected)
                if len(data) < limit:
                    break

                # Update start time
                start_dt = bar.datetime + TIMEDELTA_MAP[req.interval]
                start_time = int(datetime.timestamp(start_dt))

        return history

    def on_borrow_money(self, data, request):
        d = dict()
        if 'tranId' in data:
            d['tranId'] = data['tranId']
            d['status'] = 'succeed'
        else:
            d['status'] = 'failed'
        self.gateway.on_borrow_money(d)
    def on_repay_money(self, data, request):
        d = dict()
        if 'tranId' in data:
            d['tranId'] = data['tranId']
            d['status'] = 'succeed'
        else:
            d['status'] = 'failed'
        self.gateway.on_repay_money(d)


class BinanceTradeWebsocketApi(WebsocketClient):
    """"""

    def __init__(self, gateway):
        """"""
        super().__init__()

        self.gateway = gateway
        self.gateway_name = gateway.gateway_name

    def connect(self, url, proxy_host, proxy_port):
        """"""
        self.init(url, proxy_host, proxy_port)
        self.start()

    def on_connected(self):
        """"""
        self.gateway.write_log("交易Websocket API连接成功")

    def on_packet(self, packet: dict):  # type: (dict)->None
        """"""
        if packet["e"] == "outboundAccountInfo":
            self.on_account(packet)
        elif packet["e"] == "executionReport":
            self.on_order(packet)

    def on_account(self, packet):
        """"""
        # print('margin trader websocket on_account*'*10)
        # print(packet)
        for d in packet["B"]:
            account = AccountData(
                accountid=d["a"],
                balance=float(d["f"]) + float(d["l"]),
                frozen=float(d["l"]),
                gateway_name=self.gateway_name
            )

            if account.balance:
                self.gateway.on_account(account)

    def on_order(self, packet: dict):
        """"""
        dt = datetime.fromtimestamp(packet["O"] / 1000)
        time = dt.strftime("%Y-%m-%d %H:%M:%S")
        # print('*'*50)
        # print(packet)
        # print('^'*50)
        if packet["C"] == "null" or packet["C"] == "":
            orderid = packet["c"]
        else:
            orderid = packet["C"]

        order = OrderData(
            symbol=packet["s"],
            exchange=Exchange.BINANCE,
            orderid=orderid,
            type=ORDERTYPE_BINANCE2VT[packet["o"]],
            direction=DIRECTION_BINANCE2VT[packet["S"]],
            price=float(packet["p"]),
            volume=float(packet["q"]),
            traded=float(packet["z"]),
            status=STATUS_BINANCE2VT[packet["X"]],
            time=time,
            gateway_name=self.gateway_name
        )

        self.gateway.on_order(order)
        msg = f"Websocket get order response: {order.vt_orderid}, status: {order.status}, packet status: {packet['X']}"
        self.gateway.write_log(msg, level=DEBUG)
        # Push trade event
        trade_volume = float(packet["l"])
        if not trade_volume:
            return

        trade_dt = datetime.fromtimestamp(packet["T"] / 1000)
        trade_time = trade_dt.strftime("%Y-%m-%d %H:%M:%S")

        trade = TradeData(
            symbol=order.symbol,
            exchange=order.exchange,
            orderid=order.orderid,
            tradeid=packet["t"],
            direction=order.direction,
            price=float(packet["L"]),
            volume=trade_volume,
            time=trade_time,
            gateway_name=self.gateway_name,
        )
        self.gateway.on_trade(trade)


class BinanceDataWebsocketApi(WebsocketClient):
    """"""

    def __init__(self, gateway):
        """"""
        super().__init__()

        self.gateway = gateway
        self.gateway_name = gateway.gateway_name

        self.ticks = {}

    def connect(self, proxy_host: str, proxy_port: int):
        """"""
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port

    def on_connected(self):
        """"""
        self.gateway.write_log("行情Websocket API连接刷新")

    def subscribe(self, req: SubscribeRequest):
        """"""
        if req.symbol not in symbol_name_map:
            self.gateway.write_log(f"找不到该合约代码{req.symbol}")
            return
        # time.sleep(3)
        # Create tick buf data
        tick = DepthTickData(
            symbol=req.symbol,
            name=symbol_name_map.get(req.symbol, ""),
            exchange=Exchange.BINANCE,
            datetime=datetime.now(),
            gateway_name=self.gateway_name,
        )
        self.ticks[req.symbol.lower()] = tick

        # Close previous connection
        if self._active:
            self.stop()
            self.join()

        # Create new connection
        channels = []
        for ws_symbol in self.ticks.keys():
            # channels.append(ws_symbol + "@ticker")
            channels.append(ws_symbol + "@depth20@100ms")
            # channels.append(ws_symbol + "@bookTicker")

        url = WEBSOCKET_DATA_HOST + "/".join(channels)
        self.init(url, self.proxy_host, self.proxy_port)
        self.start()

    def on_packet(self, packet):
        """"""
        stream = packet["stream"]
        data = packet["data"]

        symbol, channel = stream.split("@", 1)
        tick = self.ticks[symbol]

        if channel == "depth20@100ms":
            tick.bids = np.array(data['bids']).astype(float)
            tick.asks = np.array(data['asks']).astype(float)

        elif channel == "ticker":
            tick.volume = float(data['v'])
            tick.open_price = float(data['o'])
            tick.high_price = float(data['h'])
            tick.low_price = float(data['l'])
            tick.last_price = float(data['c'])
            tick.datetime = datetime.fromtimestamp(float(data['E']) / 1000)
        elif channel == "bookTicker":
            tick.bid_price_1 = float(data['b'])
            tick.ask_price_1 = float(data['a'])
            tick.bid_volume_1 = float(data['B'])
            tick.ask_volume_1 = float(data['A'])
            tick.datetime = datetime.now()

        if tick.bids[0,1]:
            self.gateway.on_tick(copy(tick))
            # print(f'binance gateway tick.datetime: {tick.datetime}')
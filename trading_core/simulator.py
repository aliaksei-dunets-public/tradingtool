import pandas as pd

import constants as CONST
from model import Asset
from strategy import Strategy_CCI100_AgainstTrend
from utils import Symbol


def __determineSymbolsWithSignalByInterval(symbols, interval, strategies):
    if not symbols:
        symbolHandler = Symbol()
        symbols = symbolHandler.get_all_open_symbols()

    response = []

    for symbolDetails in symbols:
        try:
            simulationResult = Simulator(
                symbolDetails['symbol']).detectSignals(interval, strategies)

            for result in simulationResult:
                signal_df = result["signal"]
                for index, signal_row in signal_df.iterrows():
                    signal_value = signal_row[CONST.SIGNAL]
                    if signal_value:
                        response.append({"name": result["name"],
                                         "date": index,
                                         "value": signal_row["CCI"],
                                         "signal": signal_value})

        except Exception as error:
            print(f"{symbolDetails['symbol']} - {error}")
            continue

    return response


def determineSymbolsWithSignalByInterval(interval, strategies):
    return __determineSymbolsWithSignalByInterval([], interval, strategies)


def determineSymbolsWithSignal(strategies):
    response = []

    intervals = [CONST.TA_INTERVAL_4H, CONST.TA_INTERVAL_1D, CONST.TA_INTERVAL_1WK]

    for interval in intervals:
        if response:
            response.extend(__determineSymbolsWithSignalByInterval([], interval, strategies))
        else: 
            response = __determineSymbolsWithSignalByInterval([], interval, strategies)

    return response


def determineSignalsBySymbol(symbol, strategies):
    response = []

    intervals = [CONST.TA_INTERVAL_4H,
                 CONST.TA_INTERVAL_1D, CONST.TA_INTERVAL_1WK]

    for interval in intervals:
        if response:
            response.extend(__determineSymbolsWithSignalByInterval([{"symbol": symbol}], interval, strategies))
        else:
            response = __determineSymbolsWithSignalByInterval([{"symbol": symbol}], interval, strategies)

    return response


def analyzeSymbols():
    pass


class Simulator:
    def __init__(self, symbol):
        self.__asset = Asset(symbol)

    def detectSignals(self, interval, strategies):

        result = []

        for strategy in strategies:
            nameStrategy = f"{self.__asset.getSymbol()}_{interval}_{strategy.getName()}"

            signal_df = strategy.getSignalByAsset(
                self.__asset, interval).tail(1)

            result.append({"name": nameStrategy,
                           "signal": signal_df})

        return result

    def simulate(self, interval, limit=1000, balance=100, stopLossRate=2, takeProfitRate=6, feeRate=0.1):
        result = []

        history_df = self.__asset.getHistoryDataFrame(interval, limit)

        strategies = [Strategy_CCI100_AgainstTrend(
            14), Strategy_CCI100_AgainstTrend(20)]

        for strategy in strategies:

            simulation = self._simulate(
                history_df, strategy, balance, stopLossRate, takeProfitRate, feeRate)

            nameSimulation = f"{self.__asset.getSymbol()}_{interval}_{limit}_{strategy.getName()}"

            simulation['name'] = nameSimulation

            result.append(simulation)

        return result

    def analyze(self, limit=1000, balance=100):

        simulations = []

        strategies = [Strategy_CCI100_AgainstTrend(
            14), Strategy_CCI100_AgainstTrend(20)]
        options = [
            {'stopLossRate': 0, 'takeProfitRate': 0, 'feeRate': 0.1},
            {'stopLossRate': 0.2, 'takeProfitRate': 0.6, 'feeRate': 0.1},
            {'stopLossRate': 0.5, 'takeProfitRate': 1.5, 'feeRate': 0.1},
            {'stopLossRate': 1, 'takeProfitRate': 3, 'feeRate': 0.1},
            {'stopLossRate': 2, 'takeProfitRate': 6, 'feeRate': 0.1},
            {'stopLossRate': 5, 'takeProfitRate': 15, 'feeRate': 0.1},
            {'stopLossRate': 10, 'takeProfitRate': 30, 'feeRate': 0.1},
            {'stopLossRate': 20, 'takeProfitRate': 60, 'feeRate': 0.1}]

        for strategy in strategies:
            for interval in CONST.TA_INTERVALS:
                history_df = self.__asset.getHistoryDataFrame(interval, limit)

                for option in options:
                    simulation = self._simulate(
                        history_df, strategy, balance, option['stopLossRate'], option['takeProfitRate'], option['feeRate'])

                    nameSimulation = f"{self.__asset.getSymbol()}_{interval}_{strategy.getName()}_{option['stopLossRate']}_{option['takeProfitRate']}"

                    simulation['name'] = nameSimulation

                    simulations.append(simulation)

        return sorted(simulations, key=lambda i: i['balance'], reverse=True)

    def _simulate(self, historyDataframe, strategy, balance, stopLossRate, takeProfitRate, feeRate):

        orderHandler = OrderHandler(
            balance, stopLossRate, takeProfitRate, feeRate)

        for interval in strategy.getSignalByDataFrame(historyDataframe).itertuples():
            orderHandler.processInterval(interval)

        return {"balance": orderHandler.getBalance(),
                "orders": orderHandler.getOrdersDataFrame()}


class OrderHandler:
    def __init__(self, balance, stopLossRate, takeProfitRate, feeRate):
        self.__balance = balance
        self.__stopLossRate = stopLossRate
        self.__takeProfitRate = takeProfitRate
        self.__feeRate = feeRate
        self.__index = None
        self.__orders = []

    def processInterval(self, interval):

        if self.__hasOpenOrder() == True:
            self.__closeOrder(interval)

        if self.__hasOpenOrder() == False:
            self.__createOrder(interval)

    def getBalance(self):
        return self.__balance

    def getRates(self):
        return {"stopLoss": self.__stopLossRate, "takeProfit": self.__takeProfitRate, "fee": self.__feeRate}

    def getOrdersDataFrame(self):
        orders = []

        for order in self.__orders:
            orders.append(order.__dict__)

        return pd.DataFrame(orders)

    def __hasOpenOrder(self):
        if len(self.__orders) == 0:
            return False
        elif self.__orders[self.__index].status == CONST.ORDER_STATUS_OPEN:
            return True
        else:
            return False

    def __createOrder(self, interval):
        direction = ''

        if interval.Signal == CONST.STRONG_BUY:
            direction = CONST.LONG
        elif interval.Signal == CONST.STRONG_SELL:
            direction = CONST.SHORT
        else:
            return

        self.__index = 0 if self.__index == None else (self.__index + 1)

        self.__orders.append(Order(direction=direction, openDateTime=interval.Index,
                                   openPrice=interval.Close, balance=self.__balance, stopLossRate=self.__stopLossRate,
                                   takeProfitRate=self.__takeProfitRate, feeRate=self.__feeRate))

        self.__recalculateOrder(interval)

    def __closeOrder(self, interval):

        order = self.__orders[self.__index]
        closeDateTime = interval.Index
        closePrice = 0
        closeReason = None

        if order.direction == CONST.LONG:
            if order.stopLossPrice != 0 and interval.Low <= order.stopLossPrice:
                closePrice = order.stopLossPrice
                closeReason = CONST.ORDER_CLOSE_REASON_STOP_LOSS
            elif interval.Signal == CONST.STRONG_SELL or interval.Signal == CONST.SELL:
                closePrice = interval.Close
                closeReason = CONST.ORDER_CLOSE_REASON_SIGNAL
            elif order.takeProfitPrice != 0 and interval.High >= order.takeProfitPrice:
                closePrice = order.takeProfitPrice
                closeReason = CONST.ORDER_CLOSE_REASON_TAKE_PROFIT
        elif order.direction == CONST.SHORT:
            if order.takeProfitPrice != 0 and interval.Low <= order.takeProfitPrice:
                closePrice = order.takeProfitPrice
                closeReason = CONST.ORDER_CLOSE_REASON_TAKE_PROFIT
            elif interval.Signal == CONST.STRONG_BUY or interval.Signal == CONST.BUY:
                closePrice = interval.Close
                closeReason = CONST.ORDER_CLOSE_REASON_SIGNAL
            elif order.stopLossPrice != 0 and interval.High >= order.stopLossPrice:
                closePrice = order.stopLossPrice
                closeReason = CONST.ORDER_CLOSE_REASON_STOP_LOSS

        if closeReason:
            self.__orders[self.__index].closeOrder(
                closeDateTime, closePrice, closeReason)

        self.__recalculateOrder(interval)

    def __recalculateOrder(self, interval):
        self.__orders[self.__index].setExtremum(interval.Low, interval.High)
        self.__balance += self.__orders[self.__index].profit


class Order:
    def __init__(self, direction, openDateTime, openPrice, balance, stopLossRate, takeProfitRate, feeRate):
        self.direction = direction
        self.status = CONST.ORDER_STATUS_OPEN
        self.profit = 0
        self.percent = 0
        self.openDateTime = openDateTime  # .to_pydatetime()
        self.openPrice = openPrice
        self.closeDateTime = ''
        self.closePrice = 0
        self.closeReason = ''

        self.fee = (balance * feeRate) / 100
        self.amount = balance / self.openPrice

        self.maxCanLoss = 0
        self.maxCanProfit = 0

        self.maxPrice = self.openPrice
        self.minPrice = self.openPrice
        self.maxPercent = 0
        self.minPercent = 0

        if self.direction == CONST.LONG:
            stopLossValue = -self.openPrice * stopLossRate / 100
            takeProfitValue = self.openPrice * takeProfitRate / 100
        elif self.direction == CONST.SHORT:
            stopLossValue = self.openPrice * stopLossRate / 100
            takeProfitValue = -self.openPrice * takeProfitRate / 100
        else:
            raise Exception('Direction of an order is incorrect or missed')

        self.stopLossPrice = self.openPrice + stopLossValue if stopLossRate > 0 else 0
        self.takeProfitPrice = self.openPrice + \
            takeProfitValue if takeProfitRate > 0 else 0

    def closeOrder(self, closeDateTime, closePrice, closeReason):
        self.status = CONST.ORDER_STATUS_CLOSE
        self.closeDateTime = closeDateTime  # .to_datetime()
        self.closePrice = closePrice
        self.closeReason = closeReason
        self.percent = self.__getPercent(self.openPrice, self.closePrice)
        self.maxPercent = self.__getPercent(self.openPrice, self.maxPrice)
        self.minPercent = self.__getPercent(self.openPrice, self.minPrice)

        if self.direction == CONST.LONG:

            self.profit = self.__getCloseValue() - (self.__getOpenValue() + self.fee)
            self.maxCanLoss = self.__getMinValue() - (self.__getOpenValue() + self.fee)
            self.maxCanProfit = self.__getMaxValue() - (self.__getOpenValue() + self.fee)

        elif self.direction == CONST.SHORT:

            self.profit = self.__getOpenValue() - (self.__getCloseValue() + self.fee)
            self.maxCanLoss = self.__getOpenValue() - (self.__getMaxValue() + self.fee)
            self.maxCanProfit = self.__getOpenValue() - (self.__getMinValue() + self.fee)

    def setExtremum(self, Low, High):
        self.minPrice = self.minPrice if self.minPrice <= Low else Low
        self.maxPrice = self.maxPrice if self.maxPrice >= High else High

    def __getOpenValue(self):
        return self.amount * self.openPrice

    def __getCloseValue(self):
        return self.amount * self.closePrice

    def __getMinValue(self):
        return self.amount * self.minPrice

    def __getMaxValue(self):
        return self.amount * self.maxPrice

    def __getPercent(self, initial, target):
        return (target-initial) / initial * 100


if __name__ == '__main__':
    pass

import logging
from constants import TA_INTERVAL_1D
from handler import HandlerBase, HandlerCurrencyCom


class Asset:
    def __init__(self, symbol, handler: HandlerBase = HandlerCurrencyCom()):
        self.__symbol = symbol
        self.__handler = handler
        self.__name = symbol

    def getSymbol(self):
        return self.__symbol

    def getName(self):
        return self.__name

    def getHandler(self):
        return self.__handler

    def getHistoryDataFrame(self, interval=TA_INTERVAL_1D, limit=30):
        return self.__handler.getHistoryDataFrame(self.__symbol, interval, limit)


# class Signal:
#     def __init__(self, asset, interval, limit):
#         self._asset = asset
#         self._interval = interval
#         self._limit = limit

#     def getSignalsDataFrame(self):
#         pass

#     def getAsset(self):
#         return self._asset

#     def getInterval(self):
#         return self._interval

#     def getLimit(self):
#         return self._limit

# class Mediator:
#     def __init__(self, symbol: str, oHandler: HandlerBase = HandlerCurrencyCom()):
#         self.__asset = Asset(symbol, oHandler)
#         self.__handler = oHandler

#     def __repr__(self):
#         return f'{self.__asset.getSymbol()}'

#     def getAsset(self):
#         return self.__asset

#     def getHandler(self):
#         return self.__handler


if __name__ == '__main__':
    pass

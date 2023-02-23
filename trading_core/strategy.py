import constants as CONST
from indicator import IndicatorCCI


class StrategyBase():
    def __init__(self):
        self._name = ''
        self._description = ''

    def getName(self):
        return self._name

    def getDescription(self):
        return self._description

    def getStrategyByAsset(self, asset, interval, limit):
        pass

    def getSignalByAsset(self, asset, interval, limit):
        pass

    def getStrategyByDataFrame(self, historyDataFrame):
        pass

    def getSignalByDataFrame(self, historyDataFrame):
        pass


class Strategy_CCI100_AgainstTrend(StrategyBase):
    def __init__(self, length):
        StrategyBase.__init__(self)
        self._name = f'CCI({length})_100'
        self._description = f'CCI {length} +/- 100 against the trend'
        self.__cci = IndicatorCCI(length)

    def getStrategyByAsset(self, asset, interval, limit=0):
        pass

    def getSignalByAsset(self, asset, interval, limit=0):
        default_limit = self.__cci.getLength() + 1
        limit = limit if limit > default_limit else default_limit
        cci_df = self.__cci.getIndicatorByAsset(asset, interval, limit)
        cci_df.insert(cci_df.shape[1], CONST.SIGNAL,
                      self.__determineSignal(cci_df))

        return cci_df

    def getStrategyByDataFrame(self, historyDataFrame):
        pass

    def getSignalByDataFrame(self, historyDataFrame):
        if historyDataFrame.shape[0] < self.__cci.getLength() + 1:
            raise Exception(
                'Count of history data less then strategy interval')

        cci_df = self.__cci.getIndicatorByDataFrame(historyDataFrame)
        cci_df.insert(cci_df.shape[1], CONST.SIGNAL,
                      self.__determineSignal(cci_df))

        return cci_df

    def __determineSignal(self, cci_df):

        signals = []

        for i in range(len(cci_df)):

            decision = ''

            if i == 0:
                signals.append(decision)
                continue

            current_value = cci_df.iloc[i, 5]
            previous_value = cci_df.iloc[i-1, 5]

            if current_value > 100:
                if previous_value < 100:
                    decision = CONST.BUY
            elif current_value < -100:
                if previous_value > -100:
                    decision = CONST.SELL
            else:
                if previous_value > 100:
                    decision = CONST.STRONG_SELL
                elif previous_value < -100:
                    decision = CONST.STRONG_BUY

            signals.append(decision)

        return signals


if __name__ == '__main__':
    pass

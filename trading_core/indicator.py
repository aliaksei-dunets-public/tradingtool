import pandas_ta as ta


class IndicatorBase():
    def __init__(self):
        self._shortName = ''
        self._longName = ''

    def getShortName(self):
        return self._shortName

    def getLongName(self):
        return self._longName

    def getIndicatorByAsset(self, asset, interval, limit=0):
        pass

    def getIndicatorByDataFrame(self, historyDataFrame):
        pass


class IndicatorCCI(IndicatorBase):
    def __init__(self, length):
        IndicatorBase.__init__(self)
        self._shortName = 'CCI'
        self._longName = 'Commodity Channel Index'

        self.__length = length

    def getLength(self):
        return self.__length

    def getIndicatorByAsset(self, asset, interval, limit=0):
        limit = limit if limit > self.__length else self.__length
        history_df = asset.getHistoryDataFrame(interval, limit)

        return self.getIndicatorByDataFrame(history_df)

    def getIndicatorByDataFrame(self, historyDataFrame):

        if historyDataFrame.shape[0] < self.__length:
            raise Exception(
                'Count of history data less then indicator interval')

        cci_series = historyDataFrame.ta.cci(length=self.__length)

        cci_df = cci_series.to_frame(name=self._shortName)

        indicator_df = historyDataFrame.join(cci_df)
        indicator_df = indicator_df[indicator_df[self._shortName].notna()]

        return indicator_df


if __name__ == '__main__':
    pass

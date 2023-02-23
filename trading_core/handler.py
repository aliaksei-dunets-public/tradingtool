from datetime import datetime
import requests
import json
import pandas as pd
# import yfinance as yf
import os

class HandlerBase:
    def getHistoryDataFrame(self, symbol, interval, limit):
        pass

    def getExchangeInfo(self):
        pass

# class HandlerYFinance(HandlerBase):
#     def getHistoryDataFrame(self, symbol, interval, limit):
#         ticker = yf.Ticker(symbol)

#         df = pd.DataFrame(ticker.history(period='6mo', interval=interval, actions=False))
#         df_utc = df.tz_convert('UTC')

#         return df_utc

class HandlerCurrencyCom(HandlerBase):
    # TIMEFRAMES = {
    #     "M1": "1m",
    #     "M5": "5m",
    #     "M15": "15m",
    #     "M30": "30m",
    #     "H1": "1h",
    #     "H4": "4h",
    #     "D1": "1d",
    #     "W1": "1w'",
    # }


    # def _generateBars(self, tfId, limit):
    #     candleBars = []
    #     response = self.getKlines(tfId, limit)
    #     for bar in response:
    #         candleBars.append(self._createBar(
    #             openDateTime=bar[0], open=bar[1], high=bar[2], low=bar[3], close=bar[4], volume=bar[5]))

    #     return candleBars

    def getHistoryDataFrame(self, symbol, interval, limit):
        response = self.getKlines(symbol, interval, limit)

        df = pd.DataFrame(response, columns=['DatetimeFloat', 'Open', 'High', 'Low', 'Close', 'Volume'])
        df['Datetime'] = df.apply(lambda x: pd.to_datetime(datetime.fromtimestamp(x['DatetimeFloat'] / 1000.0), unit='ns'), axis=1)
        df.set_index('Datetime', inplace = True)
        df.drop(["DatetimeFloat"], axis=1, inplace = True)
        df = df.astype(float)

        return df

    def getKlines(self, symbol, interval, limit):
        params = {"symbol": symbol,
                  "interval": interval,
                  "limit": limit}
        response = requests.get(
            "https://api-adapter.backend.currency.com/api/v2/klines", params=params)

        if response.status_code == 200:
            # if constant.WRITE_REQUEST_TO_FILE == True:
            #     with open(getFileName(self._symbol, tfId), 'w') as writer:
            #         writer.write(response.text)

            return json.loads(response.text)
        else:
            raise Exception(response.text)

    def getExchangeInfo(self):
        # https://api-adapter.backend.currency.com/api/v2/exchangeInfo
        
        response = requests.get("https://api-adapter.backend.currency.com/api/v2/exchangeInfo")

        if response.status_code == 200:
            jsonResponse = json.loads(response.text)

            file_path = f'{os.getcwd()}\static\symbols_df.json'

            with open(file_path, 'w') as writer:
                writer.write(json.dumps(jsonResponse['symbols']))

            return jsonResponse['symbols']
        else:
            raise Exception(response.text)


if __name__ == '__main__':
    handler = HandlerCurrencyCom()
    handler.getExchangeInfo()
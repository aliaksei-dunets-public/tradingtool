import constants as CONST
import logging
from datetime import datetime, timezone
import pandas as pd
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from handler import HandlerCurrencyCom
import os


class Symbol:
    _instance = None

    def __new__(class_, *args, **kwargs):
        if not isinstance(class_._instance, class_):
            class_._instance = object.__new__(class_, *args, **kwargs)
            class_._instance.symbols_df = pd.DataFrame()
        return class_._instance

    def initSymbols(self):
        handler = HandlerCurrencyCom()
        df = pd.DataFrame(handler.getExchangeInfo())

        self.symbols_df = self.__prepareSymbolsDataFrame(df)

    def check_symbol(self, symbol):
        try:
            self.get_symbol_detail(symbol)
            return True
        except Exception:
            return False

    def get_symbol_detail(self, symbol):
        if self.symbols_df.empty:
            self.symbols_df = self.__getSymbolsDataFrame()

        try:
            series = self.symbols_df.loc[symbol]
            return {'symbol': series.name,
                    'name': series['name'],
                    'tradingHours': series['tradingHours'],
                    'assetType': series['assetType']}
        except KeyError:
            raise Exception(f'{symbol} not found in the list of symbols')

    def get_all_symbols(self):
        symbols = []

        for index, row in self.get_all_symbols_df().iterrows():
            symbols.append({'symbol': index,
                            'name': row['name'],
                            'assetType': row['assetType']})

        return symbols

    def get_all_symbols_df(self):
        if self.symbols_df.empty:
            self.symbols_df = self.__getSymbolsDataFrame()

        return self.symbols_df

    def get_all_open_symbols(self):
        symbols = []

        for index, row in self.get_all_open_symbols_df().iterrows():
            symbols.append({'symbol': index,
                            'name': row['name'],
                            'assetType': row['assetType']})

        return symbols

    def get_all_open_symbols_df(self):
        self.initSymbols()

        open_symbols_df = self.symbols_df.query("status == 'TRADING'")

        return open_symbols_df

    def search_symbols(self, text):
        symbols = []

        if self.symbols_df.empty:
            self.symbols_df = self.__getSymbolsDataFrame()

        found_df = self.symbols_df.loc[(
            self.symbols_df['name'].str.contains(text, case=False))]

        for index, row in found_df.iterrows():
            symbols.append({'symbol': index,
                            'name': row['name'],
                            'assetType': row['assetType']})

        return symbols

    def __getSymbolsDataFrame(self):
        file_path = f'{os.getcwd()}\static\symbols_df.json'
        df = pd.read_json(file_path)
        return self.__prepareSymbolsDataFrame(df)

    def __prepareSymbolsDataFrame(self, df):
        df_cleared = df.query(
            "quoteAssetId == 'USD' and assetType in ('CRYPTOCURRENCY','EQUITY','COMMODITY')")
        asset_df = df_cleared[['symbol', 'name',
                               'tradingHours', 'assetType', 'status']]
        asset_df.set_index('symbol', inplace=True)

        return asset_df


class SchedulerSignal:
    def __init__(self, bot) -> None:
        self.__scheduler = AsyncIOScheduler()
        self.__bot = bot
        self.__subscriptions = {}

    def addJob(self, chatId, symbol, interval, callback):

        jobId = self._generateJobId(chatId, symbol, interval)

        if chatId not in self.__subscriptions:
            self.__subscriptions[chatId] = [jobId]
        elif jobId not in self.__subscriptions[chatId]:
            self.__subscriptions[chatId].append(jobId)
        else:
            return self.__scheduler.get_job(jobId)

        job = self.__scheduler.add_job(callback, self.__generateCronTrigger(
            symbol, interval), id=jobId, args=(self.__bot, chatId, symbol, interval))

        return job

    def removeJob(self, chatId, symbol, interval):

        jobIds = []

        if chatId in self.__subscriptions:

            if interval:
                jobIds.append(self._generateJobId(chatId, symbol, interval))
            else:
                for jobId in self.__subscriptions[chatId]:
                    if jobId.startswith(f'{chatId}_{symbol}'):
                        jobIds.append(jobId)

            for jobId in jobIds:
                self.__scheduler.remove_job(jobId)
                self.__subscriptions[chatId].remove(jobId)

    def removeAllJob(self, chatId):
        if chatId in self.__subscriptions:
            for jobId in self.__subscriptions[chatId]:
                # Remove Job from Scheduler
                self.__scheduler.remove_job(jobId)

            # Remove Local JobIds
            del self.__subscriptions[chatId]

    def getJobs(self):
        jobs = []
        for chatId in self.__subscriptions:
            jobs.extend(self.__subscriptions[chatId])
        return jobs

    def getJob(self, chatId):
        return self.__subscriptions[chatId] if chatId in self.__subscriptions else []

    def getJobNextTimeRun(self, jobId):
        return self.__scheduler.get_job(jobId).next_run_time

    def getScheduler(self):
        return self.__scheduler

    def startScheduler(self):
        self.__scheduler.start()

    def __generateCronTrigger(self, symbol, interval) -> CronTrigger:

        symbol_details = Symbol().get_symbol_detail(symbol)
        trading_hours = symbol_details['tradingHours']

        cron_options = self.__getDefaultCronOptions(interval)

        if trading_hours in ['UTC; Mon - 22:00, 22:05 -; Tue - 22:00, 22:05 -; Wed - 22:00, 22:05 -; Thu - 22:00, 22:05 -; Fri - 22:00, 23:01 -; Sat - 06:00, 08:00 - 22:00, 22:05 -; Sun - 22:00, 22:05 -',
                             'UTC; Mon - 22:00, 22:15 -; Tue - 22:00, 22:15 -; Wed - 22:00, 22:15 -; Thu - 22:00, 22:15 -; Fri - 22:00, 22:15 -; Sat - 06:00, 08:00 - 22:00, 22:15 -; Sun - 22:00, 22:15 -',
                             'UTC; Mon - 22:00, 22:05 -; Tue - 22:00, 22:05 -; Wed - 22:00, 22:05 -; Thu - 22:00, 22:05 -; Fri - 22:00, 22:05 -; Sat - 06:00, 08:00 - 22:00, 22:05 -; Sun - 22:00, 22:05 -']:

            pass

        elif trading_hours in ['UTC; Mon 01:05 - 19:00; Tue 01:05 - 19:00; Wed 01:05 - 19:00; Thu 01:05 - 19:00; Fri 01:05 - 19:00',
                               'UTC; Mon 02:00 - 19:20; Tue 02:00 - 19:20; Wed 02:00 - 19:20; Thu 02:00 - 19:20; Fri 02:00 - 19:20',
                               'UTC; Mon 01:02 - 19:00; Tue 01:02 - 19:00; Wed 01:02 - 19:00; Thu 01:02 - 19:00; Fri 01:02 - 19:00',
                               'UTC; Mon 01:00 - 13:45, 14:30 - 19:20; Tue 01:00 - 13:45, 14:30 - 19:20; Wed 01:00 - 13:45, 14:30 - 19:20; Thu 01:00 - 13:45, 14:30 - 19:20; Fri 01:00 - 13:45, 14:30 - 19:20']:

            cron_options["day_of_week"] = 'mon-fri'

            if interval in [CONST.TA_INTERVAL_5M, CONST.TA_INTERVAL_15M, CONST.TA_INTERVAL_30M]:
                cron_options["hour"] = '1-19'
            elif interval == CONST.TA_INTERVAL_1H:
                cron_options["hour"] = '1-19'
            elif interval == CONST.TA_INTERVAL_4H:
                cron_options["hour"] = '0,4,8,12,16'
            elif interval == CONST.TA_INTERVAL_1D:
                pass
            elif interval == CONST.TA_INTERVAL_1WK:
                cron_options["day_of_week"] = 'mon'

        elif trading_hours in ['UTC; Mon - 22:00, 22:15 -; Tue - 22:00, 22:15 -; Wed - 22:00, 22:15 -; Thu - 22:00, 22:15 -; Fri - 22:00; Sun 22:05 -',
                               'UTC; Mon - 22:00, 23:00 -; Tue - 22:00, 23:00 -; Wed - 22:00, 23:00 -; Thu - 22:00, 23:00 -; Fri - 22:00; Sun 23:00 -',
                               'UTC; Mon - 21:59, 23:05 -; Tue - 21:59, 23:05 -; Wed - 21:59, 23:05 -; Thu - 21:59, 23:05 -; Fri - 21:59; Sun 23:05 -',
                               'UTC; Mon - 22:00, 23:05 -; Tue - 22:00, 23:05 -; Wed - 22:00, 23:05 -; Thu - 22:00, 23:05 -; Fri - 22:00; Sun 23:05 -']:

            if interval != CONST.TA_INTERVAL_1WK:
                cron_options["day_of_week"] = 'mon-fri'

        elif trading_hours == 'UTC; Mon 14:30 - 21:00; Tue 14:30 - 21:00; Wed 14:30 - 21:00; Thu 14:30 - 21:00; Fri 14:30 - 21:00':
            
            cron_options["day_of_week"] = 'mon-fri'

            if interval in [CONST.TA_INTERVAL_5M, CONST.TA_INTERVAL_15M, CONST.TA_INTERVAL_30M]:
                cron_options["hour"] = '14-21'
            elif interval == CONST.TA_INTERVAL_1H:
                cron_options["hour"] = '14-21'
            elif interval == CONST.TA_INTERVAL_4H:
                cron_options["hour"] = '16,20'
            elif interval == CONST.TA_INTERVAL_1D:
                cron_options["hour"] = '15'
            elif interval == CONST.TA_INTERVAL_1WK:
                cron_options["hour"] = '15'
                cron_options["day_of_week"] = 'mon'

        elif trading_hours == 'UTC; Mon 09:10 -; Tue - 01:00, 09:10 -; Wed - 01:00, 09:10 -; Thu - 01:00, 09:10 -; Fri - 01:00, 09:10 - 22:00':
            
            cron_options["day_of_week"] = 'mon-fri'

            if interval in [CONST.TA_INTERVAL_5M, CONST.TA_INTERVAL_15M, CONST.TA_INTERVAL_30M]:
                cron_options["hour"] = '0-1,9-23'
            elif interval == CONST.TA_INTERVAL_1H:
                cron_options["hour"] = '0-1,9-23'
            elif interval == CONST.TA_INTERVAL_4H:
                cron_options["hour"] = '0,12,16,20'
            elif interval == CONST.TA_INTERVAL_1D:
                pass
            elif interval == CONST.TA_INTERVAL_1WK:
                cron_options["day_of_week"] = 'mon'

        elif trading_hours == 'UTC; Mon 10:15 - 18:30; Tue 10:15 - 18:30; Wed 10:15 - 18:30; Thu 10:15 - 18:30; Fri 10:15 - 18:30':

            cron_options["day_of_week"] = 'mon-fri'

            if interval in [CONST.TA_INTERVAL_5M, CONST.TA_INTERVAL_15M, CONST.TA_INTERVAL_30M]:
                cron_options["hour"] = '10-19'
            elif interval == CONST.TA_INTERVAL_1H:
                cron_options["hour"] = '10-19'
            elif interval == CONST.TA_INTERVAL_4H:
                cron_options["hour"] = '12,16'
            elif interval == CONST.TA_INTERVAL_1D:
                cron_options["hour"] = '15'
            elif interval == CONST.TA_INTERVAL_1WK:
                cron_options["hour"] = '15'
                cron_options["day_of_week"] = 'mon'

        elif trading_hours == 'UTC; Mon 01:05 - 22:00; Tue 01:05 - 22:00; Wed 01:05 - 22:00; Thu 01:05 - 22:00; Fri 01:05 - 22:00':

            cron_options["day_of_week"] = 'mon-fri'

            if interval in [CONST.TA_INTERVAL_5M, CONST.TA_INTERVAL_15M, CONST.TA_INTERVAL_30M]:
                cron_options["hour"] = '1-22'
            elif interval == CONST.TA_INTERVAL_1H:
                cron_options["hour"] = '1-22'
            elif interval == CONST.TA_INTERVAL_4H:
                cron_options["hour"] = '4,8,12,16,20'
            elif interval == CONST.TA_INTERVAL_1D:
                pass
            elif interval == CONST.TA_INTERVAL_1WK:
                cron_options["day_of_week"] = 'mon'

        return CronTrigger(day_of_week=cron_options["day_of_week"], hour=cron_options["hour"], minute=cron_options["minute"], second=cron_options["second"], jitter=60, timezone='UTC')

    def __getDefaultCronOptions(self, interval):

        day_of_week = None
        hour = None
        minute = None
        second = None

        if interval == CONST.TA_INTERVAL_5M:
            minute = '*/5'
            second = '30'
        elif interval == CONST.TA_INTERVAL_15M:
            minute = '*/15'
            second = '30'
        elif interval == CONST.TA_INTERVAL_30M:
            minute = '*/30'
            second = '59'
        elif interval == CONST.TA_INTERVAL_1H:
            minute = '1'
        elif interval == CONST.TA_INTERVAL_4H:
            hour = '0,4,8,12,16,20'
            minute = '2'
        elif interval == CONST.TA_INTERVAL_1D:
            hour = '10,15'
        elif interval == CONST.TA_INTERVAL_1WK:
            day_of_week = 'mon'
            hour = '10,15'
        else:
            Exception('Incorrect interval for subscription')

        return {"day_of_week": day_of_week,
                "hour": hour,
                "minute": minute,
                "second": second}

    def _generateJobId(self, chatId, symbol, interval):
        return f'{chatId}_{symbol}_{interval}'

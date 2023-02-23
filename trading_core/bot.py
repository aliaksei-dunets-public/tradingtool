# pipenv run python botAiogram.py
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandObject
from aiogram.types import FSInputFile
import pandas as pd
from dotenv import dotenv_values

import constants as CONST
from strategy import Strategy_CCI100_AgainstTrend
from simulator import Simulator, determineSymbolsWithSignal, determineSignalsBySymbol, determineSymbolsWithSignalByInterval
from utils import SchedulerSignal, Symbol

config = dotenv_values(".env")

try:
    if not config['BOT_TOKEN']:
        raise Exception('Bot token is not maintained in the environment values')
except KeyError:
    raise Exception('Bot token is not maintained in the environment values')

# Объект бота
bot = Bot(token=config['BOT_TOKEN'])
# Диспетчер для бота
dp = Dispatcher()

scheduler = SchedulerSignal(bot)

# Включаем логирование, чтобы не пропустить важные сообщения
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Хэндлер на команду /start


@dp.message(Command(commands=["start"]))
async def cmd_start(message: types.Message):
    await message.answer('Hello')

# Хэндлер на команду /help


@dp.message(Command(commands=["help"]))
async def cmd_start(message: types.Message):
    await message.answer('''
/simulate <SYMBOL> <INTERVAL> <STOP_LOSS> <TAKE_PROFIT>
<SYMBOL>: EPAM, BABA and so on
<INTERVAL>: 5m, 15m, 30m, 1h, 4h, 1d, 1w
<STOP_LOSS>: OPTIONAL. 0% by default and stop loss isn't accepted during calculation
<TAKE_PROFIT>: OPTIONAL. 0% by default and take profit isn't accepted during calculation

/analize <SYMBOL> <LIMIT>
<SYMBOL>: EPAM, BABA and so on
<LIMIT>: OPTIONAL. How many timeframes analize

/signal <SYMBOL> <INTERVAL>
<SYMBOL>: EPAM, BABA and so on
<INTERVAL>: 5m, 15m, 30m, 1h, 4h, 1d, 1w

/search <SYMBOL_NAME>

/subscribe <SYMBOL> <INTERVAL>
<SYMBOL>: EPAM, BABA and so on
<INTERVAL>: 5m, 15m, 30m, 1h, 4h, 1d, 1w

/subscriptions

/unsubscribe <SYMBOL> <INTERVAL>
<SYMBOL>: EPAM, BABA and so on
<INTERVAL>: 5m, 15m, 30m, 1h, 4h, 1d, 1w - OPTIONAL. If value is empty the bot removes all subscription for this symbol

/unsubscribe_all
    ''')


@dp.message(Command(commands=["simulate"]))
async def cmd_simulate(message: types.Message, command: CommandObject):
    if command.args == '':
        await message.answer(f'Incorrect input attributes. Please check the command /help')
        return

    argList = command.args.split()
    symbol = symbol_in(argList[0])
    interval = argList[1]

    if len(argList) >= 3:
        stopLoss = float(argList[2])
    else:
        stopLoss = 0

    if len(argList) >= 4:
        takeProfit = float(argList[3])
    else:
        takeProfit = 0

    logging.info(
        f'/simulate {symbol} {interval} {stopLoss} {takeProfit}')

    if not Symbol().check_symbol(symbol):
        await message.answer(f'Symbol {symbol} is not valid. Try again')
        return

    if not interval in CONST.TA_INTERVALS:
        await message.answer(f'Interval {interval} is not valid. Try again')
        return

    simulator = Simulator(symbol)

    simulationResult = simulator.simulate(
        interval=interval, balance=100, stopLossRate=stopLoss, takeProfitRate=takeProfit, feeRate=0.1)

    response = 'Balances:\n'

    file_name = f'static/{message.from_user.full_name}_{message.chat.id}.xlsx'

    with pd.ExcelWriter(file_name) as writer:
        for result in simulationResult:
            response += f'<b>{result["name"]}</b> = {result["balance"]:.2f}\n'
            result["orders"].to_excel(writer, sheet_name=result["name"])

    await message.answer(response, parse_mode="HTML")
    await bot.send_document(message.chat.id, FSInputFile(file_name, filename=f"{symbol}_{interval}_{stopLoss}_{takeProfit}.xlsx"))


@dp.message(Command(commands=["analize"]))
async def cmd_analize(message: types.Message, command: CommandObject):
    if command.args == '':
        await message.answer(f'Incorrect input attributes. Please check the command /help')
        return

    argList = command.args.split()
    symbol = symbol_in(argList[0])

    if len(argList) >= 2:
        limit = int(argList[1])
    else:
        limit = 1000

    logging.info(f'/analize {symbol} ')

    if not Symbol().check_symbol(symbol):
        await message.answer(f'Symbol {symbol} is not valid. Try again')
        return

    simulator = Simulator(symbol)

    simulationResult = simulator.analyze(limit=limit)

    response = '5 Max balances:\n'

    for result in simulationResult[:5]:
        response += f'<b>{result["name"]}</b> = {result["balance"]:.2f}\n'

    await message.answer(response, parse_mode="HTML")


@dp.message(Command(commands=["signal"]))
async def cmd_signal(message: types.Message, command: CommandObject):

    response = ''

    if command.args == None:
        await message.answer(f'Incorrect input attributes. Please check the command /help')
        return

    argList = command.args.split()
    symbol = symbol_in(argList[0])
    interval = argList[1]

    if symbol != '*' and not Symbol().check_symbol(symbol):
        await message.answer(f'Symbol {symbol} is not valid. Try again')
        return

    if interval != '*' and not interval in CONST.TA_INTERVALS:
        await message.answer(f'Interval {interval} is not valid. Try again')
        return

    logging.info(f'/signal {symbol} {interval}')\

    signalList = []

    if symbol == '*':
        if interval == '*':
            signalList = determineSymbolsWithSignal(
                [Strategy_CCI100_AgainstTrend(20)])
        else:
            signalList = determineSymbolsWithSignalByInterval(
                interval, [Strategy_CCI100_AgainstTrend(20)])
    elif interval == '*':
        signalList = determineSignalsBySymbol(
            symbol, [Strategy_CCI100_AgainstTrend(20)])
    else:
        simulator = Simulator(symbol)
        simulationResult = simulator.detectSignals(
            interval, [Strategy_CCI100_AgainstTrend(20)])

        try:
            for result in simulationResult:
                signal_df = result["signal"]
                for index, signal_row in signal_df.iterrows():
                    signal_value = signal_row[CONST.SIGNAL]
                    if signal_value:
                        signalList.append({"name": result["name"],
                                           "date": index,
                                           "value": signal_row["CCI"],
                                           "signal": signal_value})

        except Exception as error:
            print(f"{symbol} - {error}")

    for result in signalList:
        response += f'{result["date"]}  -  <b>{result["name"]}</b>: ({result["value"]:.2f}) - <b>{result["signal"]}</b>\n'

    if response:
        response = f'Signals for {symbol} {interval}:\n' + response
    else:
        response = 'There is no signals'

    await message.answer(response, parse_mode="HTML")


@dp.message(Command(commands=["search"]))
async def cmd_search(message: types.Message, command: CommandObject):
    response = ''

    if command.args == None:
        await message.answer(f'Incorrect input attributes. Please check the command /help')
        return

    argList = command.args.split()
    text = argList[0]

    results = Symbol().search_symbols(text)

    for result in results:
        response += f'<b>{symbol_out(result["symbol"])}</b> - {result["name"]} \n'

    if response != '':
        response = 'Code - Name: \n' + response
    else:
        response = f'There is no symbol for search text - {text}'

    await message.answer(response, parse_mode="HTML")


@dp.message(Command(commands=["subscribe"]))
async def cmd_subscribe(message: types.Message, command: CommandObject):

    response = ''

    if command.args == None:
        await message.answer(f'Incorrect input attributes. Please check the command /help')
        return

    argList = command.args.split()
    symbolList = argList[0].split(',')
    intervalList = argList[1].split(',')

    for symbol in symbolList:
        symbol = symbol_in(symbol)
        if not Symbol().check_symbol(symbol):
            await message.answer(f'Symbol {symbol} is not valid. Try again')
            continue

        for interval in intervalList:
            if not interval in CONST.TA_INTERVALS:
                await message.answer(f'Interval {interval} is not valid. Try again')
                return

            logging.info(f'/subscribe {symbol} {interval}')

            try:
                job = scheduler.addJob(
                    chatId=message.chat.id, symbol=symbol, interval=interval, callback=processSignal)

                response = response + \
                    f'<b>{symbol} {interval}</b> subscribed. Next Run: {job.next_run_time.strftime("%Y-%m-%d %H:%M:%S %Z")} \n'
            except Exception:
                response = response + \
                    f'Incorrect interval {interval} for subscription'

    await message.answer(response, parse_mode="HTML")


@dp.message(Command(commands=["unsubscribe"]))
async def cmd_unsubscribe(message: types.Message, command: CommandObject):

    interval = ''

    if command.args == None:
        await message.answer(f'Incorrect input attributes. Please check the command /help')
        return

    argList = command.args.split()
    symbol = symbol_in(argList[0])

    if not Symbol().check_symbol(symbol):
        await message.answer(f'Symbol {symbol} is not valid. Try again')
        return

    if len(argList) == 2:
        interval = argList[1]
        if not interval in CONST.TA_INTERVALS:
            await message.answer(f'Interval {interval} is not valid. Try again')
            return

    logging.info(f'/unsubscribe {symbol} {interval}')

    scheduler.removeJob(chatId=message.chat.id,
                        symbol=symbol, interval=interval)

    await message.answer(f'Subcription with for "{symbol} {interval}" has been removed')


@dp.message(Command(commands=["unsubscribe_all"]))
async def cmd_unsubscribe_all(message: types.Message):

    scheduler.removeAllJob(chatId=message.chat.id)

    await message.answer('All jobs have been removed')


@dp.message(Command(commands=["subscriptions"]))
async def cmd_subcriptions(message: types.Message):
    response = ''
    for jobId in scheduler.getJob(message.chat.id):
        response = response + \
            f'<b>{jobId}</b> - Next Run: {scheduler.getJobNextTimeRun(jobId).strftime("%Y-%m-%d %H:%M:%S %Z")}\n'

    if response == '':
        response = "You don't have any subscriptions"

    await message.answer(response, parse_mode="HTML")


@dp.message(Command(commands=["subscriptions_all"]))
async def cmd_subcriptions_all(message: types.Message):
    response = ''
    for jobId in scheduler.getJobs():  # message.chat.id):
        response = response + \
            f'<b>{jobId}</b> - Next Run: {scheduler.getJobNextTimeRun(jobId).strftime("%Y-%m-%d %H:%M:%S %Z")}\n'

    if response == '':
        response = "You don't have any subscriptions"

    await message.answer(response, parse_mode="HTML")


async def processSignal(bot: Bot, chat_id, symbol, interval):
    response = ''

    logging.info(
        f'Job {chat_id}_{symbol}_{interval} has been executed')

    simulator = Simulator(symbol)
    simulationResult = simulator.detectSignals(
        interval, [Strategy_CCI100_AgainstTrend(20)])

    for result in simulationResult:
        signal_df = result["signal"]
        for index, signal_row in signal_df.iterrows():
            signal_value = signal_row[CONST.SIGNAL]
            if signal_value != '':
                response += f'{index}  -  <b>{result["name"]}</b>: ({signal_row["CCI"]:.2f}) - <b>{signal_value}</b>\n'

            logging.info(
                f'Job {chat_id}_{symbol}_{interval}: {index} - {result["name"]}: ({signal_row["CCI"]:.2f}) - {signal_value}')

    if response != '':
        await bot.send_message(chat_id, response, parse_mode="HTML")


async def start_up():
    logging.info('Start Up function was executed')

    default_schedules = [{'chatId': 689916629, 'symbol': 'BABA', 'interval': '4h'},
                         {'chatId': 689916629, 'symbol': 'TSLA', 'interval': '4h'},
                         {'chatId': 689916629, 'symbol': 'EPAM', 'interval': '4h'},
                         {'chatId': 689916629, 'symbol': 'BTC/USD', 'interval': '4h'},
                         {'chatId': 1658698044, 'symbol': 'BABA', 'interval': '301h'},
                         {'chatId': 1658698044, 'symbol': 'BABA', 'interval': '1h'},
                         {'chatId': 1658698044, 'symbol': 'BABA', 'interval': '4h'},
                         {'chatId': 1658698044, 'symbol': 'TSLA', 'interval': '1h'},
                         {'chatId': 1658698044, 'symbol': 'TSLA', 'interval': '4h'},
                         {'chatId': 1658698044, 'symbol': 'EPAM', 'interval': '1h'},
                         {'chatId': 1658698044, 'symbol': 'EPAM', 'interval': '4h'},
                         {'chatId': 1658698044, 'symbol': 'BTC/USD', 'interval': '30m'},
                         {'chatId': 1658698044, 'symbol': 'BTC/USD', 'interval': '1h'},
                         {'chatId': 1658698044, 'symbol': 'BTC/USD', 'interval': '4h'},
                         {'chatId': 1658698044, 'symbol': 'Natural Gas', 'interval': '30m'},
                         {'chatId': 1658698044, 'symbol': 'Natural Gas', 'interval': '1h'},
                         {'chatId': 1658698044, 'symbol': 'Natural Gas', 'interval': '4h'},
                         {'chatId': 1658698044, 'symbol': 'MSFT', 'interval': '30m'},
                         {'chatId': 1658698044, 'symbol': 'MSFT', 'interval': '1h'},
                         {'chatId': 1658698044, 'symbol': 'MSFT', 'interval': '4h'}]

    for schedule in default_schedules:
        try:
            scheduler.addJob(chatId=schedule['chatId'], symbol=schedule['symbol'],
                             interval=schedule['interval'], callback=processSignal)
        except Exception:
            logging('Error during scheduling default jobs')

    # Initialize list of symbols of exchange for singleton
    symbolHandler = Symbol()
    symbolHandler.initSymbols()


def symbol_in(symbol: str):
    return symbol.replace('_', ' ')


def symbol_out(symbol: str):
    return symbol.replace(' ', '_')

# Запуск процесса поллинга новых апдейтов


async def main():
    scheduler.startScheduler()
    await start_up()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

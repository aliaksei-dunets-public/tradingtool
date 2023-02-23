import constants as CONST
from model import Mediator
from strategy import Strategy_CCI100_AgainstTrend
from simulator import Simulator

symbol = 'BABA'
interval = CONST.TA_INTERVAL_1H

mediator = Mediator(symbol)
df = mediator.getAsset().getHistoryDataFrame(interval, CONST.TA_PERIOD_5D)

dti = df.tz_convert('UTC')

cci_20 = Strategy_CCI100_AgainstTrend(20, mediator, interval)

print(cci_20.getSignalsDataFrame())

simulator = Simulator([cci_20])

simulationResult = simulator.getSignals()

# print(simulationResult)

response = f'Signals for {symbol} {interval}:\n'

for result in simulationResult:
    signal_df = result["signal"]
    for index, signal_row in signal_df.iterrows():
        signal_value = signal_row[CONST.SIGNAL]
        if signal_value != '':
            response += f'{index}: {result["name"]} - {signal_value}\n'

print(response)
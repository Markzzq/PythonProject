import numpy as np
import pandas as pd
import datetime
import time
import schedule
import matplotlib.pyplot as plt


# akshare 作为数据源
from pybroker.ext.data import AKShare
akshare = AKShare()


import pybroker as pb
from pybroker import Strategy, StrategyConfig, YFinance, ExecContext
import yfinance as yf


START_DATE = '2019-01-01'
END_DATE = '2025-05-30'

# 下载数据的函数 (示例)
def load_data(symbols, start_date, end_date):
    if isinstance(symbols, str):
        symbols = [symbols]
    data = {}
    for symbol in symbols:
        df = akshare.query(symbols='symbol',
                            start_date='3/1/2021',
                            end_date='3/1/2023',
                            adjust="",
                            timeframe="1d")
        # df = yf.download(symbol, start=start_date, end=end_date, progress=False)
        if df.empty:
            print(f"Warning: No data downloaded for {symbol}")
            continue
        # 重命名列以符合 PyBroker 预期 (小写)
        df.rename(columns={'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Adj Close': 'adj_close',
                           'Volume': 'volume'}, inplace=True)
        df.columns = df.columns.str.lower()
        # 确保索引是 DatetimeIndex
        df.index = pd.to_datetime(df.index)
        data[symbol] = df
    if len(symbols) == 1 and symbols[0] in data:
        return data[symbols[0]]
    elif not data:
        raise ValueError("No data could be loaded for the specified symbols and dates.")
    return data



# 定义一个策略
"""
这里有很多内容需要解释！buy_low 函数将接收一个包含当前股票代码（AAPL 或 MSFT）数据的 ExecContext （ctx）。
ExecContext 将包含当前股票代码最近 K 线之前的所有收盘价。通过 ctx.close[-1] 获取最新的收盘价。

buy_low 函数将使用 ExecContext 来下达买单。购买的股份数量通过 ctx.buy_shares，设置，
它是通过 ctx.calc_target_shares 计算的。在这种情况下，要购买的股份数量将等于投资组合的 25%。

订单的限价通过 buy_limit_price 设置。如果满足条件，买单将在下一根 K 线成交。订单成交的时间可以通过 StrategyConfig.buy_delay 进行配置，
成交价可以通过 ExecContext.buy_fill_price 设置。默认情况下，买单在下一根 K 线（buy_delay=1）成交，成交价等于该 K 线的最低价和最高价之间的中点。

最后，ctx.hold_bars 指定在平仓之前持有头寸的 K 线数。平仓时，股票以市价出售，
市价等于 ExecContext.sell_fill_price，这是可配置的，默认值为K线最低价和最高价之间的中点。
"""
def buy_low(ctx):
    # If shares were already purchased and are currently being held, then return.
    if ctx.long_pos():
        return
    # If the latest close price is less than the previous day's low price,
    # then place a buy order.
    if ctx.bars >= 2 and ctx.close[-1] < ctx.low[-2]:
        # Buy a number of shares that is equal to 25% the portfolio.
        ctx.buy_shares = ctx.calc_target_shares(0.25)
        # Set the limit price of the order.
        ctx.buy_limit_price = ctx.close[-1] - 0.01
        # Hold the position for 3 bars before liquidating (in this case, 3 days).
        ctx.hold_bars = 3

"""
添加第二个执行逻辑
在同一个 Strategy 实例中，你可以为不同的股票代码使用不同的交易规则。换句话说，你并不局限于对一组股票代码只使用一套交易规则。

为了说明这一点，提供了一个名为 short_high 的函数，其中包含一个做空策略的新规则集，这与之前的规则集类似：
"""

def short_high(ctx):
    # If shares were already shorted then return.
    if ctx.short_pos():
        return
    # If the latest close price is more than the previous day's high price,
    # then place a sell order.
    if ctx.bars >= 2 and ctx.close[-1] > ctx.high[-2]:
        # Short 100 shares.
        ctx.sell_shares = 100
        # Cover the shares after 2 bars (in this case, 2 days).
        ctx.hold_bars = 2






if __name__ == '__main__':

    # yfinance = YFinance()
    # df = yfinance.query(['AAPL', 'MSFT'], start_date='3/1/2017', end_date='3/1/2022')
    # print(df)

    # 缓存数据
    # pb.enable_data_source_cache('yfinance')
    #
    # pb.enable_data_source_cache('my_strategy')

    config = StrategyConfig(initial_cash=500_000)
    strategy = Strategy(akshare, '3/1/2020', '3/1/2025', config)

    strategy.add_execution(buy_low, symbols=['600100'])
    #strategy.add_execution(short_high, ['TSLA'])

    result = strategy.backtest()

    #chart = plt.subplot2grid((3, 2), (0, 0), rowspan=3, colspan=2)

    plt.plot(result.portfolio.index, result.portfolio['market_value'])
    plt.xlabel('date')
    plt.ylabel('market value')
    plt.title('600100')
    plt.show()

    # symbol = '600100.SH'
    #
    # aapl_data = load_data(symbol, START_DATE, END_DATE)

    # print(result.metrics_df)  # 查看绩效
    print(result.orders)  # 查看订单
    # print(result.positions)  # 查看持仓
    # print(result.portfolio)  # 查看投资组合
    print(result.trades)  # 查看交易

    print('finished')
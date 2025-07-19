import numpy as np
import akshare as ak
import pandas as pd
import datetime
import time
import schedule


# plotly   一种滑动窗口绘图库
import plotly.express as px
import plotly.graph_objects as go


def task():
    stock_zh_a_spot_em_df = ak.stock_zh_a_spot_em()

    for row_index, row in stock_zh_a_spot_em_df.iterrows():
        try:
            time.sleep(0.5)

            row_code = row['代码']  # 是因为抓到的数据带了字母 只取数字
            row_name = row['名称']
            # 因子1 5分钟涨跌数据
            if row['5分钟涨跌'] > 1:
                var1 = True
            else:
                var1 = False

            # 因子2 换手率突破5%
            if row['换手率'] > 5:
                var2 = True
            else:
                var2 = False

            # 因子3 涨跌幅
            if row['涨跌幅'] > 3:
                var3 = True
            else:
                var3 = False

            # 因子4 量比
            if row['量比'] > 1.2:
                var4 = True
            else:
                var4 = False

            varAll = var1 and var2 and var3 and var4

            if varAll == True:
                anyData = {'stock': row_code, 'name': row_name, '5分钟涨跌': row['5分钟涨跌'], '换手率': row['换手率'], '涨跌幅': row['涨跌幅'], '量比': row['量比']}
                df_index = row_index + 1
                dfResult.loc[df_index] = anyData
        except:
            continue
    print(dfResult)
    # timestamp = datetime.datetime.now()
    # localtime = timestamp.strftime('%Y-%m-%d-%H-%M-%S')
    # filename = f"{localtime}.csv"
    # dfResult.to_csv(filename, encoding='utf-8-sig')







if __name__ == '__main__':

    # 读取股票代码列表
    df_stock_list = pd.read_csv("standby_list.csv")

    # 取非北交所股票 测试   北交所到265
    # df_stock = stock_zh_a_spot_df[['代码', '名称']][266:350]
    df_stock = df_stock_list[['代码', '名称']]

    # anydata 是dictionary
    anyData = {'stock': '00', 'name': 'name', '5分钟涨跌': 'var1', '换手率': 'var2', '涨跌幅': 'var3', '量比': 'var4'}
    dfResult = pd.DataFrame(anyData, index=[0])


    # task()

    # 设定任务 读取实时股票数据 循环执行
    schedule.every(2).minutes.do(task)
    # Run the scheduled tasks indefinitely
    while True:
        schedule.run_pending()


    print("finish")
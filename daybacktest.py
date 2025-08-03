import numpy as np
import akshare as ak
import pandas as pd
import datetime
import time
import schedule
import utils

# 股市行情数据获取
from Ashare import *  # 股票数据库    https://github.com/mpquant/Ashare
from MyTT import *  # myTT麦语言工具函数指标库  https://github.com/mpquant/MyTT
import baostock as bs

# 可视化界面
# plotly express   一种滑动窗口绘图库
import plotly.express as px
import plotly.graph_objects as go


def reviewData():
    start_time = time.time()

    # 读取股票列表
    df_stock_list = pd.read_csv('0721_test.csv')
    df_stock = df_stock_list[['stock', 'name']]

    # 限定回测时间  非周日以 数据结果的第二天开始计算
    START_DATE = '2025-07-22'
    END_DATE = '2025-07-25'
    C1 = 1.0
    C2 = 1.0

    dfResult = pd.DataFrame(data=None, columns=['stock', 'name', 'bias'])

    # 登陆baostock开源库
    lg = bs.login()

    ttd = 0

    for row_index, row in df_stock.iterrows():
        try:
            # 方法三
            row_code = row['stock'][:2] + "." +  row['stock'][2:]
            row_name = row['name']

            # 日线数据
            """
            adjustflag：复权类型，默认不复权：3, 1：后复权, 2：前复权。已支持分钟线、日线、周线、月线前后复权
            """
            rs = bs.query_history_k_data_plus(row_code,
                                              "date,code,open,high,low,close,preclose,volume,amount,adjustflag,turn,tradestatus,pctChg,peTTM,pbMRQ,psTTM,pcfNcfTTM,isST",
                                              start_date = START_DATE, end_date = END_DATE,
                                              frequency = "d", adjustflag = "2")

            #### 打印结果集 ####
            data_list = []
            while (rs.error_code == '0') & rs.next():
                # 获取一条记录，将记录合并在一起
                data_list.append(rs.get_row_data())
            result = pd.DataFrame(data_list, columns=rs.fields)

            N = result.shape[0]

            # # 移除停牌股票
            # if result['tradestatus'][N-1] == '0':
            #     print('停牌   out ')
            #     continue
            #
            # # 移除st 股票
            # if result['isST'][N-1] == '1':
            #     print('ST   out ')
            #     continue
            #
            # # 移除科创板股票
            # if row['代码'][2:5] == '688':
            #     #print('688   out ')
            #     continue

            # 计算kdj
            K, D, J = utils.calKDJ(result)

            # OBV指标
            OBV = utils.calOBV(result)

            # 计算数据
            OPEN = result['open'].astype(float)
            CLOSE = result['close'].astype(float)


            # 计算变化范围
            bias = CLOSE[N-1] - OPEN[0]
            if bias > 0:
                ttd = ttd + 1

            # 展示在图标中
            # fig = px.line(result, x="date", y="close", title=row_name, subtitle=row_code)
            # fig.add_trace(go.Scatter(x=[result['date'].iloc[-1]],
            #                          y=[result['close'].iloc[-1]],
            #                          text=[result['date'].iloc[-1]],
            #                          mode='markers+text',
            #                          marker=dict(color='red', size=10),
            #                          textfont=dict(color='green', size=10),
            #                          textposition='top left',
            #                          showlegend=False))
            # fig.show()

            anyData = {'stock': row_code, 'name': row_name, 'bias': bias}
            df_index = row_index + 1
            dfResult.loc[df_index] = anyData

        except:
            continue

    print(dfResult)

    print("起始股票数量 ", df_stock.shape[0])
    print("统计收盘为正收益 ", ttd)

    #### 结果集输出到csv文件 ####
    file_name = f"{START_DATE}_{END_DATE}_backtest.csv"
    dfResult.to_csv(file_name, encoding="utf-8-sig", index=False)

    #### 登出系统 ####
    bs.logout()

    end_time = time.time()
    print(f"reviewData 运行时间：{end_time - start_time} 秒")


if __name__ == '__main__':

    reviewData()








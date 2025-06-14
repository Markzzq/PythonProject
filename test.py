import numpy as np
import akshare as ak
import pandas as pd
import datetime
import time

# plotly   一种滑动窗口绘图库
import plotly.express as px
import plotly.graph_objects as go


# 获取沪深300指数成分股数据
#df_hs300 = ak.index_stock_cons('000300')
#print(df_hs300)

"""
东方财富网-行情首页-沪深京 A 股-每日行情
https://quote.eastmoney.com/concept/sh603777.html?from=classic
:param symbol: 股票代码
:type symbol: str
:param period: choice of {'daily', 'weekly', 'monthly'}
:type period: str
:param start_date: 开始日期
:type start_date: str
:param end_date: 结束日期
:type end_date: str
:param adjust: choice of {"qfq": "前复权", "hfq": "后复权", "": "不复权"}
:type adjust: str
:param timeout: choice of None or a positive float number
:type timeout: float
:return: 每日行情
:rtype: pandas.DataFrame
"""
# 获取股票的历史日线 周线 月线 行情数据  注意 这里的symbol 不需要字母sz sh
# 单个股票历史数据 后复权用于量化分析
# stock_zh_a_hist_df = ak.stock_zh_a_hist(symbol="600519",
#                                         period="daily",
#                                         start_date="20250101",
#                                         end_date='20250530',
#                                         adjust="hfq")
#print(stock_zh_a_hist_df)


"""
新浪财经-A 股-个股的历史行情数据, 大量抓取容易封 IP
https://finance.sina.com.cn/realstock/company/sh603843/nc.shtml
:param symbol: sh600000
:type symbol: str
:param start_date: 20201103; 开始日期
:type start_date: str
:param end_date: 20201103; 结束日期
:type end_date: str
:param adjust: 默认为空: 返回不复权的数据; qfq: 返回前复权后的数据; hfq: 返回后复权后的数据; hfq-factor: 返回后复权因子; qfq-factor: 返回前复权因子
:type adjust: str
:return: 行情数据
:rtype: pandas.DataFrame
"""
# 获取个股日线数据
# df_day = ak.stock_zh_a_daily(symbol='sz300468',
#                     start_date='20250101',
#                     end_date='20250530',
#                     adjust = "")



"""
股票及股票指数历史行情数据-分钟数据
https://finance.sina.com.cn/realstock/company/sh600519/nc.shtml
:param symbol: sh000300
:type symbol: str
:param period: 1, 5, 15, 30, 60 分钟的数据
:type period: str
:param adjust: 默认为空: 返回不复权的数据; qfq: 返回前复权后的数据; hfq: 返回后复权后的数据;
:type adjust: str
:return: specific data
:rtype: pandas.DataFrame
"""
# 获取个股的 分钟线 5分钟线等数据
# df_minute = ak.stock_zh_a_minute(symbol = "sh600519",
#                      period = "1",
#                      adjust = "")








# 读取股票代码列表
df_stock_list = pd.read_csv("stock_zh_list.csv")

# 取非北交所股票 测试   北交所到265
# df_stock = stock_zh_a_spot_df[['代码', '名称']][266:350]
df_stock = df_stock_list[['代码', '名称']][266:350]






import requests
url = "https://pchq.kaipanla.com/w1/api/index.php"
payload = ""
headers = {
  'Accept': 'application/json, text/javascript, */*; q=0.01',
  'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7,zh-TW;q=0.6',
  'Cache-Control': 'no-cache',
  'Connection': 'keep-alive',
  'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
  'Origin': 'https://www.kaipanla.com',
  'Pragma': 'no-cache',
  'Referer': 'https://www.kaipanla.com/',
  'Sec-Fetch-Dest': 'empty',
  'Sec-Fetch-Mode': 'cors',
  'Sec-Fetch-Site': 'same-site',
  'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36',
  'sec-ch-ua': '"Chromium";v="106", "Google Chrome";v="106", "Not;A=Brand";v="99"',
  'sec-ch-ua-mobile': '?0',
  'sec-ch-ua-platform': '"macOS"'
}




if __name__ == '__main__':
    response = requests.request("POST", url, headers=headers, data=payload)

    data = response.json()
    columns = {"代码": [], "概念名称": [], "强度": [], "未知1": [], "涨速": [], "成交额": [], "主力净额": [],
               "主力买入": [], "主力卖出": [], "量比": [], "流通市值": [], "未知2": [], "未知3": []}
    columns_list = ["代码", "概念名称", "强度", "未知1", "涨速", "成交额", "主力净额", "主力买入", "主力卖出", "量比",
                    "流通市值", "未知2", "未知3"]

    for i in data["plates"]["list"]:
        for j in range(len(i)):
            columns[columns_list[j]].append(i[j])
    import pandas as pd

    data_df = pd.DataFrame(columns)
    data_df["date"] = data["plates"]["Day"][0]
    # data_df.to_csv("概念轻强度{}.csv".format(data["plates"]["Day"][0]))
    print(data_df.head())
    print("finish")

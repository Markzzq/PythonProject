import pandas as pd
import baostock as bs

"""
当前交易日17:30，完成日K线数据入库；
当前交易日18:00，完成复权因子数据入库；
第二自然日11:00，完成分钟K线数据入库；
第二自然日1:30，完成前交易日“其它财务报告数据”入库；
周六17:30，完成周线数据入库；
"""
# 通过baostock 接口获取某一股票的历史数据并保存
def get(code, start_date, end_date):
    #### 登陆系统 ####
    lg = bs.login()
    # 显示登陆返回信息
    print('login respond error_code:' + lg.error_code)
    print('login respond error_msg:' + lg.error_msg)

    #### 获取历史K线数据 ####
    # 详细指标参数，参见“历史行情指标参数”章节
    rs = bs.query_history_k_data_plus(code,
                                      "date,code,open,high,low,close,preclose,volume,amount,adjustflag,turn,tradestatus,pctChg,peTTM,pbMRQ,psTTM,pcfNcfTTM,isST",
                                      start_date=start_date, end_date=end_date,
                                      frequency="d", adjustflag="3")
    print('query_history_k_data_plus respond error_code:' + rs.error_code)
    print('query_history_k_data_plus respond error_msg:' + rs.error_msg)

    #### 打印结果集 ####
    data_list = []
    while (rs.error_code == '0') & rs.next():
        # 获取一条记录，将记录合并在一起
        data_list.append(rs.get_row_data())
    result = pd.DataFrame(data_list, columns=rs.fields)

    #### 结果集输出到csv文件 ####
    file_name = f"{code}_history_k_data.csv"
    result.to_csv(file_name, encoding="utf-8-sig", index=False)
    print(result)

    #### 登出系统 ####
    bs.logout()


# 获取数据并保存
if __name__ == '__main__':

    # df_stock_list = pd.read_csv('stock_zh_list.csv')
    # df_stock = df_stock_list[['代码', '名称']][266:]

    anyData = {'stock': '00', 'name': 'name_test'}
    dfResult = pd.DataFrame(anyData, index=[0])

    get('sh.600000', '2025-01-01', '2025-05-30')
    print('finished')

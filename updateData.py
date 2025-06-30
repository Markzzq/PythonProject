import akshare as ak
import pandas as pd
import datetime
import time


# 更新etf 及A股 列表数据

if __name__ == '__main__':

    # # 抓取沪深基金并保存在表格中
    # etf = ak.fund_etf_category_sina(symbol="ETF基金")
    # etf.to_csv("sina_etf_list.csv", encoding='utf-8-sig')
    #
    # # A 股上市公司的实时行情数据，抓取股票列表
    # # 新浪财经-所有 A 股的实时行情数据;
    # stock_zh_a_spot_df = ak.stock_zh_a_spot()
    # stock_zh_a_spot_df.to_csv("stock_zh_list.csv", encoding='utf-8-sig')

    # 同花顺-所有 A 股的板块概念名单 题材概念
    concept_zh_a_spot_df = ak.stock_board_concept_name_ths()
    concept_zh_a_spot_df.to_csv("concept_ths_list.csv", encoding='utf-8-sig')

    # 东方财富-所有 A 股的板块概念名单 题材概念
    concept_em_df = ak.stock_board_concept_name_em()
    concept_em_df.to_csv("concept_em_list.csv", encoding='utf-8-sig')
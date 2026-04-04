import akshare as ak
import pandas as pd
import datetime
import time

# 股市行情数据获取和作图 -2
from Ashare import *  # 股票数据库    https://github.com/mpquant/Ashare
from MyTT import *  # myTT麦语言工具函数指标库  https://github.com/mpquant/MyTT

START_DATE = '2025-12-01'
END_DATE = datetime.datetime.now().strftime('%Y-%m-%d')

Cd = 1.02


def analyze_concept(filename):
    """分析概念板块数据"""
    start_time = time.time()
    
    try:
        # 读取概念板块列表
        df_concept_list = pd.read_csv(filename)
        df_concept = df_concept_list[['code', 'name']]
        
        # 初始化结果DataFrame
        dfResult = pd.DataFrame(columns=['code', 'name', '收盘价', '涨跌幅', 'MA5'])
        
        for row_index, row in df_concept.iterrows():
            try:
                # time.sleep(0.5)  # 避免请求过快
                
                # 获取概念代码和名称
                concept_code = row['code']
                concept_name = row['name']
                
                # 获取概念板块指数数据（至少120天）
                concept_data = ak.stock_board_concept_index_ths(symbol=concept_name,
                                                               start_date=START_DATE, 
                                                               end_date=END_DATE)
                
                if concept_data.empty:
                    print(f"{concept_name} ({concept_code}) 无数据，跳过")
                    continue
                
                N = concept_data.shape[0]
                if N < 60:
                    print(f"{concept_name} ({concept_code}) 数据不足60天，跳过")
                    continue
                
                # 计算技术指标
                CLOSE = concept_data['收盘价'].astype(float)
                OPEN = concept_data['开盘价'].astype(float)
                
                # 计算均线
                MA5 = MA(CLOSE, 5)  # 5日均线
                MA10 = MA(CLOSE, 10)  # 10日均线
                MA20 = MA(CLOSE, 20)  # 20日均线
                MA60 = MA(CLOSE, 60)  # 60日均线
                
                # 计算MACD指标
                dif, dea, macd = MACD(CLOSE)
                
                # 计算RSI指标
                rsi6 = RSI(CLOSE, N=6)
                rsi12 = RSI(CLOSE, N=12)
                rsi24 = RSI(CLOSE, N=24)
                
                # 初始化条件变量
                close_above_ma5 = False
                
                # 判断今日收盘价大于MA5
                if N >= 5:
                    # 确保有足够的数据点计算MA5
                    if CLOSE[N-1] > MA5[N-1]:
                        close_above_ma5 = True
                
                # 综合条件判断
                if close_above_ma5:
                    # 计算涨跌幅
                    pct_change = (CLOSE[N-1] - CLOSE[N-2]) / CLOSE[N-2] * 100
                    
                    # 添加到结果集
                    anyData = {
                        'code': concept_code,
                        'name': concept_name,
                        '收盘价': CLOSE[N-1],
                        '涨跌幅': round(pct_change, 2),
                        'MA5': round(MA5[N-1], 2)
                    }
                    reverse_index = row_index + 1
                    dfResult.loc[reverse_index] = anyData
                    print('success add one', concept_code, concept_name)
                    
            except Exception as e:
                print(f"处理 {row['code']} 时出错: {e}")
                continue
        
        # 输出结果到以当天日期命名的csv文件
        print(dfResult)
        file_name = f"{END_DATE}_concept.csv"
        dfResult.to_csv(file_name, encoding="utf-8-sig", index=False)
        print(f"结果已保存到 {file_name}")
        
    except Exception as e:
        print(f"分析过程中出错: {e}")
    
    end_time = time.time()
    print(f"analyze_concept运行时间：{end_time - start_time}秒")


def main():
    """主函数"""
    # 分析概念板块数据
    analyze_concept('concept_ths_list.csv')


if __name__ == '__main__':
    main()
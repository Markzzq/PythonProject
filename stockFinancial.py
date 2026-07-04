import numpy as np
import akshare as ak
import pandas as pd
import datetime
import time


START_DATE = '2025-01-01'
END_DATE = datetime.datetime.now().strftime('%Y-%m-%d')


def get_stock_financial_report(filename):
    """
    获取股票财报数据的统一接口，只保留财务表现良好的公司
    
    参数:
        filename: 股票代码CSV文件路径，格式需包含 '代码' 和 '名称' 列
    
    返回:
        None，结果保存到CSV文件
    """
    start_time = time.time()
    
    df_stock_list = pd.read_csv(filename)
    df_stock = df_stock_list[['代码', '名称']]
    
    df_financial_metrics = pd.DataFrame()
    
    success_count = 0
    fail_count = 0
    filtered_count = 0
    
    for row_index, row in df_stock.iterrows():
        try:
            stock_code = row['代码']
            stock_name = row['名称']
            
            if str(stock_code).startswith('bj') or str(stock_code).startswith('BJ'):
                print(f"北交所股票 {stock_code} {stock_name} 跳过")
                continue
            
            api_code = format_stock_code(stock_code)
            
            print(f"正在获取 {api_code} {stock_name} 的财报数据...")
            
            df_balance = ak.stock_financial_report_sina(stock=api_code, symbol="资产负债表")
            df_balance = filter_by_date(df_balance, START_DATE)
            
            time.sleep(0.3)
            
            df_income = ak.stock_financial_report_sina(stock=api_code, symbol="利润表")
            df_income = filter_by_date(df_income, START_DATE)
            
            time.sleep(0.3)
            
            df_cashflow = ak.stock_financial_report_sina(stock=api_code, symbol="现金流量表")
            df_cashflow = filter_by_date(df_cashflow, START_DATE)
            
            time.sleep(0.3)
            
            df_metrics = extract_financial_metrics(df_balance, df_income, df_cashflow, stock_code, stock_name)
            
            if df_metrics.empty:
                print(f"{api_code} {stock_name} 财报数据不足，跳过")
                fail_count += 1
                continue
            
            df_metrics = calculate_growth_rates(df_metrics)
            
            if is_financial_healthy(df_metrics):
                df_financial_metrics = pd.concat([df_financial_metrics, df_metrics], ignore_index=True)
                success_count += 1
                print(f"成功获取 {api_code} {stock_name} 的财报数据（财务健康）")
            else:
                filtered_count += 1
                print(f"{api_code} {stock_name} 财务数据表现不佳，过滤")
            
        except Exception as e:
            fail_count += 1
            print(f"获取 {stock_code} {stock_name} 财报数据失败: {e}")
            continue
    
    # ========== 保存结果文件 ==========
    file_financial = f"{END_DATE}_financial_report.csv"
    df_financial_metrics.to_csv(file_financial, encoding="utf-8-sig", index=False)
    print(f"财报数据已保存到 {file_financial}")
    
    end_time = time.time()
    
    print(f"\n财报数据获取完成！")
    print(f"成功（财务健康）: {success_count} 只股票")
    print(f"过滤（财务不佳）: {filtered_count} 只股票")
    print(f"失败: {fail_count} 只股票")
    print(f"运行时间: {end_time - start_time:.2f} 秒")


def format_stock_code(stock_code):
    """
    格式化股票代码，确保包含 sh/sz 前缀且为小写
    
    参数:
        stock_code: 股票代码，支持多种格式
    
    返回:
        格式化后的股票代码（如 sh600519, sz000001）
    """
    code = str(stock_code).strip().lower()
    
    if code.startswith('sh') or code.startswith('sz'):
        return code
    
    if code.startswith('6'):
        return 'sh' + code
    elif code.startswith('0') or code.startswith('3'):
        return 'sz' + code
    
    return code


def filter_by_date(df, start_date):
    """
    根据日期筛选数据，只保留2025年1月1日之后的报告期
    
    参数:
        df: 财报数据DataFrame
        start_date: 起始日期
    
    返回:
        筛选后的DataFrame
    """
    if df.empty or '报告日' not in df.columns:
        return df
    
    df['报告日'] = df['报告日'].astype(str)
    
    start_date_str = start_date.replace('-', '')
    
    return df[df['报告日'] >= start_date_str]


def extract_financial_metrics(df_balance, df_income, df_cashflow, stock_code, stock_name):
    """
    从三大报表中提取关键财务指标（支持多期对比）
    
    参数:
        df_balance: 资产负债表DataFrame
        df_income: 利润表DataFrame
        df_cashflow: 现金流量表DataFrame
        stock_code: 股票代码
        stock_name: 股票名称
    
    返回:
        包含关键财务指标的DataFrame
    """
    metrics_list = []
    
    if df_balance.empty or df_income.empty:
        return pd.DataFrame(metrics_list)
    
    df_balance['报告日'] = df_balance['报告日'].astype(str)
    df_income['报告日'] = df_income['报告日'].astype(str)
    
    balance_dates = set(df_balance['报告日'])
    income_dates = set(df_income['报告日'])
    
    common_dates = sorted(balance_dates & income_dates, reverse=True)
    
    for report_date in common_dates:
        try:
            balance_row = df_balance[df_balance['报告日'] == report_date].iloc[0]
            
            income_row = df_income[df_income['报告日'] == report_date].iloc[0]
            
            cashflow_row = None
            if not df_cashflow.empty:
                df_cashflow['报告日'] = df_cashflow['报告日'].astype(str)
                cashflow_rows = df_cashflow[df_cashflow['报告日'] == report_date]
                if not cashflow_rows.empty:
                    cashflow_row = cashflow_rows.iloc[0]
            
            metrics = {
                '股票代码': stock_code,
                '股票名称': stock_name,
                '报告期': report_date,
            }
            
            # 资产负债表指标
            metrics['货币资金'] = balance_row.get('货币资金', None)
            metrics['应收账款'] = balance_row.get('应收账款', None)
            metrics['存货'] = balance_row.get('存货', None)
            metrics['流动资产合计'] = balance_row.get('流动资产合计', None)
            metrics['非流动资产合计'] = balance_row.get('非流动资产合计', None)
            metrics['资产总计'] = balance_row.get('资产总计', None)
            metrics['流动负债合计'] = balance_row.get('流动负债合计', None)
            metrics['非流动负债合计'] = balance_row.get('非流动负债合计', None)
            metrics['负债合计'] = balance_row.get('负债合计', None)
            metrics['所有者权益(或股东权益)合计'] = balance_row.get('所有者权益(或股东权益)合计', None)
            
            # 计算资产负债率
            try:
                total_assets = float(balance_row.get('资产总计', 0))
                total_liabilities = float(balance_row.get('负债合计', 0))
                if total_assets > 0:
                    metrics['资产负债率(%)'] = round(total_liabilities / total_assets * 100, 2)
                else:
                    metrics['资产负债率(%)'] = None
            except:
                metrics['资产负债率(%)'] = None
            
            # 计算流动比率
            try:
                current_assets = float(balance_row.get('流动资产合计', 0))
                current_liabilities = float(balance_row.get('流动负债合计', 0))
                if current_liabilities > 0:
                    metrics['流动比率'] = round(current_assets / current_liabilities, 2)
                else:
                    metrics['流动比率'] = None
            except:
                metrics['流动比率'] = None
            
            # 利润表指标
            metrics['营业总收入'] = income_row.get('营业总收入', None)
            metrics['营业收入'] = income_row.get('营业收入', None)
            metrics['营业成本'] = income_row.get('营业成本', None)
            metrics['营业利润'] = income_row.get('营业利润', None)
            metrics['利润总额'] = income_row.get('利润总额', None)
            metrics['净利润'] = income_row.get('净利润', None)
            metrics['归属于母公司所有者的净利润'] = income_row.get('归属于母公司所有者的净利润', None)
            metrics['基本每股收益'] = income_row.get('基本每股收益', None)
            metrics['稀释每股收益'] = income_row.get('稀释每股收益', None)
            metrics['销售费用'] = income_row.get('销售费用', None)
            metrics['管理费用'] = income_row.get('管理费用', None)
            metrics['财务费用'] = income_row.get('财务费用', None)
            metrics['研发费用'] = income_row.get('研发费用', None)
            
            # 计算毛利率和净利率
            try:
                revenue = float(income_row.get('营业收入', 0))
                cost = float(income_row.get('营业成本', 0))
                net_profit = float(income_row.get('净利润', 0))
                
                if revenue > 0:
                    metrics['毛利率(%)'] = round((revenue - cost) / revenue * 100, 2)
                    metrics['净利率(%)'] = round(net_profit / revenue * 100, 2)
                else:
                    metrics['毛利率(%)'] = None
                    metrics['净利率(%)'] = None
            except:
                metrics['毛利率(%)'] = None
                metrics['净利率(%)'] = None
            
            # 现金流量表指标
            if cashflow_row is not None:
                metrics['经营活动产生的现金流量净额'] = cashflow_row.get('经营活动产生的现金流量净额', None)
                metrics['投资活动产生的现金流量净额'] = cashflow_row.get('投资活动产生的现金流量净额', None)
                metrics['筹资活动产生的现金流量净额'] = cashflow_row.get('筹资活动产生的现金流量净额', None)
                metrics['现金及现金等价物净增加额'] = cashflow_row.get('现金及现金等价物净增加额', None)
            
            metrics_list.append(metrics)
            
        except Exception as e:
            print(f"提取 {stock_code} {stock_name} 财务指标失败: {e}")
            continue
    
    return pd.DataFrame(metrics_list)


def get_report_period_type(report_date):
    """
    判断报告期类型（中国财报为累计报告）
    
    参数:
        report_date: 报告日期字符串，格式如 '20250331', '20250630', '20250930', '20251231'
    
    返回:
        报告期类型: 'Q1', 'H1', 'Q3', 'Annual'
    """
    date_str = str(report_date)
    month = int(date_str[4:6])
    
    if month == 3:
        return 'Q1'
    elif month == 6:
        return 'H1'
    elif month == 9:
        return 'Q3'
    elif month == 12:
        return 'Annual'
    return 'Unknown'


def calculate_single_quarter_value(df_metrics, metric_col):
    """
    从累计财报数据计算单季度值
    
    参数:
        df_metrics: 财务指标DataFrame
        metric_col: 指标列名（如 '营业收入', '净利润'）
    
    返回:
        添加单季度值列后的DataFrame
    """
    df = df_metrics.copy()
    single_col_name = metric_col + '_单季度值'
    df[single_col_name] = None
    
    for i in range(len(df)):
        report_date = str(df.iloc[i]['报告期'])
        period_type = get_report_period_type(report_date)
        
        try:
            current_value = float(df.iloc[i].get(metric_col, 0))
        except:
            continue
        
        if period_type == 'Q1':
            df.at[i, single_col_name] = current_value
        elif period_type == 'H1':
            if i + 1 < len(df):
                prev_period_type = get_report_period_type(str(df.iloc[i+1]['报告期']))
                if prev_period_type == 'Q1':
                    try:
                        prev_value = float(df.iloc[i+1].get(metric_col, 0))
                        df.at[i, single_col_name] = current_value - prev_value
                    except:
                        df.at[i, single_col_name] = current_value
                else:
                    df.at[i, single_col_name] = current_value
            else:
                df.at[i, single_col_name] = current_value
        elif period_type == 'Q3':
            if i + 1 < len(df):
                prev_period_type = get_report_period_type(str(df.iloc[i+1]['报告期']))
                if prev_period_type == 'H1':
                    try:
                        prev_value = float(df.iloc[i+1].get(metric_col, 0))
                        df.at[i, single_col_name] = current_value - prev_value
                    except:
                        df.at[i, single_col_name] = current_value
                else:
                    df.at[i, single_col_name] = current_value
            else:
                df.at[i, single_col_name] = current_value
        elif period_type == 'Annual':
            if i + 1 < len(df):
                prev_period_type = get_report_period_type(str(df.iloc[i+1]['报告期']))
                if prev_period_type == 'Q3':
                    try:
                        prev_value = float(df.iloc[i+1].get(metric_col, 0))
                        df.at[i, single_col_name] = current_value - prev_value
                    except:
                        df.at[i, single_col_name] = current_value
                else:
                    df.at[i, single_col_name] = current_value
            else:
                df.at[i, single_col_name] = current_value
    
    return df


def calculate_growth_rates(df_metrics):
    """
    计算同比增长率和环比增长率（基于单季度值）
    
    参数:
        df_metrics: 财务指标DataFrame
    
    返回:
        添加增长率后的DataFrame
    """
    if df_metrics.empty or len(df_metrics) < 2:
        return df_metrics
    
    df = df_metrics.copy()
    
    df = calculate_single_quarter_value(df, '营业收入')
    df = calculate_single_quarter_value(df, '净利润')
    
    df['营业收入_环比增长(%)'] = None
    df['营业收入_同比增长(%)'] = None
    df['净利润_环比增长(%)'] = None
    df['净利润_同比增长(%)'] = None
    
    for i in range(len(df)):
        current_date = str(df.iloc[i]['报告期'])
        
        try:
            revenue_current = float(df.iloc[i].get('营业收入_单季度值', 0))
            net_profit_current = float(df.iloc[i].get('净利润_单季度值', 0))
        except:
            continue
        
        # 计算环比增长（上一季度）
        if i + 1 < len(df):
            try:
                revenue_prev = float(df.iloc[i+1].get('营业收入_单季度值', 0))
                net_profit_prev = float(df.iloc[i+1].get('净利润_单季度值', 0))
                
                if revenue_prev > 0:
                    df.at[i, '营业收入_环比增长(%)'] = round((revenue_current - revenue_prev) / revenue_prev * 100, 2)
                if net_profit_prev != 0:
                    df.at[i, '净利润_环比增长(%)'] = round((net_profit_current - net_profit_prev) / net_profit_prev * 100, 2)
            except:
                pass
        
        # 计算同比增长（去年同期）
        last_year_date = str(int(current_date[:4]) - 1) + current_date[4:]
        last_year_row = df[df['报告期'] == last_year_date]
        
        if not last_year_row.empty:
            try:
                revenue_last_year = float(last_year_row.iloc[0].get('营业收入_单季度值', 0))
                net_profit_last_year = float(last_year_row.iloc[0].get('净利润_单季度值', 0))
                
                if revenue_last_year > 0:
                    df.at[i, '营业收入_同比增长(%)'] = round((revenue_current - revenue_last_year) / revenue_last_year * 100, 2)
                if net_profit_last_year != 0:
                    df.at[i, '净利润_同比增长(%)'] = round((net_profit_current - net_profit_last_year) / net_profit_last_year * 100, 2)
            except:
                pass
    
    return df


def is_financial_healthy(df_metrics):
    """
    判断公司财务是否健康（多个季度营收和净利润同比/环比增长）
    
    参数:
        df_metrics: 包含增长率的财务指标DataFrame
    
    返回:
        bool: True表示财务健康，False表示财务不佳
    """
    if df_metrics.empty or len(df_metrics) < 2:
        return False
    
    healthy_count = 0
    
    for i in range(min(len(df_metrics), 4)):
        row = df_metrics.iloc[i]
        
        try:
            revenue_yoy = row.get('营业收入_同比增长(%)', None)
            revenue_qoq = row.get('营业收入_环比增长(%)', None)
            net_profit_yoy = row.get('净利润_同比增长(%)', None)
            net_profit_qoq = row.get('净利润_环比增长(%)', None)
            
            revenue_positive = False
            net_profit_positive = False
            strong_growth = False
            
            # 营收增长判断
            if revenue_yoy is not None and revenue_yoy > 0:
                revenue_positive = True
            elif revenue_qoq is not None and revenue_qoq > 0:
                revenue_positive = True
            
            # 净利润增长判断
            if net_profit_yoy is not None and net_profit_yoy > 0:
                net_profit_positive = True
            elif net_profit_qoq is not None and net_profit_qoq > 0:
                net_profit_positive = True
            
            # 当前季度单季度净利润必须为正
            net_profit_single = row.get('净利润_单季度值', 0)
            if isinstance(net_profit_single, (int, float)) and net_profit_single <= 0:
                net_profit_positive = False
            
            # 优质公司判断：季度同比增长超过20%
            if revenue_yoy is not None and revenue_yoy >= 20:
                strong_growth = True
            if net_profit_yoy is not None and net_profit_yoy >= 20:
                strong_growth = True
            
            # 优质公司判断：季度环比增长超过10%
            if revenue_qoq is not None and revenue_qoq >= 10:
                strong_growth = True
            if net_profit_qoq is not None and net_profit_qoq >= 10:
                strong_growth = True
            
            # 判断条件：原有条件满足 或 优质公司条件满足
            if (revenue_positive and net_profit_positive) or strong_growth:
                healthy_count += 1
                
        except Exception as e:
            continue
    
    return healthy_count >= 2


if __name__ == '__main__':
    get_stock_financial_report('stock_A_list.csv')
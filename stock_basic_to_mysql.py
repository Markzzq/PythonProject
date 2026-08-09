import pandas as pd
import numpy as np
import datetime
import os
import time

try:
    import pymysql
    MYSQL_DRIVER = 'pymysql'
except ImportError:
    try:
        import mysql.connector
        MYSQL_DRIVER = 'mysql.connector'
    except ImportError:
        MYSQL_DRIVER = None
        print("请先安装 MySQL 驱动: pip install pymysql 或 pip install mysql-connector-python")
        exit(1)

try:
    import akshare as ak
except ImportError:
    print("请先安装 akshare: pip install akshare --upgrade")
    exit(1)


MYSQL_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'ZZQ1996zzq@',
    'database': 'stock_basic',
    'charset': 'utf8mb4'
}

STOCK_LIST_FILE = 'stock_A_list.csv'


def get_mysql_connection():
    if MYSQL_DRIVER == 'pymysql':
        return pymysql.connect(
            host=MYSQL_CONFIG['host'],
            port=MYSQL_CONFIG['port'],
            user=MYSQL_CONFIG['user'],
            password=MYSQL_CONFIG['password'],
            database=MYSQL_CONFIG['database'],
            charset=MYSQL_CONFIG['charset']
        )
    elif MYSQL_DRIVER == 'mysql.connector':
        return mysql.connector.connect(
            host=MYSQL_CONFIG['host'],
            port=MYSQL_CONFIG['port'],
            user=MYSQL_CONFIG['user'],
            password=MYSQL_CONFIG['password'],
            database=MYSQL_CONFIG['database'],
            charset=MYSQL_CONFIG['charset']
        )


def get_table_name(code):
    return f'basic_{code}'


def get_all_stock_tables(conn):
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES LIKE 'basic_%'")
    tables = [row[0] for row in cursor.fetchall()]
    cursor.close()
    return tables


def extract_market_code(code):
    if code.startswith('sh'):
        return code[2:], 'sh'
    elif code.startswith('sz'):
        return code[2:], 'sz'
    elif code.startswith('bj'):
        return code[2:], 'bj'
    return code, 'unknown'


def create_table_if_not_exists(conn, table_name, code, name):
    create_sql = f"""
    CREATE TABLE IF NOT EXISTS `{table_name}` (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        date DATE NOT NULL COMMENT '报告期日期',
        stock_code VARCHAR(20) NOT NULL COMMENT '股票代码',
        stock_name VARCHAR(100) COMMENT '股票名称',
        report_period VARCHAR(20) COMMENT '报告期(季度/年度)',
        roe DECIMAL(10, 4) COMMENT '净资产收益率(ROE)(%)',
        roe_ttm DECIMAL(10, 4) COMMENT 'ROE-TTM(%)',
        pe DECIMAL(10, 4) COMMENT '市盈率(PE)',
        pe_ttm DECIMAL(10, 4) COMMENT '市盈率TTM',
        pb DECIMAL(10, 4) COMMENT '市净率(PB)',
        dividend_yield DECIMAL(10, 4) COMMENT '股息率(%)',
        revenue DECIMAL(20, 2) COMMENT '营业总收入(亿元)',
        revenue_yoy DECIMAL(10, 4) COMMENT '营收同比增长率(%)',
        profit DECIMAL(20, 2) COMMENT '净利润(亿元)',
        profit_yoy DECIMAL(10, 4) COMMENT '净利润同比增长率(%)',
        eps DECIMAL(10, 4) COMMENT '每股收益(EPS)(元)',
        eps_ttm DECIMAL(10, 4) COMMENT '每股收益TTM(元)',
        bps DECIMAL(10, 4) COMMENT '每股净资产(BPS)(元)',
        gross_margin DECIMAL(10, 4) COMMENT '毛利率(%)',
        net_margin DECIMAL(10, 4) COMMENT '净利率(%)',
        debt_ratio DECIMAL(10, 4) COMMENT '资产负债率(%)',
        current_ratio DECIMAL(10, 4) COMMENT '流动比率',
        quick_ratio DECIMAL(10, 4) COMMENT '速动比率',
        operating_cash_flow DECIMAL(20, 2) COMMENT '经营活动现金流(亿元)',
        free_cash_flow DECIMAL(20, 2) COMMENT '自由现金流(亿元)',
        total_assets DECIMAL(20, 2) COMMENT '总资产(亿元)',
        total_liabilities DECIMAL(20, 2) COMMENT '总负债(亿元)',
        total_equity DECIMAL(20, 2) COMMENT '净资产(亿元)',
        roa DECIMAL(10, 4) COMMENT '总资产收益率(ROA)(%)',
        roic DECIMAL(10, 4) COMMENT '投入资本回报率(ROIC)(%)',
        create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
        update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
        UNIQUE KEY uk_date_period (date, report_period)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股票基本财务数据-{name}';
    """
    try:
        cursor = conn.cursor()
        cursor.execute(create_sql)
        conn.commit()
        cursor.close()
        return True
    except Exception as e:
        print(f"创建表 {table_name} 失败: {e}")
        return False


def get_last_report_date(conn, table_name):
    check_sql = f"SELECT MAX(date) as last_date FROM `{table_name}`"
    try:
        cursor = conn.cursor()
        cursor.execute(check_sql)
        result = cursor.fetchone()
        cursor.close()
        if result and result[0]:
            return result[0].strftime('%Y-%m-%d') if hasattr(result[0], 'strftime') else str(result[0])
        return None
    except Exception as e:
        print(f"查询 {table_name} 最新报告期失败: {e}")
        return None


def calculate_dividend_yield(df):
    if '每股收益' in df.columns and '收盘价' in df.columns:
        df['dividend_yield'] = df.apply(
            lambda row: (row['每股收益'] * 0.5 / row['收盘价']) * 100 if row['收盘价'] > 0 and not pd.isna(row['每股收益']) else None,
            axis=1
        )
    return df


def calculate_roe(df):
    if '净利润' in df.columns and '净资产' in df.columns:
        df['roe'] = df.apply(
            lambda row: (row['净利润'] / row['净资产']) * 100 if row['净资产'] > 0 and not pd.isna(row['净利润']) else None,
            axis=1
        )
    return df


def calculate_pe(df):
    if '收盘价' in df.columns and '每股收益' in df.columns:
        df['pe'] = df.apply(
            lambda row: row['收盘价'] / row['每股收益'] if row['每股收益'] > 0 and not pd.isna(row['每股收益']) else None,
            axis=1
        )
    return df


def calculate_pb(df):
    if '收盘价' in df.columns and '每股净资产' in df.columns:
        df['pb'] = df.apply(
            lambda row: row['收盘价'] / row['每股净资产'] if row['每股净资产'] > 0 and not pd.isna(row['每股净资产']) else None,
            axis=1
        )
    return df


def calculate_ps(df, close_price):
    if '营业总收入' in df.columns and '总股本' in df.columns and close_price > 0:
        df['ps'] = df.apply(
            lambda row: (close_price * row['总股本'] / row['营业总收入']) if row['营业总收入'] > 0 and not pd.isna(row['营业总收入']) else None,
            axis=1
        )
    return df


def get_stock_financial_data(code, market):
    ak_code = code
    if market == 'sh':
        ak_code = f'{code}.SH'
    elif market == 'sz':
        ak_code = f'{code}.SZ'
    elif market == 'bj':
        ak_code = f'{code}.BJ'
    
    data_list = []
    
    try:
        df_fin = ak.stock_financial_analysis_indicator_em(symbol=ak_code)
        if df_fin is not None and len(df_fin) > 0:
            for _, row in df_fin.iterrows():
                report_date = str(row.get('REPORT_DATE', ''))
                report_period = str(row.get('REPORT_DATE_NAME', ''))
                
                total_revenue = row.get('TOTALOPERATEREVE')
                revenue = float(total_revenue) / 100000000 if total_revenue is not None else 0
                
                total_profit = row.get('PARENTNETPROFIT')
                profit = float(total_profit) / 100000000 if total_profit is not None else 0
                
                record = {
                    'report_period': report_period if report_period else report_date[:10],
                    'roe': float(row.get('ROEJQ')) if row.get('ROEJQ') is not None else 0,
                    'roe_ttm': float(row.get('ROEKCJQ')) if row.get('ROEKCJQ') is not None else 0,
                    'pe': float(row.get('PER_TOI')) if row.get('PER_TOI') is not None else 0,
                    'pe_ttm': float(row.get('PER_TOI')) if row.get('PER_TOI') is not None else 0,
                    'pb': 0,
                    'dividend_yield': 0,
                    'revenue': revenue,
                    'revenue_yoy': float(row.get('YYZSRGDHBZC')) if row.get('YYZSRGDHBZC') is not None else 0,
                    'profit': profit,
                    'profit_yoy': float(row.get('NETPROFITRPHBZC')) if row.get('NETPROFITRPHBZC') is not None else 0,
                    'eps': float(row.get('EPSJB')) if row.get('EPSJB') is not None else 0,
                    'eps_ttm': float(row.get('EPSXS')) if row.get('EPSXS') is not None else 0,
                    'bps': float(row.get('BPS')) if row.get('BPS') is not None else 0,
                    'gross_margin': float(row.get('XSMLL')) if row.get('XSMLL') is not None else 0,
                    'net_margin': float(row.get('XSJLL')) if row.get('XSJLL') is not None else 0,
                    'debt_ratio': float(row.get('ZCFZL')) if row.get('ZCFZL') is not None else 0,
                    'current_ratio': float(row.get('LD')) if row.get('LD') is not None else 0,
                    'quick_ratio': float(row.get('SD')) if row.get('SD') is not None else 0,
                    'roa': float(row.get('NET_ROI')) if row.get('NET_ROI') is not None else 0,
                    'roic': float(row.get('ROIC')) if row.get('ROIC') is not None else 0,
                    'total_assets': 0,
                    'total_liabilities': 0,
                    'total_equity': 0,
                    'operating_cash_flow': 0,
                    'free_cash_flow': 0,
                }
                data_list.append(record)
            print(f"  stock_financial_analysis_indicator_em 获取成功，共 {len(data_list)} 条")
    except Exception as e:
        print(f"  stock_financial_analysis_indicator_em 获取失败: {e}")
    
    try:
        df_balance = ak.stock_balance_sheet_by_report_em(symbol=ak_code)
        if df_balance is not None and len(df_balance) > 0:
            for _, row in df_balance.iterrows():
                report_date = str(row.get('REPORT_DATE', ''))[:10]
                for record in data_list:
                    if report_date in record.get('report_period', ''):
                        total_assets_val = row.get('TOTAL_ASSETS')
                        record['total_assets'] = float(total_assets_val) / 100000000 if total_assets_val is not None else 0
                        
                        total_liabilities_val = row.get('TOTAL_LIABILITIES')
                        record['total_liabilities'] = float(total_liabilities_val) / 100000000 if total_liabilities_val is not None else 0
                        
                        total_equity_val = row.get('TOTAL_EQUITY')
                        record['total_equity'] = float(total_equity_val) / 100000000 if total_equity_val is not None else 0
                        
                        if record['total_equity'] > 0 and record['profit'] > 0:
                            record['roa'] = (record['profit'] / record['total_assets']) * 100 if record['total_assets'] > 0 else 0
                        break
            print(f"  stock_balance_sheet_by_report_em 获取成功")
    except Exception as e:
        print(f"  stock_balance_sheet_by_report_em 获取失败: {e}")
    
    try:
        df_cash = ak.stock_cash_flow_sheet_by_report_em(symbol=ak_code)
        if df_cash is not None and len(df_cash) > 0:
            for _, row in df_cash.iterrows():
                report_date = str(row.get('REPORT_DATE', ''))[:10]
                for record in data_list:
                    if report_date in record.get('report_period', ''):
                        net_cash_operate = row.get('NETCASH_OPERATE')
                        record['operating_cash_flow'] = float(net_cash_operate) / 100000000 if net_cash_operate is not None else 0
                        break
            print(f"  stock_cash_flow_sheet_by_report_em 获取成功")
    except Exception as e:
        print(f"  stock_cash_flow_sheet_by_report_em 获取失败: {e}")
    
    for record in data_list:
        if np.isnan(record['roe_ttm']):
            record['roe_ttm'] = record['roe']
        
        if record['bps'] > 0:
            record['pb'] = record['pe'] * record['eps'] / record['bps'] if record['pe'] > 0 and record['eps'] > 0 else 0
        
        if record['total_equity'] > 0 and record['profit'] > 0:
            record['roe'] = (record['profit'] / record['total_equity']) * 100
    
    return data_list


def import_stock_basic_data(conn, code, name):
    table_name = get_table_name(code)
    market_code, market = extract_market_code(code)
    
    print(f"\n{'='*50}")
    print(f"处理: {code} - {name}")
    print(f"目标表: {table_name}")
    print(f"市场: {market}")
    
    if not create_table_if_not_exists(conn, table_name, code, name):
        return 0
    
    last_date = get_last_report_date(conn, table_name)
    print(f"已有数据最新日期: {last_date if last_date else '无'}")
    
    print(f"正在获取财务数据...")
    data_list = get_stock_financial_data(market_code, market)
    
    if not data_list:
        print(f"未获取到 {code} 的财务数据")
        return 0
    
    print(f"共获取到 {len(data_list)} 条财务数据")
    
    processed_list = []
    for record in data_list:
        report_period = record.get('report_period', '')
        if not report_period:
            continue
        
        date_str = ''
        if '一季报' in report_period:
            year = report_period[:4]
            date_str = f'{year}-03-31'
        elif '半年报' in report_period:
            year = report_period[:4]
            date_str = f'{year}-06-30'
        elif '三季报' in report_period:
            year = report_period[:4]
            date_str = f'{year}-09-30'
        elif '年报' in report_period:
            year = report_period[:4]
            date_str = f'{year}-12-31'
        elif len(report_period) >= 10 and '-' in report_period:
            date_str = report_period[:10]
        else:
            continue
        
        try:
            datetime.datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            continue
        
        if last_date and date_str <= last_date:
            continue
        
        processed_list.append((
            date_str,
            code,
            name,
            report_period,
            None if np.isnan(record.get('roe', 0)) else record.get('roe', 0),
            None if np.isnan(record.get('roe_ttm', 0)) else record.get('roe_ttm', 0),
            None if np.isnan(record.get('pe', 0)) else record.get('pe', 0),
            None if np.isnan(record.get('pe_ttm', 0)) else record.get('pe_ttm', 0),
            None if np.isnan(record.get('pb', 0)) else record.get('pb', 0),
            None if np.isnan(record.get('dividend_yield', 0)) else record.get('dividend_yield', 0),
            None if np.isnan(record.get('revenue', 0)) else record.get('revenue', 0),
            None if np.isnan(record.get('revenue_yoy', 0)) else record.get('revenue_yoy', 0),
            None if np.isnan(record.get('profit', 0)) else record.get('profit', 0),
            None if np.isnan(record.get('profit_yoy', 0)) else record.get('profit_yoy', 0),
            None if np.isnan(record.get('eps', 0)) else record.get('eps', 0),
            None if np.isnan(record.get('eps_ttm', 0)) else record.get('eps_ttm', 0),
            None if np.isnan(record.get('bps', 0)) else record.get('bps', 0),
            None if np.isnan(record.get('gross_margin', 0)) else record.get('gross_margin', 0),
            None if np.isnan(record.get('net_margin', 0)) else record.get('net_margin', 0),
            None if np.isnan(record.get('debt_ratio', 0)) else record.get('debt_ratio', 0),
            None if np.isnan(record.get('current_ratio', 0)) else record.get('current_ratio', 0),
            None if np.isnan(record.get('quick_ratio', 0)) else record.get('quick_ratio', 0),
            None if np.isnan(record.get('operating_cash_flow', 0)) else record.get('operating_cash_flow', 0),
            None if np.isnan(record.get('free_cash_flow', 0)) else record.get('free_cash_flow', 0),
            None if np.isnan(record.get('total_assets', 0)) else record.get('total_assets', 0),
            None if np.isnan(record.get('total_liabilities', 0)) else record.get('total_liabilities', 0),
            None if np.isnan(record.get('total_equity', 0)) else record.get('total_equity', 0),
            None if np.isnan(record.get('roa', 0)) else record.get('roa', 0),
            None if np.isnan(record.get('roic', 0)) else record.get('roic', 0),
        ))
    
    if not processed_list:
        print("没有新增财务数据需要导入")
        return 0
    
    print(f"准备导入 {len(processed_list)} 条新数据")
    
    insert_sql = f"""
    INSERT INTO `{table_name}` (
        date, stock_code, stock_name, report_period,
        roe, roe_ttm, pe, pe_ttm, pb, dividend_yield,
        revenue, revenue_yoy, profit, profit_yoy,
        eps, eps_ttm, bps, gross_margin, net_margin, debt_ratio,
        current_ratio, quick_ratio, operating_cash_flow, free_cash_flow,
        total_assets, total_liabilities, total_equity, roa, roic
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
              %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
              %s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        roe = VALUES(roe),
        roe_ttm = VALUES(roe_ttm),
        pe = VALUES(pe),
        pe_ttm = VALUES(pe_ttm),
        pb = VALUES(pb),
        dividend_yield = VALUES(dividend_yield),
        revenue = VALUES(revenue),
        revenue_yoy = VALUES(revenue_yoy),
        profit = VALUES(profit),
        profit_yoy = VALUES(profit_yoy),
        eps = VALUES(eps),
        eps_ttm = VALUES(eps_ttm),
        bps = VALUES(bps),
        gross_margin = VALUES(gross_margin),
        net_margin = VALUES(net_margin),
        debt_ratio = VALUES(debt_ratio),
        current_ratio = VALUES(current_ratio),
        quick_ratio = VALUES(quick_ratio),
        operating_cash_flow = VALUES(operating_cash_flow),
        free_cash_flow = VALUES(free_cash_flow),
        total_assets = VALUES(total_assets),
        total_liabilities = VALUES(total_liabilities),
        total_equity = VALUES(total_equity),
        roa = VALUES(roa),
        roic = VALUES(roic),
        stock_name = VALUES(stock_name),
        update_time = CURRENT_TIMESTAMP
    """
    
    try:
        cursor = conn.cursor()
        cursor.executemany(insert_sql, processed_list)
        conn.commit()
        rows_inserted = cursor.rowcount
        cursor.close()
        print(f"成功导入 {rows_inserted} 条数据")
        return rows_inserted
    except Exception as e:
        conn.rollback()
        print(f"导入数据失败: {e}")
        return 0


def load_stock_list():
    if not os.path.exists(STOCK_LIST_FILE):
        print(f"未找到股票列表文件: {STOCK_LIST_FILE}")
        return []
    
    df = pd.read_csv(STOCK_LIST_FILE)
    if '代码' not in df.columns or '名称' not in df.columns:
        print("股票列表文件格式不正确，缺少'代码'或'名称'列")
        return []
    
    return df[['代码', '名称']].values.tolist()


def main():
    print("=" * 60)
    print("股票基本财务数据导入MySQL工具")
    print("=" * 60)
    print(f"股票列表文件: {STOCK_LIST_FILE}")
    print(f"数据库: {MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}/{MYSQL_CONFIG['database']}")
    print("数据来源: akshare")
    print("=" * 60)
    
    stock_list = load_stock_list()
    if not stock_list:
        print("无法加载股票列表，程序退出")
        return
    
    current_stock_codes = {code for code, name in stock_list}
    print(f"当前列表共加载 {len(stock_list)} 个股票")
    
    try:
        conn = get_mysql_connection()
        print("数据库连接成功\n")
        
        total_inserted = 0
        total_processed = 0
        
        for code, name in stock_list:
            total_processed += 1
            try:
                inserted = import_stock_basic_data(conn, code, name)
                total_inserted += inserted
            except Exception as e:
                print(f"处理 {code} {name} 时发生异常: {e}")
            finally:
                time.sleep(0.5)
        
        all_tables = get_all_stock_tables(conn)
        conn.close()
        
        existing_stock_codes = {table[6:] for table in all_tables if table.startswith('basic_')}
        removed_stocks = existing_stock_codes - current_stock_codes
        new_stocks = current_stock_codes - existing_stock_codes
        
        print("\n" + "=" * 60)
        print("处理完成!")
        print("=" * 60)
        print(f"总共处理: {total_processed} 个股票")
        print(f"总共导入: {total_inserted} 条数据")
        
        if new_stocks:
            print(f"\n本次新增的股票 ({len(new_stocks)} 个):")
            for code in sorted(new_stocks)[:10]:
                print(f"  - {code}")
            if len(new_stocks) > 10:
                print(f"  ... 还有 {len(new_stocks) - 10} 个")
        
        if removed_stocks:
            print(f"\n已从列表移除但数据库中保留历史数据的股票 ({len(removed_stocks)} 个):")
            for code in sorted(removed_stocks)[:10]:
                print(f"  - {code} (表: basic_{code})")
            if len(removed_stocks) > 10:
                print(f"  ... 还有 {len(removed_stocks) - 10} 个")
        
        print("\n" + "=" * 60)
        print("注意: 从列表中移除的股票不会删除数据库中的历史数据")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n执行失败: {e}")


if __name__ == '__main__':
    main()

import pandas as pd
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

try:
    import akshare as ak
except ImportError:
    ak = None

try:
    import baostock as bs
except ImportError:
    bs = None


ETF_MYSQL_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'ZZQ1996zzq@',
    'database': 'etf_daily',
    'charset': 'utf8mb4'
}

STOCK_MYSQL_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'ZZQ1996zzq@',
    'database': 'stock_daily',
    'charset': 'utf8mb4'
}

ETF_LIST_FILE = 'etf_core_list.csv'
STOCK_LIST_FILE = 'stock_A_list.csv'
ETF_START_DATE = '2025-01-01'
STOCK_START_DATE = '2026-01-01'


def get_mysql_connection(config):
    if MYSQL_DRIVER == 'pymysql':
        return pymysql.connect(
            host=config['host'],
            port=config['port'],
            user=config['user'],
            password=config['password'],
            database=config['database'],
            charset=config['charset']
        )
    elif MYSQL_DRIVER == 'mysql.connector':
        return mysql.connector.connect(
            host=config['host'],
            port=config['port'],
            user=config['user'],
            password=config['password'],
            database=config['database'],
            charset=config['charset']
        )


def _create_table_if_not_exists(conn, table_name, code, name, prefix):
    if prefix == 'etf':
        code_col = 'etf_code'
        name_col = 'etf_name'
        comment = 'ETF日线数据'
    else:
        code_col = 'stock_code'
        name_col = 'stock_name'
        comment = '股票日线数据'
    
    create_sql = f"""
    CREATE TABLE IF NOT EXISTS `{table_name}` (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        date DATE NOT NULL COMMENT '日期',
        open DECIMAL(10, 3) NOT NULL COMMENT '开盘价',
        close DECIMAL(10, 3) NOT NULL COMMENT '收盘价',
        high DECIMAL(10, 3) NOT NULL COMMENT '最高价',
        low DECIMAL(10, 3) NOT NULL COMMENT '最低价',
        volume BIGINT COMMENT '成交量',
        amount DECIMAL(18, 2) COMMENT '成交额(元)',
        {code_col} VARCHAR(20) NOT NULL COMMENT '{comment}-代码',
        {name_col} VARCHAR(100) COMMENT '{comment}-名称',
        create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
        update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
        UNIQUE KEY uk_date (date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='{comment}-{name}';
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


def _get_last_date(conn, table_name):
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
        print(f"查询 {table_name} 最新日期失败: {e}")
        return None


def _get_all_tables(conn, prefix):
    cursor = conn.cursor()
    cursor.execute(f"SHOW TABLES LIKE '{prefix}_%'")
    tables = [row[0] for row in cursor.fetchall()]
    cursor.close()
    return tables


def _load_list(file_path):
    if not os.path.exists(file_path):
        print(f"未找到列表文件: {file_path}")
        return []
    
    df = pd.read_csv(file_path)
    if '代码' not in df.columns or '名称' not in df.columns:
        print(f"列表文件格式不正确，缺少'代码'或'名称'列: {file_path}")
        return []
    
    return df[['代码', '名称']].values.tolist()


def _get_etf_data(code, start_date):
    start_date_obj = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
    
    try:
        df = ak.fund_etf_hist_sina(symbol=code)
        if df is not None and len(df) > 0:
            df = df[df['date'] >= start_date_obj]
            return df, 'akshare_sina'
    except Exception as e:
        print(f"akshare新浪接口获取ETF数据失败: {e}")
    
    try:
        from Ashare import get_price
        today = datetime.datetime.now()
        days_diff = (today - datetime.datetime.strptime(start_date, '%Y-%m-%d')).days
        fetch_count = days_diff + 20
        df = get_price(code, count=fetch_count, frequency='1d')
        if df is not None and len(df) > 0:
            df = df[df.index >= start_date]
        return df, 'ashare'
    except Exception as e:
        print(f"Ashare获取ETF数据失败: {e}")
        return None, 'none'


def _get_stock_data(code, start_date):
    if code.startswith('sh'):
        bs_code = f'sh.{code[2:]}'
        market = 'sh'
    elif code.startswith('sz'):
        bs_code = f'sz.{code[2:]}'
        market = 'sz'
    elif code.startswith('bj'):
        print(f"baostock不支持北交所股票: {code}")
        return None, 'bj'
    else:
        print(f"不支持的股票代码格式: {code}")
        return None, 'unknown'
    
    end_date = datetime.datetime.now().strftime('%Y-%m-%d')
    
    rs = bs.query_history_k_data_plus(
        bs_code,
        'date,open,high,low,close,volume,amount',
        start_date=start_date,
        end_date=end_date,
        frequency='d',
        adjustflag='3'
    )
    
    if rs.error_code != '0':
        print(f"baostock查询失败: {rs.error_msg}")
        return None, 'baostock'
    
    data_list = []
    while rs.next():
        data_list.append(rs.get_row_data())
    
    if len(data_list) == 0:
        return None, 'baostock'
    
    df = pd.DataFrame(data_list, columns=rs.fields)
    return df, 'baostock'


def _import_data(conn, code, name, prefix, start_date, get_data_func):
    table_name = f'{prefix}_{code}'
    
    print(f"\n{'='*50}")
    print(f"处理: {code} - {name}")
    print(f"目标表: {table_name}")
    
    if not _create_table_if_not_exists(conn, table_name, code, name, prefix):
        return 0
    
    last_date = _get_last_date(conn, table_name)
    print(f"已有数据最新日期: {last_date if last_date else '无'}")
    
    if last_date:
        last_date_obj = datetime.datetime.strptime(last_date, '%Y-%m-%d')
        fetch_start_date = (last_date_obj + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        print(f"正在获取增量数据: {fetch_start_date} 至 今天")
        df, source = get_data_func(code, fetch_start_date)
    else:
        print(f"正在获取全量数据: {start_date} 至 今天")
        df, source = get_data_func(code, start_date)
    
    print(f"数据源: {source}")
    
    if source == 'bj':
        print(f"跳过北交所股票: {code}")
        return 0
    
    if df is None or len(df) == 0:
        print(f"未获取到 {code} 的数据")
        return 0
    
    print(f"共获取到 {len(df)} 条数据")
    
    data_list = []
    for idx, row in df.iterrows():
        if source == 'akshare_sina':
            date_val = row.get('date', idx)
            date_str = date_val.strftime('%Y-%m-%d') if hasattr(date_val, 'strftime') else str(date_val)[:10]
        else:
            date_val = row.get('date', idx) if isinstance(idx, int) else idx
            date_str = date_val.strftime('%Y-%m-%d') if hasattr(date_val, 'strftime') else str(date_val)[:10]
        
        open_val = float(row.get('open', 0))
        close_val = float(row.get('close', 0))
        high_val = float(row.get('high', 0))
        low_val = float(row.get('low', 0))
        volume_val = int(float(row.get('volume', 0)))
        amount_val = float(row.get('amount', 0))
        
        record = (date_str, open_val, close_val, high_val, low_val, volume_val, amount_val, code, name)
        data_list.append(record)
    
    if not data_list:
        print("没有新增数据需要导入")
        return 0
    
    print(f"准备导入 {len(data_list)} 条新数据")
    
    if prefix == 'etf':
        code_col = 'etf_code'
        name_col = 'etf_name'
    else:
        code_col = 'stock_code'
        name_col = 'stock_name'
    
    insert_sql = f"""
    INSERT INTO `{table_name}` (date, open, close, high, low, volume, amount, {code_col}, {name_col})
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        open = VALUES(open),
        close = VALUES(close),
        high = VALUES(high),
        low = VALUES(low),
        volume = VALUES(volume),
        amount = VALUES(amount),
        {name_col} = VALUES({name_col}),
        update_time = CURRENT_TIMESTAMP
    """
    
    try:
        cursor = conn.cursor()
        cursor.executemany(insert_sql, data_list)
        conn.commit()
        rows_inserted = cursor.rowcount
        cursor.close()
        print(f"成功导入 {rows_inserted} 条数据")
        return rows_inserted
    except Exception as e:
        conn.rollback()
        print(f"导入数据失败: {e}")
        return 0


def update_etf_daily_data():
    """
    更新ETF日线数据到MySQL数据库
    
    返回:
        dict: 包含统计信息的字典
            - total_processed: 处理的ETF总数
            - total_inserted: 导入的新数据条数
            - new_etfs: 本次新增的ETF代码列表
            - removed_etfs: 已从列表移除但保留数据的ETF代码列表
    """
    print("=" * 60)
    print("ETF日线数据导入MySQL工具")
    print("=" * 60)
    print(f"开始日期: {ETF_START_DATE}")
    print(f"ETF列表文件: {ETF_LIST_FILE}")
    print(f"数据库: {ETF_MYSQL_CONFIG['host']}:{ETF_MYSQL_CONFIG['port']}/{ETF_MYSQL_CONFIG['database']}")
    print("数据来源: akshare fund_etf_hist_sina (优先) / Ashare (备用)")
    print("=" * 60)
    
    etf_list = _load_list(ETF_LIST_FILE)
    if not etf_list:
        print("无法加载ETF列表，程序退出")
        return {'total_processed': 0, 'total_inserted': 0, 'new_etfs': [], 'removed_etfs': []}
    
    current_etf_codes = {code for code, name in etf_list}
    print(f"当前列表共加载 {len(etf_list)} 个ETF")
    
    try:
        conn = get_mysql_connection(ETF_MYSQL_CONFIG)
        print("数据库连接成功\n")
        
        total_inserted = 0
        total_processed = 0
        
        for code, name in etf_list:
            total_processed += 1
            try:
                inserted = _import_data(conn, code, name, 'etf', ETF_START_DATE, _get_etf_data)
                total_inserted += inserted
            except Exception as e:
                print(f"处理 {code} {name} 时发生异常: {e}")
            finally:
                time.sleep(0.3)
        
        all_tables = _get_all_tables(conn, 'etf')
        conn.close()
        
        existing_etf_codes = {table[4:] for table in all_tables if table.startswith('etf_')}
        removed_etfs = sorted(list(existing_etf_codes - current_etf_codes))
        new_etfs = sorted(list(current_etf_codes - existing_etf_codes))
        
        print("\n" + "=" * 60)
        print("处理完成!")
        print("=" * 60)
        print(f"总共处理: {total_processed} 个ETF")
        print(f"总共导入: {total_inserted} 条数据")
        
        if new_etfs:
            print(f"\n本次新增的ETF ({len(new_etfs)} 个):")
            for code in new_etfs:
                print(f"  - {code}")
        
        if removed_etfs:
            print(f"\n已从列表移除但数据库中保留历史数据的ETF ({len(removed_etfs)} 个):")
            for code in removed_etfs:
                print(f"  - {code} (表: etf_{code})")
        
        print("\n" + "=" * 60)
        print("注意: 从列表中移除的ETF不会删除数据库中的历史数据")
        print("=" * 60)
        
        return {
            'total_processed': total_processed,
            'total_inserted': total_inserted,
            'new_etfs': new_etfs,
            'removed_etfs': removed_etfs
        }
        
    except Exception as e:
        print(f"\n执行失败: {e}")
        return {'total_processed': 0, 'total_inserted': 0, 'new_etfs': [], 'removed_etfs': []}


def update_stock_daily_data():
    """
    更新股票日线数据到MySQL数据库
    
    返回:
        dict: 包含统计信息的字典
            - total_processed: 处理的股票总数
            - total_inserted: 导入的新数据条数
            - new_stocks: 本次新增的股票代码列表
            - removed_stocks: 已从列表移除但保留数据的股票代码列表
    """
    print("=" * 60)
    print("股票日线数据导入MySQL工具")
    print("=" * 60)
    print(f"开始日期: {STOCK_START_DATE}")
    print(f"股票列表文件: {STOCK_LIST_FILE}")
    print(f"数据库: {STOCK_MYSQL_CONFIG['host']}:{STOCK_MYSQL_CONFIG['port']}/{STOCK_MYSQL_CONFIG['database']}")
    print("数据来源: baostock")
    print("=" * 60)
    
    if bs is None:
        print("baostock未安装，请先安装: pip install baostock")
        return {'total_processed': 0, 'total_inserted': 0, 'new_stocks': [], 'removed_stocks': []}
    
    lg = bs.login()
    if lg.error_code != '0':
        print(f"baostock登录失败: {lg.error_msg}")
        return {'total_processed': 0, 'total_inserted': 0, 'new_stocks': [], 'removed_stocks': []}
    print("baostock登录成功\n")
    
    stock_list = _load_list(STOCK_LIST_FILE)
    if not stock_list:
        print("无法加载股票列表，程序退出")
        bs.logout()
        return {'total_processed': 0, 'total_inserted': 0, 'new_stocks': [], 'removed_stocks': []}
    
    current_stock_codes = {code for code, name in stock_list}
    print(f"当前列表共加载 {len(stock_list)} 个股票")
    
    try:
        conn = get_mysql_connection(STOCK_MYSQL_CONFIG)
        print("数据库连接成功\n")
        
        total_inserted = 0
        total_processed = 0
        
        for code, name in stock_list:
            total_processed += 1
            try:
                inserted = _import_data(conn, code, name, 'stock', STOCK_START_DATE, _get_stock_data)
                total_inserted += inserted
            except Exception as e:
                print(f"处理 {code} {name} 时发生异常: {e}")
            finally:
                time.sleep(0.3)
        
        all_tables = _get_all_tables(conn, 'stock')
        conn.close()
        
        existing_stock_codes = {table[6:] for table in all_tables if table.startswith('stock_')}
        removed_stocks = sorted(list(existing_stock_codes - current_stock_codes))
        new_stocks = sorted(list(current_stock_codes - existing_stock_codes))
        
        bs.logout()
        
        print("\n" + "=" * 60)
        print("处理完成!")
        print("=" * 60)
        print(f"总共处理: {total_processed} 个股票")
        print(f"总共导入: {total_inserted} 条数据")
        
        if new_stocks:
            print(f"\n本次新增的股票 ({len(new_stocks)} 个):")
            for code in new_stocks:
                print(f"  - {code}")
        
        if removed_stocks:
            print(f"\n已从列表移除但数据库中保留历史数据的股票 ({len(removed_stocks)} 个):")
            for code in removed_stocks:
                print(f"  - {code} (表: stock_{code})")
        
        print("\n" + "=" * 60)
        print("注意: 从列表中移除的股票不会删除数据库中的历史数据")
        print("=" * 60)
        
        return {
            'total_processed': total_processed,
            'total_inserted': total_inserted,
            'new_stocks': new_stocks,
            'removed_stocks': removed_stocks
        }
        
    except Exception as e:
        bs.logout()
        print(f"\n执行失败: {e}")
        return {'total_processed': 0, 'total_inserted': 0, 'new_stocks': [], 'removed_stocks': []}


if __name__ == '__main__':
    update_etf_daily_data()
    update_stock_daily_data()

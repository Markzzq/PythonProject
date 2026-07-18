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
        print("请先安装 MySQL 驱动: pip install pymysql 或 pip install mysql-connector-python")
        exit(1)

try:
    import baostock as bs
except ImportError:
    print("请先安装 baostock: pip install baostock")
    exit(1)


MYSQL_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'ZZQ1996zzq@',
    'database': 'stock_daily',
    'charset': 'utf8mb4'
}

STOCK_LIST_FILE = 'stock_A_list.csv'
START_DATE = '2026-01-01'


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
    return f'stock_{code}'


def get_all_stock_tables(conn):
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES LIKE 'stock_%'")
    tables = [row[0] for row in cursor.fetchall()]
    cursor.close()
    return tables


def convert_code(code):
    if code.startswith('sh'):
        return f'sh.{code[2:]}', 'sh'
    elif code.startswith('sz'):
        return f'sz.{code[2:]}', 'sz'
    elif code.startswith('bj'):
        return None, 'bj'
    return None, 'unknown'


def create_table_if_not_exists(conn, table_name, code, name):
    create_sql = f"""
    CREATE TABLE IF NOT EXISTS `{table_name}` (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        date DATE NOT NULL COMMENT '日期',
        open DECIMAL(10, 3) NOT NULL COMMENT '开盘价',
        close DECIMAL(10, 3) NOT NULL COMMENT '收盘价',
        high DECIMAL(10, 3) NOT NULL COMMENT '最高价',
        low DECIMAL(10, 3) NOT NULL COMMENT '最低价',
        volume BIGINT COMMENT '成交量(股)',
        amount DECIMAL(18, 2) COMMENT '成交额(元)',
        stock_code VARCHAR(20) NOT NULL COMMENT '股票代码',
        stock_name VARCHAR(100) COMMENT '股票名称',
        create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
        update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
        UNIQUE KEY uk_date (date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股票日线数据-{name}';
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


def get_last_date(conn, table_name):
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


def get_stock_data(code, start_date, end_date=None):
    bs_code, market = convert_code(code)
    
    if bs_code is None:
        if market == 'bj':
            print(f"baostock不支持北交所股票: {code}")
        else:
            print(f"不支持的股票代码格式: {code}")
        return None, market
    
    if end_date is None:
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


def import_stock_data(conn, code, name):
    table_name = get_table_name(code)
    
    print(f"\n{'='*50}")
    print(f"处理: {code} - {name}")
    print(f"目标表: {table_name}")
    
    if not create_table_if_not_exists(conn, table_name, code, name):
        return 0
    
    last_date = get_last_date(conn, table_name)
    print(f"已有数据最新日期: {last_date if last_date else '无'}")
    
    if last_date:
        last_date_obj = datetime.datetime.strptime(last_date, '%Y-%m-%d')
        start_date = (last_date_obj + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        print(f"正在获取增量数据: {start_date} 至 今天")
        df, source = get_stock_data(code, start_date)
    else:
        print(f"正在获取全量数据: {START_DATE} 至 今天")
        df, source = get_stock_data(code, START_DATE)
    
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
        date_str = str(row.get('date', ''))
        open_val = float(row.get('open', 0))
        close_val = float(row.get('close', 0))
        high_val = float(row.get('high', 0))
        low_val = float(row.get('low', 0))
        volume_val = int(float(row.get('volume', 0)))
        amount_val = float(row.get('amount', 0))
        
        record = (
            date_str,
            open_val,
            close_val,
            high_val,
            low_val,
            volume_val,
            amount_val,
            code,
            name
        )
        data_list.append(record)
    
    if not data_list:
        print("没有新增数据需要导入")
        return 0
    
    print(f"准备导入 {len(data_list)} 条新数据")
    
    insert_sql = f"""
    INSERT INTO `{table_name}` (date, open, close, high, low, volume, amount, stock_code, stock_name)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        open = VALUES(open),
        close = VALUES(close),
        high = VALUES(high),
        low = VALUES(low),
        volume = VALUES(volume),
        amount = VALUES(amount),
        stock_name = VALUES(stock_name),
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
    print("股票日线数据导入MySQL工具")
    print("=" * 60)
    print(f"开始日期: {START_DATE}")
    print(f"股票列表文件: {STOCK_LIST_FILE}")
    print(f"数据库: {MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}/{MYSQL_CONFIG['database']}")
    print("数据来源: baostock")
    print("=" * 60)
    
    lg = bs.login()
    if lg.error_code != '0':
        print(f"baostock登录失败: {lg.error_msg}")
        return
    print("baostock登录成功\n")
    
    stock_list = load_stock_list()
    if not stock_list:
        print("无法加载股票列表，程序退出")
        bs.logout()
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
                inserted = import_stock_data(conn, code, name)
                total_inserted += inserted
            except Exception as e:
                print(f"处理 {code} {name} 时发生异常: {e}")
            finally:
                time.sleep(0.3)
        
        all_tables = get_all_stock_tables(conn)
        conn.close()
        
        existing_stock_codes = {table[6:] for table in all_tables if table.startswith('stock_')}
        removed_stocks = existing_stock_codes - current_stock_codes
        new_stocks = current_stock_codes - existing_stock_codes
        
        bs.logout()
        
        print("\n" + "=" * 60)
        print("处理完成!")
        print("=" * 60)
        print(f"总共处理: {total_processed} 个股票")
        print(f"总共导入: {total_inserted} 条数据")
        
        if new_stocks:
            print(f"\n本次新增的股票 ({len(new_stocks)} 个):")
            for code in sorted(new_stocks):
                print(f"  - {code}")
        
        if removed_stocks:
            print(f"\n已从列表移除但数据库中保留历史数据的股票 ({len(removed_stocks)} 个):")
            for code in sorted(removed_stocks):
                print(f"  - {code} (表: stock_{code})")
        
        print("\n" + "=" * 60)
        print("注意: 从列表中移除的股票不会删除数据库中的历史数据")
        print("=" * 60)
        
    except Exception as e:
        bs.logout()
        print(f"\n执行失败: {e}")


if __name__ == '__main__':
    main()

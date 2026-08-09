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

# 批量提交大小
BATCH_COMMIT_SIZE = 50


def safe_float(val, default=0.0):
    if val in (None, '', 'nan', 'NaN'):
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


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
    else:
        raise RuntimeError("未安装MySQL驱动 (pymysql 或 mysql.connector)")


# ============================================================
# 预加载：一次性查出所有已有表和最新日期
# ============================================================
def _prefetch_table_info(conn, prefix):
    """
    返回 dict: {code: last_date_str | None (表不存在)}
    1 次 SHOW TABLES + N 次 MAX(date) 查询 → 但在同一连接上，延迟远小于分散调用
    """
    cursor = conn.cursor()
    cursor.execute(f"SHOW TABLES LIKE '{prefix}\\_%'")
    existing_tables = {row[0] for row in cursor.fetchall()}
    cursor.close()

    prefix_len = len(prefix) + 1  # e.g. 'etf_' → 4
    info = {}
    cursor = conn.cursor()
    for tbl in existing_tables:
        code = tbl[prefix_len:]
        cursor.execute(f"SELECT MAX(date) FROM `{tbl}`")
        row = cursor.fetchone()
        info[code] = row[0].strftime('%Y-%m-%d') if row and row[0] else None
    cursor.close()
    return info


# ============================================================
# 建表（批量确保）
# ============================================================
def _ensure_tables(conn, cursor, codes_to_create, prefix):
    """为不存在的表一次性建表"""
    if prefix == 'etf':
        code_col = 'etf_code'
        name_col = 'etf_name'
        comment = 'ETF日线数据'
    else:
        code_col = 'stock_code'
        name_col = 'stock_name'
        comment = '股票日线数据'

    for code in codes_to_create:
        table_name = f'{prefix}_{code}'
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
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='{comment}-{code}';
        """
        try:
            cursor.execute(create_sql)
        except Exception as e:
            print(f"创建表 {table_name} 失败: {e}")


# ============================================================
# 数据获取
# ============================================================
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
    elif code.startswith('sz'):
        bs_code = f'sz.{code[2:]}'
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


# ============================================================
# 数据导入（单表，不提交，复用cursor）
# ============================================================
def _import_one(conn, cursor, code, name, prefix, start_date, get_data_func, last_date):
    """
    导入单只的数据，返回插入行数。不执行 commit，由调用方批量提交。
    last_date: None=表不存在/空表/须全量, str=已有数据的最后日期
    """
    table_name = f'{prefix}_{code}'

    if last_date:
        last_date_obj = datetime.datetime.strptime(last_date, '%Y-%m-%d')
        fetch_start = (last_date_obj + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        df, source = get_data_func(code, fetch_start)
    else:
        df, source = get_data_func(code, start_date)

    if source == 'bj':
        return 0

    if df is None or len(df) == 0:
        return 0

    # 向量化批量转换数据（替代 iterrows + safe_float 逐行）
    if source == 'akshare_sina':
        dates = df['date'].apply(lambda x: x.strftime('%Y-%m-%d') if hasattr(x, 'strftime') else str(x)[:10])
    elif source == 'baostock':
        dates = df['date'].str[:10]
    else:
        dates = df.index.map(lambda x: x.strftime('%Y-%m-%d') if hasattr(x, 'strftime') else str(x)[:10])

    opens = pd.to_numeric(df['open'], errors='coerce').fillna(0)
    closes = pd.to_numeric(df['close'], errors='coerce').fillna(0)
    highs = pd.to_numeric(df['high'], errors='coerce').fillna(0)
    lows = pd.to_numeric(df['low'], errors='coerce').fillna(0)
    volumes = pd.to_numeric(df['volume'], errors='coerce').fillna(0).astype(int)
    amounts = pd.to_numeric(df['amount'], errors='coerce').fillna(0)

    # 组装 tuple 列表
    data_list = list(zip(dates, opens, closes, highs, lows, volumes, amounts))

    if not data_list:
        return 0

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

    # 每条 tuple 补上 code 和 name
    data_list = [(d, o, c, h, l, v, a, code, name) for d, o, c, h, l, v, a in data_list]

    try:
        cursor.executemany(insert_sql, data_list)
        return len(data_list)
    except Exception as e:
        print(f"导入数据失败 [{table_name}]: {e}")
        return 0


# ============================================================
# 主流程：ETF
# ============================================================
def _load_list(file_path):
    if not os.path.exists(file_path):
        print(f"未找到列表文件: {file_path}")
        return []
    df = pd.read_csv(file_path)
    if '代码' not in df.columns or '名称' not in df.columns:
        print(f"列表文件格式不正确，缺少'代码'或'名称'列: {file_path}")
        return []
    return df[['代码', '名称']].values.tolist()


def update_etf_daily_data():
    print(f"ETF日线数据导入 - 日期:{ETF_START_DATE}, 文件:{ETF_LIST_FILE}, "
          f"DB:{ETF_MYSQL_CONFIG['host']}/{ETF_MYSQL_CONFIG['database']}")

    etf_list = _load_list(ETF_LIST_FILE)
    if not etf_list:
        print("无法加载ETF列表，程序退出")
        return {'total_processed': 0, 'total_inserted': 0, 'new_etfs': [], 'removed_etfs': []}

    current_codes = {code for code, name in etf_list}
    print(f"当前列表共加载 {len(etf_list)} 个ETF")

    try:
        conn = get_mysql_connection(ETF_MYSQL_CONFIG)
        cursor = conn.cursor()
        print("数据库连接成功")

        # ① 预加载表信息（1 次 SHOW TABLES + N 次 MAX(date)）
        print("预加载表信息...")
        t0 = time.time()
        table_info = _prefetch_table_info(conn, 'etf')
        print(f"  已有 {len(table_info)} 张表, 耗时 {time.time()-t0:.1f}s")

        # ② 批量建表（不存在的表）
        codes_to_create = [code for code, name in etf_list if code not in table_info]
        if codes_to_create:
            print(f"  新建 {len(codes_to_create)} 张表...")
            _ensure_tables(conn, cursor, codes_to_create, 'etf')
            conn.commit()

        # ③ 遍历导入 + 批量提交
        total_inserted = 0
        total_processed = 0
        batch_count = 0

        print("开始导入数据...")
        for code, name in etf_list:
            total_processed += 1
            try:
                last_date = table_info.get(code)
                inserted = _import_one(conn, cursor, code, name, 'etf',
                                       ETF_START_DATE, _get_etf_data, last_date)
                total_inserted += inserted
                batch_count += 1
            except Exception as e:
                print(f"处理 {code} {name} 时发生异常: {e}")

            # 批量提交
            if batch_count >= BATCH_COMMIT_SIZE:
                conn.commit()
                batch_count = 0

        # 提交最后一批
        if batch_count > 0:
            conn.commit()

        cursor.close()

        # ④ 对比差异
        existing_codes = {c for c in table_info}
        removed_etfs = sorted(list(existing_codes - current_codes))
        new_etfs = sorted(list(current_codes - existing_codes))

        conn.close()

        print("\n" + "=" * 60)
        print("处理完成!")
        print("=" * 60)
        print(f"总共处理: {total_processed} 个ETF")
        print(f"总共导入: {total_inserted} 条数据")

        if new_etfs:
            print(f"\n本次新增的ETF ({len(new_etfs)} 个):")
            for c in new_etfs:
                print(f"  - {c}")
        if removed_etfs:
            print(f"\n已从列表移除但数据库中保留历史数据的ETF ({len(removed_etfs)} 个):")
            for c in removed_etfs:
                print(f"  - {c}")

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
        import traceback
        traceback.print_exc()
        return {'total_processed': 0, 'total_inserted': 0, 'new_etfs': [], 'removed_etfs': []}


# ============================================================
# 主流程：Stock
# ============================================================
def update_stock_daily_data():
    print(f"股票日线数据导入 - 日期:{STOCK_START_DATE}, 文件:{STOCK_LIST_FILE}, "
          f"DB:{STOCK_MYSQL_CONFIG['host']}/{STOCK_MYSQL_CONFIG['database']}")

    if bs is None:
        print("baostock未安装，请先安装: pip install baostock")
        return {'total_processed': 0, 'total_inserted': 0, 'new_stocks': [], 'removed_stocks': []}

    lg = bs.login()
    if lg.error_code != '0':
        print(f"baostock登录失败: {lg.error_msg}")
        return {'total_processed': 0, 'total_inserted': 0, 'new_stocks': [], 'removed_stocks': []}
    print("baostock登录成功")

    stock_list = _load_list(STOCK_LIST_FILE)
    if not stock_list:
        print("无法加载股票列表，程序退出")
        bs.logout()
        return {'total_processed': 0, 'total_inserted': 0, 'new_stocks': [], 'removed_stocks': []}

    current_codes = {code for code, name in stock_list}
    print(f"当前列表共加载 {len(stock_list)} 个股票")

    try:
        conn = get_mysql_connection(STOCK_MYSQL_CONFIG)
        cursor = conn.cursor()
        print("数据库连接成功")

        # ① 预加载表信息
        print("预加载表信息...")
        t0 = time.time()
        table_info = _prefetch_table_info(conn, 'stock')
        print(f"  已有 {len(table_info)} 张表, 耗时 {time.time()-t0:.1f}s")

        # ② 批量建表
        codes_to_create = [code for code, name in stock_list if code not in table_info]
        if codes_to_create:
            print(f"  新建 {len(codes_to_create)} 张表...")
            _ensure_tables(conn, cursor, codes_to_create, 'stock')
            conn.commit()

        # ③ 遍历导入 + 批量提交
        total_inserted = 0
        total_processed = 0
        batch_count = 0
        last_progress = 0

        print("开始导入数据...")
        t_start = time.time()

        for code, name in stock_list:
            total_processed += 1
            try:
                last_date = table_info.get(code)
                inserted = _import_one(conn, cursor, code, name, 'stock',
                                       STOCK_START_DATE, _get_stock_data, last_date)
                total_inserted += inserted
                batch_count += 1
            except Exception as e:
                print(f"处理 {code} {name} 时发生异常: {e}")

            # 进度提示（每 500 只打印一次）
            if total_processed - last_progress >= 500:
                elapsed = time.time() - t_start
                print(f"  进度: {total_processed}/{len(stock_list)}  "
                      f"已耗时 {elapsed:.0f}s  "
                      f"速率 {total_processed/elapsed:.1f} 只/秒")
                last_progress = total_processed

            # 批量提交
            if batch_count >= BATCH_COMMIT_SIZE:
                conn.commit()
                batch_count = 0

        if batch_count > 0:
            conn.commit()

        elapsed_total = time.time() - t_start
        print(f"  全部完成! 总耗时 {elapsed_total:.0f}s  "
              f"平均 {total_processed/elapsed_total:.1f} 只/秒")

        cursor.close()

        # ④ 对比差异
        existing_codes = {c for c in table_info}
        removed_stocks = sorted(list(existing_codes - current_codes))
        new_stocks = sorted(list(current_codes - existing_codes))

        bs.logout()
        conn.close()

        print("\n" + "=" * 60)
        print("处理完成!")
        print("=" * 60)
        print(f"总共处理: {total_processed} 个股票")
        print(f"总共导入: {total_inserted} 条数据")

        if new_stocks:
            print(f"\n本次新增的股票 ({len(new_stocks)} 个):")
            for c in new_stocks:
                print(f"  - {c}")
        if removed_stocks:
            print(f"\n已从列表移除但数据库中保留历史数据的股票 ({len(removed_stocks)} 个):")
            for c in removed_stocks:
                print(f"  - {c}")

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
        import traceback
        traceback.print_exc()
        return {'total_processed': 0, 'total_inserted': 0, 'new_stocks': [], 'removed_stocks': []}


if __name__ == '__main__':
    update_etf_daily_data()
    update_stock_daily_data()

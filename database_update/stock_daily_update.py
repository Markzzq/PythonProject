import pandas as pd
import datetime, time, logging, baostock, database_config
from sqlalchemy import text

baostock.login()

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/stock_daily_update.log', encoding='utf-8', mode='w'),
        logging.StreamHandler()
    ]
)

def are_all_stocks_updated(df):
    # 检查update_date是否为当天
    error_count = 0
    today = datetime.date.today()
    for index, row in df.iterrows():
        stock_code = row['stock_code']
        stock_name = row['stock_name']
        update_date = row['update_date']

        if pd.isna(update_date):
            error_msg = f"证券代码 {stock_code}({stock_name}) 更新日期为空!"
            logging.error(error_msg)
            error_count += 1
        elif update_date != today:
            error_msg = (f"证券代码 {stock_code}({stock_name}) 未更新! "
                         f"最后更新日期: {update_date}, 当前日期: {today}")
            logging.error(error_msg)
            error_count += 1
        else:
            logging.debug(f"证券代码 {stock_code} 已更新")


    # 汇总报告
    if error_count > 0:
        logging.error(f"检查完成，共发现 {error_count} 条未更新的证券信息")
        return False
    else:
        logging.info("所有证券信息均已更新至最新")
        return True


# 获取数据并遍历stock_code
def fetch_and_iterate_stock_codes():
    engine = database_config.get_db_engine()

    try:
        # 使用pandas直接读取为DataFrame
        query = "SELECT stock_full_code, stock_code, stock_name, update_date FROM stock_basic"
        start_time = time.time()
        all_stocks = pd.read_sql(query, engine)
        if all_stocks.empty:
            logging.warning("stock_basic表中没有数据")
            return 0

        end_time = time.time()
        logging.info(f"获取到的股票代码数量{len(all_stocks)}，耗时{round(end_time - start_time,2)}")

        if not are_all_stocks_updated(all_stocks):  # 检查update_date是否为当天
            return 0

        start_date = str(pd.to_datetime('today').date() - pd.Timedelta(days=85))
        end_date = str(pd.to_datetime('today').date()) # only update data today

        cnt = 1
        success_count = 0
        for index, row in all_stocks.iterrows():
            # if cnt >= 20: break
            data = fetch_data_from_baostock(row, start_date=start_date, end_date=end_date)
            if insert_data_to_db(data):
                success_count += 1
            logging.info(f'{row['stock_full_code']} | count = {cnt} / {len(all_stocks)}')
            cnt += 1

        return success_count

    except Exception as e:
        logging.error(f"数据库操作出错: {e}")
        return 0
    finally:
        engine.dispose()


def fetch_data_from_baostock(row, start_date, end_date):
    try:
        start_read_time = time.time()
        print(f'start_date={start_date}, end_date={end_date}')
        rs = baostock.query_history_k_data_plus(row['stock_full_code'],
                                          "date,code,open,high,low,close,volume,amount,adjustflag,turn",
                                          start_date=start_date, end_date=end_date,
                                          frequency="d", adjustflag="2")
        data_list = []
        while (rs.error_code == '0') & rs.next():
            # 获取一条记录，将记录合并在一起
            data_list.append(rs.get_row_data())
        df = pd.DataFrame(data_list, columns=rs.fields)
        end_read_time = time.time()
        logging.info(f"[{row['stock_full_code']}] Time：{round(end_read_time - start_read_time, 2)}")

        processed_df = pd.DataFrame({
            'busidate': pd.to_datetime(df['date']),
            'stock_full_code': row['stock_full_code'],  # 如 '000001.SZ'
            'stock_code': row['stock_code'],  # 如 '000001'
            'stock_name': row['stock_name'],
            'open': pd.to_numeric(df['open'], errors='coerce'),  # 转换为numeric
            'close': pd.to_numeric(df['close'], errors='coerce'),
            'high': pd.to_numeric(df['high'], errors='coerce'),
            'low': pd.to_numeric(df['low'], errors='coerce'),
            'volume': pd.to_numeric(df['volume'], errors='coerce'),
            'amount': pd.to_numeric(df['amount'], errors='coerce'),
            'adjustflag': pd.to_numeric(df['adjustflag'], errors='coerce'),
            'turn': pd.to_numeric(df['turn'], errors='coerce'),
            'source': "baostock API"
        })
        # print(processed_df)
        return processed_df
    except Exception as e:
        logging.error(f"请求API时出错: {row['stock_full_code']} | {e}")
        return None

def insert_data_to_db(data):
    if data is None:
        return False

    engine = database_config.get_db_engine()
    try:
        with engine.connect() as conn:
            temp_table = f"stock_daily_temp" # 创建临时表
            data.to_sql(
                name=temp_table,
                con=conn,
                if_exists='replace',
                index=False
            )

            # 执行UPSERT操作
            upsert_sql = f"""
                        INSERT INTO stock_daily (busidate,stock_full_code,stock_code,stock_name,
                            open, close, high, low, volume, amount, adjustflag, turn, source)
                        SELECT busidate,stock_full_code,stock_code,stock_name,
                            open, close, high, low, volume, amount, adjustflag, turn, source
                        FROM {temp_table} ON CONFLICT (busidate, stock_code) 
                        DO UPDATE SET
                            stock_full_code = EXCLUDED.stock_full_code,
                            stock_name = EXCLUDED.stock_name,
                            open = EXCLUDED.open,
                            close = EXCLUDED.close,
                            high = EXCLUDED.high,
                            low = EXCLUDED.low,
                            volume = EXCLUDED.volume,
                            amount = EXCLUDED.amount,
                            adjustflag = EXCLUDED.adjustflag,
                            turn = EXCLUDED.turn,
                            source = EXCLUDED.source
                        """
            conn.execute(text(upsert_sql))
            conn.commit()

            # 删除临时表
            conn.execute(text(f"DROP TABLE IF EXISTS {temp_table}"))
            conn.commit()

            logging.info(f"成功处理 {len(data)} 条记录 (插入/更新)")
            return True
    except Exception as e:
        logging.error(f"操作失败: {e}")
        return False
    finally:
        engine.dispose()


def main():
    start_total_time = time.time()
    stock_count = fetch_and_iterate_stock_codes()
    end_total_time = time.time()

    if stock_count > 0:
        logging.info(f"成功处理证券数量[{stock_count}][Time={round(end_total_time - start_total_time, 2)}]")
    else:
        logging.info(f"未能获取到证券基本信息数据[Time={round(end_total_time - start_total_time, 2)}]")
    baostock.logout()


if __name__ == "__main__":
    main()

import pandas as pd
import logging, time, database_config
from sqlalchemy import create_engine, text

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('./logs/stock_daily_process.log', mode='w'),
        logging.StreamHandler()
    ]
)

def fetch_stock_ohlc(engine, stock_full_code, start_date, end_date):
    """
    从stock_daily表提取指定股票代码在日期范围内的OHLC数据
    :param engine: 数据库驱动
    :param stock_full_code: 股票全代码 (如 '000001.SZ')
    :param start_date: 开始日期 (格式 'YYYY-MM-DD')
    :param end_date: 结束日期 (格式 'YYYY-MM-DD')
    :return: 包含open, close数据的DataFrame
    """
    # 构建SQL查询
    query = f"""
        SELECT busidate, open, close, amount
        FROM stock_daily
        WHERE stock_full_code = '{stock_full_code}'
        AND busidate BETWEEN '{start_date}' AND '{end_date}'
        ORDER BY busidate
    """

    try:
        # 执行查询并返回DataFrame
        df = pd.read_sql(query, engine)

        # 转换日期格式
        df['busidate'] = pd.to_datetime(df['busidate']).dt.date

        logging.debug(f"成功获取 {len(df)} 条日线数据")
        return df

    except Exception as e:
        logging.error(f"查询失败: {e}")
        return pd.DataFrame()  # 返回空DataFrame

def compute_and_process(stock_full_code, ohlc_data):
    if ohlc_data.empty:
        return False

    # 获取均线序列
    close_MA5 = pd.Series(ohlc_data['close']).rolling(5).mean().values
    close_MA10 = pd.Series(ohlc_data['close']).rolling(10).mean().values
    close_MA20 = pd.Series(ohlc_data['close']).rolling(20).mean().values
    # MA30 = pd.Series(ohlc_data['close']).rolling(30).mean().values
    # MA60 = pd.Series(ohlc_data['close']).rolling(60).mean().values

    N = ohlc_data.shape[0]

    if close_MA5[N-1] > close_MA10[N - 1] > close_MA20[N - 1] and \
            ohlc_data['amount'][N - 1] > ohlc_data['amount'][N - 2] > ohlc_data['amount'][N - 3]:
        logging.info(f"找到多头并列stockcode={stock_full_code}")

    return True


def process_daily_stocks():
    engine = database_config.get_db_engine()

    try:
        query = "SELECT stock_full_code, stock_code, stock_name, update_date FROM stock_basic"
        all_stocks = pd.read_sql(query, engine)
        if all_stocks.empty:
            logging.warning("stock_basic表中没有数据")
            return 0

        logging.debug(f"获取到的股票代码数量{len(all_stocks)}")

        start_date = str(pd.to_datetime('today').date() - pd.Timedelta(days=85))
        end_date = str(pd.to_datetime('today').date())  # only update data today

        cnt = 1
        success_count = 0
        latest_date = None
        for index, row in all_stocks.iterrows():
            # if cnt >= 30: break
            start_unit_time = time.time()
            ohlc_data = fetch_stock_ohlc(engine, row['stock_full_code'], start_date, end_date)

            if latest_date is None:
                latest_date = ohlc_data['busidate'].max()
                logging.info(f"Start processing and Latest date is {latest_date}")

            if compute_and_process(row['stock_full_code'], ohlc_data):
                success_count += 1
            end_unit_time = time.time()
            logging.info(f'{row['stock_full_code']} | {cnt} / {len(all_stocks)} | {round(end_unit_time - start_unit_time,2)}s')
            cnt += 1


    except Exception as e:
        logging.error(f"数据库操作出错: {e}")
    finally:
        engine.dispose()


# 使用示例
if __name__ == "__main__":

    start_time = time.time()
    process_daily_stocks()
    end_time = time.time()

    logging.info(f"Processing daily data successfully![Time={round(end_time - start_time,2)}]")





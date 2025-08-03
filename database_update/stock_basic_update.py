import pandas as pd
import datetime, time, re, logging, database_config
from sqlalchemy import create_engine, text


# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('stock_basic_update.log', encoding='utf-8', mode='w'),
        logging.StreamHandler()
    ]
)

def process_json_to_dataframe(df):
    if df is None or df.empty:
        return None

    pattern = re.compile(r'.*ST|\*|退市', re.IGNORECASE) # 过滤掉含有* 或 ST 或退市字样的股
    filtered_df = df[~df['mc'].str.contains(pattern)]
    # 数据转换与清洗
    processed_df = pd.DataFrame({
        'id': range(1, len(filtered_df) + 1), # 从1开始的自增ID
        'stock_full_code': filtered_df['dm'].str[7:]+'.'+filtered_df['dm'].str[:6],  # 如 'SZ.000001'
        # 'stock_full_code': filtered_df['dm'],     # 如 '000001.SZ'
        'stock_code': filtered_df['dm'].str[:6],  # 如 '000001'
        'stock_name': filtered_df['mc'],
        'market': filtered_df['dm'].apply(lambda x:
            '创业板' if x.startswith('300') else
            '科创板' if x.startswith('688') else
            '深圳' if x.endswith('.SZ') else
            '上海' if x.endswith('.SH') else
            '其他'
        ),
        'industry': "",
        'update_date': datetime.date.today()  # 使用当前日期作为更新日期
    })
    return processed_df


def save_stock_basic_to_db(df, table_name):
    if df is None or df.empty:
        logging.error("没有有效数据可保存")
        return False

    engine = database_config.get_db_engine()

    try:
        with engine.connect() as conn:
            logging.debug("richdb connection established successfully!")

            # 保存数据到数据库
            # 检查连接池状态
            temp_table_name = table_name + "_temp"
            conn.execute(text(f"DROP TABLE IF EXISTS {temp_table_name}"))
            conn.commit()

            start_time = time.time()
            df.to_sql(
                name=temp_table_name,
                con=engine,
                if_exists='replace',  # 如果表存在则替换
                index=False,
                method='multi',  # 批量插入提高性能
                chunksize=1000  # 分批写入
            )
            end_time = time.time()
            logging.debug(f"temp table created successfully!time={round((end_time - start_time), 2)}")
            conn.execute(text(f"TRUNCATE TABLE {table_name}"))
            conn.commit()

            start_time = time.time()
            upsert_sql = f"""
                INSERT INTO {table_name} (id, stock_full_code, stock_code, stock_name, market, industry, update_date)
                SELECT id, stock_full_code, stock_code, stock_name, market, industry, update_date FROM {temp_table_name};
            """
            conn.execute(text(upsert_sql))
            conn.commit()
            end_time = time.time()
            logging.info(f"Richdb basic stocks updated successfully!time={end_time - start_time}")
            return True
    except Exception as e:
        logging.error(f"connection failed! {e}")
        return False


def main():
    raw_data = database_config.fetch_data_from_api()

    if not raw_data.empty:
        # 处理数据
        data = process_json_to_dataframe(raw_data)

        if data is not None:
            # 保存到数据库
            save_stock_basic_to_db(data, "stock_basic")
        else:
            logging.error("数据处理失败")
    else:
        logging.error("未能从API获取数据")


if __name__ == "__main__":
    main()

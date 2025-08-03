import os, requests, json
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

# 创建数据库连接引擎
def get_db_engine():
    load_dotenv()  # 加载.env文件

    connection_url = f"postgresql://{os.getenv('DB_USERID')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_DATABASE')}"
    return create_engine(connection_url,
                           connect_args={
                               "password": os.getenv('DB_PASSWORD'),
                               'options': f'-c search_path={os.getenv('DB_SCHEMA')} -c statement_timeout=30000'
                           },
                           pool_size=5,
                           max_overflow=10,
                           pool_timeout=30,
                           pool_recycle=3600)

def fetch_data_from_api():
    load_dotenv()  # 加载.env文件

    API_URL = f"https://api.biyingapi.com/hslt/list/{os.getenv('API_KEY')}"
    try:
        response = requests.get(API_URL)
        response.raise_for_status()  # 检查请求是否成功
        return pd.DataFrame(response.json())
    except requests.exceptions.RequestException as e:
        print(f"请求BIYING API时出错: {e}")
        return None



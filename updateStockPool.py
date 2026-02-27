import numpy as np
import akshare as ak
import pandas as pd
import datetime
import time
import schedule
import utils

# 股市行情数据获取
from Ashare import *  # 股票数据库    https://github.com/mpquant/Ashare
from MyTT import *  # myTT麦语言工具函数指标库  https://github.com/mpquant/MyTT
import baostock as bs

START_DATE = '2025-05-13'
# END_DATE = '2025-07-23'
END_DATE = datetime.datetime.now().strftime('%Y-%m-%d')
C1 = 1.02
C2 = 1.01

def updateStockPool():
    return 0




if __name__ == '__main__':

    updateStockPool()


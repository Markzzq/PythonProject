#-*- coding:utf-8 -*-    --------------Ashare 股票行情数据双核心版( https://github.com/mpquant/Ashare ) 
import json,requests,datetime
import pandas as pd
import schedule

#腾讯日线
def get_price_day_tx(code, end_date='', count=10, frequency='1d'):     #日线获取  
    unit='week' if frequency in '1w' else 'month' if frequency in '1M' else 'day'     #判断日线，周线，月线
    if end_date:  end_date=end_date.strftime('%Y-%m-%d') if isinstance(end_date,datetime.date) else end_date.split(' ')[0]
    end_date='' if end_date==datetime.datetime.now().strftime('%Y-%m-%d') else end_date   #如果日期今天就变成空    
    URL=f'http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={code},{unit},,{end_date},{count},qfq'     
    st= json.loads(requests.get(URL).content);    ms='qfq'+unit;      stk=st['data'][code]   
    buf=stk[ms] if ms in stk else stk[unit]       #指数返回不是qfqday,是day
    df=pd.DataFrame(buf,columns=['time','open','close','high','low','volume'],dtype='float')     
    df.time=pd.to_datetime(df.time);    df.set_index(['time'], inplace=True);   df.index.name=''          #处理索引 
    return df

#腾讯分钟线
def get_price_min_tx(code, end_date=None, count=10, frequency='1d'):    #分钟线获取 
    ts=int(frequency[:-1]) if frequency[:-1].isdigit() else 1           #解析K线周期数
    if end_date: end_date=end_date.strftime('%Y-%m-%d') if isinstance(end_date,datetime.date) else end_date.split(' ')[0]        
    URL=f'http://ifzq.gtimg.cn/appstock/app/kline/mkline?param={code},m{ts},,{count}' 
    st= json.loads(requests.get(URL).content);       buf=st['data'][code]['m'+str(ts)] 
    df=pd.DataFrame(buf,columns=['time','open','close','high','low','volume','n1','n2'])   
    df=df[['time','open','close','high','low','volume']]    
    df[['open','close','high','low','volume']]=df[['open','close','high','low','volume']].astype('float')
    df.time=pd.to_datetime(df.time);   df.set_index(['time'], inplace=True);   df.index.name=''          #处理索引     
    df['close'][-1]=float(st['data'][code]['qt'][code][3])                #最新基金数据是3位的
    return df


#sina新浪全周期获取函数，分钟线 5m,15m,30m,60m  日线1d=240m   周线1w=1200m  1月=7200m
def get_price_sina(code, end_date='', count=10, frequency='60m'):    #新浪全周期获取函数    
    frequency=frequency.replace('1d','240m').replace('1w','1200m').replace('1M','7200m');   mcount=count
    ts=int(frequency[:-1]) if frequency[:-1].isdigit() else 1       #解析K线周期数
    if (end_date!='') & (frequency in ['240m','1200m','7200m']): 
        end_date=pd.to_datetime(end_date) if not isinstance(end_date,datetime.date) else end_date    #转换成datetime
        unit=4 if frequency=='1200m' else 29 if frequency=='7200m' else 1    #4,29多几个数据不影响速度
        count=count+(datetime.datetime.now()-end_date).days//unit            #结束时间到今天有多少天自然日(肯定 >交易日)        
        #print(code,end_date,count)    
    URL=f'http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={code}&scale={ts}&ma=5&datalen={count}' 
    dstr= json.loads(requests.get(URL).content);       
    #df=pd.DataFrame(dstr,columns=['day','open','high','low','close','volume'],dtype='float')
    #print(dstr)
    df= pd.DataFrame(dstr,columns=['day','open','high','low','close','volume'])
    df['open'] = df['open'].astype(float); df['high'] = df['high'].astype(float);                          #转换数据类型
    df['low'] = df['low'].astype(float);   df['close'] = df['close'].astype(float);  df['volume'] = df['volume'].astype(float)    
    df.day=pd.to_datetime(df.day);    df.set_index(['day'], inplace=True);     df.index.name=''            #处理索引                 
    if (end_date!='') & (frequency in ['240m','1200m','7200m']): return df[df.index<=end_date][-mcount:]   #日线带结束时间先返回              
    return df

def get_price(code, end_date='',count=10, frequency='1d', fields=[]):        #对外暴露只有唯一函数，这样对用户才是最友好的  
    xcode= code.replace('.XSHG','').replace('.XSHE','')                      #证券代码编码兼容处理 
    xcode='sh'+xcode if ('XSHG' in code)  else  'sz'+xcode  if ('XSHE' in code)  else code     

    if  frequency in ['1d','1w','1M']:   #1d日线  1w周线  1M月线
         try:    return get_price_sina( xcode, end_date=end_date,count=count,frequency=frequency)   #主力
         except: return get_price_day_tx(xcode,end_date=end_date,count=count,frequency=frequency)   #备用                    
    
    if  frequency in ['1m','5m','15m','30m','60m']:  #分钟线 ,1m只有腾讯接口  5分钟5m   60分钟60m
         if frequency in '1m': return get_price_min_tx(xcode,end_date=end_date,count=count,frequency=frequency)
         try:    return get_price_sina(  xcode,end_date=end_date,count=count,frequency=frequency)   #主力   
         except: return get_price_min_tx(xcode,end_date=end_date,count=count,frequency=frequency)   #备用


# 实时读取日内分时数据
def task():
    df_stock_list = pd.read_csv('stock_zh_list.csv')
    df_stock = df_stock_list[['代码', '名称']][266:350]

    for row_index, row in df_stock.iterrows():
        try:
            row_code = row['代码']  # 是因为抓到的数据带了字母 只取数字
            row_name = row['名称']

            df = get_price(row_code, frequency='5m', count=20)  # 支持'1m','5m','15m','30m','60m'

            # 因子1 5分钟涨跌数据
            if row['5分钟涨跌'] > 1:
                var1 = True
            else:
                var1 = False

            # 因子2 换手率突破5%
            if row['换手率'] > 5:
                var2 = True
            else:
                var2 = False

            # 因子3 涨跌幅
            if row['涨跌幅'] > 3:
                var3 = True
            else:
                var3 = False

            # 因子4 量比
            if row['量比'] > 1.2:
                var4 = True
            else:
                var4 = False

            varAll = var1 and var2 and var3 and var4

            if varAll == True:
                anyData = {'stock': row_code, 'name': row_name, '5分钟涨跌': row['5分钟涨跌'], '换手率': row['换手率'], '涨跌幅': row['涨跌幅'], '量比': row['量比']}
                df_index = row_index + 1
                dfResult.loc[df_index] = anyData
        except:
            continue

    print(dfResult)
    timestamp = datetime.datetime.now()
    filename = f"result_{timestamp}.csv"
    dfResult.to_csv(filename, encoding='utf-8-sig')


# 设定任务 读取实时股票数据 循环执行
schedule.every(1).minutes.do(task)


if __name__ == '__main__':
    # df=get_price('sh000001',frequency='1d',count=10)      #支持'1d'日, '1w'周, '1M'月
    # print('上证指数日线行情\n',df)
    #
    # df=get_price('000001.XSHG',frequency='15m',count=10)  #支持'1m','5m','15m','30m','60m'
    # print('上证指数分钟线\n',df)

    # anydata 是dictionary
    anyData = {'stock': '00', 'name': 'name_test', '5分钟涨跌': 'var1', '换手率': 'var2', '涨跌幅': 'var3', '量比': 'var4'}
    dfResult = pd.DataFrame(anyData, index=[0])

    # Run the scheduled tasks indefinitely
    while True:
        schedule.run_pending()




import numpy as np
import akshare as ak
import pandas as pd
import datetime
import time


START_DATE = '2025-06-13'
END_DATE = datetime.datetime.now().strftime('%Y-%m-%d')


## 获取概念板块指数历史数据（最近30天）
def getConceptIndexHistory():
    start_time = time.time()

    # 读取已有的同花顺概念列表
    concept_list_file = 'concept_ths_list.csv'
    print(f"正在读取概念列表文件: {concept_list_file}")
    
    try:
        concept_name_df = pd.read_csv(concept_list_file)
        print(f"成功读取 {len(concept_name_df)} 个概念")
        print(f"数据列名: {concept_name_df.columns.tolist()}")
    except Exception as e:



        print(f"读取概念列表失败: {e}")
        return

    # 创建历史指数数据表
    all_concept_index = pd.DataFrame()
    
    # 计算30天前的日期
    days_ago = datetime.datetime.now() - datetime.timedelta(days=30)
    start_date_30d = days_ago.strftime('%Y-%m-%d')
    print(f"\n获取最近30天数据 ({start_date_30d} 至 {END_DATE})")

    # 遍历概念列表，获取每个概念的历史指数
    success_count = 0
    fail_count = 0
    
    for idx, row in concept_name_df.iterrows():
        # 根据文件结构获取概念名称
        concept_name = row.get('概念名称', row.get('name', row.get('名称', '')))
        
        if not concept_name:
            continue
            
        print(f"\r正在获取概念 [{concept_name}] 的指数数据 ({idx+1}/{len(concept_name_df)})", end='')
        
        try:
            # 获取概念板块指数（同花顺）
            concept_index_df = ak.stock_board_concept_index_ths(symbol=concept_name)
            
            if concept_index_df.empty:
                fail_count += 1
                continue
            
            # 添加概念名称列
            concept_index_df['概念名称'] = concept_name
            
            # 筛选最近30天的数据
            if '日期' in concept_index_df.columns:
                concept_index_df['日期'] = pd.to_datetime(concept_index_df['日期'])
                concept_index_df = concept_index_df[concept_index_df['日期'] >= start_date_30d]
            elif 'date' in concept_index_df.columns:
                concept_index_df['date'] = pd.to_datetime(concept_index_df['date'])
                concept_index_df = concept_index_df[concept_index_df['date'] >= start_date_30d]
            
            if concept_index_df.empty:
                fail_count += 1
                continue
            
            # 合并到总表
            all_concept_index = pd.concat([all_concept_index, concept_index_df], ignore_index=True)
            success_count += 1
            
            # 为避免请求过快，添加延迟
            time.sleep(0.2)
            
        except Exception as e:
            fail_count += 1
            continue

    # 保存概念历史指数数据表
    index_file = f"{END_DATE}_概念板块指数_近30天.csv"
    all_concept_index.to_csv(index_file, encoding="utf-8-sig", index=False)
    print(f"\n\n概念板块指数数据已保存到 {index_file}")
    print(f"成功: {success_count} 个概念, 失败: {fail_count} 个概念")
    print(f"共包含 {len(all_concept_index)} 条记录")

    end_time = time.time()
    print(f"概念板块指数数据抓取完成，总耗时：{end_time - start_time}秒")
    
    return all_concept_index


## 获取概念资金流向历史数据（最近30天）
def getConceptFundFlowHistory():
    start_time = time.time()

    # 读取已有的同花顺概念列表
    concept_list_file = 'concept_ths_list.csv'
    print(f"正在读取概念列表文件: {concept_list_file}")
    
    try:
        concept_name_df = pd.read_csv(concept_list_file)
        print(f"成功读取 {len(concept_name_df)} 个概念")
    except Exception as e:
        print(f"读取概念列表失败: {e}")
        return

    # 创建资金流向历史数据表
    all_concept_fund_flow = pd.DataFrame()
    
    # 计算30天前的日期
    days_ago = datetime.datetime.now() - datetime.timedelta(days=30)
    start_date_30d = days_ago.strftime('%Y-%m-%d')
    print(f"\n获取最近30天资金流向数据 ({start_date_30d} 至 {END_DATE})")

    # 遍历概念列表，获取每个概念的资金流向历史
    success_count = 0
    fail_count = 0
    
    for idx, row in concept_name_df.iterrows():
        # 根据文件结构获取概念名称
        concept_name = row.get('概念名称', row.get('name', row.get('名称', '')))
        
        if not concept_name:
            continue
            
        print(f"\r正在获取概念 [{concept_name}] 的资金流向数据 ({idx+1}/{len(concept_name_df)})", end='')
        
        try:
            # 获取概念资金流向历史数据
            concept_fund_flow_df = ak.stock_concept_fund_flow_hist(symbol=concept_name)
            
            if concept_fund_flow_df.empty:
                fail_count += 1
                continue
            
            # 添加概念名称列
            concept_fund_flow_df['概念名称'] = concept_name
            
            # 筛选最近30天的数据
            if '日期' in concept_fund_flow_df.columns:
                concept_fund_flow_df['日期'] = pd.to_datetime(concept_fund_flow_df['日期'])
                concept_fund_flow_df = concept_fund_flow_df[concept_fund_flow_df['日期'] >= start_date_30d]
            elif 'date' in concept_fund_flow_df.columns:
                concept_fund_flow_df['date'] = pd.to_datetime(concept_fund_flow_df['date'])
                concept_fund_flow_df = concept_fund_flow_df[concept_fund_flow_df['date'] >= start_date_30d]
            
            if concept_fund_flow_df.empty:
                fail_count += 1
                continue
            
            # 合并到总表
            all_concept_fund_flow = pd.concat([all_concept_fund_flow, concept_fund_flow_df], ignore_index=True)
            success_count += 1
            
            # 为避免请求过快，添加延迟
            time.sleep(0.2)
            
        except Exception as e:
            fail_count += 1
            continue

    # 保存概念资金流向历史数据表
    fund_flow_file = f"{END_DATE}_概念资金流向_近30天.csv"
    all_concept_fund_flow.to_csv(fund_flow_file, encoding="utf-8-sig", index=False)
    print(f"\n\n概念资金流向数据已保存到 {fund_flow_file}")
    print(f"成功: {success_count} 个概念, 失败: {fail_count} 个概念")
    print(f"共包含 {len(all_concept_fund_flow)} 条记录")

    end_time = time.time()
    print(f"概念资金流向数据抓取完成，总耗时：{end_time - start_time}秒")
    
    return all_concept_fund_flow


if __name__ == '__main__':
    # 获取概念板块指数历史数据（最近30天）
    getConceptIndexHistory()
    
    # 获取概念资金流向历史数据（最近30天）
    getConceptFundFlowHistory()

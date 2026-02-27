
# 多线程
import threading
import os

# 定义执行的线程
def run_script(script_name):
    os.system(f'python {script_name}')


if __name__ == "__main__":

    # python队列
    scripts = ['findStock.py', 'findETF.py']   # weekReview.py
    # 线程队列
    threads = []

    # 根据python名单添加到线程中
    for script in scripts:
        thread = threading.Thread(target=run_script, args=(script,))
        threads.append(thread)
        thread.start()

    # 等待线程执行
    for thread in threads:
        thread.join()

















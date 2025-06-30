
# 多线程
import threading
import os


def run_script(script_name):
    os.system(f'python {script_name}')


if __name__ == "__main__":

    scripts = ['dailyreview.py', 'findbottom.py']
    threads = []

    for script in scripts:

        thread = threading.Thread(target=run_script, args=(script,))
        threads.append(thread)
        thread.start()


    for thread in threads:
        thread.join()








if __name__ == "__main__":


    scripts = ['script1.py', 'script2.py', 'script3.py']















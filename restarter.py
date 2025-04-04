# 找到叫 guard.py 的进程，杀掉，一共有两个，找到大的那个，杀掉
import psutil
import os
import time
from datetime import datetime

last_check_date = None

while True:
    now = datetime.now()
    current_date = now.date()

    # 检查是否是新的一天且是0点
    if (last_check_date != current_date) and now.hour == 0:
        guard_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info['cmdline']
                if cmdline and 'guard.py' in ' '.join(cmdline):
                    guard_processes.append(proc.info['pid'])
            except:
                continue

        if len(guard_processes) >= 2:
            # 找到 PID 最大的进程
            largest_pid = max(guard_processes)
            try:
                os.kill(largest_pid, 9)
                print(f"Killed guard.py process with PID {largest_pid}")
            except OSError as e:
                print(f"Failed to kill process {largest_pid}: {e}")
        else:
            print(f"Found {len(guard_processes)} guard.py processes")

        last_check_date = current_date

    time.sleep(60)  # 每分钟检查一次

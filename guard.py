import os
import sys
import time
import signal
import logging
from logging.handlers import RotatingFileHandler

from main import main
import settings

def check_timeout_errors(log_file='bot.log', error_pattern='Timed out getting Updates: Pool timeout: All connections in the connection pool are occupied'):
    try:
        with open(log_file, 'r') as f:
            content = f.read()
            return content.count(error_pattern)
    except FileNotFoundError:
        return 0

def run_bot():
    timeout_check_interval = 60  # 每60秒检查一次日志
    last_check_time = time.time()
    
    while True:
        try:
            # Fork子进程
            pid = os.fork()

            if pid == 0:
                # 子进程
                try:
                    main()
                except Exception as e:
                    logging.exception("Bot crashed with error:")
                    sys.exit(1)
            else:
                # 父进程
                # 检查日志文件
                current_time = time.time()
                if current_time - last_check_time >= timeout_check_interval:
                    timeout_count = check_timeout_errors()
                    if timeout_count >= 3:
                        print(f"检测到{timeout_count}次超时错误，正在重启bot...")
                        os.kill(pid, signal.SIGTERM)
                        _, status = os.waitpid(pid, 0)
                        print("Restarting bot in 5 seconds...")
                        time.sleep(5)
                        continue
                    last_check_time = current_time

                # 等待子进程结束
                _, status = os.waitpid(pid, 0)
                if os.WIFSIGNALED(status):
                    print(f"Bot process terminated by signal {os.WTERMSIG(status)}")
                elif os.WIFEXITED(status):
                    print(f"Bot process exited with status {os.WEXITSTATUS(status)}")

                print("Restarting bot in 5 seconds...")
                time.sleep(5)

        except KeyboardInterrupt:
            print("Stopping bot...")
            if pid:
                try:
                    os.kill(pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
            sys.exit(0)

if __name__ == "__main__":
    # 配置日志
    if settings.DEBUG:
        level = logging.DEBUG
    else:
        level = logging.ERROR
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            RotatingFileHandler(
                'bot.log',
                maxBytes=20485760,  # 20MB
                backupCount=5      # Keep 5 backup files
            ),
            logging.StreamHandler()
        ]
    )

    run_bot()

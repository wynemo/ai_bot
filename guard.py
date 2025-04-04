import os
import sys
import time
import signal
import logging
from logging.handlers import RotatingFileHandler

from main import main
import settings

def run_bot():
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
                # 等待子进程结束
                _, status = os.waitpid(pid, 0)

                if os.WIFSIGNALED(status):
                    # 如果子进程被信号终止
                    print(f"Bot process terminated by signal {os.WTERMSIG(status)}")
                elif os.WIFEXITED(status):
                    # 如果子进程正常退出
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
        level = logging.INFO
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

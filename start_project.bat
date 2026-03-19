@echo off
title Guardian-Agent 2.0 一键启动器
echo [1/3] 正在启动后台服务 Redis...
:: 如果你已经将 Redis 注册为服务，可以删掉下面这一行
start /b "" "C:\Program Files\Redis\redis-server.exe"

echo [2/3] 激活虚拟环境 (.venv)...
:: 自动指向你截图中的 .venv 文件夹
set VENV_PATH=%~dp0.venv\Scripts\activate.bat
call %VENV_PATH%

echo [3/3] 正在启动 Streamlit 控制台...
:: 启动合并后的最终版代码
streamlit run agent_system_v2.py

pause
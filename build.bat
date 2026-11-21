@echo off
rem SPDX-License-Identifier: Apache-2.0
rem SPDX-FileCopyrightText: 2026 Desktiny Expansion Pack contributors
rem Đóng gói gói giao diện và plugin thành .zip trong dist\. Bấm đúp: chọn từ danh sách.
rem Hoặc: build.bat [nhan-su ky-so ...] [--host plugins.co-quan.vn]
setlocal
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"

set PY=
where py >nul 2>nul && set PY=py -3
if not defined PY where python >nul 2>nul && set PY=python
if not defined PY (
  echo Không tìm thấy Python 3.11 trở lên. Cài từ https://www.python.org/downloads/ rồi chạy lại.
  set CODE=1
  goto :end
)

rem Không ghi tên nào thì hiện danh sách để chọn; Enter = đóng gói tất cả.
if "%~1"=="" (%PY% scripts\dong_goi.py --chon) else (%PY% scripts\dong_goi.py %*)
set CODE=%ERRORLEVEL%
if "%CODE%"=="0" if "%~1"=="" start "" explorer "%~dp0dist"

:end
rem Bấm đúp từ Explorer thì giữ cửa sổ lại để đọc kết quả.
echo %cmdcmdline% | "%SystemRoot%\System32\find.exe" /i "%~0" >nul && pause
exit /b %CODE%

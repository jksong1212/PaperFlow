@echo off
cd /d "%~dp0"
@REM  set UV_PROJECT_ENVIRONMENT=C:\uv_envs\save_pw_data_v01
REM   run.bat                      -> last folder (or empty)
REM   run.bat D:\data\folder       -> open that folder
REM   run.bat D:\data\file.h5      -> open that file
uv run paperflow

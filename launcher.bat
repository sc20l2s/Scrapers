@echo off
setlocal enabledelayedexpansion

REM Activate the venv
call venv\Scripts\activate

echo.
echo ===============================
echo   Available Scraper Scripts
echo ===============================

REM # How many scraper scripts do we have?
set count=0
for %%f in (*.py) do (
    if /I not "%%f"=="launcher.bat" (
        set /a count+=1
        set "script[!count!]=%%f"
        echo   !count!^) %%f
    )
)

if %count%==0 (
    echo No scrapers found in this folder.
    pause
    exit /b
)

echo.
set /p choice=Choose a scraper to run [1-%count%]: 

if defined script[%choice%] (
    echo.
    echo Running !script[%choice%]!...
    python "!script[%choice%]!"
) else (
    echo Invalid choice.
)

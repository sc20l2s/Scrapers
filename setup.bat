@echo off
@echo Doing boring nerd shit...
python -m venv venv
call venv\Scripts\activate
pip install -r requirements.txt
echo.
echo Done. To run a scraper, use the launcher or run these commands:
echo     call venv\Scripts\activate
echo     python example_scraper.py
echo.
echo Let me know if you run into any issues
pause
@echo off
echo Starting QuantEdge Research Platform...
call .venv\Scripts\activate.bat
streamlit run src\dashboard\app.py
pause

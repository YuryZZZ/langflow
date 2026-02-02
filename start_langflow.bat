@echo off
echo Starting Langflow locally...
cd /d "C:\Users\yuryz\Documents\GitHub\Langflow"
python -m langflow run --host 0.0.0.0 --port 7860
pause
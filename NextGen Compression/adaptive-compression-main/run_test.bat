@echo off
set PYTHONPATH=.
"C:\Python313\python.exe" -m tests.full_verification > test_log.txt 2>&1
echo DONE > test_done.txt

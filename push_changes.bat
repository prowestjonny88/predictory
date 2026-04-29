@echo off
cd /d "C:\Users\Lau Wei Zhong\Documents\GitHub\predictory\predictory"

echo === Git Status ===
git status

echo.
echo === Staging changes ===
git add apps/api/planning/router.py
git add apps/api/db/models.py
git add apps/api/forecasting/engine.py
git add apps/api/services/
git add apps/api/tests/test_alerts_and_daily_plan_api.py

echo.
echo === Creating commit ===
git commit -m "Task 10: Implement recommendation decision endpoint with audit logging - Add POST endpoint for recommendation decisions - Create services/audit.py for decision logging - Update DB models and tests"

echo.
echo === Latest commit ===
git log --oneline -1

echo.
echo === Pushing to GitHub ===
git push origin main

echo.
echo === Done! ===
pause

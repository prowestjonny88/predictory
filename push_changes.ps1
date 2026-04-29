#!/usr/bin/env pwsh

cd "C:\Users\Lau Wei Zhong\Documents\GitHub\predictory\predictory"

# Check status
Write-Host "=== Git Status ===" -ForegroundColor Cyan
git status

# Stage all changes
Write-Host "`n=== Staging changes ===" -ForegroundColor Cyan
git add apps/api/planning/router.py
git add apps/api/db/models.py
git add apps/api/forecasting/engine.py
git add apps/api/services/
git add apps/api/tests/test_alerts_and_daily_plan_api.py

# Commit
Write-Host "`n=== Creating commit ===" -ForegroundColor Cyan
git commit -m "Task 10: Implement recommendation decision endpoint with audit logging

- Add POST /api/daily-plan/recommendations/{recommendation_id}/decision endpoint
  - Validates decision request (operator_action, final_prep, operator_reason)
  - Updates PrepPlanLine status (accepted/edited/rejected)
  - Logs decision audit event with forecast context
  
- Create services/audit.py with decision audit logging
  - log_decision_audit() writes to DecisionAuditEvent table
  - Records outlet_id, sku_id, daypart, and decision details
  
- Update DB models for DecisionAuditEvent and ModelRun tracking
- Enhance forecasting engine to track model_run_id and forecast_run_id
- Add regression test for recommendation decision endpoint

This completes Task 10: Recommendation Decision Recording workflow."

# Show the diff
Write-Host "`n=== Ready to push ===" -ForegroundColor Green
git log --oneline -1

# Push
Write-Host "`n=== Pushing to GitHub ===" -ForegroundColor Cyan
git push origin main

Write-Host "`n=== Done! ===" -ForegroundColor Green

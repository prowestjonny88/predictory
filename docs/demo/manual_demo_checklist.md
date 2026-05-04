# Manual Demo Checklist

Use this checklist after backend/frontend verification passes.

## Startup

- Backend health returns `status: ok` at `http://localhost:8000/health`.
- Frontend opens at `http://localhost:3000`.
- Root route redirects to `/daily-planning`.
- Sidebar shows only the demo-safe navigation path.

## Daily Planning

- Recommendation cards load without browser console errors.
- Forecast/model evidence is visible.
- Model badge shows accepted artifact metadata, including validation WAPE and validation window.
- Cards show grounded explanations rather than generic filler.
- p10/p50/p90 or uncertainty values match backend/demo data.

## Recommendation Drawer

- Drawer opens from a Daily Planning card.
- Explanation uses the selected outlet, SKU, daypart, forecast, prep quantity, and ingredient evidence.
- Ingredient impact/replenishment section is visible where available.
- No unsupported forecast, prep, or BOM numbers are invented.

## Manager Note

- Manager note parse returns a structured suggested adjustment.
- The UI shows that confirmation is required.
- No prep quantity changes before explicit confirmation.
- Confirming the adjustment updates matching prep lines and refreshes replenishment.

## Approval And Audit

- Edit requires a non-empty reason.
- Reject requires a non-empty reason.
- Approve/edit/reject actions return audit event IDs from the backend.
- Edited quantities remain visible after refresh.
- Replenishment reflects edited or applied manager-note quantities.

## Replenishment

- Replenishment page shows ingredient need, stock on hand, shortage, reorder quantity, urgency, and driving SKUs.
- Values are tied to the latest prep quantities, not hardcoded copy.

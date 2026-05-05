# Manual Demo Checklist

Use this checklist after backend/frontend verification passes.

## Startup

- Backend health returns `status: ok` at `http://localhost:8000/health`.
- Frontend opens at `http://localhost:3000`.
- Landing page opens at `http://localhost:3000`; final demo can start at Dashboard.
- Sidebar shows only Dashboard, Daily Planning, Forecast Evidence, Replenishment, and SKU Catalog.

## Dashboard

- Source badge says `backend` during rehearsal, or `demo fallback` only if the team has explicitly accepted fallback mode.
- Tomorrow readiness card shows forecast run, prep plan, replenishment, and approval status.
- Business impact row shows mismatch cost, stockout exposure, waste exposure, and pending actions.
- Top 3 exceptions appear with a single clear CTA to review Daily Planning.
- No mock sparklines, yearly trend charts, generic forecast charts, or standalone AI action panel are visible.

## Daily Planning

- Recommendation cards load without browser console errors.
- Forecast/model evidence is visible.
- Model badge shows source, live engine, offline artifact status, validation WAPE, and validation window.
- Cards show grounded explanations rather than generic filler.
- Low / Expected / High demand values match backend/demo data.
- No frontend-fabricated uncertainty or RM exposure appears.

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

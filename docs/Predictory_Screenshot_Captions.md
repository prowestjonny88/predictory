# Predictory Screenshot Capture Guide

Use this file when assembling screenshots for the final **technical-team submission**. Keep the same date selected across screens where possible, and use demo states that show visible actions or risks rather than empty tables.

## 1. Dashboard

**Target screen**
- `/dashboard`

**What the screenshot should contain**
- KPI cards visible
- recommended actions visible
- at-risk outlets visible if present
- at least one waste or stockout alert card visible

**Caption**
- **Executive Overview dashboard.** This screen gives bakery operators a fast summary of tomorrow's predicted sales, top actions, and operational risks in one place.

**Why it matters**
- shows that the implemented backend modules surface as a usable decision summary, not just raw data

## 2. Forecast

**Target screen**
- `/forecast`

**What the screenshot should contain**
- forecast lines table
- demand drivers panel expanded
- visible holiday or weather signal if available
- visible override section if an override is created

**Caption**
- **Forecast and demand drivers view.** Predictory forecasts demand by outlet and daypart while showing the contextual signals that influenced the recommendation.

**Why it matters**
- proves the system is explainable and context-aware

## 3. Prep Plan

**Target screen**
- `/prep-plan`

**What the screenshot should contain**
- recommended prep lines
- one edited line if possible
- visible approval status or approval button

**Caption**
- **Prep planning with human-in-the-loop approval.** Users can inspect, adjust, and approve the next-day production plan rather than relying on a black-box recommendation.

**Why it matters**
- demonstrates that the technical system supports human-in-the-loop operations rather than opaque automation

## 4. Replenishment

**Target screen**
- `/replenishment`

**What the screenshot should contain**
- ingredient rows
- urgency column visible
- reorder quantities visible

**Caption**
- **Ingredient replenishment recommendations.** Predictory translates prep requirements into ingredient-level reorder actions and urgency signals.

**Why it matters**
- shows the technical pipeline links forecasting to procurement execution

## 5. Risk Centre

**Target screen**
- `/risk-center`

**What the screenshot should contain**
- waste risk cards
- stockout risk cards
- any chart or imbalance summary visible

**Caption**
- **Proactive waste and stockout risk monitoring.** The risk centre surfaces likely operational failures before service begins, allowing earlier intervention.

**Why it matters**
- reinforces the SDG 12 waste-reduction narrative

## 6. AI Copilot

**Target screen**
- `/copilot`

**What the screenshot should contain**
- generated daily brief or action plan
- scenario section visible if possible

**Caption**
- **AI copilot decision support.** The copilot layer explains plans, summarizes the day ahead, and turns operational signals into readable actions.

**Why it matters**
- demonstrates explainability instead of generic "AI" branding

## 7. Scenario Planner

**Target screen**
- `/scenario-planner`

**What the screenshot should contain**
- selected preset or custom scenario text
- generated scenario result visible

**Caption**
- **Scenario planning for safe experimentation.** Users can test hypothetical changes and inspect how risks may shift before taking action in the real operation.

**Why it matters**
- shows decision support under uncertainty

## 8. Multilingual UI

**Target screen**
- any major page, ideally `/dashboard` or `/copilot`

**What the screenshot should contain**
- same page shown in either Bahasa Melayu or Simplified Chinese
- language switcher visible if possible

**Caption**
- **Multilingual experience for inclusive adoption.** Predictory supports English, Bahasa Melayu, and Simplified Chinese across the interface and copilot outputs.

**Why it matters**
- supports ASEAN inclusivity and broader usability

## Capture Rules

- use desktop browser view
- avoid browser tabs/bookmarks clutter where possible
- avoid visible terminal errors
- prefer populated states over empty states
- keep date selection consistent across screenshots
- capture high-contrast states that clearly show value, not just layout

## Final Assembly Note

When the screenshots are ready, insert them into the main report at the corresponding placeholder locations in [Predictory_Report.md](/c:/Users/JON/OneDrive/Documents/predictory/docs/Predictory_Report.md).

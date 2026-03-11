# PRD v1 — BakeWise

## Document status
Baseline PRD for 2-day hackathon build.

## Chosen defaults
- **Primary segment:** Bakery-cafe hybrid chains
- **Menu emphasis:** Fresh baked goods
- **Operating model:** Central kitchen produces core items; outlets finish and sell
- **Hero SKU:** Croissant
- **Product story:** Operational efficiency with waste reduction as the headline outcome
- **UI direction:** Modern startup SaaS

---

## 1. Product summary

**BakeWise** is an AI prep and replenishment copilot for **3–10 outlet bakery-cafe chains in Malaysia**.

It helps operators decide:
- what to prep tomorrow
- how much to send to each outlet
- what ingredients to reorder
- which SKUs are likely to be overproduced or stock out

BakeWise is **not** a POS, ERP, procurement marketplace, or generic inventory tracker.
It is a **decision layer** on top of existing systems.

### One-line positioning
**BakeWise tells bakery chains what to prep, what to replenish, and where waste will happen before it happens.**

### Differentiation
Most incumbents focus on recording transactions, stock levels, procurement steps, or generic reporting.
BakeWise focuses on **outlet/daypart prep decisions** for perishable bakery operations.

---

## 2. Problem statement

Multi-outlet bakery-cafe chains already use POS systems and basic inventory workflows, but daily prep and replenishment decisions are still mostly manual.

This causes:
- overproduction of slow-moving baked goods
- stockouts during morning and lunch peaks
- poor outlet-to-outlet allocation
- excessive ingredient purchasing
- wasted labor and oven capacity
- inconsistent freshness and customer experience

### Core problem
The business does not only need inventory visibility.
It needs **high-confidence daily prep decisions**.

### Why current tools fall short
Current tools usually answer:
- What was sold?
- What stock is left?
- Is stock low?

They do **not** answer the most operationally important question:

> How many units of each bakery item should each outlet prepare or receive for each time window tomorrow, and what should the central kitchen and purchasing team do about it today?

---

## 3. Product objective

### Primary objective
Reduce end-of-day waste in bakery-cafe chains by improving day-ahead prep and replenishment decisions.

### Secondary objectives
- reduce stockouts on fast-moving items
- improve outlet availability consistency
- reduce manual planning time
- improve ingredient purchasing discipline
- help central kitchen allocate production more accurately

### Success hypothesis
If bakery operators receive clear outlet/daypart prep recommendations and ingredient replenishment guidance, they will make fewer reactive decisions and reduce daily waste while maintaining availability.

---

## 4. Target customer

### Ideal customer profile
A Malaysia-based bakery-cafe chain with:
- 3–10 outlets
- recurring daily production
- fresh baked products with short freshness windows
- a central kitchen producing core items
- outlet-level finishing, baking, or display prep
- usable digital records from POS and basic inventory processes

### Primary buyer
- Founder / owner-operator
- Head of operations
- Operations manager

### Daily users
- Central kitchen manager
- Production planner
- Outlet manager
- Purchaser / inventory lead

### Segment intentionally excluded for MVP
- single-outlet bakeries
- fully offline businesses with no digital records
- large enterprise chains with heavy custom process requirements

---

## 5. Jobs to be done

### Primary JTBD
Help bakery-cafe operators decide what to prep, where to allocate it, and what to replenish for tomorrow.

### Supporting jobs
- forecast product demand by outlet and daypart
- convert demand forecast into prep quantities
- convert prep plan into ingredient requirements
- flag likely waste before production happens
- flag likely stockouts before peak service windows
- explain why recommendations changed

### Emotional jobs
- reduce operator anxiety around uncertain demand
- make production planning feel controlled and repeatable
- give managers confidence to override instinct with data

---

## 6. Primary use case

### Main user flow
Evening planning for the next day.

At the end of the day, the operations or central kitchen manager opens BakeWise and sees:
1. tomorrow's predicted demand by outlet and daypart
2. recommended prep quantities by SKU
3. ingredient replenishment recommendations
4. likely waste hotspots
5. likely stockout risks
6. suggested allocation from central kitchen to outlets

The manager can then:
- accept recommendations
- edit a few numbers
- mark the plan as approved
- share the production/replenishment plan with teams

---

## 7. MVP scope

### MVP promise
A bakery chain manager can use BakeWise each evening to generate a next-day prep and replenishment plan that is more accurate than historical averages alone.

### Must-have outputs
- outlet/daypart demand forecast
- prep recommendation by SKU and outlet
- ingredient replenishment recommendation
- stockout risk alert
- waste risk alert
- plain-language explanation for each recommendation

### Must-not-build in hackathon MVP
- live POS integrations
- full procurement workflows
- automated purchase orders
- full recipe costing suite
- CRM campaign automation
- staff scheduling
- supplier marketplace
- accounting features
- POS replacement

---

## 8. Functional requirements

### FR1. Outlet/daypart demand forecasting
The system shall forecast demand for selected bakery SKUs by:
- outlet
- date
- daypart

#### Default dayparts
- Morning: 7am–11am
- Midday: 11am–3pm
- Evening: 3pm–8pm

#### Example output
Outlet KLCC:
- Butter Croissant: 54 / 28 / 14
- Pain au Chocolat: 22 / 15 / 7
- Pandan Bun: 18 / 12 / 6

### FR2. Prep recommendation engine
The system shall recommend how many units of each item to prepare for the next day.

The recommendation should consider:
- forecast demand
- current ready stock
- freshness window
- prep lead time
- safety buffer
- historical waste patterns

#### Example
"Prep 88 butter croissants for KLCC tomorrow: 52 for morning, 24 for midday, 12 for evening."

### FR3. Central-kitchen allocation view
The system shall provide a planning view for central kitchen production and outlet allocation.

The view shall show:
- total required production for tomorrow
- allocation by outlet
- items that should be finished or topped up at outlet level
- imbalances across outlets

#### Example
"Central kitchen should produce 240 croissants total, distributed across 5 outlets based on forecasted morning demand."

### FR4. Ingredient replenishment recommendation
The system shall convert prep recommendations into ingredient needs.

The recommendation should use:
- recipe/BOM data
- current ingredient stock
- projected prep plan
- purchase history
- supplier lead-time assumptions

#### Example
"Reorder 10kg butter today before 4pm to support tomorrow's croissant and danish production plan."

### FR5. Waste risk alert
The system shall flag likely overprep / overstock situations before production begins.

#### Example alerts
- "Outlet Bangsar likely to overproduce croissants by 14% tomorrow evening."
- "Blueberry muffin demand has declined for 3 days; reduce prep by 10 units."

### FR6. Stockout risk alert
The system shall flag likely shortfalls in bestselling products or ingredients.

#### Example alerts
- "Morning croissant stockout risk at Outlet Mid Valley."
- "Milk inventory below safe coverage for tomorrow's drink-pastry combo demand."

### FR7. Explainability layer
Every recommendation shall include a human-readable reason.

#### Example
"Prep reduced because Wednesday evening demand has underperformed for two weeks and yesterday's waste exceeded normal levels."

### FR8. Recommendation acknowledgement
Users shall be able to:
- accept recommendation
- edit recommendation
- mark recommendation as approved

This keeps the system human-in-the-loop.

---

## 9. Non-functional requirements

### NFR1. Simplicity
A bakery operations manager should understand the main page within 30 seconds.

### NFR2. Explainability
Every forecast, alert, and recommendation should feel understandable, not black-box.

### NFR3. Actionability
Each screen should end with a decision or action.

### NFR4. Low-friction data onboarding
For the prototype, the system should support CSV/manual imports rather than requiring live integrations.

### NFR5. Demo-ready UX
The prototype should look polished enough for a pitch and demo video while remaining operationally credible.

---

## 10. Data inputs

### Required prototype data
- outlet master list
- SKU/product catalog
- historical sales by SKU, outlet, date, and time
- current stock by SKU and outlet
- ingredient inventory
- recipe/BOM mappings
- purchase history
- waste logs

### Core entities
- **Outlet**: ID, name, location, hours
- **Product/SKU**: ID, name, category, freshness window, prep lead time
- **Sales record**: timestamp, outlet, SKU, quantity sold
- **Inventory record**: outlet, SKU, on-hand quantity
- **Ingredient**: name, stock on hand, lead time, reorder threshold
- **Recipe/BOM**: SKU to ingredient quantities
- **Waste log**: date, outlet, SKU, wasted quantity, reason
- **Purchase record**: ingredient, order date, quantity, cost

---

## 11. Baseline intelligence logic

For hackathon purposes, the system does **not** need a custom-trained frontier model.
It needs a believable, explainable recommendation engine.

### Baseline demand forecast logic
For each SKU/outlet/daypart:
- weighted recent sales trend
- same-weekday pattern
- moving average with recent bias
- optional event override or manual demand adjustment

### Baseline prep logic
Prep quantity = forecast demand + safety buffer - available ready stock

### Baseline replenishment logic
Ingredient need = sum of recommended prep x recipe requirement - ingredient stock on hand

### Baseline waste logic
Flag high waste risk when:
- planned prep materially exceeds expected demand
- recent waste history on that SKU is elevated
- late-day demand is consistently weak

### Baseline stockout logic
Flag high stockout risk when:
- projected demand exceeds prep quantity or stock coverage
- bestsellers show low morning or midday coverage

This is enough for a credible prototype and demo.

---

## 12. AI framework direction

### What we should do now
Use a **hybrid system**:
1. deterministic forecasting/recommendation logic for reliability
2. LLM layer for explanations, summaries, scenario comparison, and agent workflows

### What we should not do now
- train a proprietary large model from scratch
- claim deep autonomous operations
- overbuild "agentic AI" before the core decision loop works

### Suitable AI layers for the baseline
#### AI Layer 1 — Forecast and recommendation engine
A rules + time-series logic layer that outputs forecast, prep, replenishment, waste risk, and stockout risk.

#### AI Layer 2 — Explanation copilot
An LLM converts those outputs into plain-language explanations and executive summaries.

#### AI Layer 3 — Scenario agent
An agent can answer what-if questions such as:
- "What if I cut croissant prep by 15% at Outlet A?"
- "What happens if butter delivery is delayed by one day?"

#### AI Layer 4 — Planning agent
An agent can generate a suggested next-day action plan:
- approve these prep numbers
- reorder these ingredients
- reduce these low-demand SKUs
- rebalance production between outlets

All of this should remain human-approved.

---

## 13. Agentic AI opportunities

### Agent 1. Daily planning agent
Reads forecast, inventory, BOM, and waste data to produce:
- tomorrow's prep plan
- reorder plan
- top risks
- recommended actions

### Agent 2. Anomaly investigation agent
When waste spikes or stockouts occur, explains likely causes such as:
- demand variance
- outlet underperformance
- over-prep bias
- delayed replenishment

### Agent 3. What-if simulation agent
Lets the user compare scenarios:
- prep less vs prep more
- shift stock between outlets
- change safety buffer
- respond to special event demand

### Agent 4. Data onboarding agent
Helps map messy CSV columns or SKU names into a consistent schema for onboarding.

### Agent 5. Manager brief agent
Generates a short morning or evening summary for owner/operators.

### Rule for all agents
Agents should recommend and explain, not act autonomously in the MVP.

---

## 14. Prototype screen plan

### Screen 1. Executive overview
Shows:
- tomorrow's total predicted sales
- waste risk score
- stockout risk score
- top 5 actions
- most at-risk outlets

### Screen 2. Outlet/daypart forecast
Shows:
- outlet selector
- daypart forecast cards
- SKU forecast table
- trend visuals
- reason tags

### Screen 3. Prep plan
Shows:
- recommended prep by SKU and outlet
- delta vs usual prep
- current stock
- accept/edit controls

### Screen 4. Replenishment plan
Shows:
- ingredient needs
- stock on hand
- reorder quantity
- urgency
- which SKUs are driving the reorder

### Screen 5. Risk and waste center
Shows:
- likely waste hotspots
- stockout alerts
- outlet imbalance
- suggested reductions or transfers

Optional Screen 6. What-if planner
Shows:
- scenario controls
- projected waste/stockout changes
- recommendation summary

---

## 15. Demo scenario

### Fictional customer
**Roti Lane Bakery**
- 5 outlets in Kuala Lumpur
- central kitchen produces dough and core baked items
- outlets finish selected products and manage display inventory

### Hero SKU
**Butter Croissant**

### Demo narrative
Roti Lane currently uses historical averages and manager intuition to decide tomorrow's prep. That leads to excess croissants at slower outlets and stockouts during the morning rush at stronger outlets. BakeWise forecasts demand by outlet and daypart, recommends exact prep levels, converts the prep plan into butter/flour needs, and warns where waste is likely before the next day begins.

---

## 16. Success metrics

### Primary KPI
- waste reduction percentage

### Secondary KPIs
- stockout reduction percentage
- planning time reduction
- prep variance reduction
- ingredient over-order reduction
- forecast accuracy improvement

### Demo / pitch framing
For the hackathon, present these as pilot targets or modeled outcomes, for example:
- 10%–20% lower waste
- 8%–15% fewer stockouts
- 50% less planning time

---

## 17. Risks and constraints

### Product risks
- messy or inconsistent data
- poor waste logging discipline
- users may distrust recommendations
- demand spikes may distort simple forecasts
- recommendation quality depends on data freshness

### Hackathon constraints
- limited time for full integrations
- no live production validation
- prototype must favor clarity and narrative strength

### Mitigation
- use clean mock data
- keep the logic explainable
- make every recommendation editable
- avoid overclaiming model sophistication

---

## 18. Roadmap after MVP

### Phase 2
- live POS/inventory integrations
- event/promo adjustments
- improved forecast confidence scoring
- automated reorder draft creation
- richer central kitchen scheduling support

### Phase 3
- CRM/promo triggers for slow-moving items
- cross-outlet inventory transfer optimization
- supplier delay simulation
- inventory-linked financing insights

---

## 19. Out-of-scope statement for judges and stakeholders

BakeWise does **not** replace existing systems.
It augments them by becoming the daily planning and decision layer for bakery operations.

---

## 20. Final product message

**Not inventory visibility. Inventory decisions.**

More specifically:

**BakeWise helps bakery chains forecast outlet/daypart demand, plan prep, replenish ingredients, and prevent waste before it happens.**


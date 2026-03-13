# Predictory: AI for Inclusive MSME Growth

**Team Name:** [Insert Team Name]  
**Project Name:** Predictory  

## Problem Statement
Micro, Small, and Medium Enterprises (MSMEs) are the backbone of the ASEAN economy, accounting for 97% of businesses and 85% of employment. However, a massive productivity and market access gap persists because the benefits of the digital economy are concentrated among larger corporations. 

Within the Food & Beverage sector—specifically bakery-cafes—this manifests as a total reliance on manual, intuition-based operations. Lacking access to enterprise-grade supply chain tools, these MSMEs suffer from frequent overproduction (leading to end-of-day food waste) and stockouts during peak hours (leading to lost revenue). They lack the predictive market analytics and digital capabilities needed to optimize their resources, holding them back from scaling and achieving true economic resilience.

## SDG Alignment
* **SDG 12: Responsible Consumption and Production** (Primary) – Directly targets bakery food waste reduction and optimized resource/ingredient usage.
* **SDG 8: Decent Work and Economic Growth** – Empowers traditional MSMEs to increase productivity and scale operations via digital capability upgrades.
* **SDG 9: Industry, Innovation, and Infrastructure** – Democratizes access to advanced AI-driven supply chain technology for small enterprises.

## Solution Overview
**Predictory** is an AI-assisted prep and replenishment copilot designed specifically for multi-outlet bakery-cafe chains. By providing an AI-driven ecosystem, Predictory democratizes access to enterprise-grade tools like predictive analytics and automated supply chain management. 

Instead of relying on guesswork, business owners can leverage the platform to process historical sales, operational data, and external signals (like local weather and holidays) into precise, automated, next-day actions. This bridges the digital capability gap, allowing offline or traditional MSMEs to thrive, make data-backed decisions, and scale efficiently across the region.

## Key Features
* **AI Demand Forecasting**: Accurately predicts expected demand down to the specific SKU, outlet, and daypart (morning, midday, evening).
* **Automated Prep & Replenishment Planning**: Automatically translates demand forecasts into next-day preparation quantities and ingredient replenishment orders.
* **Multilingual AI Copilot**: Makes AI accessible by synthesizing complex data into human-readable daily briefs, explanations, and actionable lists in English, Bahasa Melayu, and Simplified Chinese.
* **Proactive Risk Center**: Flags likely waste risks before production begins and highlights potential stockouts before peak service windows.
* **Scenario Planner**: Allows MSME owners to run "what-if" simulations (e.g., public holidays, promotions, bad weather) to see how changing variables will impact inventory and prep requirements.

## Technical Architecture
Predictory is built on a modern, scalable tech stack aimed at rapid delivery and maintainability:
* **Frontend**: Next.js 14, React 18, Tailwind CSS, TanStack Query (providing a fast, responsive, and multilingual UI accessible to any MSME owner).
* **Backend**: FastAPI (Python), SQLAlchemy 2.x, Alembic.
* **AI & Machine Learning**: LiteLLM and LangGraph orchestrating reasoning workflows with Gemini models. Deterministic modeling for standard forecasts seamlessly combined with GenAI for contextual reasoning.
* **Database**: PostgreSQL (Production) / SQLite (Local/Edge environments for businesses with limited connectivity).

## Project Impact
* **Economic Resilience**: Transforms MSME operational efficiency by converting supply chains from reactive to proactive, improving margins and overall profit.
* **Waste Reduction**: Drastically minimizes food and ingredient waste by aligning production tightly with real market demand, supporting sustainable business practices.
* **Digital Inclusion**: By offering a user-friendly, multilingual AI copilot, Predictory lowers the barrier to entry for digital transformation, ensuring traditional business owners are not left behind in the digital economy.
* **Scalability**: Equips small operations with the "big-enterprise functionality" they need to open new outlets confidently and scale regionally across ASEAN.
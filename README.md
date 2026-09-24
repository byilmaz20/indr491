# Steel Demand Forecasting & Raw-Material Allocation

> Industrial Engineering decision-support project combining demand forecasting and mathematical optimization for steel production planning.

Developed as an **INDR 491 Industrial Engineering Design Project** with **MMK Metalurji**.

The project answers two questions:

1. **What steel demand is likely to arrive next?**
2. **How should available HRC raw material be allocated across urgent, normal, and forecasted demand?**

The solution combines **time-series forecasting**, **data preprocessing**, and **Gurobi optimization** in one workflow.

---

## Project at a Glance

- ~**170,000 historical orders**
- ~**40,000 original product/SPEC combinations**
- ~**1,300 relevant SPEC groups**
- ~**5,000 HRC coils** in the evaluated inventory snapshot
- ~**2,000 pending orders**
- **4 forecasting methods** benchmarked
- **Gurobi multi-objective optimization**
- Full-scale optimization solved in about **80 seconds**

---

## Business Problem

MMK Metalurji produces customer-specific steel products from hot-rolled coil (**HRC**).

Orders vary mainly by **grade, width, and thickness**, and not every HRC can satisfy every order.

Planners must decide how limited raw material should be distributed between:

- urgent customer orders
- normal orders
- expected future demand

The manual planning process could take around **4–6 hours per cycle**.

This creates risks such as unused capacity, avoidable scrap, reactive re-planning, and inconsistent prioritization.

---

## Solution Architecture

```text
Historical Sales + Inventory + Orders
                ↓
        Data Preprocessing
                ↓
        Demand Forecasting
 SARIMAX / XGBoost / ESRNN / Croston
                ↓
       SPEC-Level Forecasts
                ↓
 Compatibility + Order Urgency
                ↓
      Gurobi Optimization
                ↓
   Excel Reports + Visualizations
```

> **Forecasting estimates what will be needed; optimization decides how scarce material should be used.**

---
## Data Preparation
The original catalog contained around **40,000 product/SPEC combinations**.
Products with less than **100 tons of cumulative demand** were filtered out.
This retained approximately **98% of total demand volume** while reducing the modeling scope to roughly **1,300 SPEC groups**.
The goal was to reduce complexity without losing most operationally important demand.
---
## Demand Forecasting
Four approaches were evaluated:
- **SARIMAX** — selected as the final forecasting foundation
- **XGBoost** — useful for non-linear patterns and demand spikes
- **ESRNN** — responsive to abrupt demand changes
- **Croston** — tested for intermittent demand
### Forecasting Results
The main business metric was **wMAPE**, because high-volume product groups matter more operationally.
| Model | wMAPE |
|---|---:|
| **SARIMAX** | **38.08%** |
| XGBoost | 44.03% |
| ESRNN | 51.18% |
| Croston | 88.33% |
SARIMAX was selected because it provided the best balance of **weighted accuracy, stability, interpretability, and downstream consistency**.
Reported aggregate SARIMAX metrics:
| Metric | Value |
|---|---:|
| MAE | 1,218.24 |
| MAPE | 16.62% |
| sMAPE | 127.09% |
| wMAPE | 38.08% |
| RMSE | 5,105.51 |
---
## Forecast Disaggregation
Forecasting every SPEC group directly can be unstable because many groups have sparse histories.
The project therefore:
1. forecasts at **Grade Group** level
2. calculates historical within-grade shares
3. distributes the forecast back to individual **SpecGroupId** values
This gives the optimizer granular demand estimates without sacrificing aggregate forecast stability.
---
## Raw-Material Allocation Optimization
The allocation model is implemented in `assignmentModel.py` and uses **Gurobi**.
The model follows three business priorities:
1. **Urgent orders**
2. **Normal orders**
3. **Forecast-based demand**
Lower-priority demand cannot improve at the expense of more urgent orders.
### Optimization Logic
`x_iju` = amount of HRC type `i` assigned to demand group `j` at urgency level `u`.
`y_ju` = unmet demand.
Core rules:
- total allocation cannot exceed HRC inventory
- only technically compatible HRC–product pairs are allowed
- fulfillment is tracked separately by urgency
Conceptually, the objective is:
```text
1. Minimize unmet urgent demand
2. Minimize unmet normal demand
3. Minimize unmet forecast demand
```
The implementation uses Gurobi's **multi-objective optimization** functionality.
---
## Scenario Testing
### 20% Raw-Material Shortage
Inventory was reduced by 20%. The model protected urgent orders first and reduced lower-priority fulfillment.
### Surge in Urgent Orders
Urgent demand was doubled. The optimizer shifted available material toward urgent orders.
### Forecast Uncertainty
Forecast demand was varied by approximately **±15%**. Assignments changed, but the priority structure remained stable.
---
## Performance
The full production-scale optimization instance was solved with **Gurobi 11.0.1** in approximately:
> **80 seconds on a standard mid-range computer**
This supports iterative planning and what-if analysis.
---
## Outputs
Example outputs:
```text
results/assignmentModelSummary.xlsx
results/hammaddeKullanım.xlsx
results/aciliyet_barplot.png
results/combined_met_unmet_piechart_bordered.png
results/assignment_network_force_layout.png
```
These summarize assigned tonnage, unmet demand, fulfillment by urgency, HRC utilization, and HRC-to-order relationships.
---
## Repository Structure
```text
indr491/
├── forecast_model/
├── preprocess/
├── results/
├── assignmentModel.py
├── XGBoost_Trial_V1.py
├── Hybrid_model_competition.ipynb
├── Data examination.ipynb
└── model.ipynb
```
---
## Technology Stack
`Python` · `pandas` · `numpy` · `statsmodels` · `xgboost` · `scikit-learn` · `gurobipy` · `matplotlib` · `networkx` · `openpyxl`
---
## Running the Project
```bash
git clone https://github.com/byilmaz20/indr491.git
cd indr491
python -m venv .venv
pip install pandas numpy matplotlib networkx scikit-learn statsmodels xgboost openpyxl gurobipy
python assignmentModel.py
```
A valid **Gurobi license** is required. Some input paths and files are company-specific.
---
## Current Limitations
- no live SAP integration
- no planner-facing dashboard
- historical/offline evaluation
- strict compatibility / zero-scrap policy in the evaluated version
- project-specific paths and data dependencies
---
## Roadmap
- SAP integration
- controlled-scrap optimization
- planner dashboard
- alerts for unmatched urgent orders
- rolling-horizon planning
- probabilistic forecasting
- automated model selection
- tests and CI/CD
---
## Team
**Begüm Taşyürek · Begüm Yılmaz · Beyza Leblebici · Can Koçak · Ceylin Çelik · Hanife Erin · Samet Biber**
Project report date: **10 June 2025**

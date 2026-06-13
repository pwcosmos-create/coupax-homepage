# Njob Optimization Pipeline - Status Log

> [!WARNING]
> **PROJECT STATUS UPDATE (2026-05-18)**
> User has explicitly decided to **STOP** working on njob-related tasks ("njob안해"). 
> All njob automation scripts and optimization tasks are currently suspended or discontinued.
> **CURRENT FOCUS:** The user is currently focusing **exclusively on ETF related tasks** ("etf관련만하고 있어").

## Project Goal
Automate the optimization of product categories on njobapp.com to align with 2026 Naver Smart Store standards.

## Current Working Context
- **RL Memory (`njob_rl_memory.json`)**: Contains learned keywords and their corresponding category paths and `seId` values.
- **Optimization Script (`njob_optimize_100.py`)**: Automates the "Product Edit" -> "AINain (AI Optimization)" -> "Save" flow on njobapp.com using Playwright.
- **Category Mapper (`njob_category_mapper.py`)**: Uses RL memory to predict categories for products and update memory based on new successful mappings.

## Last Known Status (2026-04-01 20:55)
- **RL Memory Stats**: 
  - Reward Count: 41
  - Penalty Count: 0
  - Last Updated: 2026-04-01
- **Recent Actions**:
  - Successfully logged into njobapp.com.
  - Performed bulk updates using Excel files (e.g., `njob_bulk_update_0401_2042.xlsx`).
  - `njob_optimize_100.py` is configured to process 100 items at a time using automated UI clicks.

## User Constraints
- **CRITICAL**: Do NOT change margins (마진변경 금지).
- Use local `njob_session.json` for persistent sessions.

## Pending Tasks
1. Continue automated optimization of the next batch of products.
2. Monitor RL feedback loop to ensure high accuracy.
3. Handle "Request-URI Too Long" errors (observed in browser history) when downloading Excel reports.

---
*Note: This file is used to sync work between Antigravity and Claude.*

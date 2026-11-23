"""Deterministic illustrative data; NOT plant benchmarks. Run from project root."""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data'
OUT.mkdir(exist_ok=True)
rng = np.random.default_rng(42)
dates = pd.date_range(end=pd.Timestamp('2026-11-15'), periods=90, freq='D')
records, feedstocks, finance, stocks = [], [], [], []
rice_stock, maize_stock, ethanol_stock, ddgs_stock, co2_stock = 1600., 1400., 180., 70., 20.
for i, dt in enumerate(dates):
    day = dt.date().isoformat()
    ethanol = round(float(rng.uniform(72, 99)), 2)
    rice_share = float(rng.uniform(.25,.75))
    grain = round(ethanol * 2.48, 3)  # illustrative blended grain requirement
    rice, maize = round(grain*rice_share,3), round(grain*(1-rice_share),3)
    ddgs, co2 = round(grain*.27,3), round(grain*.25,3)
    rice_receipt = 320. if i%3==0 else 0.
    maize_receipt = 320. if i%3==1 else 0.
    rice_stock += rice_receipt-rice
    maize_stock += maize_receipt-maize
    ethanol_dispatch = round(ethanol*float(rng.uniform(.85,1.04)),3)
    ddgs_dispatch = round(ddgs*.94,3)
    co2_dispatch = round(co2*.9,3)
    ethanol_stock += ethanol-ethanol_dispatch
    ddgs_stock += ddgs-ddgs_dispatch
    co2_stock += co2-co2_dispatch
    records.append(dict(date=day, plant_id=1, capacity_klpd=100, target_kl=95, ethanol_kl=ethanol, rice_mt=rice, maize_mt=maize, ddgs_mt=ddgs, co2_mt=co2, electricity_kwh=round(ethanol*float(rng.uniform(550,720))), steam_mt=round(ethanol*float(rng.uniform(2.3,3.2)),2), water_m3=round(ethanol*float(rng.uniform(7,11)),2), mode=['batch','continuous','hybrid'][i%3]))
    for name, qty in [('Broken rice',rice),('Maize',maize)]:
        feedstocks.append(dict(date=day, run_code=f'RUN-{i+1:04d}', material=name, quantity_mt=qty))
    for material, receipt, consumed, closing in [('Broken rice',rice_receipt,rice,rice_stock),('Maize',maize_receipt,maize,maize_stock)]:
        stocks.append(dict(date=day,material=material,uom='MT',receipt=receipt,consumed=consumed,closing=round(closing,3)))
    for material, output, dispatch, closing, uom in [('Ethanol',ethanol,ethanol_dispatch,ethanol_stock,'KL'),('DDGS',ddgs,ddgs_dispatch,ddgs_stock,'MT'),('CO2',co2,co2_dispatch,co2_stock,'MT')]:
        stocks.append(dict(date=day,material=material,uom=uom,receipt=output,consumed=dispatch,closing=round(closing,3)))
    entries = {'ethanol_sales':ethanol_dispatch*61000, 'byproduct_sales':ddgs_dispatch*11000+co2_dispatch*3500,'feedstock_cost':rice*22000+maize*21000,'utilities_cost':ethanol*6500,'labor_cost':130000,'maintenance_cost':70000,'other_cost':45000}
    for cat, amount in entries.items():
        finance.append(dict(date=day,category=cat,amount_inr=round(amount,2),source_system='SYNTHETIC',external_id=f'{day}-{cat}'))
for filename, rows in [('production_daily.csv',records),('feedstocks.csv',feedstocks),('stock_daily.csv',stocks),('finance_daily.csv',finance)]:
    pd.DataFrame(rows).to_csv(OUT/filename,index=False)
print(f'Generated {len(dates)} days of synthetic sample data in {OUT}')

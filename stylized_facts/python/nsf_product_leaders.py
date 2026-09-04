"""
SF-B done properly: CONDITIONAL ON PRODUCT, is the leading MNE exporter the same
group across countries? Controls for the fact that countries specialise in
different goods (which mechanically lowers unconditional overlap).

Unit: (parent group, country, HS6) foreign-MNE export value.
Leader of a (product, country) market = top MNE group by value.
Question: for products exported by >=2 LAC countries, does the SAME group lead
the product in multiple countries -- and how much export value does that cover?
"""
from __future__ import annotations
import sys, time
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import BASE_FILE, INT, EXCLUDED_ORIGINS, parquet_chunks  # noqa: E402

PPC = INT / "nsf_parent_prod_country.parquet"

def clean(s): return s.astype("string").str.strip().replace({"": pd.NA, ".": pd.NA})

if PPC.exists():
    print(">>> loading parent x product x country cache"); ppc = pd.read_parquet(PPC)
else:
    t0 = time.time(); parts = []
    cols = ["country_orig", "hs07_6d", "value_fob", "_merge_DNB_Orbis",
            "iso3_parent", "ent_name_par", "globalultimatebusinessname"]
    for i, ch in enumerate(parquet_chunks(BASE_FILE, cols, 1_000_000), 1):
        ch = ch[ch._merge_DNB_Orbis == 3]
        ch = ch[~ch.country_orig.isin(EXCLUDED_ORIGINS)]
        ip = clean(ch.iso3_parent)
        keep = ip.notna() & (ip != ch.country_orig)
        ch = ch[keep]
        if ch.empty: continue
        par = clean(ch.ent_name_par).fillna(clean(ch.globalultimatebusinessname)).str.upper().str.strip()
        sub = pd.DataFrame({"parent": par.values, "country": ch.country_orig.values,
                            "hs": ch.hs07_6d.astype(str).values, "val": ch.value_fob.abs().values})
        sub = sub[sub.parent.notna()]
        parts.append(sub.groupby(["parent", "country", "hs"], as_index=False).val.sum())
        print(f"    chunk {i}: {time.time()-t0:.0f}s")
    ppc = (pd.concat(parts, ignore_index=True)
             .groupby(["parent", "country", "hs"], as_index=False).val.sum())
    ppc.to_parquet(PPC, index=False)
    print(f"  rows: {len(ppc):,} ({time.time()-t0:.0f}s)")

TOT = ppc.val.sum()
print(f"parent x product x country rows: {len(ppc):,} | MNE export value ${TOT/1e9:.0f}bn")

# ---- leader of each (product, country) market ----
mkt = ppc.groupby(["hs", "country"]).agg(tot=("val", "sum")).reset_index()
lead = ppc.loc[ppc.groupby(["hs", "country"])["val"].idxmax()]  # top group per (hs,country)
lead = lead.rename(columns={"parent": "leader", "val": "leader_val"}).merge(mkt, on=["hs", "country"])
lead["leader_share"] = lead.leader_val / lead.tot
print(f"(product,country) MNE markets: {len(lead):,} | mean leader share {lead.leader_share.mean():.0%}")

# ---- products exported by MNEs in >=2 countries ----
nctry = lead.groupby("hs")["country"].transform("nunique")
lead["hs_nctry"] = nctry
multi = lead[lead.hs_nctry >= 2].copy()
val_multi = ppc.merge(multi[["hs"]].drop_duplicates(), on="hs").val.sum()
print(f"\nproducts in >=2 countries: {multi.hs.nunique():,} of {lead.hs.nunique():,} "
      f"| they are {val_multi/TOT:.0%} of MNE export value")

# for each (hs, leader): in how many countries does this group lead this product?
lc = multi.groupby(["hs", "leader"])["country"].nunique().rename("leader_nctry").reset_index()
multi = multi.merge(lc, on=["hs", "leader"])
multi["common_leader"] = multi.leader_nctry >= 2

# headline: share of MNE export value whose product-leader repeats across countries
#   (a) among leadership value in multi-country products
sc_lead = multi.loc[multi.common_leader, "leader_val"].sum() / multi["leader_val"].sum()
#   (b) among TOTAL market value in multi-country products
sc_tot = multi.loc[multi.common_leader, "tot"].sum() / multi["tot"].sum()
#   (c) as share of ALL MNE export value
sc_all = multi.loc[multi.common_leader, "leader_val"].sum() / TOT
print(f"\n=== within-product, cross-country leadership ===")
print(f"  leader repeats in >=2 countries (same product):")
print(f"     share of leader value (multi-ctry products): {sc_lead:.0%}")
print(f"     share of market value  (multi-ctry products): {sc_tot:.0%}")
print(f"     as share of ALL MNE export value:             {sc_all:.0%}")

# how many countries do repeating leaders span?
rep = lc[lc.leader_nctry >= 2].sort_values("leader_nctry", ascending=False)
print(f"  (hs,leader) pairs leading >=2 countries: {len(rep):,}")
print(f"  distribution of countries-led (among repeaters): "
      f"{dict(rep.leader_nctry.value_counts().sort_index())}")

# concentration of leadership: how many distinct groups are the leader across all markets?
print(f"\n=== leadership concentration (who are the leaders) ===")
lv = lead.groupby("leader")["leader_val"].sum().sort_values(ascending=False)
print(f"  distinct leaders across all (product,country) markets: {lead.leader.nunique():,}")
for k in (20, 50, 100):
    print(f"  top-{k} leaders control {lv.head(k).sum()/lv.sum():.0%} of all leadership value")

# examples of strong repeat-leaders (lead a product in the most countries)
print("\n=== top repeat-leaders (lead same product in most countries) ===")
ex = rep.merge(multi.groupby(["hs","leader"]).leader_val.sum().reset_index(), on=["hs","leader"])
ex = ex.sort_values(["leader_nctry","leader_val"], ascending=False).head(12)
for _, r in ex.iterrows():
    print(f"  {str(r.leader)[:32]:32s} HS{r.hs} leads {int(r.leader_nctry)} countries  ${r.leader_val/1e9:.1f}bn")
print("\n>>> nsf_product_leaders done.")

"""
wp_agro_v5_match.py  --  E11b (ix): matched controls for the entry of the first multinational
=============================================================================================

    WP_YEARS=2012-2018 python wp_agro_v5_match.py      -> output/wp_2012_2018/agro/v5/ev5_<A|B>_match.parquet

Coarsened exact matching, one stack per cohort t0 (Cengiz et al. 2019 with matched controls): treated cells of the cohort
and control cells (gvar = 0 under the treatment definition) are matched exactly on origin and on bins of pre-event local
exports (mean of t0 - 2 and t0 - 1: zero, then terciles of the positive values of the cohort) and pre-event local
exporters (0, 1, 2 to 3, 4 or more). Controls take the usual CEM weights. Each stack keeps t0 - 4 .. t0 + 4 within
2012-2018. OLS event study on the stacked sample with cell x stack and origin x year x stack fixed effects (destination x
year x stack added for origin x destination x product cells), weighted, clustered as in Stata (A by cell, B by origin
and destination pair).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

os.environ.setdefault("WP_HS17", "1")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import wp_common as W  # noqa: E402

V5 = W.WP_INT / "v5"
OUT = W.WP_OUT / "agro" / "v5"
OUTC = {"A": ["anyXL", "lnXL", "NL", "NEWL", "EXITL", "SURVL", "NEWDL"], "B": ["anyXL", "lnXL", "NL", "NEWL", "EXITL", "SURVL"]}
EV = ["ev_m4", "ev_m3", "ev_m2", "ev_0", "ev_1", "ev_2", "ev_3", "ev_4"]
TERM = dict(zip(EV, ["Tm4", "Tm3", "Tm2", "Tp0", "Tp1", "Tp2", "Tp3", "Tp4"]))


def nl_bin(v):
    return np.select([v <= 0, v <= 1, v <= 3], [0, 1, 2], 3)


def stacks(p: pd.DataFrame, g: str, dest: bool) -> tuple[pd.DataFrame, list[dict]]:
    p = p[p[g].notna()].copy()
    out, info = [], []
    for c in sorted(p.loc[p[g] > 0, g].unique()):
        c = int(c)
        s = p[(p[g] == c) | (p[g] == 0)].copy()
        pre = s[s["year"].isin([c - 2, c - 1])].groupby("cell").agg(xl=("XL", "mean"), nl=("NL", "mean"), orig=("country_orig", "first"))
        pos = pre.loc[pre["xl"] > 0, "xl"]
        cuts = pos.quantile([1 / 3, 2 / 3]).values if len(pos) > 3 else []
        pre["bx"] = np.where(pre["xl"] <= 0, 0, 1 + np.searchsorted(cuts, pre["xl"].values, side="right"))
        pre["bn"] = nl_bin(pre["nl"].values)
        tr = s.drop_duplicates("cell").set_index("cell")[g] > 0
        pre["tr"] = tr.reindex(pre.index)
        pre["stratum"] = pre["orig"] + "_" + pre["bx"].astype(str) + "_" + pre["bn"].astype(str)
        k = pre.groupby("stratum")["tr"].agg(nt="sum", n="size")
        k["nc"] = k["n"] - k["nt"]
        ok = k[(k["nt"] > 0) & (k["nc"] > 0)]
        pre = pre[pre["stratum"].isin(ok.index)]
        Nt, Nc = int(pre["tr"].sum()), int((~pre["tr"].astype(bool)).sum())
        if Nt == 0 or Nc == 0:
            continue
        w = np.where(pre["tr"], 1.0, (pre["stratum"].map(ok["nt"]) / pre["stratum"].map(ok["nc"])) * (Nc / Nt))
        pre["w"] = w
        s = s[s["cell"].isin(pre.index) & s["year"].between(c - 4, c + 4)].copy()
        s["w"] = s["cell"].map(pre["w"])
        s["stack"] = c
        rel = np.where(s[g] > 0, s["year"] - c, np.nan)
        s["ev_m4"] = ((rel <= -4) & (s[g] > 0)).astype(float)
        s["ev_m3"] = (rel == -3).astype(float)
        s["ev_m2"] = (rel == -2).astype(float)
        for kk in range(4):
            s[f"ev_{kk}"] = (rel == kk).astype(float)
        s["ev_4"] = ((rel >= 4) & (s[g] > 0)).astype(float)
        out.append(s)
        info.append({"sample": g, "cohort": c, "treated matched": Nt, "controls matched": Nc,
                     "treated in cohort": int(tr.sum()), "strata used": len(ok)})
    if not out:
        return pd.DataFrame(), info
    st = pd.concat(out, ignore_index=True)
    st["cs"] = st["cell"].astype(str) + "_" + st["stack"].astype(str)
    st["oys"] = st["country_orig"].astype(str) + "_" + st["year"].astype(str) + "_" + st["stack"].astype(str)
    if dest:
        st["dys"] = st["dest"].astype(str) + "_" + st["year"].astype(str) + "_" + st["stack"].astype(str)
    return st, info


def main() -> None:
    from scipy.stats import chi2, norm
    rows, infos = [], []
    for P in ("A", "B"):
        p = pd.read_parquet(V5 / f"ev5_{P}.parquet")
        for g in ("g_v4", "g_ps"):
            st, info = stacks(p, g, P == "B")
            infos += [dict(cellset=P, **i) for i in info]
            if st.empty:
                continue
            fe = "cs + oys" + (" + dys" if P == "B" else "")
            for y in OUTC[P]:
                d = st.dropna(subset=[y, "w"])
                try:
                    m = W.feols(f"{y} ~ {' + '.join(EV)} | {fe}", data=d, vcov={"CRV1": "clus"}, weights="w")
                except Exception as e:  # noqa: BLE001
                    rows.append(dict(cellset=P, block="match", sample=g, group="all", outcome=y, est="match", fe="EV2", term="none",
                                     status="error " + str(e)[:60]))
                    continue
                b, se = m.coef(), m.se()
                V = pd.DataFrame(np.asarray(m._vcov), index=b.index, columns=b.index)
                nt = int(d.loc[d[g] > 0, "cell"].nunique()); nc = int(d.loc[d[g] == 0, "cell"].nunique())
                base = dict(cellset=P, block="match", sample=g, group="all", outcome=y, est="match", fe="EV2", N=int(m._N),
                            ntreat=nt, ncontrol=nc, status="ok")
                for v in EV:
                    if v in b.index:
                        rows.append(dict(base, term=TERM[v], b=float(b[v]), se=float(se[v]), p=float(2 * norm.sf(abs(b[v] / se[v])))))
                pre = [v for v in ("ev_m4", "ev_m3", "ev_m2") if v in b.index]
                bb = b[pre].values; VV = V.loc[pre, pre].values
                wv = float(bb @ np.linalg.pinv(VV) @ bb)
                rows.append(dict(base, term="pre_test", b=np.nan, se=np.nan, p=float(chi2.sf(wv, len(pre)))))
                post = [v for v in ("ev_0", "ev_1", "ev_2", "ev_3", "ev_4") if v in b.index]
                a = np.full(len(post), 1 / len(post))
                est = float(a @ b[post].values); s = float(np.sqrt(a @ V.loc[post, post].values @ a))
                rows.append(dict(base, term="Post_avg", b=est, se=s, p=float(2 * norm.sf(abs(est / s)))))
                print(P, g, y, f"post {est:+.3f} ({s:.3f}) pre p {rows[-2]['p']:.3f} nt {nt} nc {nc}")
    pd.DataFrame(rows).to_parquet(OUT / "ev5_match.parquet", index=False)
    pd.DataFrame(infos).to_parquet(OUT / "ev5_match_info.parquet", index=False)


if __name__ == "__main__":
    main()

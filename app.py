"""
Vera Design Labs - Global Research Suite  (colourful edition)
Multi-tool research & mathematical modeling platform with Free/Pro gating.

Run:  streamlit run app.py

Every tool now has:
  * a simple introduction above each of its 4 plots
  * a LIVE result text under each plot (changes when sliders move)
  * "Upload My Data" tab: example sheet on screen + Excel template download,
    results table and a PDF report

HOW TO ADD A NEW TOOL (scales to 100+ tools):
  1. Write a model function  def m_my_tool(v): ... return plots, summary
     (plots = list of 4 plot-dicts, summary = dict of key numbers)
  2. Add one line to tool_access_control  ->  "Tool 12: My Tool": "Free" or "Pro"
  3. Add one entry to TOOL_REGISTRY       ->  num, model, params, category, audience, desc
"""

import hmac
import html
import io
import math
import textwrap
import warnings
from datetime import datetime

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
import sympy as sp
from matplotlib.backends.backend_pdf import PdfPages
from scipy import stats
from scipy.optimize import brentq, linprog
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

# ----------------------------------------------------------------------------
# 1. CENTRAL ACCESS CONFIGURATION  (edit values here: "Free" or "Pro")
# ----------------------------------------------------------------------------
tool_access_control = {
    # --- Learning Lab (students) ---
    "Tool 1: Mathematical Modeling": "Free",
    "Tool 3: Advanced Simulation": "Free",
    "Tool 4: Signal & Fourier Explorer": "Free",
    "Tool 5: Statistics & CLT Explorer": "Free",
    # --- Research Lab (researchers) ---
    "Tool 2: Equation Analysis": "Pro",
    "Tool 6: Data Fitting & Regression Lab": "Pro",
    "Tool 7: Uncertainty & Sensitivity Analyzer": "Pro",
    # --- Industry Lab (engineers, managers) ---
    "Tool 8: Power Factor & Energy Calculator": "Free",
    "Tool 9: Reliability & Failure Analysis": "Pro",
    "Tool 10: Engineering Economics (NPV/IRR)": "Pro",
    "Tool 11: Optimization Studio (LP)": "Pro",
}

# Razorpay placeholders (override via st.secrets["RAZORPAY_PAYMENT_LINK"])
DEFAULT_PAYMENT_LINK = "https://rzp.io/l/vera-design-labs-pro"  # sample placeholder
MAX_KEY_ATTEMPTS = 5
MAX_UPLOAD_ROWS = 50

st.set_page_config(
    page_title="Vera Design Labs - Global Research Suite",
    page_icon="🔬",
    layout="wide",
)

# ----------------------------------------------------------------------------
# 2. COLOURFUL THEME
# ----------------------------------------------------------------------------
st.markdown(
    """
<style>
.stApp {
    background:
      radial-gradient(900px 520px at 6% 0%,  rgba(168,85,247,.40), transparent 60%),
      radial-gradient(800px 520px at 96% 6%, rgba(34,211,238,.30), transparent 60%),
      radial-gradient(900px 640px at 50% 104%, rgba(244,114,182,.26), transparent 65%),
      linear-gradient(160deg, #0b0f2b 0%, #1a1448 48%, #0d2f4f 100%);
    background-attachment: fixed;
    color: #eef2ff;
}
[data-testid="stHeader"] { background: transparent; }
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(30,20,80,.92), rgba(8,40,70,.92));
    border-right: 1px solid rgba(167,139,250,.35);
}
.stApp h1 {
    background: linear-gradient(90deg,#22d3ee 0%,#a78bfa 35%,#f472b6 70%,#fbbf24 100%);
    -webkit-background-clip: text; background-clip: text;
    -webkit-text-fill-color: transparent; font-weight: 800;
}
.stApp h2, .stApp h3 { color: #c4b5fd; }
.stApp h4, .stApp h5 { color: #67e8f9; }
.stApp p, .stApp label, .stApp li { color: #eef2ff; }

/* metric cards */
[data-testid="stMetric"] {
    background: linear-gradient(135deg, rgba(255,255,255,.10), rgba(255,255,255,.03));
    border: 1px solid rgba(167,139,250,.40);
    border-radius: 14px; padding: 12px 16px;
    box-shadow: 0 8px 22px rgba(0,0,0,.28);
}
[data-testid="stMetricLabel"] p { color: #c4b5fd !important; }
[data-testid="stMetricValue"] { color: #67e8f9; }

/* tabs */
button[data-baseweb="tab"] { color: #cbd5ff; font-weight: 600; }
button[data-baseweb="tab"][aria-selected="true"] { color: #fbbf24; }
[data-baseweb="tab-highlight"] { background: linear-gradient(90deg,#22d3ee,#f472b6) !important; height: 3px; }

/* buttons */
.stButton > button, .stDownloadButton > button, [data-testid="stLinkButton"] a {
    background: linear-gradient(90deg,#7c3aed 0%,#06b6d4 100%);
    color: #fff !important; border: none; border-radius: 10px; font-weight: 600;
    box-shadow: 0 6px 16px rgba(124,58,237,.35);
}
.stButton > button:hover, .stDownloadButton > button:hover {
    filter: brightness(1.12); transform: translateY(-1px);
}

/* inputs */
div[data-baseweb="select"] > div, .stNumberInput input, .stTextInput input {
    background-color: rgba(255,255,255,.09) !important; color: #eef2ff !important;
    border-color: rgba(167,139,250,.45) !important;
}

/* custom boxes */
.tool-box {
    background: linear-gradient(135deg, rgba(124,58,237,.22), rgba(6,182,212,.16));
    border: 1px solid rgba(167,139,250,.45); border-radius: 16px;
    padding: 16px 22px; margin-bottom: 14px;
}
.badge-free { background:#10b981; color:#fff; padding:2px 9px; border-radius:6px; font-weight:700; font-size:11px; }
.badge-pro  { background:linear-gradient(90deg,#f59e0b,#ef4444); color:#fff; padding:2px 9px; border-radius:6px; font-weight:700; font-size:11px; }
.plot-title { font-weight: 700; color: #fbbf24; font-size: 1.02rem; margin-top: 6px; }
.intro-text { color: #c7d2fe; font-size: .85rem; margin-bottom: 4px; }
.live-text {
    background: linear-gradient(90deg, rgba(16,185,129,.20), rgba(16,185,129,.06));
    border-left: 4px solid #34d399; padding: 9px 13px; border-radius: 8px;
    font-size: .88rem; margin: 4px 0 22px 0; color: #eafff6;
}
</style>
""",
    unsafe_allow_html=True,
)

DARK = dict(fig="#12163a", ax="#12163a", txt="#e8eefc", grid="#33408a",
            c=["#22d3ee", "#f472b6", "#fbbf24", "#34d399", "#a78bfa", "#fb923c"], hl="#fde047")
LIGHT = dict(fig="#ffffff", ax="#f8faff", txt="#1a2238", grid="#d5dbe8",
             c=["#0891b2", "#db2777", "#d97706", "#059669", "#7c3aed", "#ea580c"], hl="#dc2626")


# ----------------------------------------------------------------------------
# Helpers (access control)
# ----------------------------------------------------------------------------
def get_secret(name: str, default: str) -> str:
    """Read from st.secrets safely (works even if no secrets.toml exists)."""
    try:
        return str(st.secrets.get(name, default))
    except Exception:
        return default


def verify_pro_key(entered: str) -> bool:
    """Constant-time comparison against the configured Pro key."""
    valid = get_secret("PRO_ACCESS_KEY", "")
    if not valid:  # no secret configured -> nobody gets Pro access
        return False
    return hmac.compare_digest(entered.encode("utf-8"), valid.encode("utf-8"))


def is_pro_unlocked() -> bool:
    return st.session_state.get("pro_unlocked", False)


# ----------------------------------------------------------------------------
# 3. GENERIC PLOT ENGINE
# ----------------------------------------------------------------------------
def style_ax(ax, pal):
    ax.set_facecolor(pal["ax"])
    for s in ax.spines.values():
        s.set_color(pal["grid"])
    ax.tick_params(colors=pal["txt"], labelsize=7.5)
    ax.xaxis.label.set_color(pal["txt"])
    ax.yaxis.label.set_color(pal["txt"])
    ax.grid(True, ls="--", alpha=0.35, color=pal["grid"])


def draw_plot(ax, p, pal):
    """p = dict(title, xlabel, ylabel, + any of: lines, hist, bars, hbars, scatter,
    paths, points, vlines, hlines, mask, fill, logx, logy, equal, solid)"""
    style_ax(ax, pal)
    cols = pal["c"]
    if "mask" in p:
        gx, gy, feas = p["mask"]
        ax.contourf(gx, gy, feas.astype(float), levels=[0.5, 1.5], colors=[cols[3]], alpha=0.25)
    if "hist" in p:
        ax.hist(p["hist"], bins=p.get("bins", 40), density=p.get("density", False),
                color=cols[0], alpha=0.8, edgecolor=pal["ax"])
    if "bars" in p:
        labs, vals = p["bars"]
        x = p.get("bar_x", list(range(len(vals))))
        colors = p.get("bar_colors") or [cols[i % len(cols)] for i in range(len(vals))]
        bars = ax.bar(x, vals, color=colors)
        if p.get("bar_labels", True):
            ax.bar_label(bars, fmt="%.1f", fontsize=7, color=pal["txt"])
        if labs:
            ax.set_xticks(x)
            ax.set_xticklabels(labs, fontsize=7)
    if "hbars" in p:
        labs, vals = p["hbars"]
        colors = p.get("bar_colors") or [cols[i % len(cols)] for i in range(len(vals))]
        bars = ax.barh([textwrap.fill(str(l), 14) for l in labs], vals, color=colors)
        ax.bar_label(bars, fmt="%.1f", fontsize=7, color=pal["txt"])
        ax.tick_params(axis="y", labelsize=6.5)
    if "paths" in p:
        px, arr = p["paths"]
        for i, row in enumerate(arr):
            ax.plot(px, row, lw=0.8, alpha=0.5, color=cols[i % len(cols)])
    for (x, y, lab, ci, sz) in p.get("scatter", []):
        ax.scatter(x, y, s=sz, color=cols[ci % len(cols)], label=lab, alpha=0.8, edgecolors="none")
    for i, (x, y, lab) in enumerate(p.get("lines", [])):
        solid = p.get("solid", False)
        ax.plot(x, y, color=cols[i % len(cols)], lw=2.3 if (i == 0 or solid) else 1.5,
                ls="-" if (i == 0 or solid) else "--", label=lab)
        if i == 0 and p.get("fill"):
            ax.fill_between(x, y, alpha=0.18, color=cols[0])
    for x, y, lab in p.get("points", []):
        ax.scatter([x], [y], s=70, color=pal["hl"], edgecolor=pal["txt"], zorder=6, label=lab)
    for x, lab in p.get("vlines", []):
        ax.axvline(x, color=pal["hl"], ls=":", lw=1.3, label=lab)
    for y, lab in p.get("hlines", []):
        ax.axhline(y, color=pal["hl"], ls=":", lw=1.3, label=lab)
    if p.get("logx"):
        ax.set_xscale("log")
    if p.get("logy"):
        ax.set_yscale("log")
    if p.get("equal"):
        ax.set_aspect("equal")
    if "xlim" in p:
        ax.set_xlim(*p["xlim"])
    if "ylim" in p:
        ax.set_ylim(*p["ylim"])
    ax.set_xlabel(p.get("xlabel", ""), fontsize=8)
    ax.set_ylabel(p.get("ylabel", ""), fontsize=8)
    ax.set_title(p["title"], fontsize=9, weight="bold", color=pal["txt"])
    h, _ = ax.get_legend_handles_labels()
    if h:
        ax.legend(fontsize=6.5, facecolor=pal["ax"], edgecolor=pal["grid"], labelcolor=pal["txt"])


def make_fig(p, pal=DARK, size=(6.4, 3.5)):
    fig, ax = plt.subplots(figsize=size)
    fig.patch.set_facecolor(pal["fig"])
    draw_plot(ax, p, pal)
    fig.tight_layout()
    return fig


def trapz(y, x):
    return float(np.sum((y[1:] + y[:-1]) * np.diff(x)) / 2)


def cumtrapz(y, x):
    return np.concatenate([[0.0], np.cumsum((y[1:] + y[:-1]) * np.diff(x) / 2)])


def P(key, label, lo, hi, default, step):
    """Parameter spec. All-int => integer slider, otherwise all-float."""
    if all(isinstance(z, int) and not isinstance(z, bool) for z in (lo, hi, default, step)):
        return (key, label, lo, hi, default, step)
    return (key, label, float(lo), float(hi), float(default), float(step))


# ----------------------------------------------------------------------------
# 4. TOOL MODELS  (each returns: list of 4 plot dicts, summary dict)
# ----------------------------------------------------------------------------
# ---- Tool 1: Mathematical modeling (logistic growth with harvesting) --------
def m_logistic(v):
    r, K, h, N0, T = v["r"], v["K"], v["h"], v["N0"], v["T"]
    rk4 = int(v["solver"]) == 1
    steps = 1000
    dt = T / steps
    f = lambda n: r * n * (1 - n / K) - h * n
    t = np.linspace(0, T, steps + 1)
    N = np.empty_like(t)
    N[0] = N0
    for i in range(steps):
        n = N[i]
        if rk4:
            k1 = f(n); k2 = f(n + 0.5 * dt * k1); k3 = f(n + 0.5 * dt * k2); k4 = f(n + dt * k3)
            N[i + 1] = n + dt * (k1 + 2 * k2 + 2 * k3 + k4) / 6
        else:
            N[i + 1] = n + dt * f(n)
    eq = max(K * (1 - h / r), 0.0)
    na = np.linspace(0, K * 1.1, 200)
    rate = f(na)
    ym = h * N
    cum = cumtrapz(ym, t)
    ha = np.linspace(0, 1, 100)
    eqh = np.maximum(K * (1 - ha / r), 0)
    msy_h, msy = r / 2, r * K / 4
    i = int(np.argmax(rate))
    collapse = " Harvest is at least the growth rate, so the population collapses." if h >= r else ""
    plots = [
        dict(title="Population over time", xlabel="Time", ylabel="Population",
             lines=[(t, N, "N(t)")], hlines=[(eq, "Equilibrium N*")], fill=True,
             intro="The solution of dN/dt = rN(1 - N/K) - hN. The dotted line is where the population settles.",
             text=f"Starting from {N0:,.0f}, the population reaches {N[-1]:,.0f} at t = {T} (peak {N.max():,.0f}); equilibrium N* = {eq:,.0f}.{collapse}"),
        dict(title="Growth rate vs population (phase line)", xlabel="Population N", ylabel="dN/dt",
             lines=[(na, rate, "dN/dt")], hlines=[(0, "No change")], points=[(N[-1], f(N[-1]), "Now")],
             intro="Where the curve is above zero the population grows; below zero it shrinks. Zero crossings are equilibria.",
             text=(f"Growth is fastest ({rate[i]:.1f} per unit time) at N = {na[i]:,.0f}." if rate.max() > 0
                   else "Growth is negative at every population size, so it can only decline.")),
        dict(title="Harvest yield over time", xlabel="Time", ylabel="Yield rate h·N",
             lines=[(t, ym, "Yield rate")], hlines=[(h * eq, "Sustainable yield")], fill=True,
             intro="How much is harvested per unit time, and the long-run (sustainable) yield.",
             text=f"Harvest now is {ym[-1]:,.1f} per unit time; total harvested so far {cum[-1]:,.0f}; sustainable yield {h*eq:,.1f}."),
        dict(title="Equilibrium and yield vs harvest rate", xlabel="Harvest rate h", ylabel="N* and yield",
             lines=[(ha, eqh, "Equilibrium N*"), (ha, ha * eqh, "Sustainable yield")],
             points=[(h, h * eq, "Your h")], vlines=([(msy_h, "Best h (MSY)")] if msy_h <= 1 else []),
             intro="Harvesting more is not always better: yield peaks at h = r/2, and collapses when h reaches r.",
             text=f"At h = {h:.2f} the sustainable yield is {h*eq:,.0f}. The maximum possible yield is {msy:,.0f} at h = {msy_h:.2f}."),
    ]
    return plots, {"Final population": f"{N[-1]:,.1f}", "Equilibrium N*": f"{eq:,.1f}", "Peak population": f"{N.max():,.1f}"}


# ---- Tool 2: Equation analysis (SymPy) --------------------------------------
_TRANSFORMS = standard_transformations + (implicit_multiplication_application, convert_xor)


def _find_roots(fn, lo, hi, n=4000):
    xs = np.linspace(lo, hi, n)
    ys = fn(xs)
    fin = np.isfinite(ys)
    scale = 1 + (np.nanmax(np.abs(ys[fin])) if fin.any() else 0)
    roots = []
    sc = lambda z: float(fn(np.array([z]))[0])
    for i in range(n - 1):
        if not (fin[i] and fin[i + 1]):
            continue
        if ys[i] == 0:
            roots.append(xs[i])
        elif ys[i] * ys[i + 1] < 0:
            try:
                r = brentq(sc, xs[i], xs[i + 1])
                if abs(sc(r)) < 1e-6 * scale:
                    roots.append(r)
            except Exception:
                pass
    out = []
    for r in roots:
        if not out or abs(r - out[-1]) > 1e-6:
            out.append(float(r))
    return out[:20]


def m_equation(v):
    x = sp.Symbol("x", real=True)
    note = ""
    f = None
    expr = (v.get("expr") or "").strip()
    if expr:
        try:
            f = sp.sympify(parse_expr(expr, local_dict={"x": x}, transformations=_TRANSFORMS))
            if f.free_symbols - {x}:
                raise ValueError("only the variable x is supported")
        except Exception as e:
            note = f" (Could not read your f(x): {e}. The polynomial was used instead.)"
            f = None
    if f is None:
        co = [sp.nsimplify(round(float(v[k]), 4), rational=True) for k in ("a", "b", "c", "d")]
        f = co[0] * x ** 3 + co[1] * x ** 2 + co[2] * x + co[3]
    xmin, xmax = float(v["x_min"]), float(v["x_max"])
    if xmax <= xmin:
        xmax = xmin + 1
    df, d2 = sp.diff(f, x), sp.diff(sp.diff(f, x), x)
    try:
        Fsym = sp.integrate(f, x)
        Fstr = sp.sstr(Fsym)
    except Exception:
        Fstr = "(no closed form found)"

    def ev(e, xs):
        try:
            y = np.asarray(sp.lambdify(x, e, "numpy")(xs), dtype=float)
            return np.broadcast_to(y, xs.shape).copy()
        except Exception:
            return np.full(xs.shape, np.nan)

    xs = np.linspace(xmin, xmax, 600)
    y, dy, d2y = ev(f, xs), ev(df, xs), ev(d2, xs)
    fn_f = lambda z: ev(f, np.asarray(z, float))
    fn_d = lambda z: ev(df, np.asarray(z, float))
    fn_2 = lambda z: ev(d2, np.asarray(z, float))
    roots, crit, infl = _find_roots(fn_f, xmin, xmax), _find_roots(fn_d, xmin, xmax), _find_roots(fn_2, xmin, xmax)
    yy = np.nan_to_num(y, nan=0.0, posinf=0.0, neginf=0.0)
    F = cumtrapz(yy, xs)
    integral = float(F[-1])
    kinds = []
    for c in crit:
        s = float(fn_2(np.array([c]))[0])
        kinds.append(f"{c:.4g} ({'minimum' if s > 0 else 'maximum' if s < 0 else 'flat'})")
    lst = lambda a: ", ".join(f"{r:.4g}" for r in a) or "none"
    pts = lambda arr, fn: [(r, float(fn(np.array([r]))[0]), "Marked points" if i == 0 else None) for i, r in enumerate(arr)]
    plots = [
        dict(title="Function f(x) and its roots", xlabel="x", ylabel="f(x)", lines=[(xs, y, "f(x)")],
             points=pts(roots, fn_f), hlines=[(0, "y = 0")], fill=True,
             intro="The graph of your function. Yellow dots are the roots, where f(x) = 0.",
             text=f"f(x) = {sp.sstr(f)}. Roots in [{xmin:g}, {xmax:g}]: {lst(roots)}.{note}"),
        dict(title="Derivative f'(x) and critical points", xlabel="x", ylabel="f'(x)", lines=[(xs, dy, "f'(x)")],
             points=pts(crit, fn_d), hlines=[(0, "y = 0")],
             intro="The slope of f. Where it crosses zero, f has a peak or a valley.",
             text=f"f'(x) = {sp.sstr(df)}. Critical points: {', '.join(kinds) or 'none'}."),
        dict(title="Second derivative f''(x) (curvature)", xlabel="x", ylabel="f''(x)", lines=[(xs, d2y, "f''(x)")],
             points=pts(infl, fn_2), hlines=[(0, "y = 0")], fill=True,
             intro="Positive means the curve bends upward, negative means downward. Zero crossings are inflection points.",
             text=f"f''(x) = {sp.sstr(d2)}. Inflection points: {lst(infl)}."),
        dict(title="Antiderivative (area under f)", xlabel="x", ylabel="F(x)", lines=[(xs, F, "F(x) from x_min")],
             fill=True, intro="Running total of the area under f(x), starting at the left end of the range.",
             text=f"Antiderivative: F(x) = {Fstr} + C. Area (definite integral) from {xmin:g} to {xmax:g} = {integral:.5g}."),
    ]
    return plots, {"Roots found": len(roots), "Critical points": len(crit), "Integral over range": round(integral, 5)}


# ---- Tool 3: Advanced simulation (Monte Carlo) ------------------------------
def m_sim(v):
    n, walkers, steps, seed = int(v["samples"]), int(v["walkers"]), int(v["steps"]), int(v["seed"])
    rng = np.random.default_rng(seed)
    pts = rng.random((n, 2))
    inside = (pts ** 2).sum(axis=1) <= 1.0
    run = 4 * np.cumsum(inside) / np.arange(1, n + 1)
    est = run[-1]
    k = min(n, 4000)
    paths = rng.choice([-1, 1], size=(walkers, steps)).cumsum(axis=1)
    final = paths[:, -1]
    tt = np.arange(1, steps + 1)
    xs = np.linspace(final.min() - 3, final.max() + 3, 200)
    sd = math.sqrt(steps)
    plots = [
        dict(title="Estimating π with random points", xlabel="x", ylabel="y", equal=True,
             scatter=[(pts[:k][inside[:k], 0], pts[:k][inside[:k], 1], "Inside circle", 0, 3),
                      (pts[:k][~inside[:k], 0], pts[:k][~inside[:k], 1], "Outside", 1, 3)],
             intro="Random points are thrown in a unit square. The share that lands inside the quarter-circle gives π/4.",
             text=f"{inside.sum():,} of {n:,} points landed inside; π is estimated as {est:.5f} (error {abs(est-np.pi):.5f})."),
        dict(title="π estimate converging", xlabel="Number of samples", ylabel="Estimate of π",
             lines=[(np.arange(1, n + 1), run, "Running estimate")], hlines=[(np.pi, "True π")], logx=True,
             intro="The estimate wobbles at first and settles as samples increase.",
             text=f"Error shrinks like 1/√N: with {n:,} samples the expected error is about {1.6/math.sqrt(n):.4f}."),
        dict(title="Random walk sample paths", xlabel="Step", ylabel="Position",
             paths=(tt, paths[:40]), lines=[(tt, np.sqrt(tt), "+√N"), (tt, -np.sqrt(tt), "-√N")],
             intro="Each coloured line is one walker taking random ±1 steps. The dashed lines show the typical spread √N.",
             text=f"{walkers} walkers, {steps} steps each. After {steps} steps the typical distance from the start is √{steps} = {sd:.1f}."),
        dict(title="Where the walkers end up", xlabel="Final position", ylabel="Probability density",
             hist=final, density=True, bins=30,
             lines=[(xs, np.exp(-0.5 * (xs / sd) ** 2) / (sd * math.sqrt(2 * math.pi)), "Normal theory")],
             intro="The histogram of final positions follows a bell curve with spread √N (central limit theorem).",
             text=f"Mean final position {final.mean():.2f}; measured std dev {final.std():.2f} versus theory {sd:.2f}."),
    ]
    return plots, {"π estimate": round(float(est), 5), "π error": round(float(abs(est - np.pi)), 5),
                   "Walk std dev": round(float(final.std()), 2)}


# ---- Tool 4: Signal & Fourier explorer --------------------------------------
def m_signal(v):
    fr = [v["f1"], v["f2"], v["f3"]]
    am = [v["a1"], v["a2"], v["a3"]]
    noise, fs = v["noise"], int(v["fs"])
    t = np.arange(0, 2.0, 1 / fs)
    rng = np.random.default_rng(1)
    comps = [a * np.sin(2 * np.pi * f * t) for a, f in zip(am, fr)]
    clean = sum(comps)
    sig = clean + noise * rng.standard_normal(t.size)
    spec = np.abs(np.fft.rfft(sig)) * 2 / t.size
    freqs = np.fft.rfftfreq(t.size, 1 / fs)
    peak = float(freqs[1:][np.argmax(spec[1:])])
    rms = float(np.sqrt(np.mean(sig ** 2)))
    w, w2 = int(0.5 * fs), int(0.25 * fs)
    fa = np.linspace(0, max(150, fs), 400)
    alias = lambda f: abs(((f + fs / 2) % fs) - fs / 2)
    app = np.array([alias(f) for f in fa])
    over = [f for f in fr if f > fs / 2]
    snr = 10 * np.log10(max(clean.var(), 1e-12) / max(noise ** 2, 1e-12)) if noise > 0 else float("inf")
    plots = [
        dict(title="Signal in the time domain", xlabel="Time (s)", ylabel="Amplitude",
             lines=[(t[:w], sig[:w], "Noisy signal"), (t[:w], clean[:w], "Clean signal")],
             intro="The measured signal (sum of three sine waves plus random noise) over the first half second.",
             text=f"RMS value is {rms:.3f}. Signal-to-noise ratio is about {'infinite (no noise)' if noise == 0 else f'{snr:.1f} dB'}."),
        dict(title="Frequency spectrum (FFT)", xlabel="Frequency (Hz)", ylabel="Amplitude",
             lines=[(freqs, spec, "Spectrum")], vlines=[(fs / 2, "Nyquist limit")], xlim=(0, min(150, fs / 2)), fill=True,
             intro="The FFT shows which frequencies the signal contains. Each tall peak is one sine wave.",
             text=f"The strongest peak is at {peak:.1f} Hz. The Nyquist limit (highest frequency that can be measured) is {fs/2:.0f} Hz."),
        dict(title="The three building-block waves", xlabel="Time (s)", ylabel="Amplitude",
             lines=[(t[:w2], comps[0][:w2], f"{fr[0]} Hz"), (t[:w2], comps[1][:w2], f"{fr[1]} Hz"), (t[:w2], comps[2][:w2], f"{fr[2]} Hz")],
             solid=True, intro="Each component on its own. Adding them together gives the signal in plot 1.",
             text=f"Components: {fr[0]} Hz (amp {am[0]:.1f}), {fr[1]} Hz (amp {am[1]:.1f}), {fr[2]} Hz (amp {am[2]:.1f})."),
        dict(title="Aliasing map", xlabel="True frequency (Hz)", ylabel="Frequency you would see (Hz)",
             lines=[(fa, app, "Apparent frequency")], points=[(f, alias(f), "Your frequencies" if i == 0 else None) for i, f in enumerate(fr)],
             vlines=[(fs / 2, "Nyquist")],
             intro="Above the Nyquist limit a frequency is folded back and shows up as a false, lower frequency (aliasing).",
             text=("WARNING: " + ", ".join(f"{f} Hz would appear as {alias(f):.0f} Hz" for f in over) + ". Raise the sampling rate."
                   if over else f"All three frequencies are below {fs/2:.0f} Hz, so no aliasing occurs.")),
    ]
    return plots, {"Dominant frequency (Hz)": round(peak, 1), "RMS": round(rms, 3), "Nyquist (Hz)": fs // 2}


# ---- Tool 5: Statistics & CLT -----------------------------------------------
def m_clt(v):
    dist, n, m = int(v["dist"]), int(v["n"]), int(v["m"])
    rng = np.random.default_rng(7)

    def draw(size):
        if dist == 0:
            return rng.uniform(0, 1, size)
        if dist == 1:
            return rng.exponential(1.0, size)
        mix = rng.random(size) < 0.5
        return np.where(mix, rng.normal(-2, 0.5, size), rng.normal(2, 0.5, size))

    name = ["Uniform", "Exponential", "Bimodal"][min(max(dist, 0), 2)]
    pop = draw(100_000)
    means = draw((m, n)).mean(axis=1)
    mu, sigma = float(pop.mean()), float(pop.std())
    se = sigma / math.sqrt(n)
    xs = np.linspace(means.min(), means.max(), 300)
    ns = np.array([1, 2, 5, 10, 20, 50, 100, 200])
    emp = [draw((400, int(k))).mean(axis=1).std() for k in ns]
    q = mu + se * stats.norm.ppf((np.arange(1, m + 1) - 0.5) / m)
    ms = np.sort(means)
    plots = [
        dict(title=f"Population ({name})", xlabel="Value", ylabel="Probability density", hist=pop, density=True, bins=50,
             intro="The shape of the original data. It may be flat, skewed or have two humps.",
             text=f"Population mean {mu:.3f}, standard deviation {sigma:.3f}, skewness {stats.skew(pop):.2f}."),
        dict(title=f"Distribution of sample means (n = {n})", xlabel="Sample mean", ylabel="Probability density",
             hist=means, density=True, bins=40,
             lines=[(xs, np.exp(-0.5 * ((xs - mu) / se) ** 2) / (se * math.sqrt(2 * math.pi)), "Normal (CLT)")],
             intro="Averages of n values. Whatever the population, the histogram of averages becomes bell-shaped.",
             text=f"Mean of the {m:,} sample means is {means.mean():.3f}; their spread is {means.std():.3f} (theory σ/√n = {se:.3f})."),
        dict(title="Spread of the mean vs sample size", xlabel="Sample size n", ylabel="Std dev of sample means",
             lines=[(ns, emp, "Measured"), (ns, sigma / np.sqrt(ns), "Theory σ/√n")], points=[(n, means.std(), "Your n")],
             logx=True, logy=True,
             intro="Bigger samples give more precise averages, in proportion to 1/√n.",
             text=f"To halve the uncertainty you need four times more data. At n = {n} the spread is {means.std():.3f}."),
        dict(title="Normality check (Q-Q plot)", xlabel="Ideal normal values", ylabel="Your sample means",
             lines=[(q, ms, "Sample means"), (q, q, "Perfect normal")],
             intro="If the points follow the dashed line, the sample means are almost perfectly normal.",
             text=f"Skewness of the sample means is {stats.skew(means):.2f} (population: {stats.skew(pop):.2f}); closer to 0 means more bell-shaped."),
    ]
    return plots, {"Population mean": round(mu, 3), "Mean of means": round(float(means.mean()), 3), "Std of means": round(float(means.std()), 3)}


# ---- Tool 6: Data fitting & regression --------------------------------------
def _polyfit_stats(x, y, deg):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        coef = np.polyfit(x, y, deg)
    yhat = np.polyval(coef, x)
    ss_res, ss_tot = float(np.sum((y - yhat) ** 2)), float(np.sum((y - y.mean()) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot else float("nan")
    n = len(x)
    adj = 1 - (1 - r2) * (n - 1) / (n - deg - 1) if n - deg - 1 > 0 else float("nan")
    return coef, yhat, r2, adj, math.sqrt(ss_res / n)


def synth_xy(v):
    rng = np.random.default_rng(3)
    x = np.linspace(0, 10, int(v["n_points"]))
    return x, v["a2"] * x ** 2 + v["a1"] * x + v["a0"] + rng.normal(0, v["noise"], x.size)


def m_fit(v, data=None):
    x, y = data if data is not None else synth_xy(v)
    deg = int(min(max(v["degree"], 1), max(len(x) - 2, 1)))
    coef, yhat, r2, adj, rmse = _polyfit_stats(x, y, deg)
    res = y - yhat
    xs = np.linspace(x.min(), x.max(), 300)
    degs = list(range(1, min(10, len(x) - 2) + 1))
    r2s = [_polyfit_stats(x, y, d)[2] for d in degs]
    adjs = [_polyfit_stats(x, y, d)[3] for d in degs]
    best = degs[int(np.nanargmax(adjs))] if degs else deg
    bins = max(5, min(20, len(x) // 3))
    plots = [
        dict(title="Data and fitted curve", xlabel="x", ylabel="y",
             scatter=[(x, y, "Data", 1, 18)], lines=[(xs, np.polyval(coef, xs), f"Degree {deg} fit")],
             intro="Your data points (pink) and the polynomial curve that best matches them.",
             text=f"Degree {deg} fit on {len(x)} points; coefficients (highest power first): {[round(float(c), 4) for c in coef]}."),
        dict(title="Residuals (data minus fit)", xlabel="x", ylabel="Residual",
             scatter=[(x, res, "Residual", 2, 18)], hlines=[(0, "Perfect fit")],
             intro="Leftover error at each point. A random scatter around zero means a good model; a pattern means something is missing.",
             text=f"Residuals range from {res.min():.3f} to {res.max():.3f}; RMSE = {rmse:.3f}."),
        dict(title="Residual distribution", xlabel="Residual", ylabel="Count", hist=res, bins=bins,
             vlines=[(0, "Zero")],
             intro="Histogram of the leftover errors. For a good fit it is roughly bell-shaped and centred on zero.",
             text=f"Mean residual {res.mean():.4f}, standard deviation {res.std():.3f}."),
        dict(title="Which degree fits best?", xlabel="Polynomial degree", ylabel="R² (cyan) / Adjusted R² (pink)",
             lines=[(degs, r2s, "R²"), (degs, adjs, "Adjusted R²")], points=[(deg, r2, "Your degree")],
             intro="R² always rises with degree, but adjusted R² punishes needless complexity, so its peak is the sensible choice.",
             text=f"R² = {r2:.4f}, adjusted R² = {adj:.4f}. Best adjusted R² is at degree {best}." +
                  (" High degrees can overfit." if deg >= 8 else "")),
    ]
    return plots, {"R²": round(r2, 4), "Adjusted R²": round(adj, 4), "RMSE": round(rmse, 3)}


# ---- Tool 7: Uncertainty & sensitivity (3 formulas) -------------------------
def m_uncert(v, vars_, fn, unit, name):
    n = int(v["samples"])
    keys = [k for k, *_ in vars_]
    labs = {k: lab for k, lab, *_ in vars_}
    nom = {k: v[k] for k in keys}
    rng = np.random.default_rng(11)
    smp = {k: np.maximum(rng.normal(nom[k], abs(nom[k]) * v[k + "_u"] / 100 + 1e-12, n), 1e-6 * abs(nom[k]) + 1e-12) for k in keys}
    y = np.asarray(fn(smp), dtype=float)
    y0 = float(fn(nom))
    lo, hi = np.percentile(y, [2.5, 97.5])
    corr = {k: (np.corrcoef(smp[k], y)[0, 1] ** 2 if v[k + "_u"] > 0 else 0.0) for k in keys}
    tot = sum(corr.values()) or 1.0
    share = {k: 100 * c / tot for k, c in corr.items()}
    top = max(share, key=share.get)
    chg = {}
    for k in keys:
        d = dict(nom)
        d[k] = nom[k] * (1 + v[k + "_u"] / 100)
        chg[k] = (float(fn(d)) - y0) / y0 * 100 if y0 else 0.0
    sub = slice(0, 2000)
    u = unit or "units"
    plots = [
        dict(title="Distribution of the result", xlabel=f"Result ({u})", ylabel="Probability density", hist=y, density=True,
             vlines=[(y0, "Nominal"), (lo, "95% low"), (hi, "95% high")],
             intro="Thousands of random trials, each with inputs varied within their uncertainty. The spread is the uncertainty of the answer.",
             text=f"Nominal result {y0:,.4g} {unit}; mean {y.mean():,.4g}; 95% of trials fall between {lo:,.4g} and {hi:,.4g}."),
        dict(title="Which input matters most?", xlabel="Share of output variance (%)", ylabel="",
             hbars=([labs[k] for k in keys], [share[k] for k in keys]),
             intro="The bigger the bar, the more that input's uncertainty drives the uncertainty of the result. Improve that measurement first.",
             text=f"Biggest source of uncertainty: {labs[top]} ({share[top]:.0f}% of the variance)."),
        dict(title=f"Result vs {labs[top]}", xlabel=labs[top], ylabel=f"Result ({u})",
             scatter=[(smp[top][sub], y[sub], "Trials", 4, 5)],
             intro="Each dot is one trial. A tight diagonal band means this input strongly controls the answer.",
             text=f"Correlation between {labs[top]} and the result: {np.corrcoef(smp[top], y)[0, 1]:+.2f}."),
        dict(title="Effect of a typical error in each input", xlabel="Change in result (%)", ylabel="",
             hbars=([labs[k] for k in keys], [chg[k] for k in keys]),
             bar_colors=[DARK["c"][3] if chg[k] >= 0 else DARK["c"][1] for k in keys],
             intro="If one input is off by its stated uncertainty (all others exact), how much does the result change?",
             text="; ".join(f"{labs[k]} +{v[k+'_u']:.1f}% gives {chg[k]:+.2f}% in the result" for k in keys) + "."),
    ]
    return plots, {"Nominal": f"{y0:,.4g} {unit}".strip(), "Mean": f"{y.mean():,.4g}", "Std dev": f"{y.std():,.4g}",
                   "95% interval": f"{lo:,.4g} to {hi:,.4g}"}


def _unc_spec(vars_, fn, unit, name):
    params = [P(k, lab, lo, hi, d, s) for k, lab, d, lo, hi, s in vars_]
    params += [P(k + "_u", f"{lab} uncertainty (%)", 0.0, 20.0, 2.0, 0.5) for k, lab, *_ in vars_]
    params.append(P("samples", "Monte Carlo samples", 1000, 100000, 20000, 1000))
    vs = [(k, lab) for k, lab, *_ in vars_]
    return dict(params=params, model=lambda v: m_uncert(v, vs, fn, unit, name))


UNC_VARIANTS = {
    "Pendulum gravity: g = 4π²L / T²": _unc_spec(
        [("L_m", "Length L (m)", 1.0, 0.1, 5.0, 0.01), ("T_s", "Period T (s)", 2.006, 0.5, 10.0, 0.001)],
        lambda s: 4 * np.pi ** 2 * s["L_m"] / s["T_s"] ** 2, "m/s²", "pendulum"),
    "Electrical power: P = V² / R": _unc_spec(
        [("V", "Voltage V (volts)", 230.0, 50.0, 1000.0, 1.0), ("R_ohm", "Resistance R (ohms)", 50.0, 1.0, 500.0, 1.0)],
        lambda s: s["V"] ** 2 / s["R_ohm"], "W", "power"),
    "Reynolds number: Re = ρvD / μ": _unc_spec(
        [("rho", "Density ρ (kg/m³)", 1000.0, 500.0, 2000.0, 10.0), ("v_ms", "Velocity v (m/s)", 1.5, 0.1, 10.0, 0.1),
         ("D_m", "Diameter D (m)", 0.05, 0.01, 1.0, 0.01), ("mu", "Viscosity μ (Pa·s)", 0.001, 0.0001, 0.01, 0.0001)],
        lambda s: s["rho"] * s["v_ms"] * s["D_m"] / s["mu"], "", "reynolds"),
}


# ---- Tool 8: Power factor correction ----------------------------------------
def m_pf(v):
    p, pf1, pf2, V, f = v["p_kw"], v["pf1"], v["pf2"], v["v_line"], v["freq"]
    adj = ""
    if pf2 <= pf1:
        pf2 = min(pf1 + 0.02, 1.0)
        adj = f" The target was raised to {pf2:.2f} because it must be higher than the existing power factor."
    q = lambda pf: p * math.tan(math.acos(pf))
    q1, q2 = q(pf1), q(pf2)
    qc = q1 - q2
    cur = lambda pf: p * 1000 / (math.sqrt(3) * V * pf)
    i1, i2 = cur(pf1), cur(pf2)
    cap_uf = qc * 1000 / (3 * 2 * math.pi * f * V ** 2) * 1e6
    pfa = np.linspace(0.5, 1.0, 60)
    pft = np.linspace(pf1, 1.0, 40)
    plots = [
        dict(title="Power triangle: before and after", xlabel="Real power P (kW)", ylabel="Reactive power Q (kVAR)", solid=True,
             lines=[([0, p, p, 0], [0, 0, q1, 0], "Before"), ([0, p, p, 0], [0, 0, q2, 0], "After")],
             intro="The flat side is useful power P. The vertical side is wasted reactive power Q. The capacitor bank shrinks Q.",
             text=f"Apparent power drops from {math.hypot(p, q1):,.0f} kVA to {math.hypot(p, q2):,.0f} kVA.{adj}"),
        dict(title="Capacitor size vs target power factor", xlabel="Target power factor", ylabel="Capacitor bank (kVAR)",
             lines=[(pft, p * (math.tan(math.acos(pf1)) - np.tan(np.arccos(pft))), "Required kVAR")], points=[(pf2, qc, "Your target")], fill=True,
             intro="The higher the target power factor, the bigger the capacitor bank you need.",
             text=f"To go from {pf1:.2f} to {pf2:.2f} you need {qc:,.1f} kVAR, which is {cap_uf:,.0f} µF per phase (delta bank at {f} Hz)."),
        dict(title="Line current vs power factor", xlabel="Power factor", ylabel="Line current (A)",
             lines=[(pfa, p * 1000 / (math.sqrt(3) * V * pfa), "Line current")],
             points=[(pf1, i1, "Before"), (pf2, i2, "After")],
             intro="At the same real power, a poor power factor forces more current through cables and transformers.",
             text=f"Line current falls from {i1:,.1f} A to {i2:,.1f} A ({(i2-i1)/i1*100:.1f}%)."),
        dict(title="Cable heating (I²R loss) vs power factor", xlabel="Power factor", ylabel="Relative loss (%)",
             lines=[(pfa, (pf1 / pfa) ** 2 * 100, "Relative loss")], points=[(pf1, 100, "Before"), (pf2, (pf1 / pf2) ** 2 * 100, "After")],
             intro="Cable loss grows with the square of current. Loss is shown relative to your existing situation (100%).",
             text=f"Cable and transformer copper losses fall to {(pf1/pf2)**2*100:.0f}% of today's value. Assumes a balanced delta load; verify with a qualified engineer."),
    ]
    return plots, {"Capacitor bank (kVAR)": round(qc, 1), "Per phase (µF)": round(cap_uf), "Current before (A)": round(i1, 1), "Current after (A)": round(i2, 1)}


# ---- Tool 9: Reliability (Weibull) ------------------------------------------
def m_rel(v):
    beta, eta, mission, n = v["beta"], v["eta"], v["mission"], int(v["n_series"])
    rel = math.exp(-((mission / eta) ** beta))
    mttf = eta * math.gamma(1 + 1 / beta)
    b10 = eta * (-math.log(0.9)) ** (1 / beta)
    t = np.linspace(1, eta * 3, 400)
    R = np.exp(-((t / eta) ** beta))
    hz = (beta / eta) * (t / eta) ** (beta - 1)
    pdf = hz * R
    na = np.arange(1, 51)
    Rn = rel ** na
    below = na[Rn < 0.9]
    if beta < 0.95:
        mode = "infant mortality: failures decrease with age, so consider burn-in testing"
    elif beta <= 1.05:
        mode = "random failures: age does not matter, so preventive replacement has no benefit"
    else:
        mode = "wear-out: failures increase with age, so plan maintenance before the B10 life"
    plots = [
        dict(title="Reliability over time", xlabel="Time (hours)", ylabel="Probability of survival", ylim=(0, 1.02),
             lines=[(t, R, "Component"), (t, R ** n, f"System ({n} in series)")], vlines=[(mission, "Mission time")],
             intro="The chance that the part (or the whole system) is still working after a given time.",
             text=f"At {mission:,.0f} h one component survives with {rel*100:.2f}% probability; the system of {n} in series with {rel**n*100:.2f}%."),
        dict(title="Hazard rate", xlabel="Time (hours)", ylabel="Failure rate (per hour)",
             lines=[(t, hz, "Hazard rate")], vlines=[(mission, "Mission time")], fill=True,
             intro="How likely a part that has survived so far is to fail in the next hour.",
             text=f"β = {beta:.1f} means {mode}."),
        dict(title="Failure density (when failures happen)", xlabel="Time (hours)", ylabel="Probability density",
             lines=[(t, pdf, "Failure density")], vlines=[(mttf, "MTTF"), (b10, "B10 life")], fill=True,
             intro="The histogram-like curve of failure times. MTTF is the average life and B10 is when 10% have failed.",
             text=f"Mean time to failure {mttf:,.0f} h; B10 life {b10:,.0f} h (10% of parts fail before this)."),
        dict(title="System reliability vs components in series", xlabel="Number of components in series", ylabel="System reliability at mission time",
             lines=[(na, Rn, "System reliability")], points=[(n, rel ** n, "Your system")], hlines=[(0.9, "90% target")], ylim=(0, 1.02),
             intro="A chain is only as reliable as all its links together: every extra component in series lowers reliability.",
             text=(f"System reliability falls below 90% once there are {int(below[0])} components in series." if below.size
                   else "System reliability stays above 90% even with 50 components in series.")),
    ]
    return plots, {"Reliability R(t)": f"{rel*100:.2f}%", "System reliability": f"{rel**n*100:.2f}%", "MTTF (h)": f"{mttf:,.0f}", "B10 life (h)": f"{b10:,.0f}"}


# ---- Tool 10: Engineering economics -----------------------------------------
def _npv(rate, flows):
    return float(sum(cf / (1 + rate) ** i for i, cf in enumerate(flows)))


def _irr(flows):
    lo, hi = -0.99, 10.0
    if _npv(lo, flows) * _npv(hi, flows) > 0:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2
        if _npv(lo, flows) * _npv(mid, flows) <= 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def m_econ(v):
    inv, cash, g, yrs, rate, salv = v["invest"], v["cash1"], v["growth"], int(v["years"]), v["rate"], v["salvage"]

    def make(c):
        fl = [-inv] + [c * (1 + g / 100) ** i for i in range(yrs)]
        fl[-1] += salv
        return fl

    flows = make(cash)
    arr = np.array(flows)
    disc = arr / (1 + rate / 100) ** np.arange(len(arr))
    npv, irr = float(disc.sum()), _irr(flows)
    cum, dcum = np.cumsum(arr), np.cumsum(disc)
    pay = next((i for i, x in enumerate(cum) if x >= 0), None)
    dpay = next((i for i, x in enumerate(dcum) if x >= 0), None)
    rates = np.linspace(0.01, 0.30, 60)
    yrsx = np.arange(len(arr))
    mult = np.linspace(0.5, 1.5, 30)
    sens = {}
    for rr in sorted({max(rate - 3, 0.5), rate, min(rate + 3, 40)}):
        sens[rr] = [_npv(rr / 100, make(cash * mm)) for mm in mult]
    colors = [DARK["c"][1] if x < 0 else DARK["c"][3] for x in cum]
    plots = [
        dict(title="Cumulative cash flow", xlabel="Year", ylabel="Cumulative cash (currency)",
             bars=([], list(cum)), bar_x=list(yrsx), bar_colors=colors, bar_labels=False,
             intro="Running total of money in and out. Red bars mean you have not yet earned your investment back.",
             text=f"Simple payback: {f'year {pay}' if pay is not None else 'not within the project life'}; discounted payback: {f'year {dpay}' if dpay is not None else 'not within the project life'}."),
        dict(title="NPV vs discount rate", xlabel="Discount rate (%)", ylabel="NPV (currency)",
             lines=[(rates * 100, [_npv(r, flows) for r in rates], "NPV")], hlines=[(0, "Break-even")],
             points=[(rate, npv, "Your rate")] + ([(irr * 100, 0, "IRR")] if irr is not None and 1 <= irr * 100 <= 30 else []),
             intro="NPV shrinks as the discount rate rises. Where it crosses zero is the IRR, the project's own rate of return.",
             text=f"NPV at {rate:.1f}% is {npv:,.0f}; IRR is {f'{irr*100:.2f}%' if irr is not None else 'not defined'}. " +
                  ("Positive NPV: the project creates value." if npv > 0 else "Negative NPV: the project destroys value.")),
        dict(title="Annual cash flow: nominal vs discounted", xlabel="Year", ylabel="Cash flow (currency)",
             lines=[(yrsx, arr, "Net cash flow"), (yrsx, disc, "Discounted")], hlines=[(0, "Zero")], solid=True,
             intro="Money later is worth less than money now. The discounted line shows each year's cash at today's value.",
             text=f"Year-1 cash {cash:,.0f} growing {g:.1f}% a year; salvage {salv:,.0f} in the last year. Profitability index {(npv+inv)/inv:.2f}."),
        dict(title="Sensitivity to the cash-flow forecast", xlabel="Cash flow as % of your estimate", ylabel="NPV (currency)",
             lines=[(mult * 100, vals, f"Rate {rr:.1f}%") for rr, vals in sens.items()], hlines=[(0, "Break-even")], solid=True,
             intro="What if income turns out lower or higher than forecast? Lines show three different discount rates.",
             text="NPV stays positive down to about " +
                  (f"{mult[np.argmax(np.array(sens[rate]) > 0)]*100:.0f}% of the forecast cash flow." if npv > 0 and (np.array(sens[rate]) <= 0).any()
                   else "the lowest value tested." if npv > 0 else "never (NPV is negative across the tested range)." if not (np.array(sens[rate]) > 0).any() else
                   f"- it turns positive above about {mult[np.argmax(np.array(sens[rate]) > 0)]*100:.0f}% of the forecast.")),
    ]
    return plots, {"NPV": f"{npv:,.0f}", "IRR": f"{irr*100:.2f}%" if irr is not None else "n/a",
                   "Payback": f"{pay} yr" if pay is not None else "not within life", "Profitability index": f"{(npv+inv)/inv:.2f}"}


# ---- Tool 11: Linear programming --------------------------------------------
def m_lp(v):
    p1, p2 = v["p1"], v["p2"]
    rows = [("Machine hours", v["m_a"], v["m_b"], v["m_cap"]), ("Labour hours", v["l_a"], v["l_b"], v["l_cap"]),
            ("Material (kg)", v["k_a"], v["k_b"], v["k_cap"])]

    def solve(a, b):
        return linprog([-a, -b], A_ub=[[x, y] for _, x, y, _ in rows], b_ub=[c for *_, c in rows],
                       bounds=[(0, None), (0, None)], method="highs")

    res = solve(p1, p2)
    if not res.success:
        raise ValueError("No bounded solution: make sure each product uses at least one resource.")
    xa, xb = res.x
    obj = -res.fun
    xi = [c / a for _, a, b, c in rows if a > 0]
    yi = [c / b for _, a, b, c in rows if b > 0]
    xmax, ymax = (max(xi) * 1.15 if xi else 100.0), (max(yi) * 1.15 if yi else 100.0)
    gx, gy = np.meshgrid(np.linspace(0, xmax, 200), np.linspace(0, ymax, 200))
    feas = np.ones_like(gx, dtype=bool)
    for _, a, b, c in rows:
        feas &= (a * gx + b * gy) <= c + 1e-9
    xs = np.linspace(0, xmax, 100)
    lines = []
    for name, a, b, c in rows:
        if b > 0:
            ys = (c - a * xs) / b
            lines.append((xs, np.where((ys >= 0) & (ys <= ymax), ys, np.nan), name))
        elif a > 0:
            lines.append(([c / a, c / a], [0, ymax], name))
    iso = (obj - p1 * xs) / p2
    lines.append((xs, np.where((iso >= 0) & (iso <= ymax), iso, np.nan), "Max-profit line"))
    used = [a * xa + b * xb for _, a, b, _ in rows]
    util = [u / c * 100 for u, (_, _, _, c) in zip(used, rows)]
    shadow = [-float(m) for m in res.ineqlin.marginals]
    scale = np.linspace(0.5, 1.5, 25)
    profits = [-solve(p1 * s, p2).fun for s in scale]
    binding = [r[0] for r, u in zip(rows, util) if u > 99.9]
    names = [r[0] for r in rows]
    top = names[int(np.argmax(shadow))]
    plots = [
        dict(title="Feasible region and optimum", xlabel="Product A (units)", ylabel="Product B (units)", solid=True,
             mask=(gx, gy, feas), lines=lines, points=[(xa, xb, "Optimum")], xlim=(0, xmax), ylim=(0, ymax),
             intro="The green area is every production plan your resources allow. The best plan sits at a corner, touched by the max-profit line.",
             text=f"Make {xa:,.2f} of Product A and {xb:,.2f} of Product B for the maximum profit of {obj:,.2f}."),
        dict(title="Resource utilisation", xlabel="", ylabel="Used (% of available)", bars=(["Machine", "Labour", "Material"], util),
             bar_colors=[DARK["c"][1] if u > 99.9 else DARK["c"][0] for u in util], hlines=[(100, "Limit")],
             intro="Resources used at the optimum. Pink bars at 100% are fully used up: they are the bottlenecks.",
             text=("Bottleneck(s): " + ", ".join(binding) + "." if binding else "No resource is fully used.")),
        dict(title="Shadow prices (value of one extra unit)", xlabel="Extra profit per extra unit", ylabel="",
             hbars=(names, shadow), bar_colors=[DARK["c"][2], DARK["c"][4], DARK["c"][3]],
             intro="How much more profit you would earn if you could add one more unit of each resource.",
             text=f"The most valuable resource to expand is {top}: each extra unit adds {max(shadow):,.2f} to profit."),
        dict(title="Profit sensitivity to the price of Product A", xlabel="Profit per unit of A", ylabel="Maximum profit",
             lines=[(p1 * scale, profits, "Max profit")], points=[(p1, obj, "Now")], fill=True,
             intro="What happens to the best achievable profit if the selling margin of Product A changes by -50% to +50%.",
             text=f"If the margin on A moved to {p1*0.8:,.1f} profit would be about {-solve(p1*0.8,p2).fun:,.1f}; at {p1*1.2:,.1f} about {-solve(p1*1.2,p2).fun:,.1f}."),
    ]
    return plots, {"Optimal Product A": round(float(xa), 2), "Optimal Product B": round(float(xb), 2), "Maximum profit": round(float(obj), 2)}


# ----------------------------------------------------------------------------
# 5. TOOL REGISTRY
# (names MUST match keys in tool_access_control)
# ----------------------------------------------------------------------------
LEARN, RESEARCH, INDUSTRY = "🎓 Learning Lab", "🔬 Research Lab", "🏭 Industry Lab"

TOOL_REGISTRY = {
    "Tool 1: Mathematical Modeling": dict(
        num=1, model=m_logistic, category=LEARN, audience="Students, Researchers",
        desc="Population dynamics with ODE solvers and equilibrium analysis.",
        params=[P("r", "Growth rate r", 0.01, 2.0, 0.5, 0.01), P("K", "Carrying capacity K", 10, 100000, 1000, 10),
                P("h", "Harvest rate h", 0.0, 1.0, 0.1, 0.01), P("N0", "Initial population N0", 1, 100000, 50, 1),
                P("T", "Time horizon T", 5, 200, 50, 1), P("solver", "Solver (1 = RK4, 0 = Euler)", 0, 1, 1, 1)]),
    "Tool 2: Equation Analysis": dict(
        num=2, model=m_equation, category=RESEARCH, audience="Students, Researchers",
        desc="Symbolic derivative, integral, roots and plots for any f(x).",
        params=[P("a", "Coefficient a (x³)", -5.0, 5.0, 1.0, 0.1), P("b", "Coefficient b (x²)", -10.0, 10.0, -6.0, 0.1),
                P("c", "Coefficient c (x)", -20.0, 20.0, 11.0, 0.1), P("d", "Constant d", -30.0, 30.0, -6.0, 0.1),
                P("x_min", "Plot x min", -20.0, 9.0, -2.0, 0.5), P("x_max", "Plot x max", -9.0, 20.0, 5.0, 0.5)],
        text_params=[("expr", "OR type your own f(x), e.g. sin(x)*x - 1  (leave blank to use the polynomial)", "")]),
    "Tool 3: Advanced Simulation": dict(
        num=3, model=m_sim, category=LEARN, audience="Students, Researchers",
        desc="Monte Carlo estimation of π and random-walk physics.",
        params=[P("samples", "Samples for π", 1000, 200000, 20000, 1000), P("walkers", "Random walkers", 10, 1000, 200, 10),
                P("steps", "Steps per walker", 50, 2000, 500, 50), P("seed", "Random seed", 0, 1000000, 42, 1)]),
    "Tool 4: Signal & Fourier Explorer": dict(
        num=4, model=m_signal, category=LEARN, audience="Students, Engineers",
        desc="Build signals, view FFT spectra, learn aliasing and Nyquist.",
        params=[P("f1", "Freq 1 (Hz)", 1, 100, 5, 1), P("f2", "Freq 2 (Hz)", 1, 100, 20, 1), P("f3", "Freq 3 (Hz)", 1, 100, 50, 1),
                P("a1", "Amp 1", 0.0, 2.0, 1.0, 0.1), P("a2", "Amp 2", 0.0, 2.0, 0.5, 0.1), P("a3", "Amp 3", 0.0, 2.0, 0.3, 0.1),
                P("noise", "Noise level", 0.0, 2.0, 0.3, 0.05), P("fs", "Sampling rate (Hz)", 128, 2048, 512, 128)]),
    "Tool 5: Statistics & CLT Explorer": dict(
        num=5, model=m_clt, category=LEARN, audience="Students, Researchers",
        desc="See the Central Limit Theorem emerge from any distribution.",
        params=[P("dist", "Population (0 = Uniform, 1 = Exponential, 2 = Bimodal)", 0, 2, 0, 1), P("n", "Sample size n", 1, 200, 30, 1),
                P("m", "Number of samples", 100, 5000, 1000, 100)]),
    "Tool 6: Data Fitting & Regression Lab": dict(
        num=6, model=m_fit, category=RESEARCH, audience="Researchers, Industry",
        desc="Upload CSV/Excel data, fit models, check R² and residuals, export a PDF.",
        mode="dataset", dataset_params=["degree"],
        data_columns=[("x", "Independent variable (e.g. time, load, voltage)"), ("y", "Measured response")],
        params=[P("degree", "Polynomial degree", 1, 10, 2, 1), P("n_points", "Sample data: number of points", 10, 200, 40, 5),
                P("noise", "Sample data: noise", 0.0, 10.0, 3.0, 0.5), P("a2", "Sample data: true x² coefficient", -2.0, 2.0, 0.5, 0.1),
                P("a1", "Sample data: true x coefficient", -10.0, 10.0, -3.0, 0.5), P("a0", "Sample data: true constant", -20.0, 20.0, 4.0, 0.5)]),
    "Tool 7: Uncertainty & Sensitivity Analyzer": dict(
        num=7, category=RESEARCH, audience="Researchers, Industry",
        desc="Monte Carlo error propagation and ranking of uncertainty sources.", variants=UNC_VARIANTS),
    "Tool 8: Power Factor & Energy Calculator": dict(
        num=8, model=m_pf, category=INDUSTRY, audience="Industry, Students",
        desc="Capacitor bank sizing and current reduction for 3-phase loads.",
        params=[P("p_kw", "Real power P (kW)", 10, 5000, 250, 10), P("pf1", "Existing power factor", 0.50, 0.99, 0.78, 0.01),
                P("pf2", "Target power factor", 0.80, 1.00, 0.97, 0.01), P("v_line", "Line voltage (V)", 100, 11000, 415, 5),
                P("freq", "Frequency (Hz)", 50, 60, 50, 10)]),
    "Tool 9: Reliability & Failure Analysis": dict(
        num=9, model=m_rel, category=INDUSTRY, audience="Industry, Researchers",
        desc="Weibull reliability, MTTF, B10 life and series-system reliability.",
        params=[P("beta", "Shape β", 0.3, 5.0, 2.0, 0.1), P("eta", "Scale η (hours)", 100, 100000, 5000, 100),
                P("mission", "Mission time (hours)", 1, 100000, 2000, 100), P("n_series", "Components in series", 1, 50, 3, 1)]),
    "Tool 10: Engineering Economics (NPV/IRR)": dict(
        num=10, model=m_econ, category=INDUSTRY, audience="Industry, Managers",
        desc="NPV, IRR, payback and discount-rate sensitivity for projects.",
        params=[P("invest", "Initial investment", 10000, 10000000, 1000000, 10000), P("cash1", "Year-1 net cash flow", 0, 5000000, 250000, 10000),
                P("growth", "Annual cash-flow growth (%)", -10.0, 20.0, 3.0, 0.5), P("years", "Project life (years)", 1, 40, 10, 1),
                P("rate", "Discount rate (%)", 1.0, 30.0, 10.0, 0.5), P("salvage", "Salvage value (end)", 0, 5000000, 100000, 10000)]),
    "Tool 11: Optimization Studio (LP)": dict(
        num=11, model=m_lp, category=INDUSTRY, audience="Industry, Managers",
        desc="Linear programming for product mix with shadow prices.",
        params=[P("p1", "Profit per unit, Product A", 1.0, 1000.0, 40.0, 1.0), P("p2", "Profit per unit, Product B", 1.0, 1000.0, 30.0, 1.0),
                P("m_a", "Machine hours: A uses", 0.0, 50.0, 2.0, 0.5), P("m_b", "Machine hours: B uses", 0.0, 50.0, 1.0, 0.5),
                P("m_cap", "Machine hours available", 1, 2000, 100, 5),
                P("l_a", "Labour hours: A uses", 0.0, 50.0, 1.0, 0.5), P("l_b", "Labour hours: B uses", 0.0, 50.0, 2.0, 0.5),
                P("l_cap", "Labour hours available", 1, 2000, 80, 5),
                P("k_a", "Material kg: A uses", 0.0, 50.0, 3.0, 0.5), P("k_b", "Material kg: B uses", 0.0, 50.0, 2.0, 0.5),
                P("k_cap", "Material kg available", 1, 2000, 180, 5)]),
}


# ----------------------------------------------------------------------------
# 6. UPLOAD / TEMPLATE / PDF HELPERS
# ----------------------------------------------------------------------------
def get_spec(T, variant):
    return T["variants"][variant] if T.get("variants") else T


def sheet_name(T, variant):
    n = T["num"]
    return f"Tool{n}" if variant is None else f"Tool{n}_{list(T['variants']).index(variant) + 1}"


def pcast(val, step):
    return int(round(val)) if isinstance(step, int) else round(round(val / step) * step, 6)


def example_table(T, spec):
    if T.get("mode") == "dataset":
        defaults = {k: d for k, _, _, _, d, _ in spec["params"]}
        x, y = synth_xy({**defaults, "n_points": 15})
        return pd.DataFrame({"x": np.round(x, 3), "y": np.round(y, 3)})
    rows = []
    for i, f in enumerate([1.0, 0.8, 1.2]):
        r = {"case": f"Case_{i+1}"}
        for k, _, lo, hi, d, s in spec["params"]:
            r[k] = pcast(min(max(d * f, lo), hi), s)
        for k, _, default in spec.get("text_params", []):
            r[k] = default
        rows.append(r)
    return pd.DataFrame(rows)


def variables_table(T, spec):
    if T.get("mode") == "dataset":
        return pd.DataFrame([{"Column name": k, "Meaning": m} for k, m in T["data_columns"]])
    out = [{"Column name": k, "Meaning": lab, "Minimum": lo, "Maximum": hi, "Typical value": d}
           for k, lab, lo, hi, d, s in spec["params"]]
    out += [{"Column name": k, "Meaning": lab + " (text, optional)", "Minimum": "", "Maximum": "", "Typical value": default}
            for k, lab, default in spec.get("text_params", [])]
    return pd.DataFrame(out)


def build_template():
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        lines = [
            "1. Open the sheet named Tool<number> for the tool you want (e.g. Tool1 = Mathematical Modeling).",
            "2. Tool 7 has three formulas: use Tool7_1, Tool7_2 or Tool7_3 (the same order as the app).",
            "3. Keep the column names in row 1 exactly as they are. Do not rename them.",
            "4. Each row is one case. Replace the example numbers with your own values.",
            "5. The 'case' column is just a label (name, trial number...). Tool 6 is different: each row is one data point (x, y).",
            "6. Values outside the allowed range are clipped; missing columns use typical values.",
            f"7. Save as .xlsx or .csv and upload it in the app. Maximum {MAX_UPLOAD_ROWS} rows per upload.",
            "Tools: " + "; ".join(f"{T['num']} = {n.split(': ', 1)[1]}" for n, T in TOOL_REGISTRY.items()),
        ]
        pd.DataFrame({"How to use this file": lines}).to_excel(xw, sheet_name="READ_ME", index=False)
        for T in sorted(TOOL_REGISTRY.values(), key=lambda t: t["num"]):
            for variant in (list(T["variants"]) if T.get("variants") else [None]):
                spec = get_spec(T, variant)
                sn = sheet_name(T, variant)
                example_table(T, spec).to_excel(xw, sheet_name=sn, index=False)
                variables_table(T, spec).to_excel(xw, sheet_name=sn + "_variables", index=False)
    return buf.getvalue()


def _read_table(file, wanted_sheet):
    if file.name.lower().endswith(".csv"):
        return pd.read_csv(file)
    xls = pd.ExcelFile(file)
    sheet = wanted_sheet if wanted_sheet in xls.sheet_names else next(
        (s for s in xls.sheet_names if s.upper() != "READ_ME" and not s.endswith("_variables")), xls.sheet_names[0])
    return xls.parse(sheet)


def load_upload(file, T, variant):
    spec = get_spec(T, variant)
    notes = []
    df = _read_table(file, sheet_name(T, variant))
    keymap = {k.lower(): k for k, *_ in spec["params"]}
    keymap.update({k.lower(): k for k, *_ in spec.get("text_params", [])})
    df.columns = [keymap.get(str(c).strip().lower(), str(c).strip().lower()) for c in df.columns]
    if len(df) > MAX_UPLOAD_ROWS:
        notes.append(f"Only the first {MAX_UPLOAD_ROWS} rows were used.")
    df = df.dropna(how="all").head(MAX_UPLOAD_ROWS).reset_index(drop=True)
    if "case" not in df.columns:
        df.insert(0, "case", [f"Case_{i+1}" for i in range(len(df))])
    for k, _, lo, hi, d, s in spec["params"]:
        if k not in df.columns:
            notes.append(f"Column '{k}' not found - typical value {d} used.")
            df[k] = d
        df[k] = pd.to_numeric(df[k], errors="coerce")
        if df[k].isna().any():
            notes.append(f"Column '{k}' had empty/non-numeric cells - typical value {d} used there.")
            df[k] = df[k].fillna(d)
        if ((df[k] < lo) | (df[k] > hi)).any():
            notes.append(f"Column '{k}' had values outside {lo} to {hi}; they were clipped.")
            df[k] = df[k].clip(lo, hi)
    for k, _, default in spec.get("text_params", []):
        df[k] = df[k].fillna(default).astype(str) if k in df.columns else default
    return df, notes


def load_dataset(file, T):
    df = _read_table(file, sheet_name(T, None))
    df.columns = [str(c).strip().lower() for c in df.columns]
    if {"x", "y"} <= set(df.columns):
        raw = df[["x", "y"]].apply(pd.to_numeric, errors="coerce").dropna()
    else:
        raw = df.select_dtypes(include=np.number).dropna()
        raw = raw.iloc[:, :2]
    if raw.shape[1] < 2 or len(raw) < 4:
        raise ValueError("Need two numeric columns (x and y) and at least 4 rows.")
    return raw.iloc[:, 0].to_numpy(float), raw.iloc[:, 1].to_numpy(float)


def run_rows(spec, df):
    out, errors = [], []
    for _, row in df.iterrows():
        vals = {k: (int(row[k]) if isinstance(s, int) else float(row[k])) for k, _, _, _, _, s in spec["params"]}
        for k, _, _ in spec.get("text_params", []):
            vals[k] = str(row[k])
        try:
            plots, summ = spec["model"](vals)
            out.append((str(row["case"]), vals, plots, summ))
        except Exception as e:
            errors.append(f"{row['case']}: {e}")
    return out, errors


def build_pdf(title, desc, results):
    buf = io.BytesIO()
    pal = LIGHT
    foot = "Vera Design Labs - Global Research Suite | Automated mathematical models; verify with qualified specialists before deployment."
    with PdfPages(buf) as pdf:
        summ_df = pd.DataFrame([{"Case": c, **s} for c, _, _, s in results])
        for start in range(0, len(summ_df), 28):
            fig = plt.figure(figsize=(8.27, 11.69))
            ax = fig.add_axes([0.06, 0.05, 0.88, 0.9])
            ax.axis("off")
            if start == 0:
                ax.text(0, 1, "Analysis Report", fontsize=22, weight="bold", va="top", color=pal["txt"])
                ax.text(0, 0.95, textwrap.fill(title, 80), fontsize=13, va="top", color=pal["c"][4])
                ax.text(0, 0.905, f"Generated {datetime.now():%d %b %Y, %H:%M}  |  {len(results)} case(s)", fontsize=9, va="top", color=pal["txt"])
                ax.text(0, 0.875, textwrap.fill(desc, 100), fontsize=9, va="top", color=pal["txt"])
                top = 0.8
            else:
                top = 0.97
            chunk = summ_df.iloc[start:start + 28]
            tbl = ax.table(cellText=chunk.values, colLabels=list(chunk.columns), loc="upper center",
                           bbox=[0, top - 0.04 * (len(chunk) + 1), 1, 0.04 * (len(chunk) + 1)])
            tbl.auto_set_font_size(False)
            tbl.set_fontsize(7.5)
            for (r, _), cell in tbl.get_celld().items():
                if r == 0:
                    cell.set_facecolor("#7c3aed")
                    cell.set_text_props(color="white", weight="bold")
            fig.text(0.5, 0.02, foot, ha="center", fontsize=6.5, color="#64748b")
            pdf.savefig(fig)
            plt.close(fig)
        for case, vals, plots, summ in results:
            fig = plt.figure(figsize=(8.27, 11.69), facecolor=pal["fig"])
            gs = fig.add_gridspec(5, 2, height_ratios=[0.8, 3, 1.6, 3, 1.6], hspace=0.5, wspace=0.28,
                                  left=0.08, right=0.96, top=0.96, bottom=0.04)
            ah = fig.add_subplot(gs[0, :])
            ah.axis("off")
            ah.text(0, 1, textwrap.fill(f"{title}  -  {case}", 75), fontsize=12, weight="bold", va="top", color=pal["txt"])
            ah.text(0, 0.45, textwrap.fill("Inputs: " + ", ".join(f"{k} = {str(x)[:40]}" for k, x in vals.items()), 125),
                    fontsize=7, va="top", color=pal["txt"])
            for i, p in enumerate(plots):
                r = 1 if i < 2 else 3
                ax = fig.add_subplot(gs[r, i % 2])
                draw_plot(ax, p, pal)
                at = fig.add_subplot(gs[r + 1, i % 2])
                at.axis("off")
                at.text(0, 1, "About: " + textwrap.fill(p["intro"], 52) + "\n\nResult: " + textwrap.fill(p["text"], 52),
                        fontsize=6.6, va="top", color=pal["txt"])
            fig.text(0.5, 0.012, foot, ha="center", fontsize=6, color="#64748b")
            pdf.savefig(fig)
            plt.close(fig)
    return buf.getvalue()


# ----------------------------------------------------------------------------
# 7. UI PIECES
# ----------------------------------------------------------------------------
def show_plot_grid(plots, intro_on=True):
    for r in range(0, 4, 2):
        cs = st.columns(2)
        for j in range(2):
            p = plots[r + j]
            with cs[j]:
                st.markdown(f"<div class='plot-title'>Plot {r+j+1}: {html.escape(p['title'])}</div>", unsafe_allow_html=True)
                if intro_on:
                    st.markdown(f"<div class='intro-text'>📘 {html.escape(p['intro'])}</div>", unsafe_allow_html=True)
                fig = make_fig(p, DARK)
                st.pyplot(fig)
                plt.close(fig)
                st.markdown(f"<div class='live-text'>🔴 LIVE &nbsp;{html.escape(p['text'])}</div>", unsafe_allow_html=True)


def show_metrics(summ):
    cols = st.columns(len(summ))
    for c, (k, val) in zip(cols, summ.items()):
        c.metric(k, str(val))


def param_widgets(spec, tag, only=None):
    vals = {}
    cols = st.columns(3)
    shown = [p for p in spec["params"] if only is None or p[0] in only]
    for i, (k, lab, lo, hi, d, s) in enumerate(shown):
        with cols[i % 3]:
            vals[k] = st.slider(lab, lo, hi, d, s, key=f"{tag}_{k}")
    for k, lab, default in spec.get("text_params", []):
        vals[k] = st.text_input(lab, default, key=f"{tag}_{k}", max_chars=200)
    return vals


def render_live(T, spec, tag):
    st.markdown("##### 🎛️ Move the sliders: all 4 plots and their texts update instantly")
    vals = param_widgets(spec, tag)
    try:
        plots, summ = spec["model"](vals)
    except Exception as e:
        st.error(f"Could not compute with these inputs: {e}")
        return
    show_metrics(summ)
    st.divider()
    show_plot_grid(plots)


def render_upload(T, spec, variant, tag, title):
    dataset = T.get("mode") == "dataset"
    st.markdown("#### Step 1 - Prepare your file like this example")
    if dataset:
        st.caption("Row 1 = column names x and y. Each following row = one measured data point. Save as .xlsx or .csv.")
    else:
        st.caption("Row 1 = column names (keep them exactly). Each following row = one case with your own numbers. Save as .xlsx or .csv.")
    st.dataframe(example_table(T, spec), width="stretch", hide_index=True)
    st.markdown("**What each column means**")
    st.dataframe(variables_table(T, spec), width="stretch", hide_index=True)
    st.download_button("⬇️ Download Excel template (all 11 tools)", build_template(), file_name="VeraLabs_input_template.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"{tag}_tpl")

    st.markdown("#### Step 2 - Upload your file")
    up = st.file_uploader("Excel (.xlsx) or CSV", type=["xlsx", "csv"], key=f"{tag}_file")
    if up is None:
        return
    try:
        if dataset:
            x, y = load_dataset(up, T)
            st.success(f"{len(x)} data points read.")
            vals = {k: d for k, _, _, _, d, _ in spec["params"]}
            vals.update(param_widgets(spec, tag + "_up", only=T["dataset_params"]))
            plots, summ = spec["model"](vals, data=(x, y))
            results = [("Dataset", vals, plots, summ)]
            errors = []
            show_metrics(summ)
            show_plot_grid(plots)
        else:
            df, notes = load_upload(up, T, variant)
            for n_ in notes:
                st.warning(n_)
            results, errors = run_rows(spec, df)
            for e in errors:
                st.error(f"Skipped - {e}")
            if not results:
                return
            st.success(f"{len(results)} case(s) calculated.")
            st.markdown("#### Step 3 - Results")
            st.dataframe(pd.DataFrame([{"Case": c, **s} for c, _, _, s in results]), width="stretch", hide_index=True)
            names = [r_[0] for r_ in results]
            sel = st.selectbox("Preview plots for case", names, key=f"{tag}_prev")
            show_plot_grid(results[names.index(sel)][2])

        st.markdown("#### Step 4 - Download the PDF report")
        sig = (up.name, up.size, tag, str(results[0][1]) if dataset else "")
        if st.button("📄 Generate PDF report", key=f"{tag}_gen"):
            with st.spinner("Building PDF..."):
                st.session_state[f"{tag}_pdf"] = (sig, build_pdf(title, T["desc"], results))
        saved = st.session_state.get(f"{tag}_pdf")
        if saved and saved[0] == sig:
            st.download_button("⬇️ Download PDF report", saved[1], key=f"{tag}_dl", mime="application/pdf",
                               file_name=f"VeraLabs_Tool{T['num']}_report_{datetime.now():%Y%m%d_%H%M}.pdf")
    except Exception as e:
        st.error(f"Could not process the file: {e}. Please compare it with the example above.")


def render_tool_ui(tool_name):
    T = TOOL_REGISTRY[tool_name]
    variant = None
    if T.get("variants"):
        variant = st.selectbox("Choose the formula", list(T["variants"]), key=f"var_{T['num']}")
    spec = get_spec(T, variant)
    vslug = 0 if variant is None else list(T["variants"]).index(variant)
    title = tool_name if variant is None else f"{tool_name} - {variant}"
    tab_live, tab_up = st.tabs(["🎛️ Live Simulator", "📤 Upload My Data & Get PDF Report"])
    with tab_live:
        render_live(T, spec, f"t{T['num']}v{vslug}_live")
    with tab_up:
        render_upload(T, spec, variant, f"t{T['num']}v{vslug}_up", title)


# ----------------------------------------------------------------------------
# 8. PRO GATE + TOOL RENDERING
# ----------------------------------------------------------------------------
def render_pro_gate(tool_name: str):
    st.warning("🔒 **Pro Feature** — This tool requires a Vera Design Labs Pro subscription.", icon="⭐")
    st.caption(TOOL_REGISTRY[tool_name]["desc"])

    left, right = st.columns(2)
    with left:
        st.markdown("#### Step 1 — Purchase access")
        st.write("Complete payment securely via Razorpay. Your Pro Access Key is delivered after payment.")
        st.link_button("💳 Pay with Razorpay", get_secret("RAZORPAY_PAYMENT_LINK", DEFAULT_PAYMENT_LINK), width="stretch")
    with right:
        st.markdown("#### Step 2 — Enter your Pro Access Key")
        attempts = st.session_state.get("key_attempts", 0)
        locked_out = attempts >= MAX_KEY_ATTEMPTS
        key = st.text_input("Pro Access Key", type="password", key=f"key_input_{tool_name}", disabled=locked_out)
        if st.button("Unlock Pro", key=f"unlock_{tool_name}", disabled=locked_out):
            if verify_pro_key(key.strip()):
                st.session_state["pro_unlocked"] = True
                st.rerun()
            else:
                st.session_state["key_attempts"] = attempts + 1
                st.error("Invalid access key.")
        if locked_out:
            st.error("Too many failed attempts. Please refresh the page or contact support.")


def render_tool(tool_name: str):
    access = tool_access_control.get(tool_name, "Pro")  # fail closed
    if access == "Free" or is_pro_unlocked():
        if access == "Pro":
            st.success("✅ Pro access unlocked", icon="⭐")
        render_tool_ui(tool_name)
    else:
        render_pro_gate(tool_name)


def badge(name: str) -> str:
    return "🆓" if tool_access_control.get(name) == "Free" else "⭐"


# ----------------------------------------------------------------------------
# 9. MAIN LAYOUT
# ----------------------------------------------------------------------------
st.title("Vera Design Labs - Global Research Suite")
st.markdown("*Mathematical modeling, analysis and simulation tools for students, researchers and industry.*")

active_tools = [n for n in tool_access_control if n in TOOL_REGISTRY]
free_n = sum(tool_access_control[n] == "Free" for n in active_tools)

with st.sidebar:
    st.header("Account")
    if is_pro_unlocked():
        st.success("Pro: Active")
        if st.button("Sign out of Pro"):
            st.session_state["pro_unlocked"] = False
            st.session_state["key_attempts"] = 0
            st.rerun()
    else:
        st.info("Plan: Free")
    st.divider()
    st.metric("Free tools", free_n)
    st.metric("Pro tools", len(active_tools) - free_n)
    st.divider()
    st.markdown("**Every tool has**\n- 4 plots with a short intro\n- live result text under each plot\n- upload Excel/CSV and download a PDF report")

categories = [LEARN, RESEARCH, INDUSTRY]
tabs = st.tabs(["📚 Catalog"] + categories)

with tabs[0]:
    st.subheader("Tool Catalog")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total tools", len(active_tools))
    c2.metric("Free", free_n)
    c3.metric("Pro", len(active_tools) - free_n)
    st.dataframe(
        pd.DataFrame([
            {"Tool": n, "Lab": TOOL_REGISTRY[n]["category"], "Audience": TOOL_REGISTRY[n]["audience"],
             "Access": tool_access_control[n], "What it does": TOOL_REGISTRY[n]["desc"]}
            for n in sorted(active_tools, key=lambda s: int(s.split(":")[0].split()[1]))
        ]),
        width="stretch", hide_index=True,
    )

for tab, cat in zip(tabs[1:], categories):
    with tab:
        names = [n for n in active_tools if TOOL_REGISTRY[n]["category"] == cat]
        if not names:
            st.info("New tools coming soon.")
            continue
        choice = st.selectbox("Choose a tool", names, format_func=lambda n: f"{badge(n)}  {n}", key=f"nav_{cat}")
        acc = tool_access_control.get(choice, "Pro")
        cls = "badge-free" if acc == "Free" else "badge-pro"
        st.markdown(
            f"<div class='tool-box'><b>{html.escape(choice)}</b> <span class='{cls}'>{acc.upper()}</span><br>"
            f"👥 {html.escape(TOOL_REGISTRY[choice]['audience'])} &nbsp;·&nbsp; {html.escape(TOOL_REGISTRY[choice]['desc'])}</div>",
            unsafe_allow_html=True,
        )
        render_tool(choice)

st.divider()
st.caption("© 2026 Vera Design Labs · Payments processed by Razorpay · Results come from simplified mathematical models; verify with qualified specialists.")

"""
Analyza nis pre AI Knizny Stroj / Amazon KDP research.

Vstup:  data/niche_scan_<datum>.csv - realne nazbierane dna z amazon.com
        (BSR, recenzie, cena) pre top 3 organicke (nie sponzorovane) knihy
        v kazdej z 8 testovanych nis.

Vystup: output/niche_report.csv  - kompletna tabulka so vsetkymi metrikami
        output/niche_report.md   - citatelny report so zavermi

Spustenie: python analyze.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from bsr_model import estimated_daily_sales, estimated_monthly_sales
from kdp_royalty import paperback_royalty

DATA_FILE = Path(__file__).parent / "data" / "niche_scan_2026-09-18.csv"
OUT_CSV = Path(__file__).parent / "output" / "niche_report.csv"
OUT_MD = Path(__file__).parent / "output" / "niche_report.md"

BSR_GREEN_THRESHOLD = 20_000  # prah z checklistu "AI Knizny Stroj"
AD_CPC_USD = 0.65             # stred verejne citovaneho rozsahu 0.38-0.95 $/klik pre kategoriu Books
EUR_TO_USD = 1.08             # priblizny kurz pouzity len na hruby prevod (nie presny K DP list price)


def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_FILE)
    required = {"niche", "title", "price_eur", "reviews", "bsr_overall",
                "competitor_type", "assumed_pages", "kindle_available"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Chybaju stlpce vo vstupnych datach: {missing}")
    if (df["bsr_overall"] <= 0).any():
        raise ValueError("Najdeny neplatny (nekladny) BSR vo vstupe")
    if (df["price_eur"] <= 0).any():
        raise ValueError("Najdena neplatna (nekladna) cena vo vstupe")
    return df


def enrich(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["price_usd"] = (df["price_eur"] * EUR_TO_USD).round(2)
    df["est_daily_sales"] = df["bsr_overall"].apply(estimated_daily_sales)
    df["est_monthly_sales"] = df["bsr_overall"].apply(estimated_monthly_sales)
    df["royalty_per_unit"] = df.apply(
        lambda r: paperback_royalty(r["price_usd"], int(r["assumed_pages"])), axis=1
    )
    df["est_monthly_royalty"] = (df["royalty_per_unit"] * df["est_monthly_sales"]).round(2)
    df["passes_20k_test"] = df["bsr_overall"] < BSR_GREEN_THRESHOLD
    return df


def score_niches(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for niche, g in df.groupby("niche"):
        green_count = int(g["passes_20k_test"].sum())
        avg_reviews = g["reviews"].mean()
        min_reviews = g["reviews"].min()
        median_reviews = g["reviews"].median()
        avg_daily_sales = g["est_daily_sales"].mean()
        avg_monthly_royalty = g["est_monthly_royalty"].mean()
        best_monthly_royalty = g["est_monthly_royalty"].max()

        indie_rows = g[g["competitor_type"] == "indie"]
        indie_slots = len(indie_rows)
        indie_winning_slots = int((indie_rows["bsr_overall"] < 50_000).sum())
        # najlepsi (najnizsi BSR) indie konkurent v nike - realny dokaz, ze
        # sa da s indie/AI knihou realne prebojovat na danom trhu
        best_indie_bsr = indie_rows["bsr_overall"].min() if indie_slots else np.nan

        # heuristicky opportunity score:
        #  - vychadza z priemerneho odhadovaneho dopytu (predaje/den)
        #  - penalizuje sa "moatom" (medianom poctu recenzii top3 - cim vyssi, tym tazsie sa tam predrat)
        #  - tvrdo sa penalizuje, ak ani jeden indie/self-pub titul v nike realne nefunguje
        #    (BSR < 50k) - to znamena, ze miesto drzia len znacky/vydavatelia/celebrity
        moat_factor = np.log10(median_reviews + 10)
        indie_feasible = indie_winning_slots > 0
        feasibility_multiplier = 1.0 if indie_feasible else 0.15
        opportunity_score = (avg_daily_sales / moat_factor) * feasibility_multiplier

        kindle_available = bool(g["kindle_available"].iloc[0])
        rows.append({
            "niche": niche,
            "format": "paperback+kindle" if kindle_available else "paperback ONLY",
            "green_count_of_3": green_count,
            "passes_checklist(>=2/3)": green_count >= 2,
            "avg_reviews_top3": round(avg_reviews, 0),
            "median_reviews_top3": round(median_reviews, 0),
            "min_reviews_top3": int(min_reviews),
            "avg_est_daily_sales": round(avg_daily_sales, 2),
            "indie_slots_of_3": indie_slots,
            "indie_winning_slots(bsr<50k)": indie_winning_slots,
            "best_indie_bsr": None if np.isnan(best_indie_bsr) else int(best_indie_bsr),
            "indie_feasible": indie_feasible,
            "avg_est_monthly_royalty_per_book_$": round(avg_monthly_royalty, 0),
            "best_est_monthly_royalty_per_book_$": round(best_monthly_royalty, 0),
            "opportunity_score": round(opportunity_score, 2),
        })
    result = pd.DataFrame(rows).sort_values("opportunity_score", ascending=False).reset_index(drop=True)
    return result


def sanity_checks(detail: pd.DataFrame, scored: pd.DataFrame) -> list:
    """Vracia zoznam problemov, ak nejake nastanu (namiesto tichého zlyhania)."""
    problems = []
    if detail["est_daily_sales"].isna().any():
        problems.append("NaN v est_daily_sales")
    if (detail["royalty_per_unit"] < 0).any():
        problems.append("Zaporny royalty_per_unit - skontroluj cenu/pocet stran")
    if scored["opportunity_score"].isna().any():
        problems.append("NaN v opportunity_score")
    # kontrola, ze sudoku (najsilnejsia nika v surovych datach) skoncila v hornej polovici rebricka
    top_half = scored.head(len(scored) // 2 + 1)["niche"].tolist()
    if "sudoku_puzzle_book" not in top_half:
        problems.append("sudoku_puzzle_book by malo byt v hornej polovici rebricka podla surovych BSR dat")
    if "wedding_planner" in top_half:
        problems.append("wedding_planner (0/3 <20k, len tradicni vydavatelia) by nemalo byt v hornej polovici")
    # nizko-obsahove niky (puzzle/planner/tracker) musia byt oznacene ako paperback-only,
    # inak by sa niekomu mohlo zdat, ze si moze vybrat aj ebook varinatu tam, kde realne neexistuje
    low_content_niches = {"sudoku_puzzle_book", "large_print_sudoku_seniors", "budget_planner",
                           "debt_payoff_tracker", "habit_tracker_journal", "wedding_planner"}
    wrongly_flagged = detail[detail["niche"].isin(low_content_niches) & detail["kindle_available"]]
    if not wrongly_flagged.empty:
        problems.append(f"Nizko-obsahova nika oznacena ako kindle_available=True: {wrongly_flagged['niche'].unique().tolist()}")
    return problems


def df_to_markdown(df: pd.DataFrame) -> str:
    """Minimalny markdown-table writer (bez zavislosti na 'tabulate', ktory tu nie je dostupny)."""
    cols = [str(c) for c in df.columns]
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    body_lines = []
    for _, row in df.iterrows():
        cells = ["" if pd.isna(v) else str(v) for v in row.tolist()]
        body_lines.append("| " + " | ".join(cells) + " |")
    return "\n".join([header, sep] + body_lines)


def write_markdown_report(detail: pd.DataFrame, scored: pd.DataFrame) -> None:
    lines = []
    lines.append("# Vysledky prieskumu 8 nis na Amazon KDP\n")
    lines.append("Dátum zberu dát: 2026-09-18 · Zdroj: amazon.com (organicke, nesponzorovane top-3 vysledky na klucove slovo)\n")
    lines.append("## Rebricek nis podla opportunity_score\n")
    lines.append(df_to_markdown(scored))
    lines.append("\n\n## Detailne data (24 knih)\n")
    cols = ["niche", "title", "competitor_type", "price_usd", "reviews",
            "bsr_overall", "passes_20k_test", "est_daily_sales",
            "royalty_per_unit", "est_monthly_royalty"]
    lines.append(df_to_markdown(detail[cols]))
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    df = load_data()
    detail = enrich(df)
    scored = score_niches(detail)

    problems = sanity_checks(detail, scored)
    if problems:
        print("POZOR - sanity check zlyhal:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1

    OUT_CSV.parent.mkdir(exist_ok=True)
    detail.to_csv(OUT_CSV, index=False)
    write_markdown_report(detail, scored)

    pd.set_option("display.width", 160)
    pd.set_option("display.max_columns", 20)
    print("\n=== REBRICEK NIS (opportunity_score, zostupne) ===\n")
    print(scored.to_string(index=False))
    print(f"\nUlozene: {OUT_CSV}")
    print(f"Ulozene: {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

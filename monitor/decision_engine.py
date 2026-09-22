"""
Rozhodovaci engine pre KDP ebook portfolio.

Vstup: bsr_history.csv (asin, date, bsr, price_usd) - manualne alebo cez
       browser session dopancane zaznamy BSR v case (Amazon blokuje
       automatizovane stahovanie CAPTCHou, pozri README.md).

Vystup: pre kazdy sledovany ASIN konkretne odporucanie (drz cenu / zdvihni
        cenu / zniz cenu / spusti promo / prepis popis a obalku), s
        dovodom a cislami.

Tato cast JE plne automaticka - ked su data v CSV, engine sam rozhodne.
Nic sa tu neuhaduje rucne.
"""
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from kdp_royalty import ebook_royalty

HISTORY_FILE = Path(__file__).parent / "bsr_history.csv"
BOOKS_FILE = Path(__file__).parent / "tracked_books.csv"
OUT_FILE = Path(__file__).parent / "recommendations.csv"

STRONG_BSR = 20_000
NEW_BOOK_MIN_DAYS = 14
TREND_WINDOW_DAYS = 14
IMPROVING_THRESHOLD = -0.20   # BSR kleslo o 20%+ = zlepsenie (nizsie cislo = lepsie)
WORSENING_THRESHOLD = 0.30    # BSR stuplo o 30%+ = zhorsenie
FLAT_BAND = 0.10              # +-10% = povazujeme za stagnaciu


@dataclass
class Recommendation:
    asin: str
    title: str
    latest_bsr: int
    trend_pct: float
    status: str
    action: str
    reason: str
    suggested_price: float
    royalty_at_suggested: float


def load_history() -> pd.DataFrame:
    df = pd.read_csv(HISTORY_FILE, parse_dates=["date"])
    if df.empty:
        raise ValueError("bsr_history.csv je prazdny - nie je co vyhodnocovat")
    if (df["bsr"] <= 0).any():
        raise ValueError("Najdeny neplatny (nekladny) BSR v historii")
    return df.sort_values(["asin", "date"])


def load_books() -> pd.DataFrame:
    return pd.read_csv(BOOKS_FILE)


def trend_pct(series_bsr: pd.Series) -> float:
    """% zmena BSR medzi prvym a poslednym zaznamom v okne. Zaporne = zlepsenie."""
    if len(series_bsr) < 2:
        return 0.0
    first, last = series_bsr.iloc[0], series_bsr.iloc[-1]
    if first == 0:
        return 0.0
    return (last - first) / first


def decide_for_book(asin: str, title: str, current_price: float, hist: pd.DataFrame) -> Recommendation:
    hist = hist[hist["asin"] == asin].sort_values("date")
    window = hist[hist["date"] >= hist["date"].max() - pd.Timedelta(days=TREND_WINDOW_DAYS)]
    latest_bsr = int(hist["bsr"].iloc[-1])
    days_tracked = (hist["date"].max() - hist["date"].min()).days
    pct = trend_pct(window["bsr"])

    if days_tracked < NEW_BOOK_MIN_DAYS:
        return Recommendation(
            asin, title, latest_bsr, round(pct, 3), "NOVA_KNIHA",
            "CAKAJ", f"Len {days_tracked} dni dat, potrebujem aspon {NEW_BOOK_MIN_DAYS} na trend.",
            current_price, ebook_royalty(current_price),
        )

    if latest_bsr < STRONG_BSR and pct <= IMPROVING_THRESHOLD:
        new_price = round(current_price + 1.0, 2)
        return Recommendation(
            asin, title, latest_bsr, round(pct, 3), "VYHRAVA",
            f"ZDVIHNI CENU na {new_price:.2f} $ a otestuj",
            f"BSR silny ({latest_bsr:,}) a zlepsuje sa o {abs(pct)*100:.0f}%. Priestor zvysit maржu, kym dopyt drzi.",
            new_price, ebook_royalty(new_price),
        )

    if latest_bsr < STRONG_BSR and abs(pct) <= FLAT_BAND:
        return Recommendation(
            asin, title, latest_bsr, round(pct, 3), "STABILNA",
            "DRZ CENU, reinvestuj do marketingu",
            f"BSR silny ({latest_bsr:,}) a stabilny. Netreba menit cenu, tlac dalej organicky marketing.",
            current_price, ebook_royalty(current_price),
        )

    if pct >= WORSENING_THRESHOLD:
        new_price = round(max(current_price - 1.0, 2.99), 2)
        return Recommendation(
            asin, title, latest_bsr, round(pct, 3), "PADA",
            f"ZNIZ CENU na {new_price:.2f} $ + spusti $0 marketing push",
            f"BSR sa zhorsil o {pct*100:.0f}% za {TREND_WINDOW_DAYS} dni. Over, ci si nedavno zdvihol cenu (vrat ju spat), inak spusti promo.",
            new_price, ebook_royalty(new_price),
        )

    if latest_bsr >= STRONG_BSR and abs(pct) <= FLAT_BAND:
        return Recommendation(
            asin, title, latest_bsr, round(pct, 3), "MRTVA",
            "PREPIS OBALKU/POPIS alebo spusti KDP Select promo (5 dni zdarma)",
            f"BSR slaby ({latest_bsr:,}) a dlhodobo sa nehyba. Kniha si nenasla publikum organicky - treba reset, nie cakat.",
            current_price, ebook_royalty(current_price),
        )

    return Recommendation(
        asin, title, latest_bsr, round(pct, 3), "SLEDUJ",
        "ZATIAL NIC, sleduj dalsi tyzden",
        "Zmiesany signal, potrebuje dlhsie okno na jasne rozhodnutie.",
        current_price, ebook_royalty(current_price),
    )


def sanity_checks(recs: list) -> list:
    problems = []
    for r in recs:
        if r.royalty_at_suggested < 0:
            problems.append(f"{r.asin}: zaporny royalty pri navrhovanej cene {r.suggested_price}")
        if r.suggested_price < 2.99:
            problems.append(f"{r.asin}: navrhovana cena {r.suggested_price} pod 2.99 $ - padne na 35% royalty pasmo")
    return problems


def main() -> int:
    books = load_books()
    history = load_history()

    recs = []
    for _, row in books.iterrows():
        rec = decide_for_book(row["asin"], row["title"], float(row["current_price_usd"]), history)
        recs.append(rec)

    problems = sanity_checks(recs)
    if problems:
        print("POZOR:")
        for p in problems:
            print(f"  - {p}")

    out_df = pd.DataFrame([r.__dict__ for r in recs])
    out_df.to_csv(OUT_FILE, index=False)

    pd.set_option("display.width", 160)
    pd.set_option("display.max_columns", 20)
    print("\n=== ODPORUCANIA ===\n")
    print(out_df.to_string(index=False))
    print(f"\nUlozene: {OUT_FILE}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())

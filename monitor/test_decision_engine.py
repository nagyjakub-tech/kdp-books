"""
Samotest decision_engine.py na syntetickych, rucne skonstruovanych scenaroch,
aby bolo isté, ze kazda vetva rozhodovania robi presne to, co ma.
Spustenie: python test_decision_engine.py
"""
import pandas as pd

from decision_engine import decide_for_book

BASE_DATE = pd.Timestamp("2026-09-01")


def days(offsets_and_bsr, asin="TEST"):
    rows = []
    for offset, bsr in offsets_and_bsr:
        rows.append({"asin": asin, "date": BASE_DATE + pd.Timedelta(days=offset), "bsr": bsr, "price_usd": 2.99})
    return pd.DataFrame(rows)


def check(name, expected_status, hist_df, price=2.99):
    rec = decide_for_book("TEST", name, price, hist_df)
    ok = rec.status == expected_status
    print(f"[{'OK' if ok else 'FAIL'}] {name:30s} -> {rec.status:12s} (ocakavane {expected_status:12s}) | {rec.action}")
    return ok


def main():
    results = []

    # 1. Nova kniha - len 5 dni dat -> musi cakat
    results.append(check(
        "Nova kniha (5 dni)", "NOVA_KNIHA",
        days([(0, 500_000), (5, 450_000)]),
    ))

    # 2. Vyhrava - silny BSR, zlepsuje sa >20% za 14 dni
    results.append(check(
        "Vyhrava (BSR 18k, zlepsenie)", "VYHRAVA",
        days([(0, 25_000), (7, 20_000), (14, 18_000)]),
    ))

    # 3. Stabilna - silny BSR, plocha krivka
    results.append(check(
        "Stabilna (BSR 15k, flat)", "STABILNA",
        days([(0, 15_000), (7, 15_500), (14, 15_200)]),
    ))

    # 4. Pada - zhorsenie o viac ako 30% za 14 dni
    results.append(check(
        "Pada (BSR 50k->80k)", "PADA",
        days([(0, 50_000), (7, 65_000), (14, 80_000)]),
    ))

    # 5. Mrtva - slaby BSR, dlhodobo sa nehyba
    results.append(check(
        "Mrtva (BSR 800k, flat)", "MRTVA",
        days([(0, 800_000), (7, 820_000), (14, 810_000)]),
    ))

    # 6. Zmiesany signal - slaby BSR ale prudko sa zlepsuje (viac ako 20% zlepsenie),
    #    no stale nad prahom STRONG_BSR -> nespada ani do VYHRAVA (lebo BSR>20k),
    #    ani do MRTVA (lebo sa hybe) -> SLEDUJ
    results.append(check(
        "Zmiesany (BSR 200k->140k)", "SLEDUJ",
        days([(0, 200_000), (7, 170_000), (14, 140_000)]),
    ))

    passed = sum(results)
    print(f"\n{passed}/{len(results)} testov presiel")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())

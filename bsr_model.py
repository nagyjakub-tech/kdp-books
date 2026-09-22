"""
BSR -> odhad predajov/den.

Amazon nezverejnuje presny vzorec medzi Best Sellers Rank a poctom predajov.
Kotevne body nizsie su zostavene z verejne publikovanych benchmarkov
(Kindlepreneur / Publisher Rocket BSR calculator, BookBeam, BookBloom -
pozri README.md), ktore sa zhoduju v ramcoch:
  BSR < 5 000        -> desiatky predajov/den
  BSR 5 000-50 000    -> 1-10 predajov/den
  BSR 50 000-100 000  -> cca 1 predaj/den
  BSR > 500 000       -> ojedinele predaje

Toto NIE JE oficialny Amazon vzorec, je to interpolacia verejnych odhadov.
Pouzivame ju len na relativne porovnanie nis medzi sebou, nie ako presnu
predikciu.
"""
import numpy as np

_ANCHOR_BSR = np.array([1, 100, 500, 1000, 5000, 10000, 20000, 50000,
                         100000, 200000, 500000, 1000000, 2000000, 5000000])
_ANCHOR_SALES = np.array([3000, 500, 200, 120, 30, 15, 7, 3,
                           1.3, 0.6, 0.15, 0.05, 0.02, 0.005])

_LOG_BSR = np.log10(_ANCHOR_BSR)
_LOG_SALES = np.log10(_ANCHOR_SALES)


def estimated_daily_sales(bsr: float) -> float:
    """Interpoluje odhad predajov/den z BSR (log-log lin. interpolacia)."""
    if bsr <= 0:
        raise ValueError("BSR musi byt kladne cislo")
    log_bsr = np.log10(bsr)
    log_sales = np.interp(log_bsr, _LOG_BSR, _LOG_SALES)
    return float(10 ** log_sales)


def estimated_monthly_sales(bsr: float) -> float:
    return estimated_daily_sales(bsr) * 30.437  # priemerny pocet dni v mesiaci


if __name__ == "__main__":
    # rychla kontrola proti hodnotam citovanym vo verejnych zdrojoch
    checks = [(20000, 7), (50000, 3), (100000, 1.3), (500000, 0.15)]
    for bsr, expected in checks:
        got = estimated_daily_sales(bsr)
        print(f"BSR {bsr:>9,} -> {got:6.2f} predajov/den  (kotva: {expected})")

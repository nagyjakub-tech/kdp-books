"""
Honorarove (royalty) vzorce Amazon KDP, platne 2026, marketplace amazon.com,
standardny (regular) trim size.
Zdroj: kdp.amazon.com/help/topic/G201834340 (Paperback Printing Cost),
krizovo overene cez Kindlepreneur a KDPage kalkulacky (viz README.md).

OPRAVA (2026-09-22): povodna verzia pouzivala nespravnu fixnu zlozku
0.85 $ pre B&W tlac. Oficialny vzorec je stupnovity podla poctu stran:
  24-110 str.  -> flat 2.30 $ (ziadna cena za stranu)
  110-828 str. -> 1.00 $ + 0.012 $/strana
Vsetky nase odhady (110-280 str.) spadaju do druheho pasma, takze chyba
sa prejavila ako fixnych +0.15 $ tlacovych nakladov navyse pri KAZDEJ
knihe v datasete (t.j. royalty/kus bolo o 0.15 $ vyssie, nez malo byt).
"""

PAPERBACK_LOW_PAGE_FLAT_COST = 2.30
PAPERBACK_LOW_PAGE_MAX = 110

PAPERBACK_FIXED_COST = 1.00
PAPERBACK_BW_PER_PAGE = 0.012
PAPERBACK_COLOR_STD_PER_PAGE = 0.0255
PAPERBACK_COLOR_PREMIUM_PER_PAGE = 0.065

EBOOK_LOW_RATE = 0.35
EBOOK_HIGH_RATE = 0.70
EBOOK_HIGH_RATE_MIN_PRICE = 2.99
EBOOK_HIGH_RATE_MAX_PRICE = 12.99
EBOOK_DELIVERY_PER_MB = 0.15


def paperback_print_cost(pages: int, color: bool = False) -> float:
    if pages <= 0:
        raise ValueError("pocet stran musi byt kladny")
    if pages <= PAPERBACK_LOW_PAGE_MAX:
        return PAPERBACK_LOW_PAGE_FLAT_COST
    per_page = PAPERBACK_COLOR_STD_PER_PAGE if color else PAPERBACK_BW_PER_PAGE
    return PAPERBACK_FIXED_COST + pages * per_page


def paperback_royalty(price: float, pages: int, color: bool = False) -> float:
    rate = 0.6 if price >= 9.99 else 0.5
    royalty = price * rate - paperback_print_cost(pages, color)
    return max(royalty, 0.0)


def ebook_royalty(price: float, size_mb: float = 3.0) -> float:
    if EBOOK_HIGH_RATE_MIN_PRICE <= price <= EBOOK_HIGH_RATE_MAX_PRICE:
        delivery = size_mb * EBOOK_DELIVERY_PER_MB
        return max(price * EBOOK_HIGH_RATE - delivery, 0.0)
    return max(price * EBOOK_LOW_RATE, 0.0)


if __name__ == "__main__":
    # kontrola proti oficialnemu prikladu z kdp.amazon.com/help: 300 str. B&W -> tlac 4.60$
    pc = paperback_print_cost(300)
    print(f"Tlac 300 str. B&W -> {pc:.2f}$ (ocakavane 4.60$ podla oficialnej dokumentacie)")
    # kontrola nizkeho pasma (<=110 str.) -> flat 2.30$
    pc_low = paperback_print_cost(100)
    print(f"Tlac 100 str. B&W -> {pc_low:.2f}$ (ocakavane flat 2.30$)")
    r = paperback_royalty(12.99, 200)
    print(f"Paperback 12.99$/200str B&W -> royalty {r:.2f}$ (opravene, povodne 4.54$ bolo o 0.15$ vyssie)")
    r2 = ebook_royalty(4.99, size_mb=2)
    print(f"Ebook 4.99$ -> royalty {r2:.2f}$ (ocakavane ~3.19$)")

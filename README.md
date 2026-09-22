# KDP niche research — metodika, zdroje, limity

## Opravy po nezávislej kontrole (2026-09-22)

Pri spätnej kontrole vlastnej práce som našiel a opravil 2 reálne chyby:

1. **Tlačový vzorec bol nesprávny.** Pôvodná verzia počítala s fixným
   nákladom 0,85 $ pre B&W tlač. Podľa oficiálnej KDP dokumentácie
   (kdp.amazon.com/help/topic/G201834340) je vzorec stupňovitý: knihy do
   110 strán majú flat náklad 2,30 $ (žiadna cena za stranu), knihy nad
   110 strán majú 1,00 $ fix + 0,012 $/strana. Chyba spôsobila, že honorár
   na kus bol vo všetkých nikách nadhodnotený o 0,15 $ — relatívne najviac
   to skreslilo práve tenké, lacné knihy (planner/puzzle), kde je to
   until 20-30 % rozdielu na honorári na kus. Opravené v `kdp_royalty.py`,
   všetky čísla v `output/` sú prepočítané s opraveným vzorcom.
2. **Nikde nebolo explicitne povedané, že odporúčané niky vyžadujú
   FYZICKÚ (paperback) knihu, nie e-book.** Celý dataset od začiatku
   obsahoval len tlačené BSR dáta, ale toto obmedzenie nebolo
   pomenované. Priamou kontrolou na amazon.com (tlačidlá dostupných
   formátov na product page) som overil: sudoku/puzzle knihy, plánovače,
   trackery a journaly (kam do písať perom priamo na stránku) **nemajú
   Kindle edíciu vôbec** — dá sa ich vydať len ako paperback. Kuchárky,
   workbooky a business knihy (súvislý text) majú aj Kindle aj paperback.
   Pridaný stĺpec `kindle_available` do dát + sanity check v `analyze.py`,
   ktorý by zlyhal, keby bola nízko-obsahová nika omylom označená ako
   dostupná na Kindle.

Konkrétne priamo overené (nie len odvodené z kategórie):
`B0DKTMJ1KC` (sudoku, len paperback), `B0FBM179D7` (sudoku, len
paperback), `B0C7J5GL8Q` (bill tracker, len paperback), `1628603135`
(kuchárka, paperback+Kindle), `164848557X` (workbook, paperback+Kindle).

Kód a dáta v tomto priečinku odpovedajú na krok 3 ("kde presne hľadať dáta")
z predošlej analýzy `aikniznystroj.sk` — ale namiesto teórie sme spravili
skutočný zber dát zo živého amazon.com a naprogramovali vyhodnotenie.

## Ako to funguje

1. `data/niche_scan_2026-09-18.csv` — surové dáta z **8 kandidátskych nís**
   (kombinácia príkladov z ich PDF + vlastný výber naprieč kategóriami).
   Pre každú niku sme zobrali **top 3 organické (nie sponzorované) výsledky**
   vyhľadávania na amazon.com a z product page vytiahli:
   - `bsr_overall` — Best Sellers Rank v kategórii Books
   - `reviews` — počet recenzií (proxy pre "moat"/konkurenčnú bariéru)
   - `price_eur` — cena zobrazená pri doručení na Slovensko
   - `competitor_type` — **ručne anotované** (`indie` vs `traditional`) podľa
     rozpoznania vydavateľa/autora (napr. Victory Belt Publishing, Peter
     Pauper Press, New Harbinger, America's Test Kitchen, Cesar Millan, Zak
     George = `traditional`; generické neznáme mená bez vydavateľstva =
     `indie`). Toto NIE JE zoškrabané automaticky, je to editoriálny úsudok
     nad verejne dostupnými menami — dá sa mýliť pri hraničných prípadoch.
   - `assumed_pages` — odhad počtu strán podľa typu knihy (nebolo
     systematicky zoškrabané, je to vstup pre výpočet honoráru; pri výbere
     konkrétnej niky na realizáciu si over skutočný počet strán u top kníh).

2. `bsr_model.py` — BSR → odhad predajov/deň. Amazon tento vzorec
   nezverejňuje. Kotevné body sú zostavené z verejne publikovaných
   benchmarkov (nie z jedného zdroja):
   - Kindlepreneur BSR Calculator — https://kindlepreneur.com/amazon-kdp-sales-rank-calculator/
   - BookBloom BSR-to-Sales guide — https://www.bookbloom.io/blog/bsr-to-sales-calculator-guide
   - BookBeam Amazon Book Sales Calculator — https://bookbeam.io/amazon-book-sales-calculator/

   **Toto je heuristika na relatívne porovnanie, nie presná predikcia.**
   Samotné verejné kalkulačky sa medzi sebou líšia v detailoch krivky.

3. `kdp_royalty.py` — oficiálne vzorce KDP (overené proti
   kdp.amazon.com/help): paperback 50/60 % podľa ceny mínus tlačové náklady
   (0,85 $ fix + 0,012 $/strana čb), ebook 35/70 % podľa cenového pásma.

4. `analyze.py` — spojí dáta, spočíta odhadovaný dopyt a honorár, oskóruje
   8 nís vlastným `opportunity_score` (nie je to metrika kurzu — je to naša
   vlastná váha, ktorá berie do úvahy dopyt, konkurenčný moat aj to, či tam
   vôbec **existuje reálny dôkaz, že to zvládol nezávislý vydavateľ**, nie
   len značka/vydavateľstvo/celebrita).

## Kľúčové zistenie, ktoré mení odporúčanie

Vlastný "5-minútový test" z ich PDF (BSR pod 20 000 aspoň v 2 z 3 kníh)
**nerozlišuje, KTO tie knihy vydal**. V dátach sme narazili na niky, kde
test formálne "prejde", ale všetky dobré pozície držia tradiční vydavatelia
alebo celebrity, ktorých nový anonymný autor s AI knihou reálne nemôže
poraziť:

| Nika | Test kurzu (≥2/3 <20k) | Kto reálne drží dobré pozície | Náš verdikt |
|---|---|---|---|
| dog_training_book | ✅ PREJDE (2/3) | Cesar Millan (TV celebrita) + Zak George (YouTube celebrita) | ⚠️ PASCA — test prejde, ale nedá sa reálne obsadiť |
| keto_cookbook | ❌ nepREJDE (1/3) | Victory Belt Publishing (špecializované vydavateľstvo) drží všetky 3 | ⚠️ Vyhni sa |
| anxiety_workbook | ❌ nepREJDE (1/3) | New Harbinger + kvalifikovaní PhD/PsyD autori | ⚠️ Vyhni sa (aj regulačné riziko) |
| sudoku_puzzle_book | ✅ PREJDE (3/3) | 2 z 3 sú anonymné indie tituly, ktoré reálne vyhrávajú | ✅ Najlepšia nika v datasete |
| air_fryer_cookbook | ✅ PREJDE (2/3) | 2 z 3 sú indie (jeden má len 107 recenzií a BSR #6 580!) | ✅ Silná nika |
| budget_planner | ❌ nepREJDE (1/3) podľa naivného testu | Ale jediný indie titul (Bill Tracker) má najlepší BSR spomedzi všetkých 3 | ✅ Test kurzu by ťa odradil neprávom |
| wedding_planner | ❌ nepREJDE (0/3) | 100 % tradiční vydavatelia (Peter Pauper Press) | ❌ Vyhni sa |
| small_business_ideas | ❌ nepREJDE (0/3) | Slabý dopyt aj pre indie aj pre tradičné tituly | ❌ Vyhni sa |

## Limity (buď si ich vedomý, než na tom postavíš rozhodnutie)

- **8 nís a 3 knihy/nika je vzorka na orientáciu, nie štatisticky robustný
  prieskum.** Pred reálnym vstupom do niky spočítaj 10-15 titulov, nie 3.
- Ceny sú zachytené v EUR pri doručení na Slovensko — nemusia presne
  zodpovedať USD list price, z ktorej KDP počíta honorár (drobná odchýlka
  pri hraničných cenách okolo 9,99 $ môže zmeniť sadzbu z 50 % na 60 %).
- `assumed_pages` je odhad, nie odscrapovaný údaj — priamo ovplyvňuje
  tlačové náklady a teda aj honorár na kus.
- BSR→predaje krivka je verejná heuristika s veľkou neistotou najmä pri
  nízkych BSR (pod 5 000) — čísla tam berte ako rádovú predstavu, nie presné.
- `est_monthly_royalty` pri TOP knihe v nike ukazuje **strop toho, čo
  zarába etablovaný líder** (roky recenzií), nie to, čo zarobí nová kniha
  v 1. mesiaci. Nová kniha štartuje pri BSR v miliónoch a musí sa
  prepracovať hore.

## Ako to spustiť znova / rozšíriť

```bash
python analyze.py
```

Vypíše rebríček do konzoly a uloží `output/niche_report.csv` a
`output/niche_report.md`. Pre novú niku pridaj riadky do CSV podľa
rovnakej schémy a skript ich automaticky zahrnie.

# Monitoring + rozhodovací systém pre KDP ebook portfólio

## Čo je tu automatické, čo nie

**Plne automaticky beží:** `decision_engine.py`. Nakŕmi sa dátami z
`bsr_history.csv` a pre každú knihu vypľuje presné rozhodnutie (zdvihni/znížz
cenu, drž, spusti promo, prepíš popis) aj s číslom novej ceny a
honorárom pri tej cene. Nič sa tu neháda ručne — je to kód, otestovaný
proti 6 scenárom v `test_decision_engine.py` (6/6 prešlo).

**Nedá sa automatizovať (Amazon to blokuje, nie ja):** sťahovanie BSR z
amazon.com. Priamy test (`requests.get` na product page) vrátil CAPTCHA
stránku namiesto dát — Amazon blokuje neprehliadačové požiadavky. Obchádzať
CAPTCHu nebudem. Jediný spôsob, ako sa k reálnym BSR dátam dostať, je
skutočný prehliadač — buď ty (30 sekúnd denne skontroluješ 3 čísla), alebo
ja v živej session keď mi napíšeš "skontroluj knihy".

## Denný postup (30 sekúnd)

1. Choď na amazon.com/dp/<ASIN> pre každú sledovanú knihu
2. Pozri "Best Sellers Rank" v Product details
3. Pridaj riadok do `bsr_history.csv`: `asin,date,bsr,price_usd`
4. Spusti `python decision_engine.py`
5. Prečítaj `recommendations.csv` — presne vieš čo robiť ďalej

## Pravidlá rozhodovania (kodifikované, nie pocit)

| Stav | Podmienka | Akcia |
|---|---|---|
| VYHRAVA | BSR < 20 000 a zlepšuje sa o 20 %+ za 14 dní | zdvihni cenu o 1 $, otestuj |
| STABILNA | BSR < 20 000, plochá krivka (±10 %) | drž cenu, tlač marketing |
| PADA | BSR sa zhoršil o 30 %+ za 14 dní | zníž cenu o 1 $ (min. 2,99 $) + $0 marketing push |
| MRTVA | BSR > 20 000, dlhodobo plochá krivka | prepíš obálku/popis alebo KDP Select 5-dňové promo zdarma |
| NOVA_KNIHA | menej než 14 dní dát | čakaj, zbieraj dáta |
| SLEDUJ | zmiešaný signál | ďalší týždeň bez zásahu |

## Prečo cloud rutina nefunguje na scraping

Cloud agent nemá prístup k reálnemu prehliadaču (ten beží len v desktop
appke), takže by musel ísť cez `curl`/`WebFetch` — presne to, čo som
otestoval a čo Amazon blokuje CAPTCHou. Cloud rutina preto v tomto setupe
beží na **generovanie marketingového obsahu a spracovanie dát, ktoré
tam nahráš** (napr. cez GitHub commit), nie na samotné sťahovanie BSR.

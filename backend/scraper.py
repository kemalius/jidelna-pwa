"""
Scraper pro jídelní systém Fusion na 213.29.8.169.

Struktura stránky (zjištěno z reálného HTML):
- Jeden den = jedna dávka <div class="rec"> bloků za sebou.
- První .rec bez .price obsahuje polévky (.menutxt), zbytek jsou hlavní jídla.
- Hlavní jídlo: <div class="price">139 Kč</div> + <div class="menuoff">N) Název <sup>alergeny</sup> <span title="tag">ikona</span>...</div>
- Aktuálně objednané jídlo dne má třídu "menuon" místo "menuoff".
- Ikony (span[title]) značí: Ryba, Vegetariánské, Houby, Bezlepkové, Nové jídlo apod.
- Stránka je v iso-8859-2 (nutno nastavit encoding ručně, apparent_encoding to netrefí spolehlivě).

Spouštět MUSÍŠ ze sítě/VPN, kde je 213.29.8.169 dostupná, a s platnou
přihlašovací session (systém vyžaduje login - viz POZNÁMKA níže).
"""

import re
import requests
from bs4 import BeautifulSoup
from datetime import date
from dataclasses import dataclass, field, asdict
from typing import Optional

BASE_URL = "http://213.29.8.169:55080/fusion/jidelna-objednavky/menu.php"
LOGIN_URL = "http://213.29.8.169:55080/fusion/jidelna-objednavky/login.php"

# Přihlašovací údaje NIKDY nedávej natvrdo do kódu - nastav je v souboru .env
# (JIDELNA_LOGIN=..., JIDELNA_HESLO=...) vedle tohoto souboru.
import os
from dotenv import load_dotenv
load_dotenv()
JIDELNA_LOGIN = os.environ.get("JIDELNA_LOGIN", "")
JIDELNA_HESLO = os.environ.get("JIDELNA_HESLO", "")


def login(session: requests.Session | None = None) -> requests.Session:
    """Přihlásí se do Fusion systému a vrátí session s platnými cookies.

    Ověřeno podle skutečného přihlašovacího formuláře (login.php, pole
    "login" a "pass", plus skrytá pole desk=0 a log=1).
    """
    if not JIDELNA_LOGIN or not JIDELNA_HESLO:
        raise RuntimeError(
            "Chybí přihlašovací údaje. Nastav proměnné prostředí "
            "JIDELNA_LOGIN a JIDELNA_HESLO."
        )

    s = session or requests.Session()
    payload = {
        "desk": "0",
        "log": "1",
        "login": JIDELNA_LOGIN,
        "pass": JIDELNA_HESLO,
    }
    resp = s.post(LOGIN_URL, data=payload, timeout=10)
    resp.raise_for_status()
    resp.encoding = "iso-8859-2"

    if "logout.php" not in resp.text and "ODHLÁSIT" not in resp.text:
        raise RuntimeError(
            "Přihlášení pravděpodobně selhalo - zkontroluj JIDELNA_LOGIN "
            "a JIDELNA_HESLO, případně mi pošli text odpovědi serveru."
        )
    return s

ALLERGEN_MAP = {
    "1": "Obiloviny obsahující lepek", "2": "Korýši", "3": "Vejce", "4": "Ryby",
    "5": "Arašídy", "6": "Sója", "7": "Mléko", "8": "Ořechy", "9": "Celer",
    "10": "Hořčice", "11": "Sezamová semena", "12": "Oxid siřičitý a siřičitany",
    "13": "Vlčí bob", "14": "Měkkýši",
}


@dataclass
class SoupItem:
    text: str  # obsahuje obě polévky pohromadě, viz POZNÁMKA v parse_menu


@dataclass
class MenuItem:
    number: int  # pořadové číslo jídla v nabídce (1,2,3...)
    name: str
    price: Optional[float]
    allergens: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)  # z ikon: Vegetariánské, Ryba, Bezlepkové, Houby, Nové jídlo
    is_selected: bool = False  # True = tohle je aktuálně objednané jídlo pro daný den
    shift: int = 1
    day: int = 1
    date: str = ""

    @property
    def id(self) -> str:
        return f"{self.date}-{self.shift}-{self.day}-{self.number}"


def fetch_menu_html(dat: str | None = None, shift: int = 1, day: int = 1, session: requests.Session | None = None) -> str:
    """Stáhne HTML jídelníčku. dat ve formátu YYYYMMDD.

    Pokud dat=None, parametr se vůbec neposílá a server sám vrátí ten den,
    který právě považuje za aktuální (spolehlivější než hádat datum
    lokálně, protože systémové datum na klientovi se s tím serverem
    nemusí vždy shodovat).

    POZNÁMKA: systém vyžaduje přihlášenou session - viz login().
    """
    params = {"shift": shift, "day": day}
    if dat:
        params["dat"] = dat
    s = session or requests.Session()
    resp = s.get(BASE_URL, params=params, timeout=10)
    resp.raise_for_status()
    resp.encoding = "iso-8859-2"
    return resp.text


def _in_offers_section(el) -> bool:
    """True pokud element leží uvnitř #offers (skrytá BURZA nabídka, ne skutečné denní menu)."""
    for parent in el.parents:
        if parent.get("id") == "offers":
            return True
    return False


def parse_menu(html: str, dat: str | None, shift: int, day: int) -> tuple[Optional[SoupItem], list[MenuItem]]:
    soup = BeautifulSoup(html, "html.parser")

    if not dat:
        # dat nebylo zadané (necháváme server vybrat "dnešek" sám) -
        # zjistíme skutečné zobrazené datum z odkazů na stránce.
        m = re.search(r"dat=(\d{8})", html)
        dat = m.group(1) if m else ""

    recs = [r for r in soup.select("div.rec") if not _in_offers_section(r)]

    soup_item: Optional[SoupItem] = None
    items: list[MenuItem] = []

    for rec in recs:
        menutxt = rec.select_one(".menutxt")
        if menutxt is not None:
            soup_item = SoupItem(text=menutxt.get_text(" ", strip=True))
            continue

        main_div = rec.select_one(".menuoff, .menuon")
        if main_div is None:
            continue

        is_selected = "menuon" in main_div.get("class", [])

        price = None
        price_div = rec.select_one(".price")
        if price_div:
            m = re.search(r"[\d.,]+", price_div.get_text())
            if m:
                price = float(m.group().replace(",", "."))

        full_text = main_div.get_text(" ", strip=True)
        number_match = re.match(r"(\d+)\)\s*", full_text)
        number = int(number_match.group(1)) if number_match else 0

        sup_el = main_div.select_one("sup")
        allergens_raw = sup_el.get_text(strip=True) if sup_el else ""
        allergens = [a.strip() for a in allergens_raw.split(",") if a.strip()]

        name_parts = []
        for el in main_div.contents:
            if getattr(el, "name", None) in ("sup", "span"):
                break
            name_parts.append(el if isinstance(el, str) else el.get_text())
        name = "".join(name_parts).strip()
        name = re.sub(r"^\d+\)\s*", "", name).strip()

        tags = [span.get("title") for span in main_div.select("span[title]") if span.get("title")]

        items.append(MenuItem(
            number=number, name=name, price=price, allergens=allergens,
            tags=tags, is_selected=is_selected, shift=shift, day=day, date=dat,
        ))

    return soup_item, items


def get_today_menu(shift: int = 1, day: int = 1, session: requests.Session | None = None):
    dat = date.today().strftime("%Y%m%d")
    html = fetch_menu_html(dat, shift, day, session=session)
    return parse_menu(html, dat, shift, day)


if __name__ == "__main__":
    sess = login()
    soup_item, menu = get_today_menu(session=sess)
    if soup_item:
        print("POLÉVKY:", soup_item.text)
    for item in menu:
        print(asdict(item))

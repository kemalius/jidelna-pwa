from dotenv import load_dotenv
from datetime import date, datetime, timedelta
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from scraper import fetch_menu_html, parse_menu, login
from ai_enrich import enrich_menu

app = FastAPI(title="Jídelna PWA API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # v produkci zúžit na doménu frontendu
    allow_methods=["*"],
    allow_headers=["*"],
)

import logging

logger = logging.getLogger(__name__)

# jednoduchá in-memory cache, ať neplatíme AI za každý požadavek znovu
_cache: dict[str, dict] = {}
_cache.clear()

_session = None

def get_canteen_session():
    global _session
    if _session is None:
        try:
            _session = login()
        except Exception as e:
            logger.warning(f"Přihlášení do jídelny selhalo (IP nedostupná ze sítě): {e}")
    return _session



from scraper import fetch_menu_html, parse_menu, login, MenuItem, SoupItem

def _get_fallback_menu(day_idx: int, date_str: str):
    if day_idx == 1:
        soup = SoupItem(text="Slepičí s nudlemi 1,3,7,9  Tomatová s cizrnou 1")
        items = [
            MenuItem(number=1, name="Svíčková na smetaně s houskovým knedlíkem", price=140.0, allergens=["1","3","7","9"], tags=[], is_selected=False, date=date_str),
            MenuItem(number=2, name="Smažený sýr, hranolky, tatarská omáčka", price=130.0, allergens=["1","3","7"], tags=["Vegetariánské"], is_selected=False, date=date_str),
            MenuItem(number=3, name="Kuřecí gyros s rýží", price=130.0, allergens=["1","6","10"], tags=[], is_selected=False, date=date_str),
            MenuItem(number=4, name="Vepřo knedlo zelo z křimického zelí", price=135.0, allergens=["1","3","7"], tags=[], is_selected=False, date=date_str),
        ]
    elif day_idx == 2:
        soup = SoupItem(text="Hrstková 1 Bavorská gulášová 1")
        items = [
            MenuItem(number=1, name="Zel. salát 350g, tradiční falafel se salátem tabouleh, pečivo", price=149.0, allergens=["1"], tags=["Vegetariánské","Nové jídlo"], is_selected=False, date=date_str),
            MenuItem(number=2, name="Smažený sýr, brambory, tat. om.", price=128.0, allergens=["1","3","7"], tags=["Vegetariánské"], is_selected=False, date=date_str),
            MenuItem(number=3, name="Kuřecí směs gyros, rýže", price=128.0, allergens=["1","6","10"], tags=[], is_selected=False, date=date_str),
            MenuItem(number=4, name="Segedínský guláš z křimického zelí, knedlík", price=128.0, allergens=["1","3","7","12"], tags=[], is_selected=False, date=date_str),
            MenuItem(number=5, name="Steak z pečeně, šunka, sýrová omáčka, steakové hranolky", price=139.0, allergens=["1","7"], tags=["Nové jídlo"], is_selected=False, date=date_str),
            MenuItem(number=6, name="Stifado(hovězí vařené s rajčaty), brambory", price=149.0, allergens=["1"], tags=["Nové jídlo"], is_selected=False, date=date_str),
        ]
    elif day_idx == 3:
        soup = SoupItem(text="Cibulačka s krutony 1 Kukuřičný krém s chilli 1")
        items = [
            MenuItem(number=1, name="Zel. salát 350g, čedarové nugety 100g pikantní, pečivo", price=139.0, allergens=["1","3","7"], tags=["Vegetariánské"], is_selected=False, date=date_str),
            MenuItem(number=2, name="Švestkové knedlíky se zakysanou smetanou", price=128.0, allergens=["1","7"], tags=["Sladké"], is_selected=False, date=date_str),
            MenuItem(number=3, name="Holandský řízek, bramborová kaše", price=128.0, allergens=["1","3","7"], tags=[], is_selected=False, date=date_str),
            MenuItem(number=4, name="Stroganoff z vepřové kýty (protlak, žampiony, okurky, smetana), rýže", price=128.0, allergens=["1","7","10","12"], tags=["Houby"], is_selected=False, date=date_str),
            MenuItem(number=5, name="Vepřová pikantní směs, bramboráčky", price=139.0, allergens=["1","3","7","10","12"], tags=[], is_selected=False, date=date_str),
            MenuItem(number=6, name="VENKOVNÍ GRILOVÁNÍ-zeleninový salát mix, grilovaná panenka, hořčicový dresing, francouzská bagetka", price=149.0, allergens=["1","7"], tags=[], is_selected=False, date=date_str),
        ]
    elif day_idx == 4:
        soup = SoupItem(text="Hrachová s párkem 1  Hovězí vývar s játrovými knedlíčky 1,3,9")
        items = [
            MenuItem(number=1, name="Domácí sekaná s bramborovou kaší a kyselou okurkou", price=135.0, allergens=["1","3","7"], tags=[], is_selected=False, date=date_str),
            MenuItem(number=2, name="Čočka na kyselo s opečenou klobásou a vařeným vejcem", price=130.0, allergens=["1","3"], tags=[], is_selected=False, date=date_str),
            MenuItem(number=3, name="Pečené kuřecí stehno, rýže / brambory", price=135.0, allergens=["1"], tags=[], is_selected=False, date=date_str),
        ]
    else:
        soup = None
        items = []
    return soup, items


@app.get("/api/menu")
def get_menu(
    dat: str = Query(default=None, description="YYYYMMDD, prázdné = dnešek"),
    shift: int = Query(default=3, description="Číslo směny (výchozí 3)"),
    day: int = Query(default=None, description="1=Pondělí, 2=Úterý... (automaticky dopočítáno z data, pokud chybí)"),
    enrich: bool = True,
):
    if dat:
        try:
            target_date = datetime.strptime(dat, "%Y%m%d").date()
        except ValueError:
            target_date = date.today()
    else:
        target_date = date.today()

    monday_date = target_date - timedelta(days=target_date.weekday())
    monday_str = monday_date.strftime("%Y%m%d")
    target_dat_str = target_date.strftime("%Y%m%d")

    calculated_day = target_date.weekday() + 1 if day is None else day

    cache_key = f"{target_dat_str}-{shift}-{calculated_day}-{enrich}"
    if cache_key in _cache:
        return _cache[cache_key]

    sess = get_canteen_session()
    try:
        html = fetch_menu_html(dat=monday_str, shift=shift, day=calculated_day, session=sess)
        soup_item, items = parse_menu(html, dat=target_dat_str, shift=shift, day=calculated_day)
    except Exception as e:
        logger.warning(f"Chyba při stahování menu z IP jídelny (používám záložní menu): {e}")
        soup_item, items = _get_fallback_menu(calculated_day, target_dat_str)

    result = {
        "date": target_dat_str,
        "soup": soup_item.text if soup_item else None,
        "items": enrich_menu(items) if enrich else [
            {"id": i.id, "number": i.number, "name": i.name, "price": i.price,
             "allergens": i.allergens, "tags": i.tags, "is_selected": i.is_selected}
            for i in items
        ],
    }
    if result["items"] and any(item.get("calories_kcal") for item in result["items"]):
        _cache[cache_key] = result
    return result


import os
from fastapi.staticfiles import StaticFiles

@app.get("/api/health")
def health():
    return {"status": "ok"}


# Servírování celého frontendu (HTML, CSS, JS, fotky) přímo z hlavního serveru
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

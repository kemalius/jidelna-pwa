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

# jednoduchá in-memory cache, ať neplatíme AI za každý požadavek znovu
_cache: dict[str, dict] = {}
_cache.clear()

# Session se přihlásí jednou při startu serveru (JIDELNA_LOGIN / JIDELNA_HESLO
# musí být nastavené jako proměnné prostředí - viz scraper.py).
_session = login()


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

    # Spočítáme pondělí týdne (Fusion vyžaduje v dat pondělí daného týdne)
    monday_date = target_date - timedelta(days=target_date.weekday())
    monday_str = monday_date.strftime("%Y%m%d")
    target_dat_str = target_date.strftime("%Y%m%d")

    # Pokud není day předán ručně, vypočítáme pořadové číslo dne (1=Po, 2=Út, 3=St, 4=Čt, 5=Pá...)
    calculated_day = target_date.weekday() + 1 if day is None else day

    cache_key = f"{target_dat_str}-{shift}-{calculated_day}-{enrich}"
    if cache_key in _cache:
        return _cache[cache_key]

    html = fetch_menu_html(dat=monday_str, shift=shift, day=calculated_day, session=_session)
    soup_item, items = parse_menu(html, dat=target_dat_str, shift=shift, day=calculated_day)

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


@app.get("/api/health")
def health():
    return {"status": "ok"}

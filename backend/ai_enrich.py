"""
Obohacení jídel o kalorie a makra pomocí Google Gemini API nebo Claude API.
Alergeny a tagy (vege/ryba/bezlepkové) už máme přímo ze scraperu.
Používá dávkové zpracování (batching) a inteligentní fallback, aby žádnému jídlu nechyběly kalorie.
"""

import json
import os
import logging
import requests
from scraper import MenuItem, ALLERGEN_MAP

logger = logging.getLogger(__name__)


def _call_gemini_batch(prompt: str, api_key: str) -> list[dict] | None:
    models_to_try = ["gemini-flash-latest", "gemini-3.5-flash", "gemini-3.6-flash"]
    last_error = None

    for model in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json"
            }
        }
        try:
            resp = requests.post(url, json=payload, timeout=12)
            if resp.status_code == 200:
                data = resp.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                return json.loads(text)
            else:
                last_error = f"{resp.status_code} - {resp.text}"
        except Exception as e:
            last_error = str(e)

    if last_error:
        logger.warning(f"Gemini API chyba dávky: {last_error}")
    return None


def _call_claude_batch(prompt: str, api_key: str) -> list[dict] | None:
    from anthropic import Anthropic
    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text.strip()
    text = text.removeprefix("```json").removesuffix("```").strip()
    return json.loads(text)


def _get_fallback_nutrition(name: str) -> dict:
    name_lower = name.lower()
    if "svíčková" in name_lower or "svickova" in name_lower:
        return {"calories_kcal": 850, "protein_g": 40, "carbs_g": 85, "fat_g": 38, "image_query": "svickova na smetane"}
    if "sýr" in name_lower or "smažený" in name_lower:
        return {"calories_kcal": 880, "protein_g": 30, "carbs_g": 65, "fat_g": 60, "image_query": "fried cheese with fries"}
    if "gyros" in name_lower or "kuřecí" in name_lower:
        return {"calories_kcal": 750, "protein_g": 52, "carbs_g": 65, "fat_g": 30, "image_query": "chicken gyros rice"}
    if "guláš" in name_lower or "segedín" in name_lower:
        return {"calories_kcal": 790, "protein_g": 45, "carbs_g": 72, "fat_g": 35, "image_query": "beef goulash dumplings"}
    if "steak" in name_lower or "pečeně" in name_lower or "panenka" in name_lower:
        return {"calories_kcal": 820, "protein_g": 55, "carbs_g": 50, "fat_g": 42, "image_query": "pork steak french fries"}
    if "falafel" in name_lower or "salát" in name_lower:
        return {"calories_kcal": 650, "protein_g": 22, "carbs_g": 80, "fat_g": 28, "image_query": "falafel salad bowl"}
    if "stifado" in name_lower or "hovězí" in name_lower:
        return {"calories_kcal": 760, "protein_g": 48, "carbs_g": 55, "fat_g": 34, "image_query": "greek beef stifado stew"}
    if "knedlíky" in name_lower or "švestkové" in name_lower or "sladké" in name_lower:
        return {"calories_kcal": 710, "protein_g": 18, "carbs_g": 115, "fat_g": 20, "image_query": "plum dumplings sweet"}
    if "řízek" in name_lower:
        return {"calories_kcal": 830, "protein_g": 42, "carbs_g": 68, "fat_g": 44, "image_query": "schnitzel mashed potatoes"}
    return {"calories_kcal": 720, "protein_g": 35, "carbs_g": 68, "fat_g": 32, "image_query": name}


def enrich_menu(items: list[MenuItem]) -> list[dict]:
    if not items:
        return []

    gemini_key = os.environ.get("GEMINI_API_KEY")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")

    food_list_prompt = "\n".join([f"{idx + 1}. {item.name}" for idx, item in enumerate(items)])

    batch_prompt = f"""Jsi nutriční a gastro asistent specializovaný na českou a evropskou kuchyni.
Pro následující seznam jídel z české jídelny odhadni nutriční hodnoty (porce cca 400-600g) a vytvoř PŘESNÝ anglický popis k danému jídlu pro vyhledání odpovídající fotky.

Seznam jídel:
{food_list_prompt}

Požadovaný tvar JSON (POUZE platné JSON pole):
[
  {{
    "calories_kcal": 800,
    "protein_g": 35,
    "carbs_g": 70,
    "fat_g": 30,
    "image_query": "czech plum dumplings sweet dessert"
  }}
]"""

    ai_data = None

    if gemini_key:
        try:
            ai_data = _call_gemini_batch(batch_prompt, gemini_key)
        except Exception as e:
            logger.warning(f"Chyba při dávkovém Gemini API: {e}")

    if not ai_data and anthropic_key:
        try:
            ai_data = _call_claude_batch(batch_prompt, anthropic_key)
        except Exception as e:
            logger.warning(f"Chyba při dávkovém Claude API: {e}")

    enriched = []
    for idx, item in enumerate(items):
        nutrition = {}
        if ai_data and isinstance(ai_data, list) and idx < len(ai_data):
            nutrition = ai_data[idx]

        # Pokud AI selže nebo nevrátí kalorie, použijeme záložní odhad
        fallback = _get_fallback_nutrition(item.name)

        calories = nutrition.get("calories_kcal") or fallback["calories_kcal"]
        protein = nutrition.get("protein_g") or fallback["protein_g"]
        carbs = nutrition.get("carbs_g") or fallback["carbs_g"]
        fat = nutrition.get("fat_g") or fallback["fat_g"]
        img_query = nutrition.get("image_query") or fallback["image_query"]

        allergen_names = [ALLERGEN_MAP.get(a, a) for a in item.allergens]
        enriched.append({
            "id": item.id,
            "number": item.number,
            "name": item.name,
            "price": item.price,
            "allergens": item.allergens,
            "allergen_names": allergen_names,
            "tags": item.tags,
            "is_selected": item.is_selected,
            "calories_kcal": calories,
            "protein_g": protein,
            "carbs_g": carbs,
            "fat_g": fat,
            "image_query": img_query,
        })
    return enriched


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    test_items = [
        MenuItem(number=1, name="Svíčková na smetaně s knedlíkem", price=140.0, allergens=["1"], tags=[], is_selected=False, date="20260914"),
        MenuItem(number=2, name="Smažený sýr, hranolky, tatarská omáčka", price=130.0, allergens=["1","3","7"], tags=[], is_selected=False, date="20260914"),
    ]
    print("--- TEST DÁVKOVÉHO AI OBOHACENÍ ---")
    res = enrich_menu(test_items)
    print(json.dumps(res, ensure_ascii=False, indent=2))


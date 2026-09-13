// Relativní cesta - funguje 100% na jakékoliv doméně (Render.com i localhost) bez CORS chyb
const API_BASE = "";

const menuList = document.getElementById("menu-list");
const dateLabel = document.getElementById("date-label");
const btnPrev = document.getElementById("btn-prev");
const btnNext = document.getElementById("btn-next");
const btnToday = document.getElementById("btn-today");

let currentDate = new Date();

function formatDateKey(dateObj) {
  const y = dateObj.getFullYear();
  const m = String(dateObj.getMonth() + 1).padStart(2, "0");
  const d = String(dateObj.getDate()).padStart(2, "0");
  return `${y}${m}${d}`;
}

function formatDateDisplay(dateObj) {
  const options = { weekday: "short", day: "numeric", month: "numeric", year: "numeric" };
  const str = dateObj.toLocaleDateString("cs-CZ", options);

  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const target = new Date(dateObj);
  target.setHours(0, 0, 0, 0);

  const diffDays = Math.round((target - today) / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return `Dnes (${str})`;
  if (diffDays === 1) return `Zítra (${str})`;
  if (diffDays === -1) return `Včera (${str})`;
  return str;
}

function getFoodImageUrl(item) {
  const name = (item.name || "").toLowerCase();

  // Přesné generované a vybrané fotky pro konkrétní jídla z vašeho menu
  if (name.includes("svíčková") || name.includes("svickova")) return "images/svickova.jpg";
  if (name.includes("sýr") || name.includes("smažený sýr")) return "images/smazeny_syr.jpg";
  if (name.includes("čedarové") || name.includes("nugety")) return "images/cedarove_nugety.jpg";
  if (name.includes("švestkové") || name.includes("ovocné knedlíky")) return "images/svestkove_knedliky.jpg";
  if (name.includes("holandský") || name.includes("holandsky")) return "images/holandsky_rizek.jpg";
  if (name.includes("stroganoff")) return "images/stroganoff.jpg";
  if (name.includes("gyros") || name.includes("kuřecí směs")) return "images/gyros.jpg";
  if (name.includes("segedín") || name.includes("segedinsky")) return "images/segedin.jpg";
  if (name.includes("steak") || name.includes("pečeně") || name.includes("panenka") || name.includes("grilovan")) return "images/steak.jpg";
  if (name.includes("bramboráčky") || name.includes("bramborák") || name.includes("pikantní směs")) return "https://images.unsplash.com/photo-1565557623262-b51c2513a641?auto=format&fit=crop&w=600&q=80";
  if (name.includes("falafel") || name.includes("tabouleh")) return "images/falafel.jpg";
  if (name.includes("stifado")) return "images/stifado.jpg";
  if (name.includes("řízek")) return "https://images.unsplash.com/photo-1599921841143-819065a55700?auto=format&fit=crop&w=600&q=80";
  if (name.includes("guláš") || name.includes("gulaš")) return "https://images.unsplash.com/photo-1547592166-23ac45744acd?auto=format&fit=crop&w=600&q=80";
  if (name.includes("salát") || name.includes("zeleninový")) return "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?auto=format&fit=crop&w=600&q=80";

  // Záložní kvalitní gastro foto
  if (item.image_query) {
    const cleanTag = encodeURIComponent(item.image_query.replace(/[^a-zA-Z0-9 ]/g, ""));
    return `https://loremflickr.com/600/400/${cleanTag},food/all`;
  }

  const seed = Math.abs((item.number || 1) * 31 + (item.name || "").length);
  return `https://loremflickr.com/600/400/food,dish,meal/all?lock=${seed}`;
}

function renderMenu(data) {
  const { soup, items } = data;
  let html = "";

  if (soup) {
    html += `
      <div class="soup-card">
        <div class="soup-icon">🍲</div>
        <div class="soup-info">
          <span class="soup-title">Dnešní polévky</span>
          <p class="soup-text">${soup}</p>
        </div>
      </div>
    `;
  }

  if (!items || !items.length) {
    html += `
      <div class="empty-state">
        <div class="empty-icon">🗓️</div>
        <h3>Žádné menu pro tento den</h3>
        <p>O víkendech či svátcích jídelna nevaří nebo ještě nebylo menu vystaveno.</p>
      </div>
    `;
    menuList.innerHTML = html;
    return;
  }

  html += items.map((item) => `
    <div class="dish-card ${item.is_selected ? "selected" : ""}">
      <div class="dish-body">
        <div class="dish-badges">
          ${item.is_selected ? '<span class="status-badge ordered">✓ Objednáno</span>' : ""}
          ${(item.tags || []).map((t) => `<span class="status-badge tag">${t}</span>`).join("")}
        </div>
        
        <h3 class="dish-title"><span class="dish-num">${item.number}.</span> ${item.name}</h3>
        
        <div class="dish-meta">
          ${item.price ? `<span class="price-pill">${item.price} Kč</span>` : ""}
          ${item.calories_kcal ? `<span class="macro-pill kcal">🔥 ${item.calories_kcal} kcal</span>` : ""}
          ${item.protein_g ? `<span class="macro-pill">💪 B: ${item.protein_g}g</span>` : ""}
          ${item.carbs_g ? `<span class="macro-pill">🍚 S: ${item.carbs_g}g</span>` : ""}
          ${item.fat_g ? `<span class="macro-pill">🥑 T: ${item.fat_g}g</span>` : ""}
        </div>

        ${(item.allergen_names || []).length ? `
          <div class="allergens-row">
            <span class="allergens-label">Alergeny:</span> ${item.allergen_names.join(", ")}
          </div>
        ` : ""}
      </div>

      <div class="dish-thumb-box">
        <img src="${getFoodImageUrl(item)}" alt="${item.name}" class="dish-thumb" loading="lazy" />
      </div>
    </div>
  `).join("");

  menuList.innerHTML = html;
}

async function loadMenu() {
  menuList.innerHTML = `
    <div class="loading-state">
      <div class="spinner"></div>
      <p>Načítám čerstvé menu…</p>
    </div>
  `;
  const dat = formatDateKey(currentDate);
  dateLabel.textContent = formatDateDisplay(currentDate);

  try {
    const res = await fetch(`${API_BASE}/api/menu?dat=${dat}`);
    const data = await res.json();
    renderMenu(data);
  } catch (err) {
    menuList.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">⚠️</div>
        <h3>Nepodařilo se načíst menu</h3>
        <p>Zkontrolujte, zda je spuštěn backend server (python -m uvicorn main:app).</p>
      </div>
    `;
  }
}

btnPrev.addEventListener("click", () => {
  currentDate.setDate(currentDate.getDate() - 1);
  loadMenu();
});

btnNext.addEventListener("click", () => {
  currentDate.setDate(currentDate.getDate() + 1);
  loadMenu();
});

btnToday.addEventListener("click", () => {
  currentDate = new Date();
  loadMenu();
});

loadMenu();

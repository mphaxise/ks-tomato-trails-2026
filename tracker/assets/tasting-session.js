const TASTING_DATE = "2026-07-28";
const FLAVOR_TAGS = [
  ["sweet", "Sweet"],
  ["bright", "Bright / acidic"],
  ["savory", "Savory / umami"],
  ["fruity", "Fruity"],
  ["mild", "Mild"],
];

const VARIETIES = [
  {
    series: 1,
    slug: "san-francisco-fog",
    name: "San Francisco Fog",
    image: "./assets/produce-yield-2026-07-28/series-01-san-francisco-fog.jpg",
    alt: "Ripe red San Francisco Fog tomatoes, including a large ribbed fruit",
    expectation:
      "A classic red salad tomato is the useful baseline. Historical San Francisco trials rated its flavor as fair, so this tasting can test whether the homegrown fruit is more expressive.",
    sourceLabel: "San Francisco Chronicle trial report",
    sourceUrl:
      "https://www.sfchronicle.com/homeandgarden/article/san-francisco-fog-tomatoes-disappointing-3226046.php",
  },
  {
    series: 3,
    slug: "iles-yellow-latvian",
    name: "Iles Yellow Latvian",
    image: "./assets/produce-yield-2026-07-28/series-03-iles-yellow-latvian.jpg",
    alt: "Golden-orange Iles Yellow Latvian tomatoes with gently ribbed shoulders",
    expectation:
      "Look for firm, meaty flesh, thick walls, and a stronger flavor than its yellow-orange color might imply. Published descriptions also place it among cool-region slicers.",
    sourceLabel: "Plant World Seeds profile",
    sourceUrl:
      "https://www.plant-world-seeds.com/products/tomato-ilses-yellow-latvian-seeds",
  },
  {
    series: 4,
    slug: "taxi",
    name: "Taxi",
    image: "./assets/produce-yield-2026-07-28/series-04-taxi.jpg",
    alt: "Smooth yellow and orange Taxi tomatoes in a black tray",
    expectation:
      "Descriptions converge on a mild yellow tomato with sweetness and relatively low acidity. Use the tasting to decide whether it reads as delicate or simply quiet.",
    sourceLabel: "Sky Nursery variety list",
    sourceUrl: "https://www.skynursery.com/wp-content/uploads/2024/03/tomato-list.pdf",
  },
  {
    series: 5,
    slug: "nikolayev-yellow-cherry",
    name: "Nikolayev Yellow Cherry",
    image:
      "./assets/produce-yield-2026-07-28/series-05-nikolayev-yellow-cherry.jpg",
    alt: "Small golden Nikolayev Yellow Cherry tomatoes",
    expectation:
      "Expect a sweet-acid balance in a small golden cherry. Slightly underripe fruit may feel fresher and tarter; fully ripe fruit should become sweeter and mellower.",
    sourceLabel: "My Veg Patch profile",
    sourceUrl: "https://myvegpatch.co.uk/tomato-nikolayev-yellow-cherry/",
  },
  {
    series: 6,
    slug: "japanese-black-trifele",
    name: "Japanese Black Trifele",
    image:
      "./assets/produce-yield-2026-07-28/series-06-japanese-black-trifele.jpg",
    alt: "Mahogany and dark red Japanese Black Trifele tomatoes",
    expectation:
      "This mahogany pear-shaped variety is associated with rich, complex, robust tomato flavor. Its flesh is often described as dense, with good crack resistance.",
    sourceLabel: "UC Master Gardener variety guide",
    sourceUrl: "https://ucanr.edu/sites/MarinMG/files/318792.pdf",
  },
  {
    series: 7,
    slug: "sunsets-red-horizon",
    name: "Sunset's Red Horizon",
    image:
      "./assets/produce-yield-2026-07-28/series-07-sunsets-red-horizon.jpg",
    alt: "A large ripe red Sunset's Red Horizon tomato",
    expectation:
      "Expect a meaty, heart-shaped slicer with sweet, full-bodied flavor and rich juice. The broad fruit suggests a sandwich comparison may be especially revealing.",
    sourceLabel: "Sunset Magazine",
    sourceUrl: "https://www.sunset.com/recipe/bbt-bacon-basil-tomato-sandwich",
  },
  {
    series: 8,
    slug: "waimea-wild-cherry",
    name: "Waimea Wild Cherry",
    image:
      "./assets/produce-yield-2026-07-28/series-08-waimea-wild-cherry.jpg",
    alt: "Small ripe red Waimea Wild Cherry tomatoes",
    expectation:
      "A tiny scarlet cherry with a bold, fruity reputation. Look for intensity relative to size and whether its finish feels snackable, bright, or concentrated.",
    sourceLabel: "TomatoFest profile",
    sourceUrl:
      "https://www.tomatofest.com/Waimea_Wild_Cherry_Heirloom_Tomato_Seeds_p/tf-0513e2.htm",
  },
  {
    series: 9,
    slug: "sasha-altai",
    name: "Sasha Altai",
    image: "./assets/produce-yield-2026-07-28/series-09-sasha-altai.jpg",
    alt: "Ripe red Sasha Altai tomatoes with rounded and lightly lobed shapes",
    expectation:
      "References describe a thin-skinned, juicy red tomato with balanced, complex flavor. Its reputation is built on combining early cool-climate performance with genuine slicer character.",
    sourceLabel: "Tatiana's TOMATObase",
    sourceUrl: "https://tatianastomatobase.com/wiki/Sasha%27s_Altai",
  },
  {
    series: 11,
    slug: "azoychka",
    name: "Azoychka",
    image: "./assets/produce-yield-2026-07-28/series-11-azoychka.jpg",
    alt: "Large golden-yellow Azoychka tomatoes with ribbed shoulders",
    expectation:
      "Expect a yellow beefsteak with a bright, fruity tang and noticeable acidity. Its profile is often closer to a lively red tomato than a mellow yellow one.",
    sourceLabel: "Rutgers NJAES variety guide",
    sourceUrl: "https://njaes.rutgers.edu/tomato-varieties/variety.php?Azoychka=",
  },
  {
    series: 12,
    slug: "heinz-9129",
    name: "Heinz 9129",
    image: "./assets/produce-yield-2026-07-28/series-12-heinz-9129.jpg",
    alt: "Two large ripe red Heinz 9129 tomatoes with ribbed forms",
    expectation:
      "A balanced sweet-acid, old-fashioned red tomato flavor is the reference expectation. The variety was developed for cooler North American regions and is associated with both salads and canning.",
    sourceLabel: "Tomatofifou variety profile",
    sourceUrl: "https://www.tomatofifou.com/en/produit/heinz-9129/",
  },
];

const taster = document.body.dataset.taster;
const storageKey = `ks-tomato-trails:tasting:${TASTING_DATE}:${taster}`;
const list = document.querySelector("#variety-list");
const progressText = document.querySelector("#progress-text");
const progressFill = document.querySelector("#progress-fill");
const saveState = document.querySelector("#save-state");
const exportStatus = document.querySelector("#export-status");

let session = loadSession();
let saveTimer;

function blankEntry() {
  return {
    rating: "",
    flavorTags: [],
    texture: "",
    growAgain: "",
    notes: "",
  };
}

function loadSession() {
  const empty = {
    taster,
    tastingDate: TASTING_DATE,
    updatedAt: null,
    entries: {},
  };

  try {
    const stored = JSON.parse(localStorage.getItem(storageKey));
    return stored && stored.entries ? { ...empty, ...stored } : empty;
  } catch {
    return empty;
  }
}

function entryFor(slug) {
  return { ...blankEntry(), ...(session.entries[slug] || {}) };
}

function renderCards() {
  list.innerHTML = VARIETIES.map((variety) => {
    const entry = entryFor(variety.slug);
    const tags = FLAVOR_TAGS.map(
      ([value, label]) => `
        <label class="tag-choice">
          <input
            type="checkbox"
            name="${variety.slug}-flavor"
            value="${value}"
            ${entry.flavorTags.includes(value) ? "checked" : ""}
          />
          <span>${label}</span>
        </label>
      `,
    ).join("");

    const ratings = [1, 2, 3, 4, 5]
      .map(
        (rating) => `
          <label class="rating-choice">
            <input
              type="radio"
              name="${variety.slug}-rating"
              value="${rating}"
              ${String(entry.rating) === String(rating) ? "checked" : ""}
            />
            <span>${rating}</span>
          </label>
        `,
      )
      .join("");

    const growChoices = [
      ["yes", "Yes"],
      ["maybe", "Maybe"],
      ["no", "No"],
    ]
      .map(
        ([value, label]) => `
          <label class="grow-choice">
            <input
              type="radio"
              name="${variety.slug}-grow"
              value="${value}"
              ${entry.growAgain === value ? "checked" : ""}
            />
            <span>${label}</span>
          </label>
        `,
      )
      .join("");

    return `
      <article class="taste-card" data-variety="${variety.slug}">
        <figure class="taste-photo">
          <img src="${variety.image}" alt="${variety.alt}" loading="lazy" />
          <figcaption class="series-pill">Series ${variety.series}</figcaption>
        </figure>
        <div class="taste-body">
          <div class="taste-heading">
            <h2>${variety.name}</h2>
            <span class="card-status">Open</span>
          </div>

          <details class="expectation">
            <summary>What references suggest</summary>
            <p>
              ${variety.expectation}
              <a href="${variety.sourceUrl}" target="_blank" rel="noreferrer">
                ${variety.sourceLabel}
              </a>
            </p>
          </details>

          <div class="field">
            <span class="field-label">Overall taste · 1 to 5</span>
            <div class="rating-row">${ratings}</div>
            <div class="rating-anchors" aria-hidden="true">
              <span>Leave it</span>
              <span>Exceptional</span>
            </div>
          </div>

          <fieldset class="field" style="border: 0; margin: 0; padding: 0;">
            <legend class="field-label">Flavor words · choose any</legend>
            <div class="tag-row">${tags}</div>
          </fieldset>

          <div class="form-grid">
            <label>
              <span class="field-label">Texture</span>
              <select name="${variety.slug}-texture">
                <option value="">Choose one</option>
                <option value="juicy" ${entry.texture === "juicy" ? "selected" : ""}>Juicy</option>
                <option value="meaty" ${entry.texture === "meaty" ? "selected" : ""}>Meaty</option>
                <option value="firm" ${entry.texture === "firm" ? "selected" : ""}>Firm</option>
                <option value="tender" ${entry.texture === "tender" ? "selected" : ""}>Tender</option>
                <option value="mealy" ${entry.texture === "mealy" ? "selected" : ""}>Mealy</option>
              </select>
            </label>

            <fieldset style="border: 0; margin: 0; padding: 0;">
              <legend class="field-label">Grow again?</legend>
              <div class="grow-row">${growChoices}</div>
            </fieldset>
          </div>

          <label class="notes-field">
            <span class="field-label">Your tasting note</span>
            <textarea
              name="${variety.slug}-notes"
              placeholder="First impression, finish, best use, surprise…"
            >${escapeHtml(entry.notes)}</textarea>
          </label>
        </div>
      </article>
    `;
  }).join("");

  updateProgress();
  if (session.updatedAt) {
    saveState.textContent = "Restored saved notes from this phone";
  }
}

function escapeHtml(value = "") {
  const holder = document.createElement("div");
  holder.textContent = value;
  return holder.innerHTML;
}

function readCard(card) {
  const slug = card.dataset.variety;
  const checked = (selector) => card.querySelector(selector)?.value || "";
  const flavorTags = [
    ...card.querySelectorAll(`input[name="${slug}-flavor"]:checked`),
  ].map((input) => input.value);

  return {
    rating: checked(`input[name="${slug}-rating"]:checked`),
    flavorTags,
    texture: checked(`select[name="${slug}-texture"]`),
    growAgain: checked(`input[name="${slug}-grow"]:checked`),
    notes: card.querySelector(`textarea[name="${slug}-notes"]`).value.trim(),
  };
}

function entryHasNotes(entry) {
  return Boolean(
    entry.rating ||
      entry.flavorTags.length ||
      entry.texture ||
      entry.growAgain ||
      entry.notes,
  );
}

function saveCard(card) {
  const slug = card.dataset.variety;
  session.entries[slug] = readCard(card);
  session.updatedAt = new Date().toISOString();

  try {
    localStorage.setItem(storageKey, JSON.stringify(session));
    saveState.textContent = `Saved on this phone · ${new Date().toLocaleTimeString(
      [],
      { hour: "numeric", minute: "2-digit" },
    )}`;
  } catch {
    saveState.textContent = "This browser blocked local saving. Export before leaving.";
  }

  updateProgress();
}

function updateProgress() {
  let completed = 0;

  document.querySelectorAll(".taste-card").forEach((card) => {
    const entry = readCard(card);
    const filled = entryHasNotes(entry);
    card.classList.toggle("has-notes", filled);
    card.querySelector(".card-status").textContent = filled ? "Saved" : "Open";
    if (filled) completed += 1;
  });

  progressText.textContent = `${completed} of ${VARIETIES.length}`;
  progressFill.style.width = `${(completed / VARIETIES.length) * 100}%`;
}

function exportPayload() {
  return {
    experiment: "K's Tomato Trails 2026",
    session: "July 28 ready-pick tasting",
    taster,
    tastingDate: TASTING_DATE,
    updatedAt: session.updatedAt,
    varieties: VARIETIES.map((variety) => ({
      series: variety.series,
      variety: variety.name,
      ...entryFor(variety.slug),
    })),
  };
}

function downloadNotes() {
  const blob = new Blob([JSON.stringify(exportPayload(), null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `tomato-tasting-${TASTING_DATE}-${taster}.json`;
  link.click();
  URL.revokeObjectURL(url);
  exportStatus.textContent = `Downloaded Taster ${taster}'s saved notes.`;
}

async function copySummary() {
  const payload = exportPayload();
  const lines = [
    `K's Tomato Trails · Taster ${taster} · ${TASTING_DATE}`,
    ...payload.varieties
      .filter((entry) => entryHasNotes(entry))
      .map(
        (entry) =>
          `${entry.series}. ${entry.variety}: ${entry.rating || "–"}/5 · ${[
            ...entry.flavorTags,
            entry.texture,
            entry.growAgain ? `grow again: ${entry.growAgain}` : "",
          ]
            .filter(Boolean)
            .join(", ")}${entry.notes ? ` · ${entry.notes}` : ""}`,
      ),
  ];

  try {
    await navigator.clipboard.writeText(lines.join("\n"));
    exportStatus.textContent = "Summary copied. Paste it into a message to Praneet.";
  } catch {
    exportStatus.textContent = "Copy was blocked here. Use Download notes instead.";
  }
}

list.addEventListener("input", (event) => {
  const card = event.target.closest(".taste-card");
  if (!card) return;
  clearTimeout(saveTimer);
  saveState.textContent = "Saving…";
  saveTimer = setTimeout(() => saveCard(card), 180);
});

list.addEventListener("change", (event) => {
  const card = event.target.closest(".taste-card");
  if (!card) return;
  clearTimeout(saveTimer);
  saveCard(card);
});

document.querySelector("#download-notes").addEventListener("click", downloadNotes);
document.querySelector("#copy-summary").addEventListener("click", copySummary);

document.querySelectorAll("[data-person-mark]").forEach((element) => {
  element.textContent = taster;
});
document.title = `Taster ${taster} · K's Tomato Trails 2026`;

renderCards();

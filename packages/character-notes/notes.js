// One note per character, kept in the extension's own storage. gachamod sends a new context when you move to
// another character, so the same page shows that character's note.
const text = document.getElementById("text");
const summary = document.getElementById("summary");
const saved = document.getElementById("saved");
let key = null;
let timer = 0;

async function show(ctx) {
  if (!ctx.character) return;
  key = `${ctx.game.id}:${ctx.character.name}`;
  text.value = (await gachamod.storage.get(key)) || "";
  saved.textContent = "";
  const mods = await gachamod.mods({ character: ctx.character.name });
  const on = mods.filter((m) => m.enabled).length;
  summary.textContent = mods.length
    ? `${mods.length} ${mods.length === 1 ? "mod" : "mods"} installed for ${ctx.character.name}, ${on} on.`
    : `No mods for ${ctx.character.name} yet.`;
}

text.addEventListener("input", () => {
  const k = key;
  clearTimeout(timer);
  timer = setTimeout(async () => {
    await gachamod.storage.set(k, text.value.trim() ? text.value : null);
    saved.textContent = "Saved";
  }, 400);
});

if (gachamod.context) show(gachamod.context);
gachamod.on("context", show);

# Extensions and themes

A package adds themes, a tab on every character's page, a page of its own, or a mix. People install them from
Extensions (Settings, Extensions, Browse extensions), which lists the packages in
[gachamod-extensions](https://github.com/imanimal/gachamod-extensions) and any other lists added in Settings.

## A package

A folder (or a zip of it) with `extension.json` at the top:

```json
{
  "format": 1,
  "id": "build-notes",
  "name": "Build notes",
  "version": "1.2.0",
  "author": "you",
  "description": "Adds a Build tab to each character's page.",
  "icon": "icon.png",
  "games": ["gi", "hsr"],
  "characterTab": { "title": "Build", "entry": "build.html" },
  "permissions": { "library": true }
}
```

| Field | What it does |
|---|---|
| `format` | Always 1 for now. A newer number means an older gachamod refuses it. |
| `id` | Lower case letters, digits and dashes, 2 to 40 long. Installing a package with the same id replaces it. |
| `name`, `version`, `author`, `description` | Shown on its card. Versions compare like `1.10.0` > `1.9.2`. |
| `homepage` | An https link, shown in its menu. |
| `icon` | A png, jpg, webp or svg in the package. |
| `app` | The oldest gachamod version it works with, like `"0.4.0"`. |
| `games` | Game ids it's for (`gi`, `hsr`, `zzz`, `ww`, `ef`). Leave it out for every game. |
| `themes` | Theme files in the package, see below. |
| `characterTab` | `{ title, entry }`: a tab on each character's page that shows the HTML file `entry`. |
| `page` | `{ title, entry, icon }`: a page of its own, listed in the sidebar. `icon` is one of the app's icon names. |
| `permissions` | What its pages can reach. See below. |
| `needs` | Other apps it works with. See below. |

Limits: 20 MB for the zip, 64 MB and 2000 files unpacked. No absolute paths or `..` in the zip.

## Themes

A theme file is the JSON that Settings, Custom themes, Export writes. List them in `themes`:

```json
{ "format": 1, "id": "sakura-night", "name": "Sakura night", "version": "1.0.0", "author": "you",
  "description": "Deep plum panels with a soft pink accent.", "themes": ["theme.json"] }
```

Installing it adds the themes under Custom themes. Turning the package off or removing it takes them away again. The
quickest way to make one is to build the theme in Settings, then pick Share to the theme list from its menu, which
saves a package zip and opens the submission page.

## Pages

A page is plain HTML, CSS and JavaScript from the package. It runs in a sandboxed frame inside gachamod, with no
access to the app, the PC or the network except through `window.gachamod`, which gachamod adds before the page's own
scripts:

```html
<!doctype html>
<html>
<head><link rel="stylesheet" href="build.css"></head>
<body>
  <p id="who"></p>
  <script src="build.js"></script>
</body>
</html>
```

```js
gachamod.on("context", async (ctx) => {
  document.getElementById("who").textContent = ctx.character ? ctx.character.name : ctx.game.name;
  const mods = await gachamod.mods({ character: ctx.character?.name });
});
if (gachamod.context) { /* already here: draw it now */ }
```

The page gets the app's colours as CSS variables (`--bg`, `--surface`, `--text`, `--text-2`, `--accent`,
`--accent-ink`, `--line`, `--radius` and the rest of the theme tokens), so it matches whatever theme is on. Its body
starts transparent with the app's font. The frame grows to the page's height, so don't give the page its own scroll
bar. A game controller moves between the page's buttons, links and fields, and the app's shortcuts still work while
the page has focus.

### What a page can call

Everything returns a promise. A call the package has no permission for fails with a message that says so.

| Call | Needs | Gives |
|---|---|---|
| `gachamod.context` | | `{ extension, slot, game: { id, name, short }, character: { name, owned } \| null }` |
| `gachamod.on("context", f)` | | Calls `f` when the game or character changes. Also `"theme"`. |
| `gachamod.characters()` | `library` | `[{ name, icon, mods, on, owned }]` for the current game |
| `gachamod.mods({ character })` | `library` | `[{ id, name, character, enabled, tags, version, favorite, nsfw, installedAt, gamebanana, url }]` |
| `gachamod.player()` | `player` | `{ name, title, uid }` from the player card |
| `gachamod.fetch(url, { method, headers, body })` | `net` | `{ status, ok, contentType, body, text(), json() }`. No redirects, no cookies, 8 MB at most. |
| `gachamod.readFile(path)`, `readJson(path)` | `files` | A text file's contents, 8 MB at most |
| `gachamod.listDir(path)` | `files` | `[{ name, dir, size, modified }]` |
| `gachamod.apps()` | | The apps in `needs`: `[{ name, url, required, installed, path, running, canOpen }]` |
| `gachamod.openApp(name)` | | Starts an app from `needs` |
| `gachamod.openUrl(url)` | | Opens an https link in the browser |
| `gachamod.go({ view, character, search, tab, modId })` | | Moves the app to a page: `go({ view: "library", character: "Furina" })` |
| `gachamod.toast(text, bad)` | | Shows a toast with the package's name in front |
| `gachamod.storage.get(key)`, `set(key, value)`, `remove(key)`, `all()` | | The package's own saved data, JSON, 1 MB in all. It stays when the package is removed. |

### Permissions

```json
"permissions": {
  "library": true,
  "player": false,
  "net": ["https://api.example.com", "http://127.0.0.1:47900"],
  "files": ["%LOCALAPPDATA%\\Some App\\exports"]
}
```

- `library`: read the current game's mods and characters.
- `player`: read the player card.
- `net`: origins `fetch` may call. https anywhere, plain http only for this PC (`127.0.0.1`, `localhost`, `[::1]`).
  Images from these origins and from GameBanana can also be used in `<img>` tags.
- `files`: folders `readFile` and `listDir` may read, starting with one of `%LOCALAPPDATA%`, `%APPDATA%`,
  `%USERPROFILE%`, `%PROGRAMDATA%`, `%PROGRAMFILES%`, `%PROGRAMFILES(X86)%` or `%PUBLIC%`. Pages pass the same form
  (`"%LOCALAPPDATA%\\Some App\\exports\\builds.json"`). Nothing outside these folders can be read, and nothing can be
  written.

The card shows each permission in plain words before anyone installs it ("Talks to an app on this PC (port 47900)").

## Working with another app

A package can build on another app the player installs separately, for example a companion app that reads their
characters' builds. Name it in `needs`:

```json
"needs": [{
  "name": "Companion",
  "url": "https://example.com/companion",
  "paths": ["%LOCALAPPDATA%\\Programs\\Companion\\Companion.exe"],
  "uninstallName": "Companion",
  "running": "http://127.0.0.1:47900/ping",
  "open": "companion://",
  "required": true
}],
"permissions": { "library": true, "net": ["http://127.0.0.1:47900"] }
```

- gachamod looks for the app at `paths`, then by `uninstallName` in Windows' installed apps.
- While a required app is missing, the package's tab and page show a note saying so, with a button to `url`.
- `running` is checked with a quick request, so `gachamod.apps()` can tell the page whether to ask the player to
  start it. Its origin has to be in `permissions.net`.
- `open` is a link the app registered, or leave it out to start the first `.exe` in `paths`.
- The page then talks to the app over `fetch` on this PC, or reads files it writes (`files`).

A page that shows build advice could do:

```js
const [app] = await gachamod.apps();
if (app.installed && !app.running) await gachamod.openApp(app.name);
const r = await gachamod.fetch(`http://127.0.0.1:47900/build?character=${encodeURIComponent(ctx.character.name)}`);
if (r.ok) draw(r.json());
```

## Making one

1. Make a folder with `extension.json` and your page.
2. In Extensions, More, Link a folder. gachamod uses the folder where it is, so saving a file and picking Reload
   pages from its menu shows the change.
3. When it works, More, Share a package zips it and opens the submission page.

## Lists (repos)

A list is an `index.json` on the web:

```json
{
  "format": 1,
  "name": "gachamod extensions",
  "submit": "https://github.com/imanimal/gachamod-extensions/issues/new?template=submit.yml",
  "packages": [{
    "id": "character-notes", "name": "Character notes", "version": "1.0.0", "kind": "extension",
    "author": "gachamod", "description": "...", "games": [], "icon": "https://.../icon.svg",
    "download": "https://.../character-notes-1.0.0.zip", "sha256": "...", "size": 4096, "updated": 1794000000,
    "permissions": { "library": true }, "needs": []
  }]
}
```

gachamod refuses a download whose SHA-256 doesn't match, and the package inside has to have the same id and version
as its entry. Lists are cached for 6 hours (Refresh on the Extensions page fetches them again). Anyone can host a
list; players add its link in Settings, Extensions, Extension lists.

gachamod's own list is built by `tools/build_index.py` in gachamod-extensions from the folders under `packages/`.

## Safety

- Pages run in a sandboxed frame with their own origin and a content security policy that blocks network calls
  except through gachamod. Each call is checked against the package's permissions in the UI and again in Rust.
- `fetch` doesn't follow redirects, so an allowed origin can't send a page elsewhere. File reads resolve links and
  `..` first, then check the folder.
- A page can still navigate its own frame to another site. It can't reach gachamod's API from there, but this is why
  gachamod's list reads every package before listing it, and why installing from a file says where it came from.
- Removing or replacing a package moves it to the app's trash, so Undo works. Copies go after 14 days.

# Putting the game on another site

The browser game in `web/` builds to a static site -- HTML, JavaScript, the
card pictures, and a copy of Pyodide -- and every path in it is relative. The
workflow in `.github/workflows/pages.yml` publishes it from `main` to

    https://bobbymeyer.github.io/succession/

There are two ways to show it on bobbymeyer.com.

## 1. An iframe (any page, any host)

Paste this where the game should go:

```html
<iframe
  src="https://bobbymeyer.github.io/succession/"
  title="Court of Succession"
  allow="fullscreen; clipboard-write"
  style="display: block; width: 100%; height: 100vh; height: 100dvh; min-height: 640px; border: 0"
></iframe>
```

What each part is for:

* **Height.** The game scrolls inside its own frame and keeps the question
  pinned in view as the board scrolls, so give it the height of the screen
  rather than trying to fit the whole board. `100dvh` is the same as `100vh`
  on browsers that know it, minus the mobile address bar.
* **`allow="fullscreen"`** lets the game's *Full screen* button work from
  inside the frame. Without it the button still shows in a plain tab.
* **`allow="clipboard-write"`** lets *Copy game record* work.
* **No `sandbox`.** The game needs scripts, a Web Worker, its own storage for
  finished games, and downloads for the CSV export. If a site builder insists
  on a sandbox, it needs at least
  `sandbox="allow-scripts allow-same-origin allow-downloads allow-modals allow-popups"`.

Inside a frame the game also offers *Open in a new tab*, for anyone on a small
screen who would rather have the whole window.

Finished games are kept in the browser's storage for the frame's own site.
Browsers keep an embedded site's storage apart from the same site visited
directly, so games played on bobbymeyer.com and games played at the github.io
address are two separate lists. Each exports on its own, and `analyze` pools
the CSVs.

## 2. At bobbymeyer.com/succession/ (Netlify)

bobbymeyer.com is served by Netlify, which can proxy a path to another site.
Add these lines to the site's `_redirects` file (or the equivalent
`[[redirects]]` blocks in `netlify.toml`):

```
/succession   /succession/                                    301!
/succession/* https://bobbymeyer.github.io/succession/:splat  200!
```

The game then lives at `https://www.bobbymeyer.com/succession/` on your own
domain -- linkable, full-page, and embeddable from any page on the site with
the iframe above pointed at `/succession/` instead.

The first line matters. The game loads its files relative to its own address,
so it must be opened with the trailing slash; without that rule GitHub's own
redirect would send visitors to the github.io address.

## Updating it

Merging to `main` rebuilds and republishes; the Netlify proxy and any iframe
pick the new version up on their own. GitHub Pages lets browsers cache files
for ten minutes, so a change can take that long to show.

## One-time setup

In the repository's **Settings -> Pages**, set **Source** to
**GitHub Actions**. Until then the deploy job fails with a message saying
Pages is not enabled.

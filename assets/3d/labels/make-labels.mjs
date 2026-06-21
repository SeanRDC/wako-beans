// Prints each bag's wrap (colour + print mask) by opening label.html in headless Chrome.
//   node assets/3d/labels/make-labels.mjs [slug ...]
import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..", "..", "..");
const out = join(here, "..", "out", "labels");
mkdirSync(out, { recursive: true });

const chrome = [
  process.env.CHROME,
  "C:/Program Files/Google/Chrome/Application/chrome.exe",
  "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
  "/usr/bin/google-chrome",
].find((p) => p && existsSync(p));
if (!chrome) throw new Error("No Chrome or Edge found. Set CHROME to its path.");

const coffees = JSON.parse(readFileSync(join(root, "src", "content", "coffees.json"), "utf8"));
const wanted = process.argv.slice(2);

for (const coffee of coffees) {
  if (wanted.length && !wanted.includes(coffee.slug)) continue;
  for (const mask of [false, true]) {
    const file = join(out, `${coffee.slug}${mask ? "-mask" : ""}.png`);
    const url = `${pathToFileURL(join(here, "label.html"))}?c=${encodeURIComponent(JSON.stringify(coffee))}${mask ? "&mask=1" : ""}`;
    execFileSync(chrome, [
      "--headless=new",
      "--disable-gpu",
      "--hide-scrollbars",
      "--force-device-scale-factor=1",
      "--window-size=3264,2000",
      "--virtual-time-budget=9000",
      `--screenshot=${file}`,
      url,
    ], { stdio: "ignore" });
    console.log("label", file);
  }
}

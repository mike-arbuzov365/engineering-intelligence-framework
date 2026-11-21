import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { once } from "node:events";
import { readFile } from "node:fs/promises";
import { createServer } from "node:http";
import { createRequire } from "node:module";

const html = await readFile(new URL("./retry.html", import.meta.url), "utf8");
const action = await readFile(new URL("./action.mjs", import.meta.url), "utf8");
const mouseOnly = action.replace('createElement("button")', 'createElement("div")');

function version(component) {
  return "sha256:" + createHash("sha256").update(html).update("\0").update(component).digest("hex");
}

async function run(candidate, probe) {
  let requests = 0;
  const routes = {
    "/": ["text/html; charset=utf-8", html],
    "/action.mjs": ["text/javascript; charset=utf-8", candidate],
  };
  const server = createServer((request, response) => {
    if (request.url === "/api/result") {
      response.writeHead(++requests === 1 ? 503 : 200).end();
    } else if (Object.hasOwn(routes, request.url)) {
      const [type, body] = routes[request.url];
      response.writeHead(200, { "content-type": type }).end(body);
    } else {
      response.writeHead(404).end();
    }
  });
  server.listen(0, "127.0.0.1");
  try {
    await once(server, "listening");
    await probe(`http://127.0.0.1:${server.address().port}`);
  } finally {
    await new Promise((resolve, reject) => {
      server.close((error) => error ? reject(error) : resolve());
    });
  }
}

if (process.argv[2] === "--api") {
  const responses = [];
  await run(mouseOnly, async (url) => {
    responses.push((await fetch(url + "/api/result")).status);
    responses.push((await fetch(url + "/api/result")).status);
    assert.deepEqual(responses, [503, 200]);
  });
  console.log(JSON.stringify({ revision: version(mouseOnly), responses }));
} else if (process.argv[2] === "--browser") {
  const require = createRequire(new URL("../../../../site/package.json", import.meta.url));
  const { chromium } = require("playwright");
  const browser = await chromium.launch({ headless: true, channel: process.env.EIF_BROWSER_CHANNEL });
  try {
    const checkKeyboard = async (candidate, keyboardReady) => {
      await run(candidate, async (url) => {
        const page = await browser.newPage();
        try {
          let releaseRetry;
          if (keyboardReady) {
            let requests = 0;
            const retryReady = new Promise(resolve => { releaseRetry = resolve; });
            await page.route("**/api/result", async route => {
              if (++requests === 2) await retryReady;
              await route.continue();
            });
          }
          await page.goto(url);
          await page.getByText("Request failed", { exact: true }).waitFor();
          await page.keyboard.press("Tab");
          const focused = await page.evaluate(() => document.activeElement?.id);
          if (keyboardReady) {
            assert.equal(focused, "retry");
            await page.keyboard.press("Enter");
            try {
              await page.getByText("Loading", { exact: true }).waitFor();
            } finally {
              releaseRetry();
            }
            await page.getByText("Request succeeded", { exact: true }).waitFor();
          } else {
            assert.notEqual(focused, "retry");
          }
        } finally {
          await page.close();
        }
      });
    };
    await checkKeyboard(mouseOnly, false);
    await checkKeyboard(action, true);
    console.log(JSON.stringify({
      revision: version(action),
      browser: browser.version(),
      negativeControl: "Tab did not reach Retry",
      check: "Tab focused Retry; Enter reached loading and success",
    }));
  } finally {
    await browser.close();
  }
} else {
  throw new Error("Use --api or --browser");
}

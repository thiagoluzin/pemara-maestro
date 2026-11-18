import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const root = new URL(".", import.meta.url).pathname.replace(/^\/(.:)/, "$1");
const compositions = join(root, "compositions");
mkdirSync(compositions, { recursive: true });

const products = [
  ["frame-02-fsp-vita-gm", "01", "FSP VITA GM 1000W", "R$ 1.000", "assets/cards/qwen_fonte_44.png"],
  ["frame-03-xpg-kyber", "02", "XPG KYBER 850W", "R$ 600", "assets/cards/qwen_fonte_288.png"],
  ["frame-04-deepcool-pl750d", "03", "DEEPCOOL PL750D", "R$ 500", "assets/cards/qwen_fonte_39.png"],
  ["frame-05-deepcool-pl650d-v2", "04", "DEEPCOOL PL650D V2", "R$ 380", "assets/cards/qwen_fonte_40.png"],
  ["frame-06-c3tech-ps-g700b", "05", "C3TECH PS-G700B", "R$ 300", "assets/cards/qwen_fonte_48.png"],
  ["frame-07-nzxt-c650", "06", "NZXT C650 GOLD", "R$ 300", "assets/cards/qwen_fonte_336.png"],
  ["frame-08-duex-dx600fse", "07", "DUEX DX-600FSE", "R$ 280", "assets/cards/qwen_fonte_47.png"],
  ["frame-09-duex-dx600fse-plus", "08", "DUEX DX-600FSE+", "R$ 230", "assets/cards/qwen_fonte_36.png"],
  ["frame-10-kmex-pw-ez8898f", "09", "K-MEX PW-EZ8898F", "R$ 230", "assets/cards/qwen_fonte_41.png"],
  ["frame-11-leadertech-lt500", "10", "LEADER TECH LT-500W", "R$ 130", "assets/cards/qwen_fonte_286.png"],
];

function productFrame(id, count, name, price, asset) {
  return `<template>
  <style>
    @font-face { font-family: "Pemara Inter"; src: url("assets/fonts/inter-latin-variable.woff2") format("woff2"); font-weight: 100 900; font-style: normal; }
    #root { position: relative; width: 1080px; height: 1920px; overflow: hidden; color: #f7fbff; font-family: "Pemara Inter", sans-serif; }
    #${id}-ground { position: absolute; inset: 0; background: radial-gradient(circle at 50% 44%, #132b3c 0%, #07111f 62%, #030914 100%); }
    #${id}-grid { position: absolute; inset: 0; opacity: .18; background-image: linear-gradient(rgba(142,163,184,.15) 2px, transparent 2px), linear-gradient(90deg, rgba(142,163,184,.15) 2px, transparent 2px); background-size: 72px 72px; }
    #${id}-glow { position: absolute; left: 80px; top: 300px; width: 920px; height: 1160px; border-radius: 50%; background: radial-gradient(circle, rgba(255,106,0,.28) 0%, rgba(55,232,135,.10) 44%, transparent 72%); filter: blur(24px); }
    #${id}-header { position: absolute; left: 64px; right: 64px; top: 84px; height: 120px; display: flex; align-items: center; justify-content: space-between; border-bottom: 3px solid rgba(142,163,184,.34); }
    #${id}-count { font-size: 48px; font-weight: 850; letter-spacing: .08em; color: #37e887; }
    #${id}-category { font-size: 26px; font-weight: 800; letter-spacing: .16em; color: #f7fbff; }
    #${id}-card-wrap { position: absolute; left: 70px; top: 246px; width: 940px; height: 1175px; padding: 18px; border: 3px solid rgba(247,251,255,.35); border-radius: 44px; background: rgba(16,28,45,.88); box-shadow: 0 36px 80px rgba(0,0,0,.46); }
    #${id}-card { width: 100%; height: 100%; object-fit: contain; border-radius: 28px; display: block; }
    #${id}-meta { position: absolute; left: 70px; right: 70px; top: 1458px; display: grid; grid-template-columns: 1fr auto; align-items: end; gap: 32px; }
    #${id}-name { font-size: 31px; line-height: 1.08; font-weight: 850; letter-spacing: -.02em; color: #f7fbff; max-width: 620px; }
    #${id}-price { font-size: 42px; line-height: 1; font-weight: 900; color: #ff6a00; white-space: nowrap; }
    #${id}-progress-track { position: absolute; left: 70px; right: 70px; top: 1568px; height: 10px; border-radius: 999px; background: rgba(142,163,184,.22); overflow: hidden; }
    #${id}-progress { width: ${Number(count) * 10}%; height: 100%; border-radius: inherit; background: linear-gradient(90deg, #ff6a00, #37e887); transform-origin: left center; }
  </style>
  <div id="root" data-composition-id="${id}" data-start="0" data-duration="3.8" data-width="1080" data-height="1920">
    <div id="${id}-ground" class="clip" data-start="0" data-duration="3.8" data-track-index="0"></div>
    <div id="${id}-grid" class="clip" data-start="0" data-duration="3.8" data-track-index="1"></div>
    <div id="${id}-glow" class="clip" data-start="0" data-duration="3.8" data-track-index="2"></div>
    <div id="${id}-header" class="clip" data-start="0" data-duration="3.8" data-track-index="3">
      <div id="${id}-count">${count} / 10</div><div id="${id}-category">FONTES · PEMARA TECH</div>
    </div>
    <div id="${id}-card-wrap" class="clip" data-start="0" data-duration="3.8" data-track-index="4"><img id="${id}-card" src="${asset}" alt="${name}"></div>
    <div id="${id}-meta" class="clip" data-start="0" data-duration="3.8" data-track-index="5"><div id="${id}-name">${name}</div><div id="${id}-price">${price}</div></div>
    <div id="${id}-progress-track" class="clip" data-start="0" data-duration="3.8" data-track-index="6"><div id="${id}-progress"></div></div>
  </div>
  <script src="assets/vendor/gsap.min.js"></script>
  <script>
    window.__timelines = window.__timelines || {};
    const tl = gsap.timeline({ paused: true });
    tl.fromTo("#${id}-header", { opacity: 0, y: -28 }, { opacity: 1, y: 0, duration: .34, ease: "power3.out" }, 0)
      .fromTo("#${id}-card-wrap", { opacity: 0, y: 36, scale: .92 }, { opacity: 1, y: 0, scale: 1, duration: .58, ease: "power3.out" }, .08)
      .fromTo("#${id}-glow", { opacity: 0, scale: .82 }, { opacity: 1, scale: 1, duration: .72, ease: "power2.out" }, .16)
      .fromTo("#${id}-meta", { opacity: 0, y: 26 }, { opacity: 1, y: 0, duration: .42, ease: "power3.out" }, .58)
      .fromTo("#${id}-progress", { scaleX: 0 }, { scaleX: 1, duration: .72, ease: "power2.out" }, .84)
      .to("#${id}-glow", { scale: 1.06, opacity: .82, duration: .96, ease: "sine.out" }, .90);
    window.__timelines["${id}"] = tl;
  </script>
</template>`;
}

function introFrame() {
  const id = "frame-01-intro";
  return `<template>
  <style>
    @font-face { font-family: "Pemara Inter"; src: url("assets/fonts/inter-latin-variable.woff2") format("woff2"); font-weight: 100 900; font-style: normal; }
    #root { position: relative; width: 1080px; height: 1920px; overflow: hidden; color: #f7fbff; font-family: "Pemara Inter", sans-serif; }
    #${id}-ground { position:absolute; inset:0; background:radial-gradient(circle at 50% 40%, #173449 0%, #07111f 58%, #030914 100%); }
    #${id}-glow { position:absolute; left:100px; top:190px; width:880px; height:1050px; border-radius:50%; background:radial-gradient(circle, rgba(255,106,0,.28), rgba(55,232,135,.10) 48%, transparent 72%); filter:blur(30px); }
    #${id}-logo { position:absolute; left:190px; top:220px; width:700px; height:430px; object-fit:contain; }
    #${id}-title { position:absolute; left:70px; right:70px; top:760px; display:flex; flex-direction:column; align-items:center; gap:8px; text-align:center; }
    #${id}-title span { display:block; font-size:98px; line-height:.94; font-weight:900; letter-spacing:-.055em; }
    #${id}-title span:last-child { color:#ff6a00; }
    #${id}-proof { position:absolute; left:270px; top:1135px; width:540px; padding:25px 34px; border:3px solid rgba(55,232,135,.7); border-radius:999px; text-align:center; font-size:38px; font-weight:850; letter-spacing:.04em; background:rgba(16,28,45,.88); }
    #${id}-rule { position:absolute; left:160px; right:160px; top:1290px; height:9px; background:linear-gradient(90deg, transparent, #ff6a00, #37e887, transparent); }
  </style>
  <div id="root" data-composition-id="${id}" data-start="0" data-duration="3.0" data-width="1080" data-height="1920">
    <div id="${id}-ground" class="clip" data-start="0" data-duration="3.0" data-track-index="0"></div>
    <div id="${id}-glow" class="clip" data-start="0" data-duration="3.0" data-track-index="1"></div>
    <img id="${id}-logo" class="clip" data-start="0" data-duration="3.0" data-track-index="2" src="assets/pemara-logo.png" alt="Pemara Tech">
    <div id="${id}-title" class="clip" data-start="0" data-duration="3.0" data-track-index="3" data-layout-allow-occlusion><span>FONTES</span><span>PEMARA TECH</span></div>
    <div id="${id}-proof" class="clip" data-start="0" data-duration="3.0" data-track-index="4" data-layout-allow-occlusion>10 MODELOS REAIS</div>
    <div id="${id}-rule" class="clip" data-start="0" data-duration="3.0" data-track-index="5"></div>
  </div>
  <script src="assets/vendor/gsap.min.js"></script>
  <script>
    window.__timelines = window.__timelines || {};
    const tl = gsap.timeline({ paused: true });
    tl.fromTo("#${id}-logo", { opacity: 0, y: -90 }, { opacity: 1, y: 0, duration: .42, ease: "power3.out" }, 0)
      .fromTo("#${id}-title span", { opacity: 0, y: 75 }, { opacity: 1, y: 0, duration: .44, stagger: .10, ease: "power3.out" }, .20)
      .fromTo("#${id}-glow", { opacity: 0, scale: .82 }, { opacity: 1, scale: 1, duration: .75, ease: "power2.out" }, .18)
      .fromTo("#${id}-proof", { opacity: 0, y: 38 }, { opacity: 1, y: 0, duration: .38, ease: "power3.out" }, .72)
      .fromTo("#${id}-rule", { scaleX: 0 }, { scaleX: 1, duration: .38, ease: "power2.out" }, .98);
    window.__timelines["${id}"] = tl;
  </script>
</template>`;
}

function outroFrame() {
  const id = "frame-12-outro";
  return `<template>
  <style>
    @font-face { font-family: "Pemara Inter"; src: url("assets/fonts/inter-latin-variable.woff2") format("woff2"); font-weight: 100 900; font-style: normal; }
    #root { position:relative; width:1080px; height:1920px; overflow:hidden; color:#f7fbff; font-family:"Pemara Inter", sans-serif; }
    #${id}-ground { position:absolute; inset:0; background:radial-gradient(circle at 50% 42%, #173449 0%, #07111f 58%, #030914 100%); }
    #${id}-glow { position:absolute; left:100px; top:200px; width:880px; height:1050px; border-radius:50%; background:radial-gradient(circle, rgba(55,232,135,.22), rgba(255,106,0,.14) 46%, transparent 72%); filter:blur(32px); }
    #${id}-logo { position:absolute; left:205px; top:180px; width:670px; height:410px; object-fit:contain; }
    #${id}-cta { position:absolute; left:64px; right:64px; top:720px; text-align:center; font-size:102px; line-height:.94; font-weight:900; letter-spacing:-.055em; }
    #${id}-cta strong { color:#ff6a00; }
    #${id}-site { position:absolute; left:110px; right:110px; top:1040px; padding:28px 22px; border:3px solid rgba(55,232,135,.72); border-radius:28px; background:rgba(16,28,45,.9); text-align:center; font-size:42px; font-weight:850; color:#37e887; }
    #${id}-region { position:absolute; left:120px; right:120px; top:1195px; text-align:center; font-size:31px; font-weight:750; letter-spacing:.08em; color:#f7fbff; }
    #${id}-rule { position:absolute; left:160px; right:160px; top:1325px; height:9px; background:linear-gradient(90deg, transparent, #ff6a00, #37e887, transparent); }
  </style>
  <div id="root" data-composition-id="${id}" data-start="0" data-duration="3.0" data-width="1080" data-height="1920">
    <div id="${id}-ground" class="clip" data-start="0" data-duration="3.0" data-track-index="0"></div>
    <div id="${id}-glow" class="clip" data-start="0" data-duration="3.0" data-track-index="1"></div>
    <img id="${id}-logo" class="clip" data-start="0" data-duration="3.0" data-track-index="2" src="assets/pemara-logo.png" alt="Pemara Tech">
    <div id="${id}-cta" class="clip" data-start="0" data-duration="3.0" data-track-index="3">ESCOLHA<br><strong>A SUA</strong></div>
    <div id="${id}-site" class="clip" data-start="0" data-duration="3.0" data-track-index="4">LOJA.PEMARATECH.COM.BR</div>
    <div id="${id}-region" class="clip" data-start="0" data-duration="3.0" data-track-index="5">SÃO JOSÉ DO RIO PRETO E REGIÃO</div>
    <div id="${id}-rule" class="clip" data-start="0" data-duration="3.0" data-track-index="6"></div>
  </div>
  <script src="assets/vendor/gsap.min.js"></script>
  <script>
    window.__timelines = window.__timelines || {};
    const tl = gsap.timeline({ paused: true });
    tl.fromTo("#${id}-logo", { opacity: 0, y: -70 }, { opacity: 1, y: 0, duration: .40, ease: "power3.out" }, 0)
      .fromTo("#${id}-cta", { opacity: 0, y: 70 }, { opacity: 1, y: 0, duration: .46, ease: "power3.out" }, .16)
      .fromTo("#${id}-glow", { opacity: 0, scale: .82 }, { opacity: 1, scale: 1, duration: .72, ease: "power2.out" }, .18)
      .fromTo("#${id}-site", { opacity: 0, y: 34 }, { opacity: 1, y: 0, duration: .36, ease: "power3.out" }, .66)
      .fromTo("#${id}-region", { opacity: 0, y: 24 }, { opacity: 1, y: 0, duration: .34, ease: "power3.out" }, .88)
      .fromTo("#${id}-rule", { scaleX: 0 }, { scaleX: 1, duration: .34, ease: "power2.out" }, 1.06);
    window.__timelines["${id}"] = tl;
  </script>
</template>`;
}

writeFileSync(join(compositions, "frame-01-intro.html"), introFrame(), "utf8");
writeFileSync(join(compositions, "frame-01-intro.motion.json"), JSON.stringify({ scene: "frame-01-intro", duration_s: 3.0, duration: 3.0, rules: ["waterfall-entry", "ambient-glow-bloom"], exit: { vector: "stationary 0 px/s", still_moving: false }, entry: { vector: "down 214 px/s", from_rest: false }, assertions: [{ kind: "appearsBy", selector: "#frame-01-intro-logo", bySec: 0.5 }, { kind: "before", a: "#frame-01-intro-logo", b: "#frame-01-intro-proof" }, { kind: "staysInFrame", selector: "#frame-01-intro-logo" }] }, null, 2) + "\n");

for (const product of products) {
  const [id] = product;
  writeFileSync(join(compositions, `${id}.html`), productFrame(...product), "utf8");
  writeFileSync(join(compositions, `${id}.motion.json`), JSON.stringify({ scene: id, duration_s: 3.8, duration: 3.8, rules: ["spring-pop-entrance", "ambient-glow-bloom"], exit: { vector: "stationary 0 px/s", still_moving: false }, entry: { vector: "up 62 px/s", from_rest: false }, assertions: [{ kind: "appearsBy", selector: `#${id}-card-wrap`, bySec: 0.5 }, { kind: "before", a: `#${id}-card-wrap`, b: `#${id}-meta` }, { kind: "staysInFrame", selector: `#${id}-card-wrap` }] }, null, 2) + "\n");
}

writeFileSync(join(compositions, "frame-12-outro.html"), outroFrame(), "utf8");
writeFileSync(join(compositions, "frame-12-outro.motion.json"), JSON.stringify({ scene: "frame-12-outro", duration_s: 3.0, duration: 3.0, rules: ["waterfall-entry", "ambient-glow-bloom"], exit: { vector: "stationary 0 px/s", still_moving: false }, entry: { vector: "down 152 px/s", from_rest: false }, assertions: [{ kind: "appearsBy", selector: "#frame-12-outro-logo", bySec: 0.5 }, { kind: "before", a: "#frame-12-outro-logo", b: "#frame-12-outro-site" }, { kind: "staysInFrame", selector: "#frame-12-outro-site" }] }, null, 2) + "\n");

const scenes = [
  ["frame-01-intro", 0, 3.0],
  ...products.map((p, i) => [p[0], 2.6 + i * 3.4, 3.8]),
  ["frame-12-outro", 36.6, 3.0],
];

const hosts = scenes.map(([id, start, duration], i) => `    <div id="host-${id}" class="clip scene-host" data-composition-id="${id}" data-composition-src="compositions/${id}.html" data-start="${start.toFixed(1)}" data-duration="${duration.toFixed(1)}" data-track-index="${(i % 2) + 1}"></div>`).join("\n");
const transitions = scenes.slice(1).map(([id, start], i) => {
  const previous = scenes[i][0];
  const lead = i === 0 ? "tl.to" : ".to";
  return `    ${lead}("#host-${previous}", { y: -1920, duration: .40, ease: "power3.in" }, ${start.toFixed(1)})\n      .fromTo("#host-${id}", { y: 1920 }, { y: 0, duration: .40, ease: "power3.out" }, ${start.toFixed(1)})`;
}).join("\n");

const index = `<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=1080,height=1920">
  <script src="assets/vendor/gsap.min.js"></script>
  <style>
    @font-face { font-family: "Pemara Inter"; src: url("assets/fonts/inter-latin-variable.woff2") format("woff2"); font-weight: 100 900; font-style: normal; }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    html, body { width: 1080px; height: 1920px; overflow: hidden; background: #07111f; }
    body { font-family: "Pemara Inter", sans-serif; }
    #root { position: relative; width: 1080px; height: 1920px; overflow: hidden; background: #07111f; }
    .scene-host { position: absolute; inset: 0; width: 1080px; height: 1920px; overflow: hidden; }
  </style>
</head>
<body>
  <div id="root" data-composition-id="main" data-start="0" data-duration="39.6" data-width="1080" data-height="1920">
${hosts}
  </div>
  <script>
    window.__timelines = window.__timelines || {};
    const tl = gsap.timeline({ paused: true });
${transitions};
    window.__timelines["main"] = tl;
  </script>
</body>
</html>`;

writeFileSync(join(root, "index.html"), index, "utf8");
console.log(`Built ${scenes.length} scenes and root timeline (${scenes.at(-1)[1] + scenes.at(-1)[2]}s).`);

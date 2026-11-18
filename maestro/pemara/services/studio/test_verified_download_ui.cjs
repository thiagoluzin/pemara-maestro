const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync(require('node:path').join(__dirname, '../../app/assets/maestro.js'), 'utf8');
function actual(name) {
  const start = source.indexOf(`function ${name}(`);
  assert.ok(start >= 0);
  const rest = source.slice(start);
  const end = rest.slice(1).search(/\n(?:async )?function /);
  return end < 0 ? rest : rest.slice(0, end + 1);
}
function anchor() {
  return { attrs: {}, className: 'btn', classList: { contains: () => false },
    get href() { return this.attrs.href; }, set href(x) { this.attrs.href = x; },
    hasAttribute(n) { return n in this.attrs; }, setAttribute(n,v) { this.attrs[n]=v; },
    getAttribute(n) { return this.attrs[n]; }, removeAttribute(n) { delete this.attrs[n]; },
    insertAdjacentElement(where, next) { this.nextElementSibling=next; } };
}
const context = vm.createContext({ URL, window: { location: { href: 'https://maestro.pemaratech.com.br/' } },
  document: { createElement: () => anchor() }, API: { studio: '/api/studio' } });
vm.runInContext(actual('setVerifiedDownloadLink') + '\n' + actual('audioMp3Output'), context);
const link=anchor(); link.href='/api/studio/api/video-projects/p/final-preview?v=hash&download=true';
link.setAttribute('download','video.mp4'); context.setVerifiedDownloadLink(link);
const zip=link.nextElementSibling;
assert.equal(new URL(zip.href).searchParams.get('v'),'hash');
assert.equal(new URL(zip.href).searchParams.get('archive'),'true');
assert.equal(zip.getAttribute('download'),'video.mp4.zip');
link.href='/api/studio/api/video-projects/q/takes/02/preview?download=true';
context.setVerifiedDownloadLink(link);
assert.equal(link.nextElementSibling,zip);
assert.ok(zip.href.includes('/q/takes/02/preview'));
link.removeAttribute('href'); context.setVerifiedDownloadLink(link);
assert.equal(zip.hidden,true); assert.equal(zip.hasAttribute('href'),false);
const music=context.audioMp3Output({ title:'Última música', url:'/api/generative/comfy-view?filename=a.flac&subfolder=audio' });
const musicUrl=new URL(music.archive,'https://maestro.pemaratech.com.br');
assert.equal(musicUrl.searchParams.get('source'),'/api/generative/comfy-view?filename=a.flac&subfolder=audio');
assert.equal(musicUrl.searchParams.get('archive'),'true');
console.log('PASS: video ZIP URL, updated selection, hidden download and music ZIP URL');

const fs = require("node:fs");
const vm = require("node:vm");
const assert = require("node:assert/strict");
const source = fs.readFileSync(require("node:path").join(__dirname,"maestro.js"),"utf8");
const select = {value:"ace_step_local",set innerHTML(value){this.html=value;this.value="ace_step_local";}};
const state = {genAudioProviderSelections:{},genStatus:{defaults:{audio_provider:"levo2_local",music_provider:"yue2_local",sfx_provider:"stable_audio"},
 providers:{audio:{ace_step_local:{configured:true,modes:["music"]},yue2_local:{configured:true,modes:["music"]},stable_audio:{configured:true,modes:["sfx"]}}}}};
const context = {state,$:()=>select,html:x=>x,syncGenAudioProviderDetails:()=>{}};
vm.createContext(context);
for(const [start,end] of [["function genAudioProvidersForMode","function syncGenAudioProviderDetails"],
 ["function syncGenAudioProviderOptions","function videoEngineById"]]){
 vm.runInContext(source.slice(source.indexOf(start),source.indexOf(end,source.indexOf(start))),context);
}
context.syncGenAudioProviderOptions("music");
assert.equal(select.value,"yue2_local","initial automatic ACE selection must not override YuE2");
delete state.genStatus.defaults.music_provider;
context.syncGenAudioProviderOptions("music");
assert.equal(select.value,"yue2_local","old server defaults must not restore LeVo or first ACE selection");
state.genAudioProviderSelections.music="ace_step_local";
context.syncGenAudioProviderOptions("music");
assert.equal(select.value,"ace_step_local","explicit owner choice must survive refresh");
delete state.genAudioProviderSelections.music;
state.genStatus.providers.audio.yue2_local.configured=false;
context.syncGenAudioProviderOptions("music");
assert.equal(select.value,"yue2_local","unavailable YuE2 must not silently become ACE");
context.syncGenAudioProviderOptions("sfx");
assert.equal(select.value,"stable_audio","music preference must not leak into SFX");
delete state.genStatus.providers.audio.yue2_local;
context.syncGenAudioProviderOptions("music");
assert.equal(select.value,"","missing preferred engine must not silently select another music provider");
console.log("PASS: six provider selection behaviors");

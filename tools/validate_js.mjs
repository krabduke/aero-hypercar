/* Check the browser solver against the Python one.
 *
 * The browser runs a coarser lattice than aero/analyse.py on purpose, so the
 * two will not agree exactly. What has to hold is that they describe the same
 * car: the same downforce to within a stated tolerance, the same sign, and the
 * same response to ground effect.
 */
import { Tunnel } from '../viewer/windtunnel.js';
import { readFileSync } from 'node:fs';

const cfg = JSON.parse(readFileSync(new URL('./tunnel.json', import.meta.url)));
const ctl = {}; for(const c of cfg.controls) ctl[c.id] = c.value;

const t = new Tunnel(cfg);
const v = cfg.v_default;
const q = 0.5*1.225*v*v;

console.log('\nBROWSER SOLVER CHECK  (VX-1 wings, in ground effect)');
console.log(`  reference area ${cfg.s_ref.toFixed(3)} m2   speed ${(v*3.6).toFixed(0)} km/h`);

let a = performance.now();
const ge = t.solve({alpha: 0, v, controls: ctl, ground: true});
const t1 = performance.now() - a;
const free = t.solve({alpha: 0, v, controls: ctl, ground: false});
a = performance.now();
for(let i = 0; i < 30; i++) t.solve({alpha: 0, v, controls: {...ctl, drs: i}, ground: true});
const per = (performance.now() - a)/30;

const dfGE = -ge.CL*q*cfg.s_ref/9.81;
const dfFree = -free.CL*q*cfg.s_ref/9.81;

console.log(`\n  panels ${ge.panels}   first solve ${t1.toFixed(0)} ms`
          + `   repeat ${per.toFixed(2)} ms`);
console.log(`  free air        ${dfFree.toFixed(0)} kg`);
console.log(`  in ground effect${dfGE.toFixed(0).padStart(9)} kg`
          + `   (${((dfGE/dfFree-1)*100).toFixed(1)} %)`);
console.log(`  induced drag    ${(ge.CDi*q*cfg.s_ref/9.81).toFixed(0)} kg-force`);
console.log(`  downforce/drag  ${ge.LD.toFixed(1)}`);

console.log('\n  DRS sweep (rear flap opening sheds downforce and drag):');
for(const d of [0, 8, 16, 24, 28]){
  const s = t.solve({alpha: 0, v, controls: {...ctl, drs: d}, ground: true});
  console.log(`    ${String(d).padStart(2)} deg   downforce ${(-s.CL*q*cfg.s_ref/9.81).toFixed(0).padStart(4)} kg`
            + `   drag ${(s.CDi*q*cfg.s_ref/9.81).toFixed(0).padStart(4)} kg`);
}

console.log('\n  Front flap sweep (aero balance):');
for(const d of [-6, -3, 0, 5, 10]){
  const s = t.solve({alpha: 0, v, controls: {...ctl, front_flap: d}, ground: true});
  let f = 0, tot = 0;
  for(const [k, val] of Object.entries(s.bySurface)){
    tot += val; if(cfg.front_surfaces.includes(k)) f += val;
  }
  console.log(`    ${String(d).padStart(3)} deg   downforce ${(-s.CL*q*cfg.s_ref/9.81).toFixed(0).padStart(4)} kg`
            + `   front share ${(f/tot*100).toFixed(0)} %`);
}

// Python reports 577 kg in ground effect at 250 km/h on a finer lattice.
const REF = 577;
const err = Math.abs(dfGE/REF - 1)*100;
const ok = err < 25 && dfGE > 0 && dfGE > dfFree;
console.log('\n' + '='.repeat(62));
console.log(`  against aero/analyse.py: ${dfGE.toFixed(0)} kg vs ${REF} kg`
          + `  (${err.toFixed(0)} %, limit 25 % on a coarser lattice)`);
console.log(ok ? 'PASS  browser solver agrees with the Python solver'
               : 'FAIL  browser solver disagrees with the Python solver');
process.exit(ok ? 0 : 1);

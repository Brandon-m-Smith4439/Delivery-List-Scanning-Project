// File: tests/scan_reference_contract.cjs
const fs = require('fs'), vm = require('vm'), assert = require('assert/strict');
const source = fs.readFileSync('static/js/app.js', 'utf8');
function definition(name) {
  const start = source.search(new RegExp(`(?:async )?function ${name}\\(`));
  assert(start >= 0, name);
  const end = source.slice(start + 1).search(/\n(?:async )?function /);
  return end < 0 ? source.slice(start) : source.slice(start, start + 1 + end);
}
const state = {backend:true,page:'admin',lists:[{id:'one',deliveryDate:'2026-09-09'}],meta:{deliveryDate:'2026-09-09'},
  items:[],scanDateWideLoadTokenV485:0,pageIndex:3,glassTypeFilters:new Set()};
let resolveFetch, navigations=0;
const context = vm.createContext({state,console,AbortController,Map,Date,Number,Math,Array,String,Boolean,
  performance,encodeURIComponent,els:{},
  window:{setTimeout,clearTimeout},
  fetchJson:()=>new Promise(r=>resolveFetch=r),
  scanDateWideCatalogSignatureV486:()=> 'revision-1',
  scanStagePresetV485:()=> 'airport_staging',
  buildDateWideScanItemsV485:()=>[{id:'item'}],
  renderStationOptions:()=>{},renderScanPage:()=>{},renderDeliveryDateSelect:()=>{},
  showPage:()=>{assert.equal(state.scanDateWideLoadingV485,false);assert.equal(state.scanDateWideAbortControllerV512,null);navigations++},
  escapeHtml:value=>String(value).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;'),
  compactMachineLabelV475:()=> '',cuttingLabelEdgeCalloutsV507:()=>[],appLocale:()=> 'en-US',PLANT_TIME_ZONE_V516:'America/New_York'});
for(const name of ['cancelScanDateWideLoadV512','activateScanDateV485','parseGeneratedSketchDimensionV516','generatedSketchDimensionsV516','generatedProductionSketchV516']) {
  vm.runInContext(definition(name),context);
}
const bundle={records:[{list:{id:'one'},payload:{meta:{id:'one',deliveryDate:'2026-09-09'}}}]};
(async()=>{
 const pending=context.activateScanDateV485('2026-09-09',true);resolveFetch(bundle);await pending;
 assert.equal(navigations,1);assert.equal(state.pageIndex,3);
 const oldItems=state.items;
 const cancelled=context.activateScanDateV485('2026-09-09',false);
 context.cancelScanDateWideLoadV512();resolveFetch({records:[]});await cancelled;
 assert.equal(state.items,oldItems,'Late cancelled result must not replace current rows');
 assert.equal(context.parseGeneratedSketchDimensionV516('29-1/16"'),29.0625);
 assert.equal(context.parseGeneratedSketchDimensionV516('1/0'),0);
 assert.equal(context.parseGeneratedSketchDimensionV516('unknown 32'),0);
 const item={order:'238001',item:'001',dimensions:'5" x 100"',cutting:{shapeNumber:99}};
 const html=context.generatedProductionSketchV516(item);
 assert(html.includes('SIZE ENVELOPE ONLY'));assert(!html.includes('<circle'));
 const box=html.match(/<rect x="[^"]+" y="[^"]+" width="([^"]+)" height="([^"]+)" fill="#fbfdff"/);
 assert.equal(Number(box[1])/Number(box[2]),.05);
 const g={width:100,height:5,units:'inches',source:'item.dxf',paths:[[[0,0],[100,0],[100,5],[0,5],[0,0]]]};
 const real=context.generatedProductionSketchV516(item,{}, {},g);
 assert(real.includes('<polyline'));assert(real.includes('source orientation'));
 const mismatch=context.generatedProductionSketchV516({...item,dimensions:'30" x 60"'}, {}, {},g);
 assert(!mismatch.includes('<polyline'));assert(mismatch.includes('SIZE ENVELOPE ONLY'));
 console.log('Scan ownership, cancellation and reference geometry behavior passed.');
})().catch(error=>{console.error(error);process.exitCode=1});

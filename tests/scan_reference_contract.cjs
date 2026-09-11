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
  items:[],scanDateWideLoadTokenV485:0,pageIndex:3,glassTypeFilters:new Set(),scanDateWideCacheV526:new Map(),scanDateWideCacheLimitV526:5,
  scanDatePrefetchV527:new Map()};
let resolveFetch, fetchCalls=0, navigations=0;
const context = vm.createContext({state,console,AbortController,Map,Date,Number,Math,Array,String,Boolean,
  performance,encodeURIComponent,els:{},
  window:{setTimeout,clearTimeout},
  fetchJson:()=>{fetchCalls++;return new Promise(r=>resolveFetch=r)},
  scanDateWideCatalogSignatureV486:()=> 'revision-1',
  scanStagePresetV485:()=> 'airport_staging',
  buildDateWideScanItemsV485:()=>[{id:'item'}],
  renderStationOptions:()=>{},renderScanPage:()=>{},renderDeliveryDateSelect:()=>{},
  scheduleScanDatePrefetchV527:()=>{},
  showPage:()=>{assert.equal(state.scanDateWideLoadingV485,false);assert.equal(state.scanDateWideAbortControllerV512,null);navigations++},
  escapeHtml:value=>String(value).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;'),
  compactMachineLabelV475:()=> '',cuttingLabelEdgeCalloutsV507:()=>[],appLocale:()=> 'en-US',PLANT_TIME_ZONE_V516:'America/New_York'});
for(const name of ['cachedScanDateBundleV526','rememberScanDateBundleV526','invalidateScanDateBundleV526','cancelScanDateWideLoadV512','activateScanDateV485','parseGeneratedSketchDimensionV516','generatedSketchDimensionsV516','generatedProductionSketchV516']) {
  vm.runInContext(definition(name),context);
}
const bundle={records:[{list:{id:'one'},payload:{meta:{id:'one',deliveryDate:'2026-09-09'}}}]};
(async()=>{
 const pending=context.activateScanDateV485('2026-09-09',true);resolveFetch(bundle);await pending;
 assert.equal(navigations,1);assert.equal(state.pageIndex,3);assert.equal(fetchCalls,1);
 const cached=context.activateScanDateV485('2026-09-09',false);await cached;
 assert.equal(fetchCalls,1,'Unchanged repeat date must reuse the v0.526 signature cache');
 assert.equal(state.scanDateWideLastLoadMsV486,0,'Cached date switch should report zero network-load time');
 const oldItems=state.items;
 state.scanDateWideCacheV526.clear();
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

 // v0.526: a pending result that omitted checkedAt still inherits the successful
 // batch timestamp. Automatic Scan rendering must not recheck it until ten
 // minutes have elapsed; once stale, it becomes eligible exactly once.
 let fabricationRequests=0;
 const fabricationKey='926001|001';
 const cadenceState={backend:true,page:'scan',fabricationStatusCacheV474:new Map([[fabricationKey,{fabricated:false,retryAfterSeconds:0}]]),
   productionProgressCheckedV522:new Map([[fabricationKey,{at:Date.now(),retryAfterSeconds:60}]]),cuttingStatusCacheV522:new Map(),
   fabricationStatusPendingV474:new Set(),fabricationStatusBatchTokenV474:0,fabricationStatusEpochV522:0,productionFileSettings:{cacheMinutes:1},
   items:[],globalSearchLastResults:[],orderDetailProductionCacheV507:new Map(),orderDetailRenderedPayloadV507:null};
  const cadenceContext=vm.createContext({state:cadenceState,document:{hidden:false},Date,Number,Math,Array,String,Boolean,Map,Set,console,FABRICATION_AUTO_RETRY_MS_V526:600000,
   hasAnyPermission:()=>true,fabricationRevisionV521:()=>'',fabricationStatusKeyV474:()=>fabricationKey,cuttingProgressPresentationV498:()=>({complete:false}),
   requestFabricationBatchV522:async()=>{fabricationRequests++;return {results:[{key:fabricationKey,status:{fabricated:false,retryAfterSeconds:300},cutting:{},progressRetryAfterSeconds:300}]}},
   fabricationStatusItemKeyV521:()=>fabricationKey,window:{setTimeout},scheduleScanRender:()=>{},printWorkspaceIsVisible:()=>false});
 vm.runInContext(definition('hydrateFabricationStatusesV474'),cadenceContext);
 const cadenceRow={order:'926001',item:'001',job:'J',product:'Glass'};
 await cadenceContext.hydrateFabricationStatusesV474([cadenceRow],{context:'scan'});
 assert.equal(fabricationRequests,0,'Fresh pending fabrication must respect the 10-minute Scan retry window');
 cadenceState.productionProgressCheckedV522.set(fabricationKey,{at:Date.now()-601000,retryAfterSeconds:60});
  await cadenceContext.hydrateFabricationStatusesV474([cadenceRow],{context:'scan'});
  assert.equal(fabricationRequests,1,'Stale pending fabrication should become eligible after 10 minutes');
  cadenceState.fabricationStatusCacheV474.delete(fabricationKey);
  await cadenceContext.hydrateFabricationStatusesV474([cadenceRow],{context:'scan'});
  assert.equal(fabricationRequests,1,'A partial response with no cached status must still respect its recent attempt timestamp');

  let failedRepaints=0;
  cadenceState.page='scan';
  cadenceState.productionProgressCheckedV522.set(fabricationKey,{at:Date.now()-601000,retryAfterSeconds:60});
  cadenceContext.requestFabricationBatchV522=async()=>{fabricationRequests++;throw new Error('share unavailable')};
  cadenceContext.scheduleScanRender=()=>{failedRepaints++};
  await cadenceContext.hydrateFabricationStatusesV474([cadenceRow],{context:'scan'});
  await cadenceContext.hydrateFabricationStatusesV474([cadenceRow],{context:'scan'});
  assert.equal(fabricationRequests,2,'A failed fabrication request must not retry again on the next render');
  assert.equal(failedRepaints,0,'A failed fabrication request must not replace Scan rows');
  console.log('Scan ownership, cancellation, date cache, fabrication cadence and reference geometry behavior passed.');
})().catch(error=>{console.error(error);process.exitCode=1});

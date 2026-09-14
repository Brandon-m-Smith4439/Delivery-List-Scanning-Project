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
   isRemakeItem:(row)=>Boolean(row?.remake),
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


  // v0.528 completion audit: import-status snapshots that omit the catalog must
  // never erase usable Home/Scan state while a manual/automatic A+W run finishes.
  const importState={lists:[{id:'live-list',deliveryDate:'2026-09-16'}],items:[{id:'live-item'}],meta:{id:'live-list'},
    adminRecentImports:[],adminTodayImportEntries:[],adminTodayImportLoaded:false,activeListId:'live-list'};
  let catalogApplies=0,visibleRefreshes=0;
  const importDocument={
    getElementById:()=>null,
    dispatchEvent:()=>{},
    addEventListener:()=>{},
  };
  const importContext=vm.createContext({state:importState,console,Array,String,Boolean,Date,Map,Set,
    document:importDocument,CustomEvent:function(){},window:{setTimeout:(fn)=>{fn();},requestAnimationFrame:(fn)=>{fn();}},
    dlsAutomationLatestImportCheckedAt:'',
    dlsAutomationMergeRecentImports:(current,latest)=>[...(current||[]),...(latest||[])],
    todayKey:()=> '2026-09-11',
    dlsAutomationApplyDeliveryCatalog:()=>{catalogApplies++;return true;},
    dlsAutomationActiveDetailIsStale:()=>false,
    dlsAutomationRefreshVisibleListViews:()=>{visibleRefreshes++;},
    refreshAdminTodayImportRuns:()=>Promise.resolve(),
    dlsAutomationRefreshActiveListDetail:()=>Promise.resolve(true),
  });
  const importStart=source.indexOf('function dlsAutomationApplyImportSnapshot(');
  const importEnd=source.indexOf('\ndocument.addEventListener("dls:delivery-list-data-refreshed"',importStart);
  assert(importStart >= 0 && importEnd > importStart,'dlsAutomationApplyImportSnapshot exact boundary');
  vm.runInContext(source.slice(importStart,importEnd),importContext);
  importContext.dlsAutomationApplyImportSnapshot({lists:[],latestImportResults:[{runId:'run-1'}],lastCheckedAt:'2026-09-11T12:00:00Z'});
  assert.equal(catalogApplies,0,'Empty import-result catalog must not replace an already loaded delivery catalog');
  assert.equal(importState.lists.length,1);assert.equal(importState.lists[0].id,'live-list');
  assert.equal(importState.items.length,1);assert.equal(importState.items[0].id,'live-item');
  assert.equal(visibleRefreshes,1,'Visible page may repaint while retaining its loaded data');

  // All Scans must render one Internal Reject incident even when the same reject
  // reaches the merged history through multiple source/event representations.
  const dedupeContext=vm.createContext({console,Set,String,Array,scanEntryDisplayItem:(entry)=>entry.item||{}});
  vm.runInContext(definition('dedupeRecentEventsV527'),dedupeContext);
  const deduped=dedupeContext.dedupeRecentEventsV527([
    {eventType:'internal_reject',rejectId:'reject-77',item:{order:'238100',item:'001'}},
    {eventType:'reject_sync',details:{rejectId:'reject-77'},item:{order:'238100',item:'001'}},
    {eventType:'scan',item:{order:'238100',item:'001'}},
  ]);
  assert.equal(deduped.length,2,'Duplicate representations of one rejectId must collapse to one All Scans row');

  // A deferred sketch parse that sees the large REMAKE text is authoritative for
  // the existing item-level remake owner without mutating production-line data.
  const remakeKey='238200|001';
  const remakeState={fabricationStatusCacheV474:new Map([[remakeKey,{sketchRemake:true}]])};
  const remakeContext=vm.createContext({state:remakeState,Boolean,String,
    fabricationStatusItemKeyV521:()=>remakeKey});
  vm.runInContext(definition('isRemakeItem'),remakeContext);
  assert.equal(remakeContext.isRemakeItem({order:'238200',item:'001'}),true,'Sketch REMAKE evidence must flag the item as a remake');

  console.log('Scan ownership, cancellation, date cache, fabrication cadence and reference geometry behavior passed.');
})().catch(error=>{console.error(error);process.exitCode=1});

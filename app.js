/*
  Delivery List Scanner UI
  ------------------------
  Code map for future edits:
  - State/element references live at the top of this file.
  - Shared helpers come next: formatting, dates, permissions, fetch helpers, search helpers.
  - Page renderers are grouped by area: Home, Scan, Racks, Bay Map, Admin, Print/Email.
  - Event wiring is intentionally centralized near the bottom in wireEvents().

  Keep edits copy-paste friendly. Prefer changing an existing function/block instead of
  adding a second override below it; the app has grown through many UI polish passes and
  duplicated behavior is the main thing that can make it slower or harder to debug.
*/
const STORAGE_KEY = "delivery-list-scanner-demo-v1";
const STATIONS_KEY = "delivery-list-scanner-stations-v1";
const LANGUAGE_KEY = "delivery-list-scanner-language-v1";
const DEFAULT_STATIONS = ["Airport Rd", "Indian Trail", "Greenville", "Customer Pickup", "DTC"];
const ROLE_OPTIONS = ["Operator", "Supervisor", "Indian Trail Operator", "Indian Trail Lead", "Indian Trail Manager", "Admin"];
const CUSTOMER_ROUTE_OPTIONS = [
  { value: "CPU", label: "CPU / Customer Pickup" },
  { value: "DTC", label: "DTC / Deliver to Customer" },
  { value: "GNV", label: "GNV / Greenville" },
];
const CUSTOMER_ROUTE_DEFAULT_ADDRESSES = {
  CPU: "1709 Airport Rd, Monroe, NC 28110",
  GNV: "Greenville address pending",
};
const ADMIN_DELIVERY_LIST_DEFAULT_PAST_DAYS = 21;
const ADMIN_DELIVERY_LIST_LOAD_MORE_DAYS = 7;

const state = {
  page: "home",
  meta: null,
  lists: [],
  stations: DEFAULT_STATIONS.slice(),
  activeListId: "",
  items: [],
  recent: [],
  errors: [],
  selectedId: null,
  filter: "all",
  glassTypeFilter: "all",
  search: "",
  pageIndex: 1,
  pageSize: 25,
  homeSearch: "",
  homeStageFilter: "all",
  overviewRange: "30",
  homePageIndex: 1,
  homePageSize: 25,
  expandedDeliveryDate: "",
  collapsedGlassTypes: new Set(),
  baySearch: "",
  bayStatusFilter: "all",
  bayCategoryFilter: "all",
  bayGlassFilter: "all",
  baySpecialFilter: "all",
  staleBayOrders: [],
  staleBayAlertDate: "",
  selectedBayCode: "",
  bayEditMode: false,
  pendingBayMove: null,
  collapsedBaySections: new Set(),
  baySectionsDefaultCollapsed: false,
  bayActionUndoStack: [],
  bayActionRedoStack: [],
  bayLayoutUndoStack: [],
  bayLayoutRedoStack: [],
  bayLayoutDraft: null,
  bayLayoutOriginal: null,
  selectedBayOverrideCode: "",
  bayOverrideMode: "auto",
  bayOverrideOpenSections: new Set(),
  bayHoldingSections: new Set(),
  bayGroupColumns: {},
  racks: [],
  rackSummary: null,
  selectedRackCode: "T",
  selectedRackOverviewCode: "",
  selectedRackSetLabel: "",
  rackScanListId: "",
  rackModal: null,
  rackMoveItemId: "",
  rackManagerSelectedCode: "",
  rackManagerEditingRackCode: "",
  rackManagerEditingSetLabel: "",
  rackStatusFilter: "all",
  rackSort: "code-asc",
  printContext: null,
  bayLayout: null,
  bays: [],
  bayEvents: [],
  manageItemsQuery: "",
  manageItemsSelectedId: "",
  bayEditorSelectedGroup: "",
  bayEditorSelectedBay: "",
  adminCustomerRouteRules: [],
  customerEmailSettings: { contacts: [], cc: [], outbox: [] },
  bayScannerSettings: { manualRules: [], barcodeRules: [] },
  bayAutoAssignSettings: {
    standardMaxInches: 59.99,
    tallMinInches: 60,
    oversizeMinInches: 96,
    standardBayType: "Standard",
    tallBayType: "Tall",
    oversizeBayType: "Oversize",
    mirrorBayType: "Mirror",
    framedMirrorBayType: "Framed Mirror",
    cpuBayType: "CPU",
    manualAssignTypes: ["Tall", "Oversize"],
  },
  activeSessions: [],
  adminUsers: [],
  adminRoles: [],
  allPermissions: [],
  adminRecentImports: [],
  adminListSearchTimer: null,
  adminDeliveryListVisiblePastDays: ADMIN_DELIVERY_LIST_DEFAULT_PAST_DAYS,
  rolePermissionOpenRoles: new Set(),
  rolePermissionOpenCategories: new Set(),
  rolePermissionScrollTop: 0,
  manualEditLookups: { products: [], routes: [], processes: [] },
  manualEditDirty: false,
  manualEditListId: "",
  manualEditQuery: "",
  expandedRackGroups: new Set(),
  expandedRackCodes: new Set(),
  backend: false,
  authenticated: false,
  user: null,
  permissions: [],
  eventsWired: false,
  pollTimer: null,
  lastScan: null,
  homeReportSummary: null,
  homeChartMetric: "glass",
  homeChartView: "bar",
  homeChartQuery: "",
  homeChartLimit: "all",
  homeChartSort: "value-desc",
  language: (() => {
    try {
      return localStorage.getItem(LANGUAGE_KEY) === "es" ? "es" : "en";
    } catch {
      return "en";
    }
  })(),
  restoreFullscreenAfterPrint: false,
};

const els = {
  loginPanel: document.getElementById("loginPanel"),
  loginForm: document.getElementById("loginForm"),
  loginUsername: document.getElementById("loginUsername"),
  loginPassword: document.getElementById("loginPassword"),
  loginError: document.getElementById("loginError"),
  forgotPasswordBtn: document.getElementById("forgotPasswordBtn"),
  passwordResetPanel: document.getElementById("passwordResetPanel"),
  resetIdentityInput: document.getElementById("resetIdentityInput"),
  requestResetCodeBtn: document.getElementById("requestResetCodeBtn"),
  resetCodeInput: document.getElementById("resetCodeInput"),
  resetNewPasswordInput: document.getElementById("resetNewPasswordInput"),
  confirmPasswordResetBtn: document.getElementById("confirmPasswordResetBtn"),
  cancelPasswordResetBtn: document.getElementById("cancelPasswordResetBtn"),
  passwordResetMessage: document.getElementById("passwordResetMessage"),
  signedInUser: document.getElementById("signedInUser"),
  signedInRole: document.getElementById("signedInRole"),
  userMenuDisplayName: document.getElementById("userMenuDisplayName"),
  userMenuDetails: document.getElementById("userMenuDetails"),
  backendStatus: document.getElementById("backendStatus"),
  logoutBtn: document.getElementById("logoutBtn"),
  headerGlobalSearchInput: document.getElementById("headerGlobalSearchInput"),
  headerGlobalSearchBtn: document.getElementById("headerGlobalSearchBtn"),
  headerGlobalSearchResults: document.getElementById("headerGlobalSearchResults"),
  globalPrintExportBtn: document.getElementById("globalPrintExportBtn"),
  languageToggleBtn: document.getElementById("languageToggleBtn"),
  loginLanguageToggleBtn: document.getElementById("loginLanguageToggleBtn"),
  fullscreenToggleBtn: document.getElementById("fullscreenToggleBtn"),
  bayAutoAssignOverview: document.getElementById("bayAutoAssignOverview"),

  homePage: document.getElementById("homePage"),
  homeWelcome: document.getElementById("homeWelcome"),
  overviewStats: document.getElementById("overviewStats"),
  overviewRangeSelect: document.getElementById("overviewRangeSelect"),
  homeUserCard: document.getElementById("homeUserCard"),
  homeRecentLists: document.getElementById("homeRecentLists"),
  homeActivity: document.getElementById("homeActivity"),
  homeStatsPdfBtn: document.getElementById("homeStatsPdfBtn"),
  homeStatisticsRangeText: document.getElementById("homeStatisticsRangeText"),
  homeStatsChart: document.getElementById("homeStatsChart"),
  homeMonthlyRemakes: document.getElementById("homeMonthlyRemakes"),
  statsChartModal: document.getElementById("statsChartModal"),
  statsChartBackdrop: document.getElementById("statsChartBackdrop"),
  statsChartCloseBtn: document.getElementById("statsChartCloseBtn"),
  statsChartMetricSelect: document.getElementById("statsChartMetricSelect"),
  statsChartViewSelect: document.getElementById("statsChartViewSelect"),
  statsChartSortSelect: document.getElementById("statsChartSortSelect"),
  statsChartLimitSelect: document.getElementById("statsChartLimitSelect"),
  statsChartFilterInput: document.getElementById("statsChartFilterInput"),
  statsChartResetBtn: document.getElementById("statsChartResetBtn"),
  statsChartResultCount: document.getElementById("statsChartResultCount"),
  statsChartModalTitle: document.getElementById("statsChartModalTitle"),
  statsChartModalSubtitle: document.getElementById("statsChartModalSubtitle"),
  statsChartModalCanvas: document.getElementById("statsChartModalCanvas"),
  homeListSearch: document.getElementById("homeListSearch"),
  homeStageFilter: document.getElementById("homeStageFilter"),
  homeListGrid: document.getElementById("homeListGrid"),
  homeListCount: document.getElementById("homeListCount"),
  homePageSize: document.getElementById("homePageSize"),
  homePager: document.getElementById("homePager"),
  homePagerTop: document.getElementById("homePagerTop"),
  todayDateLabel: document.getElementById("todayDateLabel"),
  todayStageGrid: document.getElementById("todayStageGrid"),

  scanPage: document.getElementById("scanPage"),
  pageTitle: document.getElementById("pageTitle"),
  stageSubtitle: document.getElementById("stageSubtitle"),
  stageHeading: document.getElementById("stageHeading"),
  scannerName: document.getElementById("scannerName"),
  deliveryListSelect: document.getElementById("deliveryListSelect"),
  deliveryDateSelect: document.getElementById("deliveryDateSelect"),
  deliveryStageSelect: document.getElementById("deliveryStageSelect"),
  stationSelect: document.getElementById("stationSelect"),
  stationProfileDisplay: document.getElementById("stationProfileDisplay"),
  operatorInput: document.getElementById("operatorInput"),
  progressText: document.getElementById("progressText"),
  progressFill: document.getElementById("progressFill"),
  searchInput: document.getElementById("searchInput"),
  scanForm: document.getElementById("scanForm"),
  scanInput: document.getElementById("scanInput"),
  scanRackPanel: document.getElementById("scanRackPanel"),
  scanRackSelect: document.getElementById("scanRackSelect"),
  scanRackCompleteBtn: document.getElementById("scanRackCompleteBtn"),
  scanRackPrintBtn: document.getElementById("scanRackPrintBtn"),
  scanRackStatus: document.getElementById("scanRackStatus"),
  scanBayOverridePanel: document.getElementById("scanBayOverridePanel"),
  scanBayOverrideSelected: document.getElementById("scanBayOverrideSelected"),
  scanBayOverrideClearBtn: document.getElementById("scanBayOverrideClearBtn"),
  scanBayOverrideMode: document.getElementById("scanBayOverrideMode"),
  scanBayOverrideSelect: document.getElementById("scanBayOverrideSelect"),
  scanBayOverrideGroups: document.getElementById("scanBayOverrideGroups"),
  manualScanForm: document.getElementById("manualScanForm"),
  manualOrderInput: document.getElementById("manualOrderInput"),
  manualItemInput: document.getElementById("manualItemInput"),
  manualAssignPanel: document.getElementById("manualAssignPanel"),
  manualAssignForm: document.getElementById("manualAssignForm"),
  manualAssignOrderInput: document.getElementById("manualAssignOrderInput"),
  manualAssignItemInput: document.getElementById("manualAssignItemInput"),
  manualAssignQtyInput: document.getElementById("manualAssignQtyInput"),
  manualAssignStatus: document.getElementById("manualAssignStatus"),
  listRows: document.getElementById("listRows"),
  recentRows: document.getElementById("recentRows"),
  viewAllRecent: document.getElementById("viewAllRecent"),
  mobileListCards: document.getElementById("mobileListCards"),
  lastCard: document.getElementById("lastCard"),
  lastScanTime: document.getElementById("lastScanTime"),
  lastJob: document.getElementById("lastJob"),
  lastOrder: document.getElementById("lastOrder"),
  lastItem: document.getElementById("lastItem"),
  lastQty: document.getElementById("lastQty"),
  lastDims: document.getElementById("lastDims"),
  lastCustomer: document.getElementById("lastCustomer"),
  totalItemsText: document.getElementById("totalItemsText"),
  countAll: document.getElementById("countAll"),
  countRemaining: document.getElementById("countRemaining"),
  countPartial: document.getElementById("countPartial"),
  countComplete: document.getElementById("countComplete"),
  countRemakes: document.getElementById("countRemakes"),
  countRushes: document.getElementById("countRushes"),
  countUpdated: document.getElementById("countUpdated"),
  countErrors: document.getElementById("countErrors"),
  countIndianTrailRoute: document.getElementById("countIndianTrailRoute"),
  countCpuRoute: document.getElementById("countCpuRoute"),
  countDtcRoute: document.getElementById("countDtcRoute"),
  countGreenvilleRoute: document.getElementById("countGreenvilleRoute"),
  glassFilterTabs: document.getElementById("glassFilterTabs"),
  remainingQty: document.getElementById("remainingQty"),
  partialQty: document.getElementById("partialQty"),
  completeQty: document.getElementById("completeQty"),
  errorQty: document.getElementById("errorQty"),
  remainingPct: document.getElementById("remainingPct"),
  partialPct: document.getElementById("partialPct"),
  completePct: document.getElementById("completePct"),
  pageSize: document.getElementById("pageSize"),
  pageSizeBottom: document.getElementById("pageSizeBottom"),
  scanPagerTop: document.getElementById("scanPagerTop"),
  scanPagerBottom: document.getElementById("scanPagerBottom"),
  undoBtn: document.getElementById("undoBtn"),
  redoBtn: document.getElementById("redoBtn"),

  racksPage: document.getElementById("racksPage"),
  rackSummary: document.getElementById("rackSummary"),
  rackListSelect: document.getElementById("rackListSelect"),
  rackSelect: document.getElementById("rackSelect"),
  rackScanForm: document.getElementById("rackScanForm"),
  rackScanInput: document.getElementById("rackScanInput"),
  rackScanStatus: document.getElementById("rackScanStatus"),
  rackGrid: document.getElementById("rackGrid"),
  rackCreateOpenBtn: document.getElementById("rackCreateOpenBtn"),
  rackSetCreateOpenBtn: document.getElementById("rackSetCreateOpenBtn"),
  rackEditOpenBtn: document.getElementById("rackEditOpenBtn"),

  bayMapPage: document.getElementById("bayMapPage"),
  bayOverviewStats: document.getElementById("bayOverviewStats"),
  bayMapSearch: document.getElementById("bayMapSearch"),
  bayScanOutForm: document.getElementById("bayScanOutForm"),
  bayScanOutInput: document.getElementById("bayScanOutInput"),
  bayScanBayInput: document.getElementById("bayScanBayInput"),
  bayScanModeToggle: document.getElementById("bayScanModeToggle"),
  bayManualOrderInput: document.getElementById("bayManualOrderInput"),
  bayManualItemInput: document.getElementById("bayManualItemInput"),
  bayManualQtyInput: document.getElementById("bayManualQtyInput"),
  bayManualSubmitBtn: document.getElementById("bayManualSubmitBtn"),
  bayScanOutStatus: document.getElementById("bayScanOutStatus"),
  bayScanOutRecent: document.getElementById("bayScanOutRecent"),
  bayLastCard: document.getElementById("bayLastCard"),
  bayLastTitle: document.getElementById("bayLastTitle"),
  bayLastAction: document.getElementById("bayLastAction"),
  bayLastOrder: document.getElementById("bayLastOrder"),
  bayLastBay: document.getElementById("bayLastBay"),
  bayLastTime: document.getElementById("bayLastTime"),
  bayAllScansBtn: document.getElementById("bayAllScansBtn"),
  bayUndoBtn: document.getElementById("bayUndoBtn"),
  bayRedoBtn: document.getElementById("bayRedoBtn"),
  bayStatusFilter: document.getElementById("bayStatusFilter"),
  bayGlassFilter: document.getElementById("bayGlassFilter"),
  baySpecialFilter: document.getElementById("baySpecialFilter"),
  bayCategoryFilters: document.getElementById("bayCategoryFilters"),
  baySelectedPanel: document.getElementById("baySelectedPanel"),
  baySelectedModal: document.getElementById("baySelectedModal"),
  baySelectedBackdrop: document.getElementById("baySelectedBackdrop"),
  baySelectedCloseBtn: document.getElementById("baySelectedCloseBtn"),
  bayAllBaysList: document.getElementById("bayAllBaysList"),
  bayCheckBtn: document.getElementById("bayCheckBtn"),
  bayFilterDrawer: document.getElementById("bayFilterDrawer"),
  bayActiveFilterBar: document.getElementById("bayActiveFilterBar"),
  bayActiveFilterSummary: document.getElementById("bayActiveFilterSummary"),
  bayActiveFilterCount: document.getElementById("bayActiveFilterCount"),
  bayClearFiltersBtn: document.getElementById("bayClearFiltersBtn"),
  bayFlowPanel: document.getElementById("bayFlowPanel"),
  indianTrailSummary: document.getElementById("indianTrailSummary"),
  bayActionButtons: document.getElementById("bayActionButtons"),
  bayMapCanvas: document.getElementById("bayMapCanvas"),
  baySelectedText: document.getElementById("baySelectedText"),
  sdiPanel: document.getElementById("sdiPanel"),
  sdiBackdrop: document.getElementById("sdiBackdrop"),
  sdiForm: document.getElementById("sdiForm"),
  sdiCloseBtn: document.getElementById("sdiCloseBtn"),
  sdiClearBtn: document.getElementById("sdiClearBtn"),
  sdiOrderInput: document.getElementById("sdiOrderInput"),
  sdiBayInput: document.getElementById("sdiBayInput"),
  sdiTruckExemptInput: document.getElementById("sdiTruckExemptInput"),
  sdiReasonInput: document.getElementById("sdiReasonInput"),
  sdiTypeInput: document.getElementById("sdiTypeInput"),
  sdiCurrentList: document.getElementById("sdiCurrentList"),
  manageItemsPanel: document.getElementById("manageItemsPanel"),
  manageItemsBackdrop: document.getElementById("manageItemsBackdrop"),
  manageItemsCloseBtn: document.getElementById("manageItemsCloseBtn"),
  manageItemsSearch: document.getElementById("manageItemsSearch"),
  manageItemsList: document.getElementById("manageItemsList"),
  manageItemsSelected: document.getElementById("manageItemsSelected"),
  manageItemsTargetBay: document.getElementById("manageItemsTargetBay"),
  manageItemsReason: document.getElementById("manageItemsReason"),
  manageItemsMoveBtn: document.getElementById("manageItemsMoveBtn"),
  manageItemsClearBtn: document.getElementById("manageItemsClearBtn"),
  manageItemsScannerBtn: document.getElementById("manageItemsScannerBtn"),
  manageItemsSdiBtn: document.getElementById("manageItemsSdiBtn"),
  manageItemsStatus: document.getElementById("manageItemsStatus"),
  bayEditorBackdrop: document.getElementById("bayEditorBackdrop"),
  bayEditorPanel: document.getElementById("bayEditorPanel"),
  bayEditorCloseBtn: document.getElementById("bayEditorCloseBtn"),
  bayEditorNewGroupBtn: document.getElementById("bayEditorNewGroupBtn"),
  bayEditorGroupList: document.getElementById("bayEditorGroupList"),
  bayEditorGroupForm: document.getElementById("bayEditorGroupForm"),
  bayEditorBayList: document.getElementById("bayEditorBayList"),
  staleBayBackdrop: document.getElementById("staleBayBackdrop"),
  staleBayPanel: document.getElementById("staleBayPanel"),
  staleBayList: document.getElementById("staleBayList"),
  staleBayCloseBtn: document.getElementById("staleBayCloseBtn"),
  staleBayOkBtn: document.getElementById("staleBayOkBtn"),
  staleBayPrintBtn: document.getElementById("staleBayPrintBtn"),
  staleBaySnoozeAllBtn: document.getElementById("staleBaySnoozeAllBtn"),
  staleBaySnoozeAllDays: document.getElementById("staleBaySnoozeAllDays"),
  bayLayoutManager: document.getElementById("bayLayoutManager"),
  bayLayoutCloseBtn: document.getElementById("bayLayoutCloseBtn"),
  bayLayoutSelect: document.getElementById("bayLayoutSelect"),
  bayLayoutDisplayInput: document.getElementById("bayLayoutDisplayInput"),
  bayLayoutSectionInput: document.getElementById("bayLayoutSectionInput"),
  bayLayoutCategoryInput: document.getElementById("bayLayoutCategoryInput"),
  bayLayoutRowInput: document.getElementById("bayLayoutRowInput"),
  bayLayoutColInput: document.getElementById("bayLayoutColInput"),
  bayLayoutCapacityInput: document.getElementById("bayLayoutCapacityInput"),
  bayLayoutActiveInput: document.getElementById("bayLayoutActiveInput"),
  bayLayoutSaveBtn: document.getElementById("bayLayoutSaveBtn"),
  bayLayoutDeleteBtn: document.getElementById("bayLayoutDeleteBtn"),
  bayLayoutUndoBtn: document.getElementById("bayLayoutUndoBtn"),
  bayLayoutRedoBtn: document.getElementById("bayLayoutRedoBtn"),
  bayCollapseAllBtn: document.getElementById("bayCollapseAllBtn"),
  bayExpandAllBtn: document.getElementById("bayExpandAllBtn"),
  bayHoldAllBtn: document.getElementById("bayHoldAllBtn"),
  bayLayoutConfirmBtn: document.getElementById("bayLayoutConfirmBtn"),
  bayLayoutCancelBtn: document.getElementById("bayLayoutCancelBtn"),

  printOptionsPanel: document.getElementById("printOptionsPanel"),
  printOptionsBackdrop: document.getElementById("printOptionsBackdrop"),
  printOptionsDate: document.getElementById("printOptionsDate"),
  printOptionsStages: document.getElementById("printOptionsStages"),
  printOptionsGlassType: document.getElementById("printOptionsGlassType"),
  printCustomerFilter: document.getElementById("printCustomerFilter"),
  printOrderFilter: document.getElementById("printOrderFilter"),
  printUpdatedOnly: document.getElementById("printUpdatedOnly"),
  printRushOnly: document.getElementById("printRushOnly"),
  printRemakeOnly: document.getElementById("printRemakeOnly"),
  printOptionsClose: document.getElementById("printOptionsClose"),
  printOptionsSubmit: document.getElementById("printOptionsSubmit"),

  adminPage: document.getElementById("adminPage"),
  adminSummary: document.getElementById("adminSummary"),
  adminLastUpdated: document.getElementById("adminLastUpdated"),
  adminDeliveryLists: document.getElementById("adminDeliveryLists"),
  adminModal: document.getElementById("adminModal"),
  adminModalBackdrop: document.getElementById("adminModalBackdrop"),
  adminModalTitle: document.getElementById("adminModalTitle"),
  adminModalBody: document.getElementById("adminModalBody"),
  adminModalClose: document.getElementById("adminModalClose"),
  folderImportBtn: document.getElementById("folderImportBtn"),
  tempFolderInput: document.getElementById("tempFolderInput"),
  importPreviewBox: document.getElementById("importPreviewBox"),
  importHistory: document.getElementById("importHistory"),
  importFromDate: document.getElementById("importFromDate"),
  importToDate: document.getElementById("importToDate"),
  importWindowResetBtn: document.getElementById("importWindowResetBtn"),
  deleteDateSelect: document.getElementById("deleteDateSelect"),
  deleteListSelect: document.getElementById("deleteListSelect"),
  deleteListBtn: document.getElementById("deleteListBtn"),
  deleteDateBtn: document.getElementById("deleteDateBtn"),
  deleteListStatus: document.getElementById("deleteListStatus"),
  resetListSelect: document.getElementById("resetListSelect"),
  adminResetScansBtn: document.getElementById("adminResetScansBtn"),
  resetScansStatus: document.getElementById("resetScansStatus"),
  createUserForm: document.getElementById("createUserForm"),
  newUserName: document.getElementById("newUserName"),
  newUserDisplay: document.getElementById("newUserDisplay"),
  newUserEmail: document.getElementById("newUserEmail"),
  newUserPassword: document.getElementById("newUserPassword"),
  newUserRole: document.getElementById("newUserRole"),
  adminUsers: document.getElementById("adminUsers"),
  newStationInput: document.getElementById("newStationInput"),
  addStationBtn: document.getElementById("addStationBtn"),
  adminStations: document.getElementById("adminStations"),
  customerRouteRuleForm: document.getElementById("customerRouteRuleForm"),
  customerRoutePatternInput: document.getElementById("customerRoutePatternInput"),
  customerRouteSelect: document.getElementById("customerRouteSelect"),
  customerRouteRules: document.getElementById("customerRouteRules"),
  customerEmailOverview: document.getElementById("customerEmailOverview"),
  bayScannerRuleOverview: document.getElementById("bayScannerRuleOverview"),
  manualEditSearch: document.getElementById("manualEditSearch"),
  manualEditStageSelect: document.getElementById("manualEditStageSelect"),
  manualEditSearchBtn: document.getElementById("manualEditSearchBtn"),
  manualEditResults: document.getElementById("manualEditResults"),
  activeSessions: document.getElementById("activeSessions"),
};

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function pad(value, length) {
  return String(value).padStart(length, "0");
}

const SPANISH_UI_TEXT = new Map([
  ["Home", "Inicio"],
  ["Scan", "Escanear"],
  ["Racks", "Racks"],
  ["Bay Map", "Mapa de Bahias"],
  ["Admin", "Administracion"],
  ["Search", "Buscar"],
  ["Print/Export", "Imprimir/Exportar"],
  ["Sign out", "Cerrar sesion"],
  ["Sign in", "Iniciar sesion"],
  ["Secure sign in", "Inicio de sesion seguro"],
  ["Welcome back", "Bienvenido de nuevo"],
  ["BFS Email or Username", "Correo BFS o nombre de usuario"],
  ["Password", "Contrasena"],
  ["Forgot password?", "Olvido su contrasena?"],
  ["Password reset", "Restablecer contrasena"],
  ["Reset access", "Restablecer acceso"],
  ["Request reset code", "Solicitar codigo"],
  ["Reset Code", "Codigo de restablecimiento"],
  ["New Password", "Nueva contrasena"],
  ["Reset password", "Restablecer contrasena"],
  ["Back to sign in", "Volver al inicio"],
  ["Delivery List Overview", "Resumen de listas de entrega"],
  ["Today's Delivery Progress", "Progreso de entregas de hoy"],
  ["Find Delivery List", "Buscar lista de entrega"],
  ["Statistics Dashboard", "Panel de estadisticas"],
  ["Plant performance", "Rendimiento de planta"],
  ["Range", "Rango"],
  ["Last 30 days", "Ultimos 30 dias"],
  ["Last week", "Ultima semana"],
  ["Full year", "Ano completo"],
  ["All lists", "Todas las listas"],
  ["PDF", "PDF"],
  ["Remakes", "Rehechos"],
  ["Stage Breakdown", "Desglose por etapa"],
  ["Action & Scan Health", "Actividad y estado de escaneo"],
  ["Date", "Fecha"],
  ["Stage", "Etapa"],
  ["Station", "Estacion"],
  ["Status", "Estado"],
  ["All", "Todos"],
  ["Not Scanned", "Sin escanear"],
  ["Partial", "Parcial"],
  ["Complete", "Completo"],
  ["Rushes", "Urgentes"],
  ["New/Updated", "Nuevo/Actualizado"],
  ["Errors", "Errores"],
  ["Route", "Ruta"],
  ["Glass Type", "Tipo de vidrio"],
  ["Rows", "Filas"],
  ["Job Nr.", "Num. de trabajo"],
  ["Order Nr.", "Num. de orden"],
  ["Item Nr.", "Num. de articulo"],
  ["Qty.", "Cant."],
  ["Qty", "Cant."],
  ["Dimensions", "Dimensiones"],
  ["Customer", "Cliente"],
  ["Flags", "Indicadores"],
  ["Location", "Ubicacion"],
  ["Process State", "Estado del proceso"],
  ["Transportation Method", "Metodo de transporte"],
  ["Complete Rack", "Completar rack"],
  ["Complete", "Completar"],
  ["Uncomplete", "Reabrir"],
  ["Print Packing List", "Imprimir lista de empaque"],
  ["Not On The Way", "No esta en camino"],
  ["Mark Returned", "Marcar devuelto"],
  ["Scan Barcode", "Escanear codigo de barras"],
  ["Undo", "Deshacer"],
  ["Redo", "Rehacer"],
  ["Manual Scan", "Escaneo manual"],
  ["Submit", "Enviar"],
  ["Scan History", "Historial de escaneos"],
  ["All scans", "Todos los escaneos"],
  ["Recent scans", "Escaneos recientes"],
  ["Remaining", "Restante"],
  ["Needs Review", "Requiere revision"],
  ["Rack Overview", "Resumen de racks"],
  ["Edit Racks", "Editar racks"],
  ["Indian Trail Inventory", "Inventario de Indian Trail"],
  ["Bay Map Command Center", "Centro de control de bahias"],
  ["Open list", "Abrir lista"],
  ["Open manifest", "Abrir manifiesto"],
  ["Outbound sent", "Salida enviada"],
  ["Received at Indian Trail", "Recibido en Indian Trail"],
  ["Admin Dashboard", "Panel de administracion"],
  ["Delivery List Management", "Administracion de listas de entrega"],
  ["Edit Delivery Lists", "Editar listas de entrega"],
  ["Customer Route Rules", "Reglas de rutas de clientes"],
  ["Edit Customer Routes", "Editar rutas de clientes"],
  ["Customer Email Rules", "Reglas de correo de clientes"],
  ["Edit Emails", "Editar correos"],
  ["Users", "Usuarios"],
  ["Edit Users", "Editar usuarios"],
  ["Active Sessions", "Sesiones activas"],
  ["Open", "Abierto"],
  ["Empty", "Vacio"],
  ["On the way", "En camino"],
  ["Truck", "Camion"],
  ["Steel", "Acero"],
  ["Wood", "Madera"],
  ["Aluminum", "Aluminio"],
  ["Other", "Otro"],
  ["No rack", "Sin rack"],
  ["Loading racks...", "Cargando racks..."],
  ["Choose an option", "Elija una opcion"],
  ["No matching options", "No hay opciones coincidentes"],
  ["Filter options...", "Filtrar opciones..."],
  ["Open full chart", "Abrir grafica completa"],
  ["Reset filters", "Restablecer filtros"],
  ["Save", "Guardar"],
  ["Cancel", "Cancelar"],
  ["Delete", "Eliminar"],
  ["Close", "Cerrar"],
  ["Add", "Agregar"],
  ["Edit", "Editar"],
]);

[
  ["Bay Map", "Mapa de Bahías"],
  ["Admin", "Administración"],
  ["Sign out", "Cerrar sesión"],
  ["Sign in", "Iniciar sesión"],
  ["Secure sign in", "Inicio de sesión seguro"],
  ["Welcome back", "Bienvenido de nuevo"],
  ["BFS Email or Username", "Correo BFS o nombre de usuario"],
  ["Password", "Contraseña"],
  ["Forgot password?", "¿Olvidó su contraseña?"],
  ["Password reset", "Restablecer contraseña"],
  ["Request reset code", "Solicitar código"],
  ["Reset Code", "Código de restablecimiento"],
  ["New Password", "Nueva contraseña"],
  ["Reset password", "Restablecer contraseña"],
  ["Back to sign in", "Volver al inicio de sesión"],
  ["Today's Delivery Progress", "Progreso de entregas de hoy"],
  ["Statistics Dashboard", "Panel de estadísticas"],
  ["Last 30 days", "Últimos 30 días"],
  ["Last week", "Última semana"],
  ["Full year", "Año completo"],
  ["Station", "Estación"],
  ["Location", "Ubicación"],
  ["Manual Scan", "Escaneo manual"],
  ["Scan History", "Historial de escaneos"],
  ["Needs Review", "Requiere revisión"],
  ["Bay Map Command Center", "Centro de control de bahías"],
  ["Admin Dashboard", "Panel de administración"],
  ["Delivery List Management", "Administración de listas de entrega"],
  ["Customer Route Rules", "Reglas de rutas de clientes"],
  ["Active Sessions", "Sesiones activas"],
  ["All stages", "Todas las etapas"],
  ["All statuses", "Todos los estados"],
  ["All glass types", "Todos los tipos de vidrio"],
  ["All bay orders", "Todas las órdenes en bahías"],
  ["Attention", "Atención"],
  ["Assigned station", "Estación asignada"],
  ["Available", "Disponible"],
  ["Bay", "Bahía"],
  ["Bay Auto Assigner", "Asignador automático de bahías"],
  ["Bay Code", "Código de bahía"],
  ["Bay Directory", "Directorio de bahías"],
  ["Bay Scan", "Escaneo de bahía"],
  ["Bay Scan History", "Historial de escaneos de bahía"],
  ["Bay Scanner Rules", "Reglas del escáner de bahías"],
  ["Blocked Scans", "Escaneos bloqueados"],
  ["Cancel", "Cancelar"],
  ["Chart data", "Datos de la gráfica"],
  ["Chart style", "Estilo de gráfica"],
  ["Check", "Verificar"],
  ["Clear", "Limpiar"],
  ["Clear filters", "Limpiar filtros"],
  ["Close", "Cerrar"],
  ["Collapse All", "Contraer todo"],
  ["Customer Emails", "Correos de clientes"],
  ["Customer manifests", "Manifiestos de clientes"],
  ["Data driven", "Basado en datos"],
  ["Delivery Date", "Fecha de entrega"],
  ["Delivery List", "Lista de entrega"],
  ["Delivery lists", "Listas de entrega"],
  ["Details open when a bay is selected", "Los detalles se abren al seleccionar una bahía"],
  ["Display", "Mostrar"],
  ["Done", "Listo"],
  ["Donut chart", "Gráfica de dona"],
  ["Edit Bays", "Editar bahías"],
  ["Edit Map", "Editar mapa"],
  ["Edit Physical Bay Map", "Editar mapa físico de bahías"],
  ["Edit auto assigner", "Editar asignación automática"],
  ["Edit customer routes", "Editar rutas de clientes"],
  ["Edit delivery lists", "Editar listas de entrega"],
  ["Edit emails", "Editar correos"],
  ["Edit lookups", "Editar catálogos"],
  ["Edit role permissions", "Editar permisos de roles"],
  ["Edit rules", "Editar reglas"],
  ["Edit users", "Editar usuarios"],
  ["Errors / Needs Review", "Errores / Requiere revisión"],
  ["Expand All", "Expandir todo"],
  ["Export XLSX", "Exportar XLSX"],
  ["Filter chart labels", "Filtrar etiquetas de la gráfica"],
  ["Filters", "Filtros"],
  ["Find Bay", "Buscar bahía"],
  ["Find Match", "Buscar coincidencia"],
  ["Full Statistics Chart", "Gráfica completa de estadísticas"],
  ["Glass type", "Tipo de vidrio"],
  ["Grouped by rack/category", "Agrupado por rack/categoría"],
  ["Highest first", "Mayor primero"],
  ["Import / Update Delivery List", "Importar / Actualizar lista de entrega"],
  ["Import folder and date settings", "Carpeta de importación y fechas"],
  ["Indian Trail Bay Assignment", "Asignación de bahía de Indian Trail"],
  ["Indian Trail only", "Solo Indian Trail"],
  ["Item", "Artículo"],
  ["Latest 2", "Últimos 2"],
  ["Lists", "Listas"],
  ["Lowest first", "Menor primero"],
  ["Manage Bay Items", "Administrar artículos de bahía"],
  ["Manage Items", "Administrar artículos"],
  ["Manual", "Manual"],
  ["Manual Assign", "Asignación manual"],
  ["Manual Bay Assign", "Asignación manual de bahía"],
  ["Move Item", "Mover artículo"],
  ["Occupied", "Ocupado"],
  ["Old Bay Review", "Revisión de bahías antiguas"],
  ["Order", "Orden"],
  ["Outbound", "Salida"],
  ["Physical Bay Map", "Mapa físico de bahías"],
  ["Print", "Imprimir"],
  ["Print / Export Delivery Lists", "Imprimir / Exportar listas de entrega"],
  ["Print Packing Slip", "Imprimir lista de empaque"],
  ["Products, routes, and process options.", "Productos, rutas y opciones de proceso."],
  ["Progress by route/stage", "Progreso por ruta/etapa"],
  ["Rack recovery", "Recuperación de racks"],
  ["Ready notices", "Avisos de disponibilidad"],
  ["Reason", "Motivo"],
  ["Review", "Revisar"],
  ["Run Print/Export", "Ejecutar Imprimir/Exportar"],
  ["Rush", "Urgente"],
  ["Rush orders", "Órdenes urgentes"],
  ["Save Layout", "Guardar diseño"],
  ["Scan staging pieces into racks, close racks, and print rack packing lists.", "Escanee piezas de preparación en racks, cierre racks e imprima listas de empaque."],
  ["Scanned vs open work", "Escaneado frente a trabajo pendiente"],
  ["Scans by operator", "Escaneos por operador"],
  ["Select a delivery list", "Seleccione una lista de entrega"],
  ["Select an item to begin.", "Seleccione un artículo para comenzar."],
  ["Selected Bay", "Bahía seleccionada"],
  ["Selected Bay Tools", "Herramientas de la bahía seleccionada"],
  ["Settings", "Configuración"],
  ["Show all", "Mostrar todo"],
  ["Sort", "Ordenar"],
  ["Specific customers", "Clientes específicos"],
  ["Specific orders", "Órdenes específicas"],
  ["Statistics explorer", "Explorador de estadísticas"],
  ["Summary", "Resumen"],
  ["System activity", "Actividad del sistema"],
  ["Target Bay", "Bahía de destino"],
  ["Today", "Hoy"],
  ["Top 10", "10 principales"],
  ["Top 20", "20 principales"],
  ["Top 5", "5 principales"],
  ["Updated items only", "Solo artículos actualizados"],
  ["Users & Permissions", "Usuarios y permisos"],
  ["Waiting", "En espera"],
].forEach(([english, spanish]) => SPANISH_UI_TEXT.set(english, spanish));

const SPANISH_UI_ADDITIONS = new Map([
  ["+ New Bay Group", "+ Nuevo grupo de bahías"],
  ["A to Z", "A a Z"],
  ["Action", "Acción"],
  ["Add to bay", "Agregar a la bahía"],
  ["are active bays without a confirmed map group/position. Assign them to a group here or in Edit Map.", "son bahías activas sin un grupo o una posición confirmados en el mapa. Asígnelas a un grupo aquí o en Editar mapa."],
  ["Assign", "Asignar"],
  ["Assign order, Job Nr., barcode, or wording into target bay.", "Asigne una orden, un núm. de trabajo, un código de barras o texto a la bahía de destino."],
  ["Attention filters", "Filtros de atención"],
  ["Auto", "Automático"],
  ["Auto Assign", "Asignación automática"],
  ["Auto suggested bay", "Bahía sugerida automáticamente"],
  ["Auto uses the preassigned or suggested bay. Manual sends the selected bay with the next Indian Trail scan.", "Automático usa la bahía preasignada o sugerida. Manual envía la bahía seleccionada con el siguiente escaneo de Indian Trail."],
  ["Bar chart", "Gráfica de barras"],
  ["Bay barcode formats", "Formatos de códigos de barras de bahía"],
  ["Bay glass type filter", "Filtro de tipo de vidrio de bahía"],
  ["Bay map search and filters", "Búsqueda y filtros del mapa de bahías"],
  ["Bay Map v16: command-center layout keeps the scanner available while giving users faster search, filters, and bay actions.", "El diseño del centro de control mantiene disponible el escáner y ofrece búsquedas, filtros y acciones de bahía más rápidas."],
  ["Bay orders", "Órdenes en bahías"],
  ["Bay scan undo and redo", "Deshacer y rehacer escaneos de bahía"],
  ["Bay special filter", "Filtro especial de bahía"],
  ["Bay status filter", "Filtro de estado de bahía"],
  ["Bay type mapping", "Asignación de tipos de bahía"],
  ["Check from", "Revisar desde"],
  ["Check through", "Revisar hasta"],
  ["Choose add/remove, pick a target bay when needed, then scan.", "Elija agregar o quitar, seleccione una bahía de destino cuando sea necesario y luego escanee."],
  ["Choose where CPU, mirrors, standard, tall, and oversize glass should go.", "Elija a dónde deben ir CPU, espejos, vidrio estándar, alto y sobredimensionado."],
  ["Clear Item", "Quitar artículo"],
  ["Clear SDI", "Quitar SDI"],
  ["Clear Rush / Remake", "Quitar urgente / rehacer"],
  ["Click bay or type code", "Haga clic en una bahía o escriba el código"],
  ["Close admin window", "Cerrar ventana de administración"],
  ["Close edit bays window", "Cerrar ventana de edición de bahías"],
  ["Close manage items window", "Cerrar ventana de administración de artículos"],
  ["Close old bay orders", "Cerrar órdenes antiguas de bahía"],
  ["Close print/export", "Cerrar Imprimir/Exportar"],
  ["Close SDI window", "Cerrar ventana SDI"],
  ["Close selected bay", "Cerrar bahía seleccionada"],
  ["Close statistics chart", "Cerrar gráfica de estadísticas"],
  ["Control thresholds and manual assignment categories.", "Controle los límites y las categorías de asignación manual."],
  ["Create, rename, delete, and set bay group behavior from one workflow.", "Cree, renombre, elimine y configure grupos de bahías desde un solo flujo de trabajo."],
  ["Current dashboard range", "Rango actual del panel"],
  ["Customer Pickup", "Recogida del cliente"],
  ["Default: last week + future", "Predeterminado: última semana + futuras"],
  ["Delivery list filters", "Filtros de listas de entrega"],
  ["Delivery list pages", "Páginas de listas de entrega"],
  ["Delivery List Scanner", "Escáner de listas de entrega"],
  ["Drag whole bay groups into the layout you want. Bay names, bay counts, and bay rules are handled in the separate Edit Bays GUI.", "Arrastre grupos completos de bahías al diseño deseado. Los nombres, cantidades y reglas de bahía se administran en la ventana separada Editar bahías."],
  ["Enter fullscreen", "Entrar en pantalla completa"],
  ["Exit fullscreen", "Salir de pantalla completa"],
  ["Enter your BFS email or username. In local mode, the reset code will display here so an admin can complete the reset without email delivery.", "Ingrese su correo BFS o nombre de usuario. En modo local, el código aparecerá aquí para que un administrador pueda completar el restablecimiento sin enviar un correo."],
  ["Exceptions and manual activity", "Excepciones y actividad manual"],
  ["Explore the selected dashboard range.", "Explore el rango seleccionado del panel."],
  ["Extra scan formats for the Bay Map scanner only.", "Formatos de escaneo adicionales solo para el escáner del mapa de bahías."],
  ["Find bays, assign glass, review old orders, and manage the physical bay layout from one page.", "Busque bahías, asigne vidrio, revise órdenes antiguas y administre el diseño físico desde una sola página."],
  ["Generate statistics PDF report", "Generar informe PDF de estadísticas"],
  ["Glass Delivery Scanner", "Escáner de entregas de vidrio"],
  ["Glass type filters", "Filtros de tipo de vidrio"],
  ["Glass type quantity chart", "Gráfica de cantidad por tipo de vidrio"],
  ["Imports plus admin-added values.", "Importaciones más valores agregados por el administrador."],
  ["In Transit: 0", "En tránsito: 0"],
  ["Indian Trail bay actions", "Acciones de bahía de Indian Trail"],
  ["Indian Trail bay scanner", "Escáner de bahías de Indian Trail"],
  ["Indian Trail Route", "Ruta de Indian Trail"],
  ["Item Nr. optional", "Núm. de artículo opcional"],
  ["Known non-standard labels that should not warn.", "Etiquetas no estándar conocidas que no deben generar advertencias."],
  ["Last updated: --", "Última actualización: --"],
  ["List", "Lista"],
  ["Live", "En vivo"],
  ["Local demo", "Demostración local"],
  ["Lookup Manager", "Administrador de catálogos"],
  ["Main pages", "Páginas principales"],
  ["Manage system settings, users, stations, imports, racks, and plant operations.", "Administre la configuración, los usuarios, las estaciones, las importaciones, los racks y las operaciones de planta."],
  ["Manual assign memory", "Memoria de asignación manual"],
  ["Manual bay location", "Ubicación manual de bahía"],
  ["Manual Edit dropdowns", "Menús de edición manual"],
  ["Manual edit stage", "Etapa de edición manual"],
  ["Manually select Indian Trail bay", "Seleccionar manualmente una bahía de Indian Trail"],
  ["Map layout edit mode", "Modo de edición del diseño del mapa"],
  ["Mark Rush / SDI", "Marcar urgente / SDI"],
  ["Mark rush, remake, or same-day install handling without mixing this workflow into Manage Items.", "Marque urgente, rehacer o instalación el mismo día sin mezclar este flujo con Administrar artículos."],
  ["Mark SDI / Rush", "Marcar SDI / urgente"],
  ["Menu", "Menú"],
  ["Mobile navigation", "Navegación móvil"],
  ["Move / target bay", "Mover / bahía de destino"],
  ["Move, clear, target, or mark items without using the SDI window.", "Mueva, quite, dirija o marque artículos sin usar la ventana SDI."],
  ["New today", "Nuevo hoy"],
  ["Newest future list", "Lista futura más reciente"],
  ["No bay scans yet", "Aún no hay escaneos de bahía"],
  ["No bay selected", "No hay una bahía seleccionada"],
  ["No scans yet", "Aún no hay escaneos"],
  ["Old Bays", "Bahías antiguas"],
  ["Old orders", "Órdenes antiguas"],
  ["Optional", "Opcional"],
  ["Optional bay", "Bahía opcional"],
  ["Optional, comma-separated", "Opcional, separado por comas"],
  ["Order / Job / Scan Text", "Orden / trabajo / texto escaneado"],
  ["Order Type", "Tipo de orden"],
  ["Order, Job Nr., barcode, or label text", "Orden, núm. de trabajo, código de barras o texto de etiqueta"],
  ["Pagination", "Paginación"],
  ["Picking / SDI", "Selección / SDI"],
  ["Plant Operations", "Operaciones de planta"],
  ["Pre Assigned", "Preasignado"],
  ["Print Investigation List", "Imprimir lista de investigación"],
  ["Production scanning, rack control, and delivery visibility in one place.", "Escaneo de producción, control de racks y visibilidad de entregas en un solo lugar."],
  ["Ready", "Listo"],
  ["Reason / note", "Motivo / nota"],
  ["Recent bay scans", "Escaneos recientes de bahía"],
  ["Redo last bay action", "Rehacer la última acción de bahía"],
  ["Redo last scan", "Rehacer el último escaneo"],
  ["Redo layout change", "Rehacer cambio de diseño"],
  ["Remove from bay", "Quitar de la bahía"],
  ["Review orders that have been sitting in Indian Trail bays for more than 10 days. Snooze rows that are verified, or print the investigation list for a physical walkthrough.", "Revise las órdenes que llevan más de 10 días en bahías de Indian Trail. Pospuonga las filas verificadas o imprima la lista de investigación para una revisión física."],
  ["Route filters", "Filtros de ruta"],
  ["Safe", "Seguro"],
  ["Scan order to remove from bay...", "Escanee una orden para quitarla de la bahía..."],
  ["Scan tracking", "Seguimiento de escaneos"],
  ["Scanner:", "Escáner:"],
  ["SDI / Rush", "SDI / urgente"],
  ["Rush / Remake", "Urgente / rehacer"],
  ["SDI / Rush Order", "Orden SDI / urgente"],
  ["Rush / Remake Order", "Orden urgente / rehecha"],
  ["Search bay, order, item, customer, glass type, size...", "Buscar bahía, orden, artículo, cliente, tipo de vidrio o tamaño..."],
  ["Search first, then click a bay to manage its orders, target it for scanning, or start a move.", "Busque primero y luego haga clic en una bahía para administrar sus órdenes, enviarla al escáner o iniciar un movimiento."],
  ["Search glass types, stages, users...", "Buscar tipos de vidrio, etapas o usuarios..."],
  ["Search order or customer", "Buscar orden o cliente"],
  ["Search order, item, customer, bay...", "Buscar orden, artículo, cliente o bahía..."],
  ["Select a bay on the map to view orders, send the bay to the scanner, hold/block it, or move assigned glass.", "Seleccione una bahía en el mapa para ver órdenes, enviarla al escáner, ponerla en espera/bloquearla o mover el vidrio asignado."],
  ["Select Rush or Remake", "Seleccione urgente o rehacer"],
  ["Send straight to installer truck / skip bay", "Enviar directamente al camión del instalador / omitir bahía"],
  ["Sent after all customer pieces are scanned on staging.", "Se envía después de escanear en preparación todas las piezas del cliente."],
  ["Sent after delivery-list import/update when an email match exists.", "Se envía después de importar/actualizar la lista cuando existe una coincidencia de correo."],
  ["Showing all chart categories", "Mostrando todas las categorías de la gráfica"],
  ["Sign in with your BFS email or assigned username to continue.", "Inicie sesión con su correo BFS o nombre de usuario asignado para continuar."],
  ["Signed in", "Sesión iniciada"],
  ["Snooze all days", "Posponer todos los días"],
  ["Snooze selected/all", "Posponer seleccionados/todos"],
  ["SO / Order Nr.", "SO / Núm. de orden"],
  ["Job Nr. / SO / Order Nr.", "Núm. de trabajo / SO / Núm. de orden"],
  ["Paste the full Job Nr., customer description, SO number, order number, or barcode.", "Pegue el núm. de trabajo completo, la descripción del cliente, el número SO, el número de orden o el código de barras."],
  ["Enter a Job Nr., SO number, order number, or barcode.", "Ingrese un núm. de trabajo, número SO, número de orden o código de barras."],
  ["Bay Map update complete", "Actualización del mapa de bahías completada"],
  ["Bay Map update cleared", "Actualización del mapa de bahías eliminada"],
  ["Rush marked", "Urgente marcado"],
  ["Remake marked", "Rehacer marcado"],
  ["Rush / Remake cleared", "Marca urgente / rehacer eliminada"],
  ["Job Nr. / Order", "Núm. de trabajo / orden"],
  ["Items updated", "Artículos actualizados"],
  ["Print Rush sheet", "Imprimir hoja urgente"],
  ["Print remake sheet", "Imprimir hoja de rehacer"],
  ["Done", "Listo"],
  ["Update complete", "Actualización completada"],
  ["Saved successfully", "Guardado correctamente"],
  ["Print complete", "Impresión completada"],
  ["Return to fullscreen", "Volver a pantalla completa"],
  ["The print window closed. Your browser requires one click to enter fullscreen again.", "La ventana de impresión se cerró. Su navegador requiere un clic para volver a pantalla completa."],
  ["Stay in windowed mode", "Permanecer en modo ventana"],
  ["Allow popups to open the print preview.", "Permita ventanas emergentes para abrir la vista previa de impresión."],
  ["Job Nr., SO number, order number, or barcode was not found on active delivery lists", "No se encontró el núm. de trabajo, número SO, número de orden o código de barras en las listas de entrega activas"],
  ["Select a bay assignment or enter a Job Nr., SO number, or order number", "Seleccione una asignación de bahía o ingrese un núm. de trabajo, número SO o número de orden"],
  ["Stage completion", "Finalización por etapa"],
  ["Stages", "Etapas"],
  ["Status filters", "Filtros de estado"],
  ["Tall / oversize rules", "Reglas para alto / sobredimensionado"],
  ["Temp Delivery Lists folder", "Carpeta temporal de listas de entrega"],
  ["Temp Delivery Lists folder path", "Ruta de la carpeta temporal de listas de entrega"],
  ["Time", "Hora"],
  ["Undo last bay action", "Deshacer la última acción de bahía"],
  ["Undo last scan", "Deshacer el último escaneo"],
  ["Undo layout change", "Deshacer cambio de diseño"],
  ["Unmapped bays", "Bahías sin asignar en el mapa"],
  ["Use auto-suggested bay", "Usar bahía sugerida automáticamente"],
  ["Use Bay For Scanner", "Usar bahía para el escáner"],
  ["Z to A", "Z a A"],
  ["Loading Indian Trail bays...", "Cargando bahías de Indian Trail..."],
  ["Allow popups to generate the statistics PDF report.", "Permita ventanas emergentes para generar el informe PDF de estadísticas."],
  ["Assignment not found.", "No se encontró la asignación."],
  ["Bay auto-assigner settings saved.", "Se guardó la configuración del asignador automático de bahías."],
  ["Bay map layout changes were cancelled.", "Se cancelaron los cambios del diseño del mapa de bahías."],
  ["Bay map layout confirmed.", "Se confirmó el diseño del mapa de bahías."],
  ["Choose a destination rack before confirming the move.", "Elija un rack de destino antes de confirmar el movimiento."],
  ["Choose a manual Indian Trail bay before scanning, or switch bay assignment back to Auto.", "Elija una bahía manual de Indian Trail antes de escanear o cambie la asignación a Automático."],
  ["Choose a rack or truck before overriding outbound scan safety.", "Elija un rack o camión antes de omitir la seguridad del escaneo de salida."],
  ["Choose a staging list and rack, then scan a piece.", "Elija una lista de preparación y un rack, y luego escanee una pieza."],
  ["Complete this rack before printing its packing list.", "Complete este rack antes de imprimir su lista de empaque."],
  ["Delete this line item from its delivery list?", "¿Eliminar esta línea de su lista de entrega?"],
  ["Email body copied.", "Se copió el cuerpo del correo."],
  ["Enter or generate a new password before saving.", "Ingrese o genere una contraseña nueva antes de guardar."],
  ["Manual bay assign needs an order number.", "La asignación manual de bahía necesita un número de orden."],
  ["Manual scan needs an order number and item number.", "El escaneo manual necesita un número de orden y de artículo."],
  ["Move all grouped bays out of the temporary holding area before closing edit mode.", "Mueva todos los grupos de bahías fuera del área temporal antes de cerrar el modo de edición."],
  ["Move all grouped bays out of the temporary holding area before confirming.", "Mueva todos los grupos de bahías fuera del área temporal antes de confirmar."],
  ["Move all grouped bays out of the temporary holding area before leaving the Bay Map.", "Mueva todos los grupos de bahías fuera del área temporal antes de salir del mapa de bahías."],
  ["No bay map match found for that search.", "No se encontró una coincidencia en el mapa para esa búsqueda."],
  ["No delivery lists are available to print.", "No hay listas de entrega disponibles para imprimir."],
  ["Only admins can edit the bay map layout.", "Solo los administradores pueden editar el diseño del mapa de bahías."],
  ["Save Customer Email", "Guardar correo del cliente"],
  ["Select a bay before sending it to the scanner.", "Seleccione una bahía antes de enviarla al escáner."],
  ["Select a bay first.", "Seleccione primero una bahía."],
  ["Select an item before opening SDI.", "Seleccione un artículo antes de abrir SDI."],
  ["Select at least one stage to print or export.", "Seleccione al menos una etapa para imprimir o exportar."],
  ["Select Rush or Remake before marking SDI.", "Seleccione urgente o rehacer antes de marcar SDI."],
  ["Spacer added to the bay map.", "Se agregó un separador al mapa de bahías."],
  ["Temporary password generated. Save it, then give it to the user.", "Se generó una contraseña temporal. Guárdela y entréguela al usuario."],
  ["That bay does not have an assignment to move.", "Esa bahía no tiene una asignación para mover."],
  ["Use the grouped bay header to move bay sets around the edit grid.", "Use el encabezado del grupo para mover conjuntos de bahías en la cuadrícula de edición."],
  ["You have unsaved manual delivery-list edits. Close without saving?", "Tiene cambios manuales sin guardar. ¿Cerrar sin guardar?"],
  ["You have unsaved manual delivery-list edits. Go back without saving?", "Tiene cambios manuales sin guardar. ¿Volver sin guardar?"],
  ["You have unsaved manual delivery-list edits. Leave without saving?", "Tiene cambios manuales sin guardar. ¿Salir sin guardar?"],
  ["You have unsaved manual delivery-list edits. Load another stage without saving?", "Tiene cambios manuales sin guardar. ¿Cargar otra etapa sin guardar?"],
  ["Active delivery lists", "Listas de entrega activas"],
  ["Active Delivery Lists", "Listas de entrega activas"],
  ["Active Racks", "Racks activos"],
  ["Active Users", "Usuarios activos"],
  ["Admin & Users", "Administración y usuarios"],
  ["Admin dashboard, users, roles, active sessions, passwords, and updates.", "Panel de administración, usuarios, roles, sesiones activas, contraseñas y actualizaciones."],
  ["All Bay Scans", "Todos los escaneos de bahía"],
  ["All Bays", "Todas las bahías"],
  ["All Delivery Lists", "Todas las listas de entrega"],
  ["All matching", "Todas las coincidencias"],
  ["All Users", "Todos los usuarios"],
  ["Ambiguous delivery-list match", "Coincidencia ambigua de lista de entrega"],
  ["Another active route rule already uses that customer pattern", "Otra regla de ruta activa ya usa ese patrón de cliente"],
  ["Assigned", "Asignado"],
  ["Available bay", "Bahía disponible"],
  ["Bad scans", "Escaneos incorrectos"],
  ["Bay action", "Acción de bahía"],
  ["Bay actions", "Acciones de bahía"],
  ["Bay Actions", "Acciones de bahía"],
  ["Bay Overrides", "Anulaciones de bahía"],
  ["Bay row not found.", "No se encontró la fila de la bahía."],
  ["Blocked", "Bloqueado"],
  ["Box label", "Etiqueta de caja"],
  ["Category", "Categoría"],
  ["Chart data", "Datos de la gráfica"],
  ["Chart style", "Estilo de gráfica"],
  ["Choose a dashboard section to view details.", "Elija una sección del panel para ver detalles."],
  ["Choose a target bay before manual assigning.", "Elija una bahía de destino antes de asignar manualmente."],
  ["Choose an option", "Elija una opción"],
  ["Clear filters", "Limpiar filtros"],
  ["Clear or move the rack contents before deleting this rack", "Quite o mueva el contenido del rack antes de eliminarlo"],
  ["Customer manifests", "Manifiestos de clientes"],
  ["Data driven", "Basado en datos"],
  ["Delete all stages", "Eliminar todas las etapas"],
  ["Delivery list not found", "No se encontró la lista de entrega"],
  ["Draft", "Borrador"],
  ["Email Drafts", "Borradores de correo"],
  ["Email draft not found", "No se encontró el borrador de correo"],
  ["Enter a valid BFS email address", "Ingrese un correo BFS válido"],
  ["Failed", "Fallido"],
  ["Generate temporary password", "Generar contraseña temporal"],
  ["Glass/product descriptions used in manual delivery-list edits.", "Descripciones de vidrio/producto usadas en la edición manual de listas."],
  ["Importing, previewing, editing, printing, reports, and global search.", "Importación, vista previa, edición, impresión, informes y búsqueda global."],
  ["Inactive", "Inactivo"],
  ["Indian Trail receiving, bay map, bay actions, SDI, reports, and layout.", "Recepción de Indian Trail, mapa de bahías, acciones, SDI, informes y diseño."],
  ["Invalid or expired reset code", "Código de restablecimiento inválido o vencido"],
  ["Line item not found", "No se encontró la línea"],
  ["Logged in", "Sesión activa"],
  ["Logged out", "Sesión cerrada"],
  ["Main scanner access, scan visibility, undo, and reset controls.", "Acceso principal al escáner, visibilidad de escaneos, deshacer y controles de reinicio."],
  ["Manual adjustments and exception review/resolution.", "Ajustes manuales y revisión/resolución de excepciones."],
  ["New", "Nuevo"],
  ["New Stage", "Nueva etapa"],
  ["No Updates", "Sin cambios"],
  ["No data", "Sin datos"],
  ["No matching options", "No hay opciones coincidentes"],
  ["No updates", "Sin cambios"],
  ["Operator", "Operador"],
  ["Indian Trail Operator", "Operador de Indian Trail"],
  ["Indian Trail Lead", "Líder de Indian Trail"],
  ["Indian Trail Manager", "Gerente de Indian Trail"],
  ["Password must be at least 8 characters", "La contraseña debe tener al menos 8 caracteres"],
  ["Password reset. Sign in with the new password.", "Contraseña restablecida. Inicie sesión con la nueva contraseña."],
  ["Please sign in to continue.", "Inicie sesión para continuar."],
  ["Queued", "En cola"],
  ["Rack and scan management", "Administración de racks y escaneos"],
  ["Rack overview, rack scanning, and rack management.", "Resumen, escaneo y administración de racks."],
  ["Ready notices", "Avisos de disponibilidad"],
  ["Recorded scan activity by user for the selected dashboard range.", "Actividad de escaneo por usuario para el rango seleccionado."],
  ["Remake lines", "Líneas rehechas"],
  ["Remake pieces", "Piezas rehechas"],
  ["Remake pieces and distinct remake lines for the active dashboard filter.", "Piezas rehechas y líneas distintas para el filtro activo del panel."],
  ["Remakes in selected range", "Rehechos en el rango seleccionado"],
  ["Request failed:", "La solicitud falló:"],
  ["Reset all stages", "Restablecer todas las etapas"],
  ["Reset scans", "Restablecer escaneos"],
  ["Reset scans?", "¿Restablecer escaneos?"],
  ["Role not found", "No se encontró el rol"],
  ["Routing values such as CPU, DTC, GNV, or custom customer routes.", "Valores de ruta como CPU, DTC, GNV o rutas personalizadas de clientes."],
  ["Save password", "Guardar contraseña"],
  ["Save role", "Guardar rol"],
  ["Save route", "Guardar ruta"],
  ["Save Rule", "Guardar regla"],
  ["Scanning", "Escaneando"],
  ["Scanning and list access", "Escaneo y acceso a listas"],
  ["Search failed:", "La búsqueda falló:"],
  ["Send status", "Estado de envío"],
  ["Sent", "Enviado"],
  ["Show password", "Mostrar contraseña"],
  ["SMTP live", "SMTP activo"],
  ["Station setup and customer route rule management.", "Configuración de estaciones y reglas de rutas de clientes."],
  ["Stations", "Estaciones"],
  ["Stations & Rules", "Estaciones y reglas"],
  ["Status values such as New, Updated, Rush, Remake, and SDI.", "Valores de estado como Nuevo, Actualizado, Urgente, Rehacer y SDI."],
  ["System notice", "Aviso del sistema"],
  ["Temporary password", "Contraseña temporal"],
  ["The default admin user cannot be deactivated", "El usuario administrador predeterminado no se puede desactivar"],
  ["This is a test email from the Delivery List Scanner customer email system.", "Este es un correo de prueba del sistema de correos para clientes del Escáner de listas de entrega."],
  ["Total Bays", "Bahías totales"],
  ["Total Qty", "Cantidad total"],
  ["Truck Pieces", "Piezas en camión"],
  ["Unable to load delivery list", "No se pudo cargar la lista de entrega"],
  ["Unassigned", "Sin asignar"],
  ["Unavailable", "No disponible"],
  ["Unknown", "Desconocido"],
  ["Unknown user", "Usuario desconocido"],
  ["Updated", "Actualizado"],
  ["Updated at:", "Actualizado:"],
  ["User actions", "Acciones de usuario"],
  ["User and system management", "Administración de usuarios y sistema"],
  ["Users", "Usuarios"],
  ["Yes", "Sí"],
  ["No", "No"],
  ["Remake", "Rehacer"],
  ["Add Rule", "Agregar regla"],
  ["Add spacer to which bay group?", "¿A qué grupo de bahías desea agregar un separador?"],
  ["Add spacer", "Agregar separador"],
  ["Bay auto-assign thresholds must be greater than zero", "Los límites de asignación automática deben ser mayores que cero"],
  ["Bay group is required", "El grupo de bahía es obligatorio"],
  ["Bay group not found", "No se encontró el grupo de bahía"],
  ["Bay not found", "No se encontró la bahía"],
  ["Bay status must be Available, ManualAssign, or ScanBlocked", "El estado debe ser Disponible, Asignación manual o Escaneo bloqueado"],
  ["Clear or move active assignments before deleting this bay", "Quite o mueva las asignaciones activas antes de eliminar esta bahía"],
  ["Clear or move active assignments before deleting this group", "Quite o mueva las asignaciones activas antes de eliminar este grupo"],
  ["Customer email contact not found", "No se encontró el contacto de correo del cliente"],
  ["Customer match text is required", "El texto de coincidencia del cliente es obligatorio"],
  ["Customer pattern is required", "El patrón del cliente es obligatorio"],
  ["Customer route rule not found", "No se encontró la regla de ruta del cliente"],
  ["Default stations cannot be removed", "Las estaciones predeterminadas no se pueden eliminar"],
  ["DTC customer route rules require a delivery address", "Las reglas DTC requieren una dirección de entrega"],
  ["Enter a valid recipient email for the test message", "Ingrese un correo de destinatario válido para el mensaje de prueba"],
  ["Identity, reset code, and new password are required", "Se requieren la identidad, el código y la contraseña nueva"],
  ["If that account exists, a reset code was created.", "Si la cuenta existe, se creó un código de restablecimiento."],
  ["Invalid exception status", "Estado de excepción inválido"],
  ["Lookup type must be product, route, or process", "El tipo de catálogo debe ser producto, ruta o proceso"],
  ["Lookup value is required", "El valor del catálogo es obligatorio"],
  ["Manual assignment text is required", "El texto de asignación manual es obligatorio"],
  ["Manual input pattern is required", "El patrón de entrada manual es obligatorio"],
  ["Manual input rule type must be exact, contains, or regex", "La regla manual debe ser exacta, contiene o expresión regular"],
  ["Move amount is required", "La cantidad a mover es obligatoria"],
  ["No active bay assignment matched that scan", "Ninguna asignación activa de bahía coincidió con ese escaneo"],
  ["No active Indian Trail inbound list", "No hay una lista de entrada activa de Indian Trail"],
  ["No delivery lists found for that date", "No se encontraron listas para esa fecha"],
  ["No outbound delivery list was found for this rack", "No se encontró una lista de salida para este rack"],
  ["Not on active Indian Trail inbound list. Send to supervisor.", "No está en la lista activa de entrada de Indian Trail. Envíe al supervisor."],
  ["Only line items already scanned at Staging can be assigned to a rack", "Solo las líneas ya escaneadas en Preparación se pueden asignar a un rack"],
  ["Only racks marked on the way can be marked Not On The Way", "Solo los racks marcados En camino se pueden marcar No está en camino"],
  ["Order number was not found on active delivery lists", "No se encontró el número de orden en las listas activas"],
  ["Oversize minimum must be greater than or equal to tall minimum", "El mínimo sobredimensionado debe ser mayor o igual al mínimo alto"],
  ["Quantity already received. Send to supervisor.", "La cantidad ya fue recibida. Envíe al supervisor."],
  ["Rack code is required", "El código del rack es obligatorio"],
  ["Rack destination could not be determined safely. Clear or split this rack before completing it.", "No se pudo determinar el destino del rack de forma segura. Vacíe o divida el rack antes de completarlo."],
  ["Rack has no active pieces to scan outbound", "El rack no tiene piezas activas para escanear en salida"],
  ["Rack item not found", "No se encontró el artículo del rack"],
  ["Rack line item not found", "No se encontró la línea del rack"],
  ["Rack must have active pieces before it can be completed", "El rack debe tener piezas activas antes de completarlo"],
  ["Rack scans must be made from a staging delivery list", "Los escaneos de rack deben hacerse desde una lista de Preparación"],
  ["Rack set prefix is required", "El prefijo del conjunto de racks es obligatorio"],
  ["Reset code created. Use it within 30 minutes.", "Código creado. Úselo dentro de 30 minutos."],
  ["Route is required", "La ruta es obligatoria"],
  ["Scan barcode is required", "El código de barras es obligatorio"],
  ["Scanned quantity must be between 0 and total quantity", "La cantidad escaneada debe estar entre 0 y la cantidad total"],
  ["Select a bay assignment or enter an order number", "Seleccione una asignación de bahía o ingrese un número de orden"],
  ["Station name is required", "El nombre de la estación es obligatorio"],
  ["Station not found", "No se encontró la estación"],
  ["That BFS email is already assigned to another user", "Ese correo BFS ya está asignado a otro usuario"],
  ["Truck cannot be deleted", "El camión no se puede eliminar"],
  ["Truck rack code cannot be changed", "El código del rack de camión no se puede cambiar"],
  ["User already exists", "El usuario ya existe"],
  ["User not found", "No se encontró el usuario"],
  ["Username and password are required", "Se requieren el usuario y la contraseña"],
  ["You cannot delete the user you are currently signed in as", "No puede eliminar el usuario con el que inició sesión"],
  ["accepted bay barcode rule", "regla aceptada de código de barras de bahía"],
  ["active | complete", "activos | completos"],
  ["bays", "bahías"],
  ["lists", "listas"],
  ["new, updated, unchanged, failed.", "nuevos, actualizados, sin cambios y fallidos."],
  ["new, updated, unchanged.", "nuevos, actualizados y sin cambios."],
  ["occupied | preassigned", "ocupado | preasignado"],
  ["on time / late", "a tiempo / tarde"],
  ["open", "abierto"],
  ["pcs", "pzas"],
  ["piece", "pieza"],
  ["pieces", "piezas"],
  ["pieces on the way | Truck | Racks", "piezas en camino | Camión | Racks"],
  ["Process", "Proceso"],
  ["remake row", "fila rehecha"],
  ["removed.", "eliminado."],
  ["rows", "filas"],
  ["SDI | manual assign | blocked", "SDI | asignación manual | bloqueado"],
  ["sent / received", "enviado / recibido"],
  ["Tall starts at inches", "Alto comienza en pulgadas"],
  ["| grouped by rack, then glass type", "| agrupado por rack y luego por tipo de vidrio"],
]);
SPANISH_UI_ADDITIONS.forEach((spanish, english) => SPANISH_UI_TEXT.set(english, spanish));

const SPANISH_UI_EXTENDED = new Map([
  ["% of physical bays ready", "% de bahías físicas listas"],
  ["Accepted bay barcode rule", "Regla aceptada de código de barras de bahía"],
  ["Accepted bay scanner barcode formats", "Formatos aceptados por el escáner de bahías"],
  ["Accepted without asking for confirmation.", "Aceptado sin pedir confirmación."],
  ["Actions", "Acciones"],
  ["active rule", "regla activa"],
  ["Add Barcode Rule", "Agregar regla de código de barras"],
  ["Add bay count", "Cantidad de bahías a agregar"],
  ["Add Bays To Group", "Agregar bahías al grupo"],
  ["Add CC", "Agregar CC"],
  ["Add clean product names, route codes, and process states so the manual editor stays consistent.", "Agregue nombres limpios de productos, códigos de ruta y estados de proceso para mantener consistente el editor manual."],
  ["Add Customer Email", "Agregar correo de cliente"],
  ["Add Customer Route", "Agregar ruta de cliente"],
  ["Add customer-to-route rules here. Custom route codes create custom route stages during import.", "Agregue aquí reglas de cliente a ruta. Los códigos personalizados crean etapas de ruta durante la importación."],
  ["Add Lookup", "Agregar valor de catálogo"],
  ["Add lookup value", "Agregar valor de catálogo"],
  ["Add Memory", "Agregar memoria"],
  ["Add user", "Agregar usuario"],
  ["Adjust the search or filters and try again.", "Ajuste la búsqueda o los filtros e inténtelo de nuevo."],
  ["Admin and bay activity", "Actividad de administración y bahías"],
  ["All active bay assignments will appear on the left.", "Todas las asignaciones activas de bahía aparecerán a la izquierda."],
  ["All Glass", "Todo el vidrio"],
  ["All Glass Types", "Todos los tipos de vidrio"],
  ["All rack sets at a glance", "Todos los conjuntos de racks de un vistazo"],
  ["All Stages", "Todas las etapas"],
  ["Assign behavior", "Comportamiento de asignación"],
  ["Assigned / occupied", "Asignado / ocupado"],
  ["Assigned age", "Antigüedad de asignación"],
  ["Auto assign", "Asignación automática"],
  ["Auto assign / free for preassign", "Asignación automática / disponible para preasignar"],
  ["Back to delivery lists", "Volver a listas de entrega"],
  ["Bad Scans", "Escaneos incorrectos"],
  ["Barcode", "Código de barras"],
  ["Bay / User Actions", "Acciones de bahía / usuario"],
  ["Bay availability", "Disponibilidad de bahía"],
  ["Bay count", "Cantidad de bahías"],
  ["Bay Map only", "Solo mapa de bahías"],
  ["Bay Map scanner and manual assignment rules", "Reglas del escáner del mapa y asignación manual"],
  ["Bay prefix", "Prefijo de bahía"],
  ["Bay selected.", "Bahía seleccionada."],
  ["Bays affected", "Bahías afectadas"],
  ["BFS Email", "Correo BFS"],
  ["Block Scans", "Bloquear escaneos"],
  ["Blocked for all scanning", "Bloqueada para todos los escaneos"],
  ["Body", "Cuerpo"],
  ["Cancel scan", "Cancelar escaneo"],
  ["Capacity", "Capacidad"],
  ["CC on all customer emails", "CC en todos los correos de clientes"],
  ["CC optional", "CC opcional"],
  ["Change the coded rack name, display name, or rack set/type from the same edit area used for rack sets.", "Cambie el código del rack, el nombre visible o el conjunto/tipo desde la misma área usada para los conjuntos de racks."],
  ["Change the route dropdown, then use the save icon on that row.", "Cambie la ruta y luego use el icono de guardar en esa fila."],
  ["Checked categories will not be auto-preassigned. They will require manual placement.", "Las categorías marcadas no se preasignarán automáticamente. Requerirán colocación manual."],
  ["Checking outbound scans against received scans.", "Comparando escaneos de salida con escaneos recibidos."],
  ["Choose an open rack or truck...", "Elija un rack o camión abierto..."],
  ["Choose from dropdowns or type a custom value.", "Elija en los menús o escriba un valor personalizado."],
  ["Clear right now", "Liberar ahora"],
  ["Clears, moves, edits", "Liberaciones, movimientos y ediciones"],
  ["Column", "Columna"],
  ["Complete rack", "Completar rack"],
  ["Confirm", "Confirmar"],
  ["Confirm Move", "Confirmar movimiento"],
  ["Contains text", "Contiene texto"],
  ["Copy Body", "Copiar cuerpo"],
  ["Could not load glass type quantities.", "No se pudieron cargar las cantidades por tipo de vidrio."],
  ["Create a grouped set of bays to begin.", "Cree un conjunto agrupado de bahías para comenzar."],
  ["Create a grouped set of bays, then move it into the exact map position in Edit Map.", "Cree un conjunto agrupado y luego muévalo a la posición exacta en Editar mapa."],
  ["Create Group", "Crear grupo"],
  ["Create grouped set", "Crear conjunto agrupado"],
  ["Create Rack", "Crear rack"],
  ["Create Rack Set", "Crear conjunto de racks"],
  ["Created", "Creado"],
  ["Current customer rules", "Reglas actuales de clientes"],
  ["Current SDI Orders", "Órdenes SDI actuales"],
  ["Current Rush / Remake Orders", "Órdenes urgentes / rehechas actuales"],
  ["No current Rush or Remake orders.", "No hay órdenes urgentes ni rehechas actuales."],
  ["Mark Rush / Remake", "Marcar urgente / rehacer"],
  ["Rush / Remake cleared", "Marca urgente / rehacer eliminada"],
  ["Customer / match text", "Cliente / texto de coincidencia"],
  ["Customer email rules", "Reglas de correo de clientes"],
  ["Customer manifest and ready-notice emails", "Manifiestos de clientes y correos de disponibilidad"],
  ["Customer match text", "Texto de coincidencia del cliente"],
  ["customer route rule", "regla de ruta del cliente"],
  ["Date & Time Scanned", "Fecha y hora del escaneo"],
  ["days", "días"],
  ["Deactivate", "Desactivar"],
  ["Deactivate User", "Desactivar usuario"],
  ["Deactivate user?", "¿Desactivar usuario?"],
  ["Delete Group", "Eliminar grupo"],
  ["Deleted date", "Fecha eliminada"],
  ["Deleted stage", "Etapa eliminada"],
  ["delivery date / stage", "fecha de entrega / etapa"],
  ["delivery list file checked. Existing New/Updated markers were refreshed where applicable.", "archivo de lista revisado. Se actualizaron los indicadores Nuevo/Actualizado donde correspondía."],
  ["Delivery list stage", "Etapa de lista de entrega"],
  ["Delivery Progress", "Progreso de entrega"],
  ["Delivery Scanner Statistics Report", "Informe de estadísticas del escáner de entregas"],
  ["Destination", "Destino"],
  ["Destination address", "Dirección de destino"],
  ["Display label", "Etiqueta visible"],
  ["Display name", "Nombre visible"],
  ["Display Name", "Nombre visible"],
  ["Drop group here", "Suelte el grupo aquí"],
  ["Duplicate scans", "Escaneos duplicados"],
  ["Duplicate Scans", "Escaneos duplicados"],
  ["Edit dropdown choices used by manual list editing", "Editar opciones usadas en la edición manual de listas"],
  ["Edit individual racks, add rack sets, delete empty racks, or delete empty rack sets.", "Edite racks individuales, agregue conjuntos y elimine racks o conjuntos vacíos."],
  ["Edit Map Layout", "Editar diseño del mapa"],
  ["Edit names, capacity, behavior, or remove empty bays.", "Edite nombres, capacidad y comportamiento, o elimine bahías vacías."],
  ["Edit set", "Editar conjunto"],
  ["Email", "Correo"],
  ["email", "correo"],
  ["Email address", "Dirección de correo"],
  ["email rule", "regla de correo"],
  ["Enter an item number to pick one exact row.", "Ingrese un número de artículo para seleccionar una fila exacta."],
  ["Exact text", "Texto exacto"],
  ["Existing password cannot be viewed.", "La contraseña existente no se puede ver."],
  ["Extra barcode formats accepted only on the Bay Map scanner.", "Formatos adicionales aceptados solo en el escáner del mapa de bahías."],
  ["Filled", "Ocupado"],
  ["Filtered range", "Rango filtrado"],
  ["From", "Desde"],
  ["Generate or enter a new one, then save it.", "Genere o ingrese una nueva y luego guárdela."],
  ["Generate PDF", "Generar PDF"],
  ["Glass groups", "Grupos de vidrio"],
  ["Glass mix by quantity", "Mezcla de vidrio por cantidad"],
  ["glass type", "tipo de vidrio"],
  ["Glass Types by Quantity", "Tipos de vidrio por cantidad"],
  ["Glass types by quantity", "Tipos de vidrio por cantidad"],
  ["global CC", "CC global"],
  ["Group", "Grupo"],
  ["group", "grupo"],
  ["Group name", "Nombre del grupo"],
  ["Grouped bay set", "Conjunto agrupado de bahías"],
  ["grouped set", "conjunto agrupado"],
  ["Host", "Servidor"],
  ["If SMTP is not configured, this creates a draft you can open below.", "Si SMTP no está configurado, esto crea un borrador que puede abrir abajo."],
  ["Import complete.", "Importación completada."],
  ["Import completed with issues.", "La importación terminó con problemas."],
  ["Import delivery lists to populate statistics.", "Importe listas de entrega para generar estadísticas."],
  ["Import delivery lists to populate the glass-type pie chart.", "Importe listas para generar la gráfica de tipos de vidrio."],
  ["In-Transit Manifest", "Manifiesto en tránsito"],
  ["Incomplete Delivery Lists", "Listas de entrega incompletas"],
  ["Indian Trail bay assignments older than 10 days will appear here.", "Las asignaciones de Indian Trail con más de 10 días aparecerán aquí."],
  ["Indian Trail bay auto-assigner", "Asignador automático de bahías de Indian Trail"],
  ["Indian Trail Bay Scan History", "Historial de escaneos de bahía de Indian Trail"],
  ["Indian Trail Receiving", "Recepción de Indian Trail"],
  ["Individual Bays", "Bahías individuales"],
  ["Internal email drafts", "Borradores internos de correo"],
  ["items", "artículos"],
  ["job group", "grupo de trabajo"],
  ["Job Nr. groups", "Grupos por núm. de trabajo"],
  ["Jobs in this bay", "Trabajos en esta bahía"],
  ["Known phrases and odd labels that will not ask for confirmation.", "Frases conocidas y etiquetas especiales que no pedirán confirmación."],
  ["Label", "Etiqueta"],
  ["Largest glass dimension controls Standard / Tall / Oversize.", "La dimensión mayor controla Estándar / Alto / Sobredimensionado."],
  ["Last seen", "Visto por última vez"],
  ["latest actions", "acciones recientes"],
  ["Line items", "Líneas"],
  ["Load All", "Cargar todo"],
  ["Load more older delivery lists", "Cargar más listas antiguas"],
  ["Loading", "Cargando"],
  ["Loading bays...", "Cargando bahías..."],
  ["Loading editable rows...", "Cargando filas editables..."],
  ["Loading glass types...", "Cargando tipos de vidrio..."],
  ["Loading in-transit manifest...", "Cargando manifiesto en tránsito..."],
  ["Lookup type", "Tipo de catálogo"],
  ["manual", "manual"],
  ["Manual assign only", "Solo asignación manual"],
  ["Manual assignment categories", "Categorías de asignación manual"],
  ["Manual edits", "Ediciones manuales"],
  ["Manual only", "Solo manual"],
  ["Manual Scans", "Escaneos manuales"],
  ["Map column", "Columna del mapa"],
  ["Map row", "Fila del mapa"],
  ["Match customers to the route they should import into.", "Relacione clientes con la ruta en la que deben importarse."],
  ["Match each classification to one of your bay groups/types.", "Relacione cada clasificación con un grupo/tipo de bahía."],
  ["Match terms", "Términos de coincidencia"],
  ["Match type", "Tipo de coincidencia"],
  ["Matches:", "Coincidencias:"],
  ["Message", "Mensaje"],
  ["Monthly Remakes", "Rehechos mensuales"],
  ["Move Piece", "Mover pieza"],
  ["Move to", "Mover a"],
  ["Name", "Nombre"],
  ["Name root", "Raíz del nombre"],
  ["Need walkthrough", "Requiere revisión física"],
  ["Needs attention", "Requiere atención"],
  ["Needs review", "Requiere revisión"],
  ["New Bay Group", "Nuevo grupo de bahías"],
  ["New bay prefix", "Nuevo prefijo de bahía"],
  ["New custom routes become their own stage during import when a customer matches that route.", "Las rutas personalizadas se convierten en su propia etapa cuando un cliente coincide."],
  ["New customer / job match text", "Nuevo texto de coincidencia de cliente / trabajo"],
  ["New rack set / type", "Nuevo conjunto / tipo de rack"],
  ["New route code", "Nuevo código de ruta"],
  ["No active sessions", "No hay sesiones activas"],
  ["No aged rows", "No hay filas antiguas"],
  ["No assigned station", "Sin estación asignada"],
  ["No bay groups found.", "No se encontraron grupos de bahías."],
  ["No bay items found.", "No se encontraron artículos en la bahía."],
  ["No bay scan history is available yet.", "Aún no hay historial de escaneos de bahía."],
  ["No customer route rules", "No hay reglas de rutas de clientes"],
  ["No data is available for this chart in the selected range.", "No hay datos para esta gráfica en el rango seleccionado."],
  ["No delivery lists match.", "Ninguna lista de entrega coincide."],
  ["No editable rows found.", "No se encontraron filas editables."],
  ["No empty compatible bay found", "No se encontró una bahía compatible vacía"],
  ["No glass quantity data yet.", "Aún no hay datos de cantidades de vidrio."],
  ["No glass type quantity data available.", "No hay datos de cantidad por tipo de vidrio."],
  ["No glass types found for the selected stages.", "No se encontraron tipos de vidrio para las etapas seleccionadas."],
  ["No import history yet. Imports from the temp folder or single files will appear here.", "Aún no hay historial de importación. Las importaciones aparecerán aquí."],
  ["No incomplete-list report data available.", "No hay datos de listas incompletas."],
  ["No old bay orders right now.", "No hay órdenes antiguas de bahía en este momento."],
  ["No operator scan data available.", "No hay datos de escaneo por operador."],
  ["No order, item, customer, rack, bay, or route matched that search.", "Ninguna orden, artículo, cliente, rack, bahía o ruta coincidió con la búsqueda."],
  ["No pieces are currently in transit.", "No hay piezas actualmente en tránsito."],
  ["No pieces assigned.", "No hay piezas asignadas."],
  ["No racks available. Create a rack to get started.", "No hay racks disponibles. Cree uno para comenzar."],
  ["No results", "Sin resultados"],
  ["No rows match the current filters.", "Ninguna fila coincide con los filtros actuales."],
  ["No scan data was changed.", "No se modificaron datos de escaneo."],
  ["No stage data", "Sin datos de etapas"],
  ["No stage data available.", "No hay datos de etapas disponibles."],
  ["No stations loaded.", "No hay estaciones cargadas."],
  ["No updates found.", "No se encontraron cambios."],
  ["No users loaded.", "No hay usuarios cargados."],
  ["Nothing needs review", "Nada requiere revisión"],
  ["Old bay rows", "Filas antiguas de bahía"],
  ["Oldest row", "Fila más antigua"],
  ["On-Time Delivery", "Entrega a tiempo"],
  ["Open a role, review permissions by page/action group, then save that role.", "Abra un rol, revise los permisos por página/acción y guarde el rol."],
  ["open draft / sent recently", "borrador abierto / enviado recientemente"],
  ["Open drafts here before SMTP is configured or after a send error.", "Abra borradores aquí antes de configurar SMTP o después de un error."],
  ["Open in Email App", "Abrir en la aplicación de correo"],
  ["Open Manage Items", "Abrir Administrar artículos"],
  ["Outbound safety check", "Verificación de seguridad de salida"],
  ["Override and scan outbound", "Anular y escanear salida"],
  ["Oversize starts at inches", "Sobredimensionado comienza en pulgadas"],
  ["Permissions / Notes", "Permisos / notas"],
  ["Physical locations", "Ubicaciones físicas"],
  ["Pieces", "Piezas"],
  ["Pieces (High-Low)", "Piezas (mayor a menor)"],
  ["Pieces in", "Piezas en"],
  ["Pieces on the way", "Piezas en camino"],
  ["Please wait while the current in-transit jobs are pulled together.", "Espere mientras se cargan los trabajos en tránsito."],
  ["Port", "Puerto"],
  ["Prevented by system", "Impedido por el sistema"],
  ["Primary Job", "Trabajo principal"],
  ["Print / Save PDF", "Imprimir / guardar PDF"],
  ["Product", "Producto"],
  ["Progress", "Progreso"],
  ["Protected", "Protegido"],
  ["Qty Scanned", "Cant. escaneada"],
  ["Quick view of customers that will be split to special/custom stages during import.", "Vista rápida de clientes que se dividirán en etapas especiales durante la importación."],
  ["Rack Actions", "Acciones del rack"],
  ["Rack code", "Código del rack"],
  ["Rack count", "Cantidad de racks"],
  ["Rack ID (A-Z)", "ID de rack (A-Z)"],
  ["Rack ID (Z-A)", "ID de rack (Z-A)"],
  ["Rack Manager", "Administrador de racks"],
  ["Rack name", "Nombre del rack"],
  ["Rack set / type", "Conjunto / tipo de rack"],
  ["Rack Sets", "Conjuntos de racks"],
  ["Rack type", "Tipo de rack"],
  ["Racks / truck groups", "Racks / grupos de camiones"],
  ["Received", "Recibido"],
  ["Recent bay actions", "Acciones recientes de bahía"],
  ["recent scan", "escaneo reciente"],
  ["Regex pattern", "Patrón de expresión regular"],
  ["Remaining Qty", "Cantidad restante"],
  ["remembered manual input", "entrada manual recordada"],
  ["Remembered manual inputs", "Entradas manuales recordadas"],
  ["Rename the rack set/type and optionally rebuild each rack display name from one shared name root.", "Renombre el conjunto/tipo y opcionalmente reconstruya los nombres visibles desde una raíz compartida."],
  ["Rename this grouped set, set assign behavior, create more bays inside it, or delete the group after clearing active assignments.", "Renombre este conjunto, configure su asignación, cree más bahías o elimínelo después de liberar asignaciones."],
  ["Reset cancelled", "Restablecimiento cancelado"],
  ["Role", "Rol"],
  ["Role Permissions", "Permisos del rol"],
  ["Role permissions are loading. Close and reopen this panel if they do not appear.", "Los permisos se están cargando. Cierre y vuelva a abrir el panel si no aparecen."],
  ["Save Auto Assigner", "Guardar asignador automático"],
  ["Save Group", "Guardar grupo"],
  ["Save Rack", "Guardar rack"],
  ["Save Set", "Guardar conjunto"],
  ["Scanned", "Escaneado"],
  ["Scanned Pieces", "Piezas escaneadas"],
  ["Scans", "Escaneos"],
  ["Scans by Operator", "Escaneos por operador"],
  ["Scans reset", "Escaneos restablecidos"],
  ["Search within stage", "Buscar dentro de la etapa"],
  ["Select a bay to manage it.", "Seleccione una bahía para administrarla."],
  ["Select a delivery list to load editable rows.", "Seleccione una lista para cargar filas editables."],
  ["Select an item", "Seleccione un artículo"],
  ["Select destination...", "Seleccione destino..."],
  ["Select the destination before printing the packing list. Indian Trail is the default.", "Seleccione el destino antes de imprimir. Indian Trail es el predeterminado."],
  ["Selected Job Nr.", "Núm. de trabajo seleccionado"],
  ["Selected Rack", "Rack seleccionado"],
  ["Send Test / Save Draft", "Enviar prueba / guardar borrador"],
  ["Send test email", "Enviar correo de prueba"],
  ["Send test to", "Enviar prueba a"],
  ["sent", "enviado"],
  ["Server-side only. Passwords never belong in app.js or the browser.", "Solo del servidor. Las contraseñas nunca deben estar en app.js ni en el navegador."],
  ["Set name", "Nombre del conjunto"],
  ["Set suffix", "Sufijo del conjunto"],
  ["Size", "Tamaño"],
  ["Size thresholds", "Límites de tamaño"],
  ["SMTP setup readiness", "Estado de configuración SMTP"],
  ["Starting rack number", "Número inicial del rack"],
  ["Subject", "Asunto"],
  ["Temporary Holding Area", "Área temporal de espera"],
  ["Text / pattern", "Texto / patrón"],
  ["The next two actions will appear here.", "Las dos acciones siguientes aparecerán aquí."],
  ["These addresses receive every customer manifest and ready notice.", "Estas direcciones reciben todos los manifiestos y avisos de disponibilidad."],
  ["These categories will not be auto-preassigned.", "Estas categorías no se preasignarán automáticamente."],
  ["These rules only apply to Indian Trail Bay Map scanning/manual assign. They do not change the main delivery-list scanner.", "Estas reglas solo se aplican al mapa de Indian Trail y no cambian el escáner principal."],
  ["To", "Para"],
  ["Top type", "Tipo principal"],
  ["Total", "Total"],
  ["total pieces in this range", "piezas totales en este rango"],
  ["Transportation method for this piece", "Método de transporte para esta pieza"],
  ["Typed order/item scans", "Escaneos escritos de orden/artículo"],
  ["Unable to load manifest", "No se pudo cargar el manifiesto"],
  ["Uncomplete Rack", "Reabrir rack"],
  ["Unrecognized manual assignment", "Asignación manual no reconocida"],
  ["Use For Scanner", "Usar para escáner"],
  ["Use regex for extra labels/barcodes that can be scanned into a target bay.", "Use expresiones regulares para etiquetas/códigos adicionales que se puedan escanear en una bahía."],
  ["Use the Bay Map to free a bay or pick manually.", "Use el mapa para liberar una bahía o seleccionar manualmente."],
  ["Use Value for the actual saved code. Use Display label for the cleaner name people see.", "Use Valor para el código guardado y Etiqueta visible para el nombre mostrado."],
  ["User", "Usuario"],
  ["Username", "Nombre de usuario"],
  ["Users appear here after login.", "Los usuarios aparecen aquí después de iniciar sesión."],
  ["Value / code", "Valor / código"],
  ["When Outbound scans Indian Trail pieces and they have not been received yet, they will appear here grouped by rack and glass type.", "Cuando Salida escanee piezas de Indian Trail que aún no se recibieron, aparecerán aquí agrupadas por rack y tipo de vidrio."],
  ["Where is going?", "¿A dónde va?"],
  ["Yes, assign once", "Sí, asignar una vez"],
  ["Yes, remember this", "Sí, recordar esto"],
]);
SPANISH_UI_EXTENDED.forEach((spanish, english) => SPANISH_UI_TEXT.set(english, spanish));

const SPANISH_PLACEHOLDERS = new Map([
  ["Global search...", "Búsqueda global..."],
  ["Search date, stage, route...", "Buscar fecha, etapa o ruta..."],
  ["Search orders, jobs, customers...", "Buscar órdenes, trabajos o clientes..."],
  ["Scan or enter barcode...", "Escanee o ingrese el código..."],
  ["Enter password", "Ingrese la contraseña"],
  ["6-digit code", "Código de 6 dígitos"],
  ["At least 8 characters", "Al menos 8 caracteres"],
]);
[
  ["Click bay or type code", "Haga clic en una bahía o escriba el código"],
  ["Optional", "Opcional"],
  ["Optional bay", "Bahía opcional"],
  ["Optional, comma-separated", "Opcional, separado por comas"],
  ["Order, Job Nr., barcode, or label text", "Orden, núm. de trabajo, código de barras o texto de etiqueta"],
  ["Reason / note", "Motivo / nota"],
  ["Search bay, order, item, customer, glass type, size...", "Buscar bahía, orden, artículo, cliente, tipo de vidrio o tamaño..."],
  ["Search glass types, stages, users...", "Buscar tipos de vidrio, etapas o usuarios..."],
  ["Search order or customer", "Buscar orden o cliente"],
  ["Search order, item, customer, bay...", "Buscar orden, artículo, cliente o bahía..."],
  ["Search date, Job Nr., order number, stage...", "Buscar fecha, núm. de trabajo, orden o etapa..."],
  ["Scan order to add to selected bay...", "Escanee una orden para agregarla a la bahía seleccionada..."],
  ["Scan order to remove from bay...", "Escanee una orden para quitarla de la bahía..."],
  ["Temp Delivery Lists folder path", "Ruta de la carpeta temporal de listas de entrega"],
  ["Showers, Mirror, Coral...", "Regaderas, espejo, coral..."],
  ["R1S or T2", "R1S o T2"],
].forEach(([english, spanish]) => SPANISH_PLACEHOLDERS.set(english, spanish));

const languageUi = {
  observer: null,
};

const SPANISH_DYNAMIC_PATTERNS = [
  [/^(Rush|Remake) marked for Job Nr\. (.+)\.$/i, (_, type, job) => `${type.toLowerCase() === "rush" ? "Urgente" : "Rehacer"} marcado para el núm. de trabajo ${job}.`],
  [/^(Rush|Remake) marked for order (.+)\.$/i, (_, type, order) => `${type.toLowerCase() === "rush" ? "Urgente" : "Rehacer"} marcado para la orden ${order}.`],
  [/^(\d+) piece on the way$/i, (_, count) => `${count} pieza en camino`],
  [/^(\d+) pieces on the way$/i, (_, count) => `${count} piezas en camino`],
  [/^(\d+) stage$/i, (_, count) => `${count} etapa`],
  [/^(\d+) stages$/i, (_, count) => `${count} etapas`],
  [/^(\d+) list$/i, (_, count) => `${count} lista`],
  [/^(\d+) lists$/i, (_, count) => `${count} listas`],
  [/^(\d+) total items?$/i, (_, count) => `${count} artículos totales`],
  [/^(\d+) item$/i, (_, count) => `${count} artículo`],
  [/^(\d+) items$/i, (_, count) => `${count} artículos`],
  [/^(\d+) piece$/i, (_, count) => `${count} pieza`],
  [/^(\d+) pieces$/i, (_, count) => `${count} piezas`],
  [/^(\d+) pcs$/i, (_, count) => `${count} pzas`],
  [/^(\d+)pcs$/i, (_, count) => `${count}pzas`],
  [/^(\d+) row$/i, (_, count) => `${count} fila`],
  [/^(\d+) rows$/i, (_, count) => `${count} filas`],
  [/^(\d+) rack$/i, (_, count) => `${count} rack`],
  [/^(\d+) racks$/i, (_, count) => `${count} racks`],
  [/^(\d+) bay$/i, (_, count) => `${count} bahía`],
  [/^(\d+) bays$/i, (_, count) => `${count} bahías`],
  [/^(\d+) user$/i, (_, count) => `${count} usuario`],
  [/^(\d+) users$/i, (_, count) => `${count} usuarios`],
  [/^(\d+) scan$/i, (_, count) => `${count} escaneo`],
  [/^(\d+) scans$/i, (_, count) => `${count} escaneos`],
  [/^(\d+) order$/i, (_, count) => `${count} orden`],
  [/^(\d+) orders$/i, (_, count) => `${count} órdenes`],
  [/^(\d+) active$/i, (_, count) => `${count} activos`],
  [/^(\d+) inactive$/i, (_, count) => `${count} inactivos`],
  [/^(\d+) complete$/i, (_, count) => `${count} completos`],
  [/^(\d+) open$/i, (_, count) => `${count} abiertos`],
  [/^(\d+) available$/i, (_, count) => `${count} disponibles`],
  [/^(\d+) occupied$/i, (_, count) => `${count} ocupados`],
  [/^(\d+) sent$/i, (_, count) => `${count} enviados`],
  [/^(\d+) draft$/i, (_, count) => `${count} borrador`],
  [/^(\d+) drafts$/i, (_, count) => `${count} borradores`],
  [/^(\d+) failed$/i, (_, count) => `${count} fallidos`],
  [/^(\d+) email rule$/i, (_, count) => `${count} regla de correo`],
  [/^(\d+) email rules$/i, (_, count) => `${count} reglas de correo`],
  [/^(\d+) global CC address$/i, (_, count) => `${count} dirección CC global`],
  [/^(\d+) global CC addresses$/i, (_, count) => `${count} direcciones CC globales`],
  [/^Progress:\s*(.*)$/i, (_, value) => `Progreso: ${value}`],
  [/^Staged Qty:\s*(.*)$/i, (_, value) => `Cant. preparada: ${value}`],
  [/^Outbound Qty:\s*(.*)$/i, (_, value) => `Cant. de salida: ${value}`],
  [/^Received Qty:\s*(.*)$/i, (_, value) => `Cant. recibida: ${value}`],
  [/^Delivery on-time\s*(.*)$/i, (_, value) => `Entrega a tiempo ${value}`],
  [/^Last updated:\s*(.*)$/i, (_, value) => `Última actualización: ${value}`],
  [/^Updated at:\s*(.*)$/i, (_, value) => `Actualizado: ${value}`],
  [/^Scanner:\s*(.*)$/i, (_, value) => `Escáner: ${value}`],
  [/^Assigned station:\s*(.*)$/i, (_, value) => `Estación asignada: ${value}`],
  [/^In Transit:\s*(.*)$/i, (_, value) => `En tránsito: ${value}`],
  [/^Racks in transit$/i, () => "Racks en tránsito"],
  [/^In transit racks:\s*(.*)$/i, (_, value) => `Racks en tránsito: ${value}`],
  [/^Page\s+(\d+)\s+of\s+(\d+)$/i, (_, page, total) => `Página ${page} de ${total}`],
  [/^Showing\s+(\d+)\s+of\s+(\d+)$/i, (_, shown, total) => `Mostrando ${shown} de ${total}`],
  [/^(\d+)\s+rows\s*\/\s*(\d+)\s+pieces$/i, (_, rows, pieces) => `${rows} filas / ${pieces} piezas`],
  [/^(\d+)\s+racks?\s*\/\s*(\d+)\s+pieces$/i, (_, racks, pieces) => `${racks} racks / ${pieces} piezas`],
  [/^(\d+)\s+bays?\s*\/\s*(\d+)\s+used$/i, (_, bays, used) => `${bays} bahías / ${used} usadas`],
  [/^(\d+)\s+racks?\s*\|\s*(\d+)\s+active\s*\|\s*(\d+)\s+complete$/i, (_, racks, active, complete) => `${racks} racks | ${active} activos | ${complete} completos`],
  [/^(\d+)\s+active\s*\|\s*(\d+)\s+complete$/i, (_, active, complete) => `${active} activos | ${complete} completos`],
  [/^(\d+)\s+stages?\s*[•|]\s*Delivery on-time\s*(.*)$/i, (_, stages, value) => `${stages} etapas • Entrega a tiempo ${value}`],
  [/^(\d+)\s+stages?\s*[•|]\s*Updated\s*(.*)$/i, (_, stages, value) => `${stages} etapas • Actualizado ${value}`],
  [/^All Glass\s*\((\d+)\)$/i, (_, count) => `Todo el vidrio (${count})`],
  [/^(.+?)\s+(\d+)pcs\s+\((Empty|Open|Complete|On the way)\)$/i, (_, code, qty, status) => `${code} ${qty} pzas (${SPANISH_UI_TEXT.get(status) || status})`],
  [/^(.+?)\s+\((Empty|Open|Complete|On the way)\)$/i, (_, code, status) => `${code} (${SPANISH_UI_TEXT.get(status) || status})`],
  [/^(.+?)\s+-\s+(Empty|Open|Complete|On the way)$/i, (_, label, status) => `${label} - ${SPANISH_UI_TEXT.get(status) || status}`],
  [/^Open\s+(.+)$/i, (_, value) => `Abrir ${value}`],
  [/^Remove\s+(.+)$/i, (_, value) => `Quitar ${value}`],
  [/^Edit\s+(.+)$/i, (_, value) => `Editar ${value}`],
  [/^Save\s+(.+)$/i, (_, value) => `Guardar ${value}`],
  [/^Delete\s+(.+)$/i, (_, value) => `Eliminar ${value}`],
  [/^Reset\s+(.+)$/i, (_, value) => `Restablecer ${value}`],
  [/^Select\s+(.+)$/i, (_, value) => `Seleccione ${value}`],
  [/^No\s+(.+)\s+yet$/i, (_, value) => `Aún no hay ${value}`],
  [/^Password updated for\s+(.+)\.$/i, (_, user) => `Contraseña actualizada para ${user}.`],
  [/^Saved\s+(.+)\.$/i, (_, value) => `Se guardó ${value}.`],
  [/^Rack code\s+(.+)\s+already exists$/i, (_, code) => `El código de rack ${code} ya existe`],
  [/^Rack\s+(.+)\s+was not found$/i, (_, code) => `No se encontró el rack ${code}`],
  [/^Unknown bay:\s*(.+)$/i, (_, code) => `Bahía desconocida: ${code}`],
  [/^Unknown or blocked bay:\s*(.+)$/i, (_, code) => `Bahía desconocida o bloqueada: ${code}`],
  [/^Temp Delivery Lists folder not found:\s*(.+)$/i, (_, folder) => `No se encontró la carpeta temporal de listas: ${folder}`],
  [/^Request failed:\s*(.+)$/i, (_, value) => `La solicitud falló: ${value}`],
  [/^Search failed:\s*(.+)$/i, (_, value) => `La búsqueda falló: ${value}`],
  [/^(All|Complete|Partial|Remaining|Remakes|Rushes|Updated|Review)\s*\((\d+)\)$/i, (_, label, count) => `${SPANISH_UI_TEXT.get(label) || label} (${count})`],
  [/^(\d+)\s+days$/i, (_, count) => `${count} días`],
  [/^(\d+)\s+bays?\s*\/\s*(\d+)\s+used$/i, (_, bays, used) => `${bays} bahías / ${used} usadas`],
  [/^(\d+)\s+active\s*\|\s*(\d+)\s+complete$/i, (_, active, complete) => `${active} activos | ${complete} completos`],
  [/^(\d+)\s+stages?\s*-\s*Delivery on-time\s*(.*)$/i, (_, stages, value) => `${stages} etapas - Entrega a tiempo ${value}`],
  [/^No delivery lists are loaded for\s+(.+)\.$/i, (_, date) => `No hay listas de entrega cargadas para ${date}.`],
  [/^(\d+)\s+older delivery date(?:s)? hidden\s*\((\d+)\s+stage(?:s)?\)\.$/i, (_, dates, stages) => `${dates} fechas antiguas ocultas (${stages} etapas).`],
  [/^(\d+)\s+bay group(?:s)? shown\. Click a bay for tools or use Manage Items for bulk order work\.$/i, (_, count) => `${count} grupos de bahías mostrados. Haga clic en una bahía para usar sus herramientas o use Administrar artículos para trabajo en lote.`],
  [/^Every stage for\s+(.+)\s+is back to zero scanned quantity\.$/i, (_, date) => `Todas las etapas de ${date} volvieron a cero escaneos.`],
  [/^(.+)\s+is back to zero scanned quantity\.$/i, (_, label) => `${label} volvió a cero escaneos.`],
  [/^(\d+)\s+stages? removed\.$/i, (_, count) => `Se eliminaron ${count} etapas.`],
  [/^Showing\s+(\d+)\s+of\s+(\d+)\s+rows?$/i, (_, shown, total) => `Mostrando ${shown} de ${total} filas`],
];

function translateDynamicUiText(cleanText) {
  const exact = SPANISH_UI_TEXT.get(cleanText);
  if (exact) return exact;

  for (const [pattern, replacement] of SPANISH_DYNAMIC_PATTERNS) {
    const match = cleanText.match(pattern);
    if (!match) continue;
    return typeof replacement === "function"
      ? replacement(...match)
      : cleanText.replace(pattern, replacement);
  }

  return cleanText;
}

function translatedUiValue(value) {
  const text = String(value ?? "");
  const leading = text.match(/^\s*/)?.[0] || "";
  const trailing = text.match(/\s*$/)?.[0] || "";
  const clean = text.trim();
  if (!clean) return text;
  return `${leading}${translateDynamicUiText(clean)}${trailing}`;
}

function translateUiTextNode(node) {
  const current = node.nodeValue || "";

  if (state.language === "es") {
    if (current === node.__dlsSpanishText) return;
    node.__dlsEnglishText = current;
    const translated = translatedUiValue(current);
    node.__dlsSpanishText = translated;
    if (translated !== current) node.nodeValue = translated;
    return;
  }

  if (node.__dlsEnglishText !== undefined && current !== node.__dlsEnglishText) {
    node.nodeValue = node.__dlsEnglishText;
  }
}

function translateUiAttributes(element) {
  const attributes = ["placeholder", "title", "aria-label"];
  if (element.tagName === "OPTGROUP" && element.hasAttribute("label")) attributes.push("label");
  if (element.tagName === "INPUT" && ["button", "submit", "reset"].includes(String(element.type || "").toLowerCase()) && element.hasAttribute("value")) attributes.push("value");

  for (const attribute of attributes) {
    if (!element.hasAttribute?.(attribute)) continue;
    const storageKey = `dls${attribute.replace(/-([a-z])/g, (_, letter) => letter.toUpperCase())}En`;
    const current = element.getAttribute(attribute) || "";

    if (state.language === "es") {
      const spanishKey = `${storageKey}Es`;
      if (!element.dataset[storageKey] || current !== element.dataset[spanishKey]) {
        element.dataset[storageKey] = current;
      }
      const translated = attribute === "placeholder"
        ? (SPANISH_PLACEHOLDERS.get(current) || translatedUiValue(current))
        : translatedUiValue(current);
      element.dataset[spanishKey] = translated;
      element.setAttribute(attribute, translated);
    } else if (element.dataset[storageKey]) {
      element.setAttribute(attribute, element.dataset[storageKey]);
    }
  }
}

function shouldSkipUiTranslation(element) {
  return Boolean(element?.closest?.("script, style, textarea, [contenteditable='true'], [data-no-translate]"));
}

function applyLanguageToRoot(root = document.body) {
  if (!root) return;

  if (root.nodeType === Node.TEXT_NODE) {
    if (!shouldSkipUiTranslation(root.parentElement)) translateUiTextNode(root);
    return;
  }

  if (!(root instanceof Element || root instanceof Document || root instanceof DocumentFragment)) return;

  if (root instanceof Element) translateUiAttributes(root);
  root.querySelectorAll?.("[placeholder], [title], [aria-label], optgroup[label], input[type=button][value], input[type=submit][value], input[type=reset][value]").forEach((element) => translateUiAttributes(element));

  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  let node = walker.nextNode();
  while (node) {
    if (!shouldSkipUiTranslation(node.parentElement)) translateUiTextNode(node);
    node = walker.nextNode();
  }
}

function syncLanguageControls() {
  const spanish = state.language === "es";
  document.documentElement.lang = spanish ? "es" : "en";
  document.title = spanish ? "Escáner de Listas de Entrega" : "Delivery List Scanner";

  [els.languageToggleBtn, els.loginLanguageToggleBtn].forEach((button) => {
    if (!button) return;
    const label = button.querySelector("span:last-child");
    if (label) label.textContent = spanish ? "EN" : "ES";
    const description = spanish ? "Cambiar a Inglés" : "Cambiar a Español";
    button.title = description;
    button.setAttribute("aria-label", description);
  });
}

function setAppLanguage(language) {
  state.language = language === "es" ? "es" : "en";
  try {
    localStorage.setItem(LANGUAGE_KEY, state.language);
  } catch {
    // Language persistence is optional in restricted browser modes.
  }
  applyLanguageToRoot(document.body);
  syncLanguageControls();
  syncAllCustomSelects();
}

function toggleAppLanguage() {
  setAppLanguage(state.language === "es" ? "en" : "es");
}

function initLanguageSystem() {
  if (languageUi.observer) return;
  applyLanguageToRoot(document.body);
  syncLanguageControls();

  languageUi.observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      if (mutation.type === "characterData") {
        applyLanguageToRoot(mutation.target);
        return;
      }
      mutation.addedNodes.forEach((node) => applyLanguageToRoot(node));
    });
  });
  languageUi.observer.observe(document.body, { childList: true, subtree: true, characterData: true });
}

function syncFullscreenControl() {
  const active = Boolean(document.fullscreenElement);
  if (!els.fullscreenToggleBtn) return;
  els.fullscreenToggleBtn.classList.toggle("is-active", active);
  const label = active ? "Exit fullscreen" : "Enter fullscreen";
  els.fullscreenToggleBtn.title = state.language === "es"
    ? (active ? "Salir de pantalla completa" : "Entrar en pantalla completa")
    : label;
  els.fullscreenToggleBtn.setAttribute("aria-label", els.fullscreenToggleBtn.title);
}

async function toggleFullscreen() {
  if (!document.fullscreenEnabled) {
    showInlineError(state.language === "es" ? "La pantalla completa no está disponible en este navegador." : "Fullscreen is not available in this browser.");
    return;
  }

  if (document.fullscreenElement) await document.exitFullscreen();
  else await document.documentElement.requestFullscreen();
}

const customSelectUi = {
  initialized: false,
  openSelect: null,
  menu: null,
  highlightedIndex: -1,
  observer: null,
  syncTimer: null,
};

function customSelectIsEligible(select) {
  return (
    select instanceof HTMLSelectElement &&
    !select.multiple &&
    Number(select.size || 0) <= 1 &&
    !select.hidden &&
    !select.dataset.nativeSelect
  );
}

function customSelectAccessibleLabel(select) {
  const explicit = select.getAttribute("aria-label") || select.getAttribute("title");
  if (explicit) return explicit;

  const label = select.labels?.[0];
  if (label) {
    const labelText = label.querySelector(":scope > span")?.textContent || label.textContent;
    const clean = String(labelText || "").replace(/\s+/g, " ").trim();
    if (clean) return clean;
  }

  return select.id
    ? select.id.replace(/([a-z])([A-Z])/g, "$1 $2").replace(/[-_]+/g, " ")
    : "Choose an option";
}

function customSelectSelectedText(select) {
  const option = select.selectedOptions?.[0] || select.options?.[select.selectedIndex];
  return option?.textContent?.trim() || select.getAttribute("placeholder") || "Choose an option";
}

function syncCustomSelect(select) {
  const shell = select.closest(".custom-select-shell");
  const trigger = shell?.querySelector(":scope > .custom-select-trigger");
  const value = trigger?.querySelector(".custom-select-value");
  if (!shell || !trigger || !value) return;

  const option = select.selectedOptions?.[0] || select.options?.[select.selectedIndex];
  const disabled = Boolean(select.disabled);
  const hidden = Boolean(select.hidden);
  const sourceClasses = [...select.classList].filter((name) => name !== "custom-select-native");

  trigger.className = "custom-select-trigger";
  sourceClasses.forEach((name) => trigger.classList.add(name));
  trigger.disabled = disabled;
  trigger.setAttribute("aria-disabled", disabled ? "true" : "false");
  trigger.setAttribute("aria-expanded", customSelectUi.openSelect === select ? "true" : "false");
  trigger.title = option?.textContent?.trim() || customSelectAccessibleLabel(select);
  value.textContent = customSelectSelectedText(select);

  shell.hidden = hidden;
  shell.classList.toggle("is-disabled", disabled);
  shell.classList.toggle("is-open", customSelectUi.openSelect === select);
  shell.classList.toggle("is-placeholder", !option || (!option.value && option.disabled));

  if (customSelectUi.openSelect === select && customSelectUi.menu) {
    customSelectUi.menu.querySelectorAll("[data-custom-option-index]").forEach((button) => {
      const optionIndex = Number(button.dataset.customOptionIndex);
      const selected = optionIndex === select.selectedIndex;
      button.classList.toggle("is-selected", selected);
      button.setAttribute("aria-selected", selected ? "true" : "false");
    });
  }
}

function syncAllCustomSelects() {
  if (customSelectUi.openSelect && !customSelectUi.openSelect.isConnected) closeCustomSelect(false);
  document.querySelectorAll("select[data-custom-select-enhanced='true']").forEach((select) => syncCustomSelect(select));
}

function positionCustomSelectMenu() {
  const select = customSelectUi.openSelect;
  const menu = customSelectUi.menu;
  const trigger = select?.closest(".custom-select-shell")?.querySelector(":scope > .custom-select-trigger");
  if (!select || !menu || !trigger) return;

  const rect = trigger.getBoundingClientRect();
  const viewportPadding = 10;
  const longestOptionLength = [...select.options].reduce(
    (length, option) => Math.max(length, option.textContent?.trim().length || 0),
    0,
  );
  const contentWidth = Math.min(420, Math.max(210, longestOptionLength * 7.2 + 58));
  const preferredWidth = Math.max(rect.width, contentWidth);
  const maxWidth = Math.max(210, window.innerWidth - viewportPadding * 2);
  const menuWidth = Math.min(preferredWidth, maxWidth);

  menu.style.width = `${menuWidth}px`;
  menu.style.left = `${Math.min(Math.max(rect.left, viewportPadding), window.innerWidth - menuWidth - viewportPadding)}px`;

  const menuHeight = Math.min(menu.scrollHeight || 320, Math.max(180, window.innerHeight - viewportPadding * 2));
  const spaceBelow = window.innerHeight - rect.bottom - viewportPadding;
  const spaceAbove = rect.top - viewportPadding;
  const openAbove = spaceBelow < Math.min(menuHeight, 280) && spaceAbove > spaceBelow;

  menu.classList.toggle("opens-above", openAbove);
  menu.style.maxHeight = `${Math.max(160, openAbove ? spaceAbove : spaceBelow)}px`;
  menu.style.top = openAbove
    ? `${Math.max(viewportPadding, rect.top - Math.min(menuHeight, spaceAbove) - 7)}px`
    : `${Math.min(window.innerHeight - viewportPadding, rect.bottom + 7)}px`;
}

function setCustomSelectHighlight(index, focus = true) {
  const buttons = [...(customSelectUi.menu?.querySelectorAll("[data-custom-option-index]:not(:disabled)") || [])];
  if (!buttons.length) {
    customSelectUi.highlightedIndex = -1;
    return;
  }

  const safeIndex = Math.min(Math.max(index, 0), buttons.length - 1);
  customSelectUi.highlightedIndex = safeIndex;
  buttons.forEach((button, buttonIndex) => button.classList.toggle("is-highlighted", buttonIndex === safeIndex));

  if (focus) {
    buttons[safeIndex].focus({ preventScroll: true });
    buttons[safeIndex].scrollIntoView({ block: "nearest" });
  }
}

function closeCustomSelect(restoreFocus = false) {
  const select = customSelectUi.openSelect;
  const trigger = select?.closest(".custom-select-shell")?.querySelector(":scope > .custom-select-trigger");

  customSelectUi.menu?.remove();
  customSelectUi.menu = null;
  customSelectUi.openSelect = null;
  customSelectUi.highlightedIndex = -1;

  if (select) syncCustomSelect(select);
  if (restoreFocus) trigger?.focus();
}

function customSelectOptionRows(select, query = "") {
  const cleanQuery = String(query || "").trim().toLowerCase();
  const rows = [];
  let currentGroup = "";

  [...select.options].forEach((option, index) => {
    if (option.hidden) return;
    const text = option.textContent?.trim() || option.value;
    if (cleanQuery && !`${text} ${option.value}`.toLowerCase().includes(cleanQuery)) return;

    const parentGroup = option.parentElement instanceof HTMLOptGroupElement
      ? option.parentElement.label.trim()
      : "";

    if (parentGroup && parentGroup !== currentGroup) {
      rows.push({ type: "group", label: parentGroup });
      currentGroup = parentGroup;
    }

    rows.push({ type: "option", option, index, text });
  });

  return rows;
}

function renderCustomSelectOptions(select, optionsHost, query = "") {
  optionsHost.replaceChildren();
  const rows = customSelectOptionRows(select, query);

  if (!rows.some((row) => row.type === "option")) {
    const empty = document.createElement("div");
    empty.className = "custom-select-empty";
    empty.textContent = "No matching options";
    optionsHost.append(empty);
    customSelectUi.highlightedIndex = -1;
    return;
  }

  rows.forEach((row) => {
    if (row.type === "group") {
      const group = document.createElement("div");
      group.className = "custom-select-group";
      group.textContent = row.label;
      optionsHost.append(group);
      return;
    }

    const button = document.createElement("button");
    button.type = "button";
    button.className = "custom-select-option";
    button.dataset.customOptionIndex = String(row.index);
    button.disabled = Boolean(row.option.disabled);
    button.setAttribute("role", "option");
    button.setAttribute("aria-selected", row.index === select.selectedIndex ? "true" : "false");
    button.classList.toggle("is-selected", row.index === select.selectedIndex);

    const label = document.createElement("span");
    label.className = "custom-select-option-label";
    label.textContent = row.text;

    const check = document.createElement("span");
    check.className = "custom-select-option-check";
    check.setAttribute("aria-hidden", "true");

    button.append(label, check);
    optionsHost.append(button);

    button.addEventListener("click", () => {
      if (row.option.disabled) return;
      const changed = select.selectedIndex !== row.index;
      select.selectedIndex = row.index;
      syncCustomSelect(select);
      closeCustomSelect(true);

      if (changed) {
        select.dispatchEvent(new Event("input", { bubbles: true }));
        select.dispatchEvent(new Event("change", { bubbles: true }));
      }
    });
  });

  const enabledButtons = [...optionsHost.querySelectorAll("[data-custom-option-index]:not(:disabled)")];
  const selectedEnabledIndex = enabledButtons.findIndex((button) => Number(button.dataset.customOptionIndex) === select.selectedIndex);
  setCustomSelectHighlight(selectedEnabledIndex >= 0 ? selectedEnabledIndex : 0, false);
}

function openCustomSelect(select) {
  if (!customSelectIsEligible(select) || select.disabled) return;
  if (customSelectUi.openSelect === select) {
    closeCustomSelect(true);
    return;
  }

  closeCustomSelect(false);
  customSelectUi.openSelect = select;

  const shell = select.closest(".custom-select-shell");
  const trigger = shell?.querySelector(":scope > .custom-select-trigger");
  if (!shell || !trigger) return;

  const menu = document.createElement("div");
  menu.className = "custom-select-menu";
  menu.id = `${select.id || `customSelect${Date.now()}`}Menu`;
  menu.setAttribute("role", "listbox");
  menu.setAttribute("aria-label", customSelectAccessibleLabel(select));

  const optionsHost = document.createElement("div");
  optionsHost.className = "custom-select-options";

  const visibleOptionCount = [...select.options].filter((option) => !option.hidden).length;
  if (visibleOptionCount >= 10) {
    const searchWrap = document.createElement("label");
    searchWrap.className = "custom-select-search";

    const searchIcon = document.createElement("span");
    searchIcon.className = "custom-select-search-icon";
    searchIcon.setAttribute("aria-hidden", "true");

    const search = document.createElement("input");
    search.type = "search";
    search.autocomplete = "off";
    search.placeholder = "Filter options...";
    search.setAttribute("aria-label", `Filter ${customSelectAccessibleLabel(select)}`);
    search.addEventListener("input", () => {
      renderCustomSelectOptions(select, optionsHost, search.value);
      positionCustomSelectMenu();
    });
    search.addEventListener("keydown", (event) => {
      if (event.key === "ArrowDown") {
        event.preventDefault();
        setCustomSelectHighlight(0);
      } else if (event.key === "Escape") {
        event.preventDefault();
        closeCustomSelect(true);
      }
    });

    searchWrap.append(searchIcon, search);
    menu.append(searchWrap);
  }

  menu.append(optionsHost);
  document.body.append(menu);
  customSelectUi.menu = menu;

  trigger.setAttribute("aria-controls", menu.id);
  renderCustomSelectOptions(select, optionsHost);
  syncCustomSelect(select);
  positionCustomSelectMenu();

  menu.addEventListener("keydown", (event) => {
    const enabledButtons = [...menu.querySelectorAll("[data-custom-option-index]:not(:disabled)")];
    const focusedIndex = enabledButtons.indexOf(document.activeElement);

    if (event.key === "ArrowDown") {
      event.preventDefault();
      setCustomSelectHighlight(focusedIndex >= 0 ? focusedIndex + 1 : customSelectUi.highlightedIndex + 1);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setCustomSelectHighlight(focusedIndex >= 0 ? focusedIndex - 1 : customSelectUi.highlightedIndex - 1);
    } else if (event.key === "Home") {
      event.preventDefault();
      setCustomSelectHighlight(0);
    } else if (event.key === "End") {
      event.preventDefault();
      setCustomSelectHighlight(enabledButtons.length - 1);
    } else if (event.key === "Escape" || event.key === "Tab") {
      closeCustomSelect(event.key === "Escape");
    }
  });

  const searchInput = menu.querySelector(".custom-select-search input");
  if (searchInput) {
    searchInput.focus();
  } else {
    requestAnimationFrame(() => setCustomSelectHighlight(customSelectUi.highlightedIndex >= 0 ? customSelectUi.highlightedIndex : 0));
  }
}

function enhanceCustomSelect(select) {
  if (!customSelectIsEligible(select) || select.dataset.customSelectEnhanced === "true") return;

  const shell = document.createElement("span");
  shell.className = "custom-select-shell";
  shell.dataset.customSelectFor = select.id || "dynamic";

  const trigger = document.createElement("button");
  trigger.type = "button";
  trigger.className = "custom-select-trigger";
  trigger.setAttribute("role", "combobox");
  trigger.setAttribute("aria-haspopup", "listbox");
  trigger.setAttribute("aria-expanded", "false");
  trigger.setAttribute("aria-label", customSelectAccessibleLabel(select));

  const value = document.createElement("span");
  value.className = "custom-select-value";

  const arrow = document.createElement("span");
  arrow.className = "custom-select-arrow";
  arrow.setAttribute("aria-hidden", "true");

  trigger.append(value, arrow);
  select.parentNode?.insertBefore(shell, select);
  shell.append(select, trigger);

  select.dataset.customSelectEnhanced = "true";
  select.classList.add("custom-select-native");
  select.tabIndex = -1;
  select.setAttribute("aria-hidden", "true");

  trigger.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    openCustomSelect(select);
  });

  trigger.addEventListener("keydown", (event) => {
    if (["Enter", " ", "ArrowDown", "ArrowUp"].includes(event.key)) {
      event.preventDefault();
      openCustomSelect(select);
    }
  });

  select.addEventListener("input", () => syncCustomSelect(select));
  select.addEventListener("change", () => syncCustomSelect(select));

  syncCustomSelect(select);
}

function enhanceCustomSelects(root = document) {
  if (root instanceof HTMLSelectElement) {
    enhanceCustomSelect(root);
    return;
  }
  root.querySelectorAll?.("select").forEach((select) => enhanceCustomSelect(select));
}

function initCustomSelectSystem() {
  if (customSelectUi.initialized) return;
  customSelectUi.initialized = true;

  enhanceCustomSelects(document);

  customSelectUi.observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      if (mutation.type === "childList") {
        mutation.addedNodes.forEach((node) => {
          if (node instanceof Element) enhanceCustomSelects(node);
        });
      }

      const select = mutation.target instanceof HTMLSelectElement
        ? mutation.target
        : mutation.target.closest?.("select");
      if (select) {
        if (select.dataset.customSelectEnhanced === "true") syncCustomSelect(select);
        else enhanceCustomSelect(select);
      }
    });
  });

  customSelectUi.observer.observe(document.body, {
    childList: true,
    subtree: true,
    attributes: true,
    attributeFilter: ["class", "disabled", "hidden"],
  });

  document.addEventListener("click", (event) => {
    if (!customSelectUi.openSelect || !customSelectUi.menu) return;
    const trigger = customSelectUi.openSelect.closest(".custom-select-shell")?.querySelector(":scope > .custom-select-trigger");
    if (customSelectUi.menu.contains(event.target) || trigger?.contains(event.target)) return;
    closeCustomSelect(false);
  }, true);

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && customSelectUi.openSelect) closeCustomSelect(true);
  });

  document.addEventListener("change", () => queueMicrotask(syncAllCustomSelects), true);
  window.addEventListener("resize", () => customSelectUi.openSelect && positionCustomSelectMenu());
  document.addEventListener("scroll", (event) => {
    if (!customSelectUi.openSelect || customSelectUi.menu?.contains(event.target)) return;
    closeCustomSelect(false);
  }, true);

  customSelectUi.syncTimer = window.setInterval(syncAllCustomSelects, 300);
}

function canonicalBarcode(order, item) {
  return `T200${pad(order, 6)}${pad(item, 3)}000`;
}

function formatDisplayDate(value) {
  const parts = String(value || "").split("-").map(Number);
  if (parts.length !== 3 || parts.some(Number.isNaN)) return String(value || "");
  return `${parts[1]}/${parts[2]}/${parts[0]}`;
}

function formatDateTime(value) {
  if (!value) return "";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString();
}

function todayKey() {
  const now = new Date();
  return `${now.getFullYear()}-${pad(now.getMonth() + 1, 2)}-${pad(now.getDate(), 2)}`;
}

function dateInputValue(date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1, 2)}-${pad(date.getDate(), 2)}`;
}

const IMPORT_MAX_DATE = "";

function defaultImportFromDate() {
  const from = new Date();
  from.setDate(from.getDate() - 7);
  return dateInputValue(from);
}

function resetImportDateWindow() {
  if (els.importFromDate) els.importFromDate.value = defaultImportFromDate();
  if (els.importToDate) {
    els.importToDate.value = "";
    els.importToDate.placeholder = "Newest future list";
  }
}

function currentImportDateWindow() {
  const dateFrom = (els.importFromDate?.value || defaultImportFromDate()).trim();
  const dateTo = (els.importToDate?.value || "").trim();

  if (els.importFromDate && !els.importFromDate.value) els.importFromDate.value = dateFrom;
  if (els.importToDate && !els.importToDate.value) els.importToDate.placeholder = "Newest future list";

  return { dateFrom, dateTo };
}

function parseDateKey(value) {
  const parts = String(value || "").split("-").map(Number);
  if (parts.length !== 3 || parts.some(Number.isNaN)) return null;
  return new Date(parts[0], parts[1] - 1, parts[2]);
}

function filterListsByOverviewRange(lists = state.lists) {
  if (state.overviewRange === "all") return lists.slice();
  const days = Number(state.overviewRange || 30);
  if (!days) return lists.slice();
  const end = new Date();
  end.setHours(23, 59, 59, 999);
  const start = new Date(end);
  start.setDate(start.getDate() - days + 1);
  start.setHours(0, 0, 0, 0);
  return lists.filter((list) => {
    const date = parseDateKey(list.deliveryDate);
    return date && date >= start && date <= end;
  });
}

function latestDeliveryDate(lists = state.lists) {
  const dates = lists.map((list) => list.deliveryDate).filter(Boolean).sort();
  return dates[dates.length - 1] || todayKey();
}

function dashboardDateKey(lists = state.lists) {
  const today = todayKey();
  return lists.some((list) => list.deliveryDate === today) ? today : latestDeliveryDate(lists);
}

function progressPercent(list) {
  return Number(list?.totalQty || 0) ? (Number(list.scannedQty || 0) / Number(list.totalQty || 1)) * 100 : 0;
}

function formatPercent(value) {
  return `${Math.round(Number(value || 0))}%`;
}

function stageCategory(list) {
  const stage = `${list?.stage || ""} ${list?.scanner || ""}`.toLowerCase();
  if (stage.includes("outbound")) return "outbound";
  if (stage.includes("dtc") || stage.includes("deliver to customer")) return "dtc";
  if (stage.includes("greenville") || /\bgnv\b/.test(stage)) return "greenville";
  if (stage.includes("indian trail") || stage.includes("inbound")) return "received";
  if (stage.includes("customer pickup")) return "pickup";
  return "staged";
}

function stageLabel(list) {
  const category = stageCategory(list);
  if (category === "outbound") return "Outbound";
  if (category === "greenville") return "BFS Greenville";
  if (category === "received") return "Received";
  if (category === "pickup") return "Customer Pickup";
  if (category === "dtc") return "Delivery to Customer";
  return "Staged";
}

function slugify(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
}

function uniqueText(values) {
  const seen = new Set();
  const result = [];
  for (const value of values) {
    const clean = String(value || "").trim();
    if (!clean || seen.has(clean.toLowerCase())) continue;
    seen.add(clean.toLowerCase());
    result.push(clean);
  }
  return result;
}

function listsByDeliveryDate(lists = state.lists) {
  const groups = new Map();
  for (const list of lists) {
    const key = list.deliveryDate || "undated";
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(list);
  }
  return [...groups.entries()]
    .sort(([dateA], [dateB]) => String(dateB).localeCompare(String(dateA)))
    .map(([date, dateLists]) => ({
      date,
      lists: dateLists.slice().sort((a, b) => stageSort(a) - stageSort(b) || a.label.localeCompare(b.label)),
    }));
}

function stageSort(list) {
  return { staged: 1, outbound: 2, received: 3, greenville: 4, pickup: 5, dtc: 6 }[stageCategory(list)] || 9;
}

function selectedDeliveryDate() {
  return state.meta?.deliveryDate || state.lists.find((list) => list.id === state.activeListId)?.deliveryDate || state.lists[0]?.deliveryDate || "";
}

function hasPermission(permission) {
  if (!state.backend) return true;
  return state.permissions.includes(permission);
}

function hasAnyPermission(permissions) {
  return permissions.some((permission) => hasPermission(permission));
}

function setControlAllowed(element, allowed, hide = false) {
  if (!element) return;
  element.disabled = !allowed;
  if (hide) element.hidden = !allowed;
  element.classList.toggle("is-disabled", !allowed);
}

function userAssignedStations(user = state.user) {
  const explicit = Array.isArray(user?.assignedStations) ? user.assignedStations : [];
  const stationText = String(user?.station || user?.assignedStation || "");
  const parsed = stationText
    .split(/[|,]/)
    .map((station) => station.trim())
    .filter(Boolean);

  return uniqueText([...explicit, ...parsed]);
}

function userAssignedStation(user = state.user) {
  return userAssignedStations(user)[0] || "";
}

function userAssignedStationLabel(user = state.user, fallback = "") {
  const stations = userAssignedStations(user);
  if (stations.length) return stations.join(", ");
  return String(fallback || "No assigned station").trim();
}

function currentScanStation() {
  return userAssignedStation() || els.stationSelect?.value || state.meta?.scanner || DEFAULT_STATIONS[0] || "";
}

function requestContext() {
  return {
    user: state.user?.username || els.operatorInput?.value || "Scanner",
    station: currentScanStation(),
  };
}

function showImportStatusLoading(message, detail = "") {
  if (!els.importPreviewBox) return;

  els.importPreviewBox.hidden = false;
  els.importPreviewBox.classList.remove("success", "review", "notice", "import-status-compact");
  els.importPreviewBox.classList.add("loading");

  els.importPreviewBox.innerHTML = `
    <strong>${escapeHtml(message)}</strong>
    <span class="loading-bar"><i></i></span>
    ${detail ? `<span>${escapeHtml(detail)}</span>` : ""}
  `;
}

function showImportStatusResult(kind, title, detail = "", actionsHtml = "") {
  if (!els.importPreviewBox) return;

  const statusClass = kind === "review" ? "review" : kind === "notice" ? "notice" : "success";

  els.importPreviewBox.hidden = false;
  els.importPreviewBox.classList.remove("loading", "success", "review", "notice");
  els.importPreviewBox.classList.add(statusClass, "import-status-compact");

  els.importPreviewBox.innerHTML = `
    <strong>${escapeHtml(title)}</strong>
    ${detail ? `<span>${escapeHtml(detail)}</span>` : ""}
    ${actionsHtml ? `<div class="import-status-actions">${actionsHtml}</div>` : ""}
  `;
}

function waitForNextPaint() {
  return new Promise((resolve) => {
    requestAnimationFrame(() => {
      requestAnimationFrame(resolve);
    });
  });
}

function updateModalScrollLock() {
  const modalIsOpen = [
    els.adminModal,
    els.printOptionsPanel,
    els.baySelectedModal,
    els.staleBayPanel,
    els.sdiPanel,
    els.manageItemsPanel,
    els.bayEditorPanel,
    document.getElementById("emailDraftPreviewShell"),
    document.getElementById("actionFeedbackShell"),
    els.statsChartModal,
  ].some((panel) => panel && !panel.hidden);

  document.body.classList.toggle("modal-scroll-locked", modalIsOpen);
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, {
    cache: "no-store",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    const text = await response.text();
    let message = text || `Request failed: ${response.status}`;
    try {
      const payload = JSON.parse(text);
      message = payload.error || payload.message || message;
    } catch {
      // Keep raw text when the server does not return JSON.
    }
    if (response.status === 401 && state.backend && url !== "/api/login") {
      state.authenticated = false;
      state.user = null;
      state.permissions = [];
      showLogin("Please sign in to continue.");
    }
    throw new Error(message);
  }
  return response.json();
}

async function detectBackend() {
  try {
    const health = await fetchJson("/api/health");
    state.backend = Boolean(health.ok);
  } catch {
    state.backend = false;
  }
}

function showLogin(message = "") {
  if (!els.loginPanel) return;
  els.loginPanel.hidden = false;
  document.querySelector(".app")?.setAttribute("aria-hidden", "true");
  if (els.loginError) {
    els.loginError.textContent = message;
    els.loginError.classList.remove("success");
  }
  window.setTimeout(() => (els.loginPassword || els.loginUsername)?.focus(), 30);
}

function hideLogin() {
  if (!els.loginPanel) return;
  els.loginPanel.hidden = true;
  if (els.passwordResetPanel) els.passwordResetPanel.hidden = true;
  document.querySelector(".app")?.removeAttribute("aria-hidden");
  if (els.loginError) {
    els.loginError.textContent = "";
    els.loginError.classList.remove("success");
  }
}

async function loadSession() {
  const payload = await fetchJson("/api/session");
  state.authenticated = Boolean(payload.authenticated);
  state.user = payload.user || null;
  state.permissions = state.user?.permissions || [];
  if (state.authenticated) {
    hideLogin();
    if (els.operatorInput) els.operatorInput.value = state.user.displayName || state.user.username || "Scanner";
  }
  return payload;
}

async function login(username, password) {
  const payload = await fetchJson("/api/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
  state.authenticated = true;
  state.user = payload.user;
  state.permissions = payload.user?.permissions || [];
  hideLogin();
  if (els.loginPassword) els.loginPassword.value = "";
  if (els.operatorInput) els.operatorInput.value = state.user.displayName || state.user.username || "Scanner";
}

function showPasswordResetPanel(show = true) {
  if (!els.passwordResetPanel) return;
  els.passwordResetPanel.hidden = !show;
  if (els.loginForm) els.loginForm.hidden = Boolean(show);
  if (els.passwordResetMessage) {
    els.passwordResetMessage.textContent = "";
    els.passwordResetMessage.classList.remove("success");
  }
  if (show) {
    if (els.resetIdentityInput && els.loginUsername?.value) els.resetIdentityInput.value = els.loginUsername.value.trim();
    window.setTimeout(() => (els.resetIdentityInput || els.loginUsername)?.focus(), 30);
  } else {
    window.setTimeout(() => els.loginUsername?.focus(), 30);
  }
}

function setPasswordResetMessage(message, success = false) {
  if (!els.passwordResetMessage) return;
  els.passwordResetMessage.textContent = message;
  els.passwordResetMessage.classList.toggle("success", success);
}

async function requestPasswordResetCode() {
  const identity = els.resetIdentityInput?.value.trim() || "";
  if (!identity) throw new Error("Enter your BFS email or username first.");
  const payload = await fetchJson("/api/password-reset/request", {
    method: "POST",
    body: JSON.stringify({ identity }),
  });
  const codeText = payload.resetCode ? ` Reset code: ${payload.resetCode}` : "";
  setPasswordResetMessage(`${payload.message || "Reset request created."}${codeText}`, true);
  if (payload.resetCode && els.resetCodeInput) els.resetCodeInput.value = payload.resetCode;
  els.resetCodeInput?.focus();
}

async function confirmPasswordReset() {
  const identity = els.resetIdentityInput?.value.trim() || "";
  const resetCode = els.resetCodeInput?.value.trim() || "";
  const newPassword = els.resetNewPasswordInput?.value || "";
  if (!identity || !resetCode || !newPassword) throw new Error("Enter your identity, reset code, and new password.");
  const payload = await fetchJson("/api/password-reset/confirm", {
    method: "POST",
    body: JSON.stringify({ identity, resetCode, newPassword }),
  });
  if (els.loginUsername) els.loginUsername.value = identity;
  if (els.loginPassword) els.loginPassword.value = "";
  if (els.resetCodeInput) els.resetCodeInput.value = "";
  if (els.resetNewPasswordInput) els.resetNewPasswordInput.value = "";
  showPasswordResetPanel(false);
  if (els.loginError) {
    els.loginError.textContent = payload.message || "Password reset. You can sign in now.";
    els.loginError.classList.add("success");
  }
}

async function logout() {
  if (state.backend) {
    await fetchJson("/api/logout", { method: "POST", body: JSON.stringify({}) });
  }
  state.authenticated = false;
  state.user = null;
  state.permissions = [];
  stopPolling();
  showLogin("Signed out.");
}

function cleanBarcode(value) {
  return String(value || "")
    .replace(/\*/g, "")
    .replace(/[\r\n]/g, "")
    .trim()
    .split("")
    .filter((ch) => /[0-9a-z]/i.test(ch))
    .join("")
    .toUpperCase();
}

function digitsOnly(value) {
  return String(value || "").replace(/\D/g, "");
}

function inferredRoute(item) {
  const route = String(item.route || "").trim().toUpperCase();
  const text = [item.route, item.job, item.customer, item.product, item.processState, item.queueState].join(" ");
  if (/\bCPU[-\s]*(IT|INT)\b/i.test(text) || /\bIT[-\s]*CPU\b/i.test(text)) return "";
  if (/\bCPU[-\s]*AIR\b/i.test(text)) return "CPU";
  if (/\b(GNV|GREENVILLE)\b/i.test(text)) return "GNV";
  if (/\b(DTC|DELIVER\s+TO\s+CUSTOMER)\b/i.test(text)) return "DTC";
  if (/\b(INT|INDIAN\s+TRAIL)\b/i.test(text)) return "";
  if (route === "CPU" || /\bCPU\b/i.test(text)) return "CPU";
  if (["INT", "IT", "INDIAN TRAIL"].includes(route)) return "";
  return route;
}

function routeCategory(item) {
  const route = inferredRoute(item);
  if (route === "CPU") return "cpu";
  if (route === "GNV") return "greenville";
  if (route === "DTC") return "dtc";
  return "indian_trail";
}

function routeLabel(item) {
  const route = inferredRoute(item);
  if (route === "CPU") return "CPU";
  if (route === "GNV") return "GNV";
  if (route === "DTC") return "DTC";
  return "";
}

function isCpuItem(item) {
  return routeCategory(item) === "cpu";
}

function filterItemsForProfile(items, profile) {
  if (profile === "cpu") return items.filter(isCpuItem);
  if (profile === "indian_trail") return items.filter((item) => routeCategory(item) === "indian_trail");
  if (profile === "greenville") return items.filter((item) => routeCategory(item) === "greenville");
  if (profile === "dtc") return items.filter((item) => routeCategory(item) === "dtc");
  return items.slice();
}

function cloneItems(items) {
  const seen = new Map();
  return (items || []).map((item, index) => {
    const baseId = item.id || `${item.order}-${item.item}`;
    const count = seen.get(baseId) || 0;
    seen.set(baseId, count + 1);
    return {
      ...item,
      id: count ? `${baseId}-${count + 1}` : baseId,
      sourceId: baseId,
      lineIndex: index + 1,
      scanned: Number(item.scanned || 0),
      qty: Number(item.qty || 0),
      lastError: item.lastError || "",
    };
  });
}

function createDemoLists(payload) {
  const baseItems = payload.items || [];
  const definitions = [
    ["staging-airport", "Staging - Airport Rd", "Airport Rd", "all"],
    ["outbound-airport", "Outbound - Airport Rd", "Airport Rd", "all"],
    ["inbound-indian-trail", "Inbound - Indian Trail", "Indian Trail", "indian_trail"],
    ["bfs-greenville", "BFS Greenville", "Greenville", "greenville"],
    ["customer-pickup", "Customer Pickup", "Customer Pickup", "cpu"],
    ["dtc", "DTC - Deliver to Customer", "DTC", "dtc"],
  ];
  return definitions
    .map(([suffix, stage, scanner, profile]) => {
      const items = filterItemsForProfile(baseItems, profile);
      if (profile !== "all" && !items.length) return null;
      const cloned = cloneItems(items);
      const totalQty = cloned.reduce((sum, item) => sum + Number(item.qty || 0), 0);
      const scannedQty = cloned.reduce((sum, item) => sum + Number(item.scanned || 0), 0);
      return {
        id: `${payload.deliveryDate}-${suffix}`,
        label: `${formatDisplayDate(payload.deliveryDate)} - ${stage}`,
        deliveryDate: payload.deliveryDate,
        stage,
        scanner,
        itemCount: cloned.length,
        totalQty,
        scannedQty,
        deliveryPercent: totalQty ? (scannedQty / totalQty) * 100 : 0,
        onTimeQty: 0,
        lateQty: 0,
        onTimePercent: 0,
        items: cloned,
      };
    })
    .filter(Boolean);
}

function loadLocalStations() {
  try {
    const saved = JSON.parse(localStorage.getItem(STATIONS_KEY) || "[]");
    state.stations = uniqueText([...DEFAULT_STATIONS, ...saved]);
  } catch {
    state.stations = DEFAULT_STATIONS.slice();
  }
}

function saveLocalStations() {
  localStorage.setItem(STATIONS_KEY, JSON.stringify(state.stations));
}

function renderStationOptions(preferredStation = "") {
  if (!els.stationSelect) return;

  const assignedStations = userAssignedStations();
  const assignedStation = assignedStations[0] || "";
  const current = assignedStation || preferredStation || els.stationSelect.value || state.meta?.scanner || DEFAULT_STATIONS[0];

  state.stations = uniqueText([...DEFAULT_STATIONS, ...state.stations, ...assignedStations, current]);
  els.stationSelect.innerHTML = state.stations
    .map((station) => `<option value="${escapeHtml(station)}">${escapeHtml(station)}</option>`)
    .join("");
  els.stationSelect.value = state.stations.includes(current) ? current : state.stations[0];
  els.stationSelect.disabled = true;
  els.stationSelect.title = assignedStations.length
    ? `Assigned station${assignedStations.length === 1 ? "" : "s"}: ${assignedStations.join(", ")}`
    : "No assigned station on this login; using the selected delivery list default.";

  if (els.stationProfileDisplay) {
    const label = userAssignedStationLabel(state.user, current);
    els.stationProfileDisplay.textContent = label;
    els.stationProfileDisplay.title = els.stationSelect.title;
    els.stationProfileDisplay.classList.toggle("has-multiple", assignedStations.length > 1);
    els.stationProfileDisplay.classList.toggle("is-unassigned", !assignedStations.length);
  }
}

async function loadStations() {
  if (state.backend) {
    const payload = await fetchJson("/api/stations");
    state.stations = uniqueText([...DEFAULT_STATIONS, ...(payload.stations || [])]);
  } else {
    loadLocalStations();
  }
  renderStationOptions(state.meta?.scanner);
}

async function addStationFromInput() {
  const name = els.newStationInput?.value.trim() || "";
  if (!name) {
    els.newStationInput?.focus();
    return;
  }
  if (state.backend) {
    const payload = await fetchJson("/api/stations", {
      method: "POST",
      body: JSON.stringify({ name }),
    });
    state.stations = uniqueText([...DEFAULT_STATIONS, ...(payload.stations || [])]);
  } else {
    state.stations = uniqueText([...state.stations, name]);
    saveLocalStations();
  }
  if (els.newStationInput) els.newStationInput.value = "";
  renderStationOptions(name);
  renderAdminStations();
}

async function removeStation(name) {
  if (!state.backend) return;
  const payload = await fetchJson("/api/stations/remove", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
  state.stations = uniqueText([...DEFAULT_STATIONS, ...(payload.stations || [])]);
  renderStationOptions();
  renderAdminStations();
}

function applyBackendPayload(payload) {
  state.meta = payload.meta;
  state.activeListId = payload.meta.id;
  state.items = cloneItems(payload.items || []);
  state.recent = payload.recent || [];
  state.errors = payload.errors || [];
  state.lastScan = payload.lastScan || state.recent[0] || null;
  state.selectedId = state.lastScan?.item?.id || state.selectedId;
  renderStationOptions(payload.meta.scanner);
}

async function loadDeliveryLists(preferredListId = "") {
  if (state.backend) {
    const payload = await fetchJson("/api/delivery-lists");
    state.lists = payload.lists || [];
  }
  renderHome();
  renderDeliveryListSelect();
  if (preferredListId) {
    await activateList(preferredListId, false);
  }
}

function setActiveList(listId) {
  const nextList = state.lists.find((list) => list.id === listId) || state.lists[0];
  if (!nextList) return;
  state.activeListId = nextList.id;
  state.meta = {
    deliveryDate: nextList.deliveryDate,
    stage: nextList.stage,
    scanner: nextList.scanner,
    label: nextList.label,
  };
  state.items = cloneItems(nextList.items || []);
  state.recent = [];
  state.errors = [];
  state.selectedId = null;
  state.lastScan = null;
  restoreState();
  renderStationOptions(nextList.scanner);
}

async function activateList(listId, navigate = true) {
  if (!listId) return;
  const changingList = listId !== state.activeListId;
  if (state.backend) {
    const payload = await fetchJson(`/api/delivery-lists/${encodeURIComponent(listId)}`);
    applyBackendPayload(payload);
  } else {
    setActiveList(listId);
  }
  if (changingList) {
    // v39: Global search can seed the Scan page search after navigation.
    // For normal list switching, clear the previous list search so a stale order
    // number does not hide rows on the next delivery list.
    state.search = "";
    if (els.searchInput) els.searchInput.value = "";
  }
  if (changingList || navigate) {
    state.pageIndex = 1;
    state.glassTypeFilter = "all";
  }
  renderScanPage();
  if (navigate) showPage("scan");
  if (navigate || document.activeElement === els.scanInput) els.scanInput?.focus();
}

function storageKey() {
  return `${STORAGE_KEY}-${state.activeListId || "default"}`;
}

function saveState() {
  if (state.backend) return;
  const payload = {
    scanned: Object.fromEntries(state.items.map((item) => [item.id, item.scanned])),
    recent: state.recent,
    errors: state.errors,
    selectedId: state.selectedId,
    lastScan: state.lastScan,
  };
  localStorage.setItem(storageKey(), JSON.stringify(payload));
}

function restoreState() {
  if (state.backend) return;
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey()) || "{}");
    if (saved.scanned) {
      for (const item of state.items) {
        item.scanned = Math.min(Number(saved.scanned[item.id] || 0), item.qty);
      }
    }
    state.recent = Array.isArray(saved.recent) ? saved.recent.slice(0, 30) : [];
    state.errors = Array.isArray(saved.errors) ? saved.errors.slice(0, 30) : [];
    state.selectedId = saved.selectedId || null;
    state.lastScan = saved.lastScan || null;
  } catch {
    localStorage.removeItem(storageKey());
  }
}

function itemStatus(item) {
  if (item.scanned >= item.qty) return "complete";
  if (item.scanned > 0) return "partial";
  return "remaining";
}

function itemText(item) {
  return [item.product, item.job, item.customer, item.route, item.processState, item.queueState, item.suggestedBay].join(" ");
}

function isRemakeItem(item) {
  return /\b(REMAKE|RM)\b/i.test(`${item.processState || ""} ${item.queueState || ""}`);
}

function isRushItem(item) {
  return /\b(RUSH|SDI)\b/i.test(`${item.processState || ""} ${item.queueState || ""}`);
}

function isRemakeOrRush(item) {
  return isRemakeItem(item) || isRushItem(item);
}

function isNewOrUpdatedItem(item) {
  return /\b(NEW LINE|NEW|UPDATED|UPDATE|CHANGED|CHANGE)\b/i.test(`${item.processState || ""} ${item.queueState || ""}`);
}

function hasScanError(item) {
  return Boolean(String(item?.errorReason || item?.lastError || "").trim());
}

function itemPieceQty(item) {
  return Math.max(Number(item?.qty || 0), 0);
}

function itemScannedPieceQty(item) {
  return Math.min(Math.max(Number(item?.scanned || 0), 0), itemPieceQty(item));
}

function pieceCount(items) {
  return items.reduce((sum, item) => sum + itemPieceQty(item), 0);
}

function unscannedPieceCount(items) {
  return items.reduce((sum, item) => sum + Math.max(itemPieceQty(item) - itemScannedPieceQty(item), 0), 0);
}

function unresolvedPriorityItems(items = state.items) {
  return items.filter((item) => isRemakeOrRush(item) && itemStatus(item) !== "complete");
}

function unresolvedRemakeItems(items = state.items) {
  return items.filter((item) => isRemakeItem(item) && itemStatus(item) !== "complete");
}

function unresolvedRushItems(items = state.items) {
  return items.filter((item) => isRushItem(item) && itemStatus(item) !== "complete");
}

function scanFlash(kind = "notice") {
  const className = kind === "success" ? "scan-flash-success" : kind === "error" ? "scan-flash-error" : "scan-flash-notice";
  document.body.classList.remove("scan-flash-success", "scan-flash-error", "scan-flash-notice");
  void document.body.offsetWidth;
  document.body.classList.add(className);
  window.setTimeout(() => document.body.classList.remove(className), 900);
}

function getStats(items = state.items, errors = state.errors) {
  const totalQty = pieceCount(items);
  const scannedQty = items.reduce((sum, item) => sum + itemScannedPieceQty(item), 0);
  const remainingQty = Math.max(totalQty - scannedQty, 0);

  const remainingItems = pieceCount(items.filter((item) => itemStatus(item) === "remaining"));
  const partialItems = pieceCount(items.filter((item) => itemStatus(item) === "partial"));
  const completeItems = pieceCount(items.filter((item) => itemStatus(item) === "complete"));
  const errorCount = unscannedPieceCount(items.filter(hasScanError));

  const percent = totalQty ? (scannedQty / totalQty) * 100 : 0;

  return { totalQty, scannedQty, remainingQty, partialItems, completeItems, remainingItems, percent, errorCount };
}

function filteredItems() {
  const search = state.search.trim().toLowerCase();

  return state.items.filter((item) => {
    const status = itemStatus(item);
    const matchesFilter =
      state.filter === "all" ||
      state.filter === status ||
      (state.filter === "errors" && hasScanError(item)) ||
      (state.filter === "remakes" && isRemakeItem(item)) ||
      (state.filter === "rushes" && isRushItem(item)) ||
      (state.filter === "priority" && isRemakeOrRush(item)) ||
      (state.filter === "updated" && isNewOrUpdatedItem(item)) ||
      (state.filter === "cpu-route" && /\bCPU\b|customer pickup/i.test(`${item.route || ""} ${item.customer || ""} ${item.job || ""}`)) ||
      (state.filter === "dtc-route" && /\bDTC\b|deliver to customer/i.test(`${item.route || ""} ${item.customer || ""} ${item.job || ""}`)) ||
      (state.filter === "greenville-route" && /\bGNV\b|greenville/i.test(`${item.route || ""} ${item.customer || ""} ${item.job || ""}`)) ||
      (state.filter === "indian-trail-route" && !/\bCPU\b|\bDTC\b|\bGNV\b|customer pickup|deliver to customer|greenville/i.test(`${item.route || ""} ${item.customer || ""} ${item.job || ""}`));

    if (!matchesFilter) return false;
    if (state.glassTypeFilter !== "all" && glassTypeLabel(item) !== state.glassTypeFilter) return false;
    if (!search) return true;

    const haystack = [item.order, item.item, item.job, item.customer, item.dimensions, item.product, item.route, item.barcode]
      .join(" ")
      .toLowerCase();

    return haystack.includes(search);
  });
}

function groupItemsByGlass(items) {
  const groups = new Map();
  for (const item of items) {
    const label = glassTypeLabel(item);
    if (!groups.has(label)) groups.set(label, []);
    groups.get(label).push(item);
  }
  return [...groups.entries()].map(([label, items]) => ({ label, items }));
}

function getPagedItems() {
  const rows = filteredItems();
  const groups = groupItemsByGlass(rows);

  const orderedEntries = groups.flatMap((group) =>
    group.items.map((item) => ({
      label: group.label,
      item,
    })),
  );

  const totalPages = Math.max(1, Math.ceil(orderedEntries.length / state.pageSize));
  state.pageIndex = Math.min(Math.max(state.pageIndex, 1), totalPages);

  const pageStart = (state.pageIndex - 1) * state.pageSize;
  const pageEntries = orderedEntries.slice(pageStart, pageStart + state.pageSize);

  const pageGroups = [];
  for (const entry of pageEntries) {
    const lastGroup = pageGroups[pageGroups.length - 1];

    if (lastGroup && lastGroup.label === entry.label) {
      lastGroup.items.push(entry.item);
    } else {
      pageGroups.push({
        label: entry.label,
        items: [entry.item],
      });
    }
  }

  const pageRows = pageEntries.map((entry) => entry.item);
  return { rows, pageRows, pageGroups, totalPages };
}

function stageVerb() {
  const stage = String(state.meta?.stage || "").toLowerCase();
  if (stage.includes("indian trail") || stage.includes("inbound")) return "Received";
  if (stage.includes("outbound")) return "Outbound";
  if (stage.includes("customer pickup")) return "CPU";
  if (stage.includes("greenville")) return "Greenville";
  if (stage.includes("dtc") || stage.includes("deliver to customer")) return "Delivered";
  return "Staged";
}

function renderProcessState(item) {
  return `${stageVerb()}: ${item.scanned}/${item.qty}`;
}

function locationLabel(item) {
  const stageText = `${state.meta?.stage || ""} ${state.meta?.scanner || ""}`.toLowerCase();
  const rackCode = String(item.rackCode || "").trim().toUpperCase();
  if (stageText.includes("indian trail")) return item.bayCode ? `Bay ${item.bayCode}` : "";
  if (rackCode === "T" || /^T\d+$/i.test(rackCode) || /truck|no rack/i.test(`${item.rackName || ""} ${item.rackType || ""}`)) {
    return rackCode === "T" ? "Truck" : `Truck ${rackCode.replace(/^T/i, "")}`;
  }
  if (rackCode) return rackCode;
  return "";
}

function clearSelectedLineItem(render = true) {
  if (!state.selectedId) return;
  state.selectedId = null;
  saveState();
  if (render) renderScanPage();
}

function canAssignRackLocation() {
  const roles = state.user?.roles || [];
  return Boolean(
    state.backend &&
      isStagingScanContext() &&
      (hasPermission("manage_racks") || roles.includes("Admin") || roles.includes("Supervisor")),
  );
}

function rackStatusValue(rack) {
  return String(rack?.status || "").trim().toLowerCase();
}

function rackIsLockedForLineAssignment(rack) {
  return ["closed", "complete", "completed", "in transit", "on the way"].includes(rackStatusValue(rack));
}

function rackForCode(code) {
  const cleanCode = String(code || "").trim().toUpperCase();
  if (!cleanCode) return null;
  return (state.racks || []).find((rack) => String(rack.code || "").trim().toUpperCase() === cleanCode) || null;
}

function itemCanShowRackLocationDropdown(item) {
  if (!canAssignRackLocation() || item.id !== state.selectedId) return false;
  if (itemScannedPieceQty(item) <= 0) return false;

  const currentRackCode = String(item.rackCode || "").trim();
  if (!currentRackCode) return true;

  const currentRack = rackForCode(currentRackCode);
  return !currentRack || !rackIsLockedForLineAssignment(currentRack);
}

function locationBadgeClass(location) {
  return `location-badge ${
    location.toLowerCase().includes("bay")
      ? "bay"
      : location.toLowerCase().includes("truck")
        ? "truck"
        : "rack"
  }`;
}

function rackLocationDropdown(item, currentLocation = "") {
  if (!itemCanShowRackLocationDropdown(item)) {
    return currentLocation ? `<span class="${escapeHtml(locationBadgeClass(currentLocation))}">${escapeHtml(currentLocation)}</span>` : "";
  }

  const currentRackCode = String(item.rackCode || "").trim().toUpperCase() === "T" ? "T" : String(item.rackCode || "").trim();
  const assignableRacks = (state.racks || []).filter((rack) => !rackIsLockedForLineAssignment(rack));
  const rackOptions = groupedRackOptionsHtml(assignableRacks, currentRackCode);

  return `
    <label class="line-rack-location-control" title="Supervisor/Admin rack recovery assignment">
      <span>Rack</span>
      <select data-line-rack-select="${escapeHtml(item.id)}" ${rackOptions ? "" : "disabled"}>
        <option value="">${rackOptions ? "No rack" : "Loading racks..."}</option>
        ${rackOptions}
      </select>
    </label>
  `;
}

function renderCounts() {
  const stats = getStats();
  const totalItems = pieceCount(state.items);
  const glassCounts = new Map();
  for (const item of state.items) {
    const label = glassTypeLabel(item);
    glassCounts.set(label, (glassCounts.get(label) || 0) + Number(item.qty || 0));
  }

  const remakeItems = state.items.filter(isRemakeItem);
  const rushItems = state.items.filter(isRushItem);
  const updatedItems = state.items.filter(isNewOrUpdatedItem);

  const remakeOpen = unscannedPieceCount(remakeItems);
  const remakeAll = pieceCount(remakeItems);
  const rushOpen = unscannedPieceCount(rushItems);
  const rushAll = pieceCount(rushItems);
  const updatedCount = pieceCount(updatedItems);

  const routeCounts = {
    "indian-trail-route": pieceCount(state.items.filter((item) => !/\bCPU\b|\bDTC\b|\bGNV\b|customer pickup|deliver to customer|greenville/i.test(`${item.route || ""} ${item.customer || ""} ${item.job || ""}`))),
    "cpu-route": pieceCount(state.items.filter((item) => /\bCPU\b|customer pickup/i.test(`${item.route || ""} ${item.customer || ""} ${item.job || ""}`))),
    "dtc-route": pieceCount(state.items.filter((item) => /\bDTC\b|deliver to customer/i.test(`${item.route || ""} ${item.customer || ""} ${item.job || ""}`))),
    "greenville-route": pieceCount(state.items.filter((item) => /\bGNV\b|greenville/i.test(`${item.route || ""} ${item.customer || ""} ${item.job || ""}`))),
  };
  if (els.countAll) els.countAll.textContent = `(${totalItems})`;
  if (els.countRemaining) els.countRemaining.textContent = `(${stats.remainingItems})`;
  if (els.countPartial) els.countPartial.textContent = `(${stats.partialItems})`;
  if (els.countComplete) els.countComplete.textContent = `(${stats.completeItems})`;
  if (els.countRemakes) els.countRemakes.textContent = `(${remakeAll})`;
  if (els.countRushes) els.countRushes.textContent = `(${rushAll})`;
  document.querySelectorAll('[data-filter="remakes"]').forEach((button) => {
    button.classList.toggle("has-alert", Boolean(remakeOpen));
    button.classList.toggle("is-clear", !remakeOpen);
  });
  document.querySelectorAll('[data-filter="rushes"]').forEach((button) => {
    button.classList.toggle("has-alert", Boolean(rushOpen));
    button.classList.toggle("is-clear", !rushOpen);
  });
  if (els.countUpdated) els.countUpdated.textContent = `(${updatedCount})`;
  if (els.countErrors) els.countErrors.textContent = `(${stats.errorCount})`;

  document.querySelectorAll('[data-filter="errors"]').forEach((button) => {
    button.classList.toggle("has-alert", Boolean(stats.errorCount));
  });

  if (els.countIndianTrailRoute) els.countIndianTrailRoute.textContent = `(${routeCounts["indian-trail-route"]})`;
  if (els.countCpuRoute) els.countCpuRoute.textContent = `(${routeCounts["cpu-route"]})`;
  if (els.countDtcRoute) els.countDtcRoute.textContent = `(${routeCounts["dtc-route"]})`;
  if (els.countGreenvilleRoute) els.countGreenvilleRoute.textContent = `(${routeCounts["greenville-route"]})`;
  document.querySelectorAll(".route-filter-tab").forEach((button) => {
    const count = routeCounts[button.dataset.filter] || 0;
    button.hidden = count === 0;
  });
  if (state.filter.endsWith("-route") && !routeCounts[state.filter]) {
    state.filter = "all";
    document.querySelectorAll("[data-filter]").forEach((button) => button.classList.toggle("is-active", button.dataset.filter === state.filter));
  }
  if (state.glassTypeFilter !== "all" && !glassCounts.has(state.glassTypeFilter)) state.glassTypeFilter = "all";
  if (els.glassFilterTabs) {
    const sortedGlassEntries = [...glassCounts.entries()].sort(
      (a, b) => Number(b[1] || 0) - Number(a[1] || 0) || a[0].localeCompare(b[0]),
    );

    const visibleGlassEntries = sortedGlassEntries.slice(0, 3);
    const hiddenGlassEntries = sortedGlassEntries.slice(3);
    const selectedHiddenGlass = hiddenGlassEntries.find(([label]) => label === state.glassTypeFilter);
    const selectedHiddenCount = selectedHiddenGlass ? selectedHiddenGlass[1] : 0;

    const visibleGlassButtons = visibleGlassEntries.map(
      ([label, count]) =>
        `<button class="tab glass-filter-tab ${state.glassTypeFilter === label ? "is-active" : ""}" data-glass-filter="${escapeHtml(label)}" type="button">${escapeHtml(label)} <span>(${escapeHtml(count)})</span></button>`,
    );

    const moreGlassButton = hiddenGlassEntries.length
      ? `
        <details class="glass-filter-more">
          <summary class="tab glass-filter-tab glass-filter-more-summary ${selectedHiddenGlass ? "is-active" : ""}">
            ${selectedHiddenGlass ? escapeHtml(state.glassTypeFilter) : "More Glass Types"}
            <span>${selectedHiddenGlass ? `(${escapeHtml(selectedHiddenCount)})` : `+${hiddenGlassEntries.length}`}</span>
          </summary>
          <div class="glass-filter-menu">
            ${hiddenGlassEntries
              .map(
                ([label, count]) =>
                  `<button class="tab glass-filter-tab ${state.glassTypeFilter === label ? "is-active" : ""}" data-glass-filter="${escapeHtml(label)}" type="button">${escapeHtml(label)} <span>(${escapeHtml(count)})</span></button>`,
              )
              .join("")}
          </div>
        </details>
      `
      : "";

    const glassButtons = [
      `<button class="tab glass-filter-tab ${state.glassTypeFilter === "all" ? "is-active" : ""}" data-glass-filter="all" type="button">All Glass <span>(${totalItems})</span></button>`,
      ...visibleGlassButtons,
      moreGlassButton,
    ];

    els.glassFilterTabs.innerHTML = glassButtons.join("");
  }
  if (els.totalItemsText) els.totalItemsText.textContent = `${state.items.length} rows / ${totalItems} pieces`;
  if (els.progressText) els.progressText.textContent = `${stageVerb()} Qty: ${stats.scannedQty}/${stats.totalQty} - ${formatPercent(stats.percent)} Complete`;
  if (els.progressFill) els.progressFill.style.width = `${Math.min(stats.percent, 100)}%`;
  if (els.remainingQty) els.remainingQty.textContent = String(stats.remainingQty);
  if (els.partialQty) els.partialQty.textContent = String(stats.partialItems);
  if (els.completeQty) els.completeQty.textContent = String(stats.completeItems);
  if (els.errorQty) els.errorQty.textContent = String(stats.errorCount);
  if (els.remainingPct) els.remainingPct.textContent = formatPercent(100 - stats.percent);
  if (els.partialPct) els.partialPct.textContent = formatPercent(stats.totalQty ? (stats.partialItems / stats.totalQty) * 100 : 0);
  if (els.completePct) els.completePct.textContent = formatPercent(stats.percent);
}

function renderPagers(totalRows, totalPages) {
  if (els.pageSize && Number(els.pageSize.value) !== state.pageSize) els.pageSize.value = String(state.pageSize);
  if (els.pageSizeBottom && Number(els.pageSizeBottom.value) !== state.pageSize) els.pageSizeBottom.value = String(state.pageSize);
  const render = () => {
    const buttons = [];
    buttons.push(`<button type="button" data-page-action="prev" ${state.pageIndex <= 1 ? "disabled" : ""}>&lt;</button>`);
    const pages = [];
    for (let page = 1; page <= totalPages; page += 1) {
      if (page === 1 || page === totalPages || Math.abs(page - state.pageIndex) <= 2) {
        pages.push(page);
      }
    }
    let previous = 0;
    for (const page of pages) {
      if (page - previous > 1) buttons.push("<span>...</span>");
      buttons.push(`<button type="button" data-page-number="${page}" class="${page === state.pageIndex ? "is-active" : ""}">${page}</button>`);
      previous = page;
    }
    buttons.push(`<button type="button" data-page-action="next" ${state.pageIndex >= totalPages ? "disabled" : ""}>&gt;</button>`);
    buttons.push(`<span class="pager-summary">${totalRows} rows</span>`);
    return `<div class="pager">${buttons.join("")}</div>`;
  };
  if (els.scanPagerTop) els.scanPagerTop.innerHTML = render();
  if (els.scanPagerBottom) els.scanPagerBottom.innerHTML = render();
}

function glassTypeLabel(item) {
  return String(item.product || item.job || item.suggestedBay || "Other Glass").trim() || "Other Glass";
}

function renderItemRow(item) {
  const status = itemStatus(item);
  const selected = item.id === state.selectedId;
  const route = routeLabel(item);
  const routeTag = route
    ? `<span class="route-tag ${escapeHtml(route.toLowerCase())}">${escapeHtml(route)}</span>`
    : "";
  const location = locationLabel(item);
  const locationHtml = rackLocationDropdown(item, location);

  const markers = [
    isRemakeItem(item) ? '<span class="row-marker remake-marker">RM</span>' : "",
    isRushItem(item) ? '<span class="row-marker rush-marker">Rush</span>' : "",
  ]
    .filter(Boolean)
    .join("");

  const rowError = hasScanError(item);
  const processClass = rowError ? "error" : status;
  const processText = rowError ? item.errorReason || item.lastError || "Scan issue" : renderProcessState(item);
  const lastScanNote = item.lastScannedAt
    ? `<span class="last-scan-note">Scanned: ${escapeHtml(formatDateTime(item.lastScannedAt))}${item.lastScannedStation ? ` - ${escapeHtml(item.lastScannedStation)}` : ""}</span>`
    : "";

  return `
    <tr class="${selected ? "is-selected" : ""} ${status === "complete" ? "is-complete" : ""} ${isNewOrUpdatedItem(item) ? "is-new-line" : ""}" data-id="${escapeHtml(item.id)}">
      <td><span class="job-title">${escapeHtml(item.product || item.job)}</span><span class="job-subtitle">${escapeHtml(item.job)}</span>${lastScanNote}</td>
      <td>${escapeHtml(item.order)}</td>
      <td>${escapeHtml(item.item)}</td>
      <td><span class="qty-pill ${status}">${item.scanned} / ${item.qty}</span></td>
      <td>${escapeHtml(item.dimensions)}</td>
      <td>${escapeHtml(item.customer)}</td>
      <td>${markers}</td>
      <td>${routeTag}</td>
      <td class="location-cell">${locationHtml}</td>
      <td><span class="process-pill ${processClass}">${escapeHtml(processText)}</span></td>
    </tr>
  `;
}

function renderTable() {
  if (!els.listRows) return;
  const { rows, pageGroups, totalPages } = getPagedItems();
  renderPagers(rows.length, totalPages);
  if (!pageGroups.length) {
    els.listRows.innerHTML = `<tr><td colspan="10">No rows match the current filters.</td></tr>`;
    return;
  }
  els.listRows.innerHTML = pageGroups
    .map(({ label, items: groupItems }) => {
      const totalQty = groupItems.reduce((sum, item) => sum + Number(item.qty || 0), 0);
      const scannedQty = groupItems.reduce((sum, item) => sum + Math.min(Number(item.scanned || 0), Number(item.qty || 0)), 0);
      const updatedCount = groupItems.filter(isNewOrUpdatedItem).length;
      const collapsed = state.collapsedGlassTypes.has(label);
      return `
        <tr class="glass-group-row" data-glass-group="${escapeHtml(label)}">
          <td colspan="10">
            <button type="button" data-toggle-glass-group="${escapeHtml(label)}">
              <strong>${escapeHtml(label)}${updatedCount ? ` <span class="new-line-marker group-marker" title="New or updated lines">${escapeHtml(updatedCount)} New</span>` : ""}</strong>
              <span>${escapeHtml(scannedQty)} / ${escapeHtml(totalQty)} pieces</span>
              <small>${collapsed ? "Expand" : "Collapse"}</small>
            </button>
          </td>
        </tr>
        ${collapsed ? "" : groupItems.map(renderItemRow).join("")}
      `;
    })
    .join("");
}

function stagingLists() {
  return state.lists.filter((list) => /staging/i.test(`${list.stage || ""} ${list.label || ""}`));
}

async function refreshRacksPage() {
  if (!hasAnyPermission(["view_racks", "scan_racks", "manage_racks"])) return;
  if (state.backend) {
    const payload = await fetchJson("/api/racks");
    state.racks = payload.racks || [];
    state.rackSummary = payload.summary || null;
  }
  renderRacksPage();
}

function renderRackSelects() {
  const stageLists = stagingLists();
  if (!state.rackScanListId || !stageLists.some((list) => list.id === state.rackScanListId)) {
    state.rackScanListId = stageLists[0]?.id || "";
  }
  if (!state.selectedRackCode || !state.racks.some((rack) => rack.code === state.selectedRackCode)) {
    state.selectedRackCode = state.racks.find((rack) => rack.code === "T")?.code || state.racks[0]?.code || "";
  }
  if (els.rackListSelect) {
    els.rackListSelect.innerHTML = stageLists
      .map((list) => `<option value="${escapeHtml(list.id)}">${escapeHtml(formatDisplayDate(list.deliveryDate))} - ${escapeHtml(list.stage)}</option>`)
      .join("");
    els.rackListSelect.value = state.rackScanListId;
  }
  if (els.rackSelect) {
    els.rackSelect.innerHTML = groupedRackOptionsHtml(state.racks, state.selectedRackCode);
    els.rackSelect.value = state.selectedRackCode;
    syncCustomSelect(els.rackSelect);
  }
}

function rackGroupLabel(rack) {
  return rack.code === "T" || /truck/i.test(rack.type || "") ? "Truck" : rack.type || "Racks";
}

function groupedRackOptionsHtml(racks = [], selectedCode = "") {
  const groups = new Map();
  for (const rack of racks) {
    const label = rackGroupLabel(rack);
    if (!groups.has(label)) groups.set(label, []);
    groups.get(label).push(rack);
  }

  const groupEntries = [...groups.entries()].sort(([labelA], [labelB]) => {
    if (labelA === "Truck") return -1;
    if (labelB === "Truck") return 1;
    return labelA.localeCompare(labelB, undefined, { numeric: true, sensitivity: "base" });
  });

  return groupEntries
    .map(([label, groupRacks]) => `
      <optgroup label="${escapeHtml(label)}">
        ${groupRacks
          .slice()
          .sort((rackA, rackB) => String(rackA.code || "").localeCompare(String(rackB.code || ""), undefined, { numeric: true, sensitivity: "base" }))
          .map((rack) => `<option value="${escapeHtml(rack.code)}" ${String(rack.code) === String(selectedCode) ? "selected" : ""}>${rackOptionLabel(rack)}</option>`)
          .join("")}
      </optgroup>
    `)
    .join("");
}

function isTruckRack(rack) {
  return Boolean(rack && (rack.code === "T" || /^T\d+$/i.test(String(rack.code || "")) || /truck/i.test(rack.type || "")));
}

function nextTruckRackDefaults() {
  const truckRacks = (state.racks || []).filter(isTruckRack);
  const usedCodes = new Set(truckRacks.map((rack) => String(rack.code || "").toUpperCase()));
  let number = 2;
  while (usedCodes.has(`T${number}`)) number += 1;
  return {
    code: `T${number}`,
    name: `Truck ${number}`,
    type: "Truck",
  };
}

function rackOptionLabel(rack) {
  const code = String(rack?.code || "").trim() || "Rack";
  const qty = Number(rack?.qty || 0);
  const lower = String(rack?.status || "Open").toLowerCase();
  const stateText = lower === "in transit" ? "On the way" : lower === "closed" ? "Complete" : qty ? "Open" : "Empty";
  const qtyText = qty ? ` ${qty}pcs` : "";
  return `${escapeHtml(code)}${escapeHtml(qtyText)} (${escapeHtml(stateText)})`;
}

function rackDestinationLabel(value) {
  const text = String(value || "Indian Trail").trim();
  if (/^cpu$/i.test(text)) return "CPU";
  if (/^dtc$/i.test(text)) return "DTC";
  if (/green|gnv/i.test(text)) return "Greenville";
  if (/indian|trail|^it$/i.test(text)) return "Indian Trail";
  return text || "Indian Trail";
}

function rackDestinationClass(value) {
  const text = rackDestinationLabel(value).toLowerCase();
  if (text.includes("cpu")) return "cpu";
  if (text.includes("green")) return "greenville";
  if (text.includes("dtc")) return "dtc";
  return "indian-trail";
}

function rackVisualClass(rack) {
  const status = String(rack.status || "").toLowerCase();
  if (status === "in transit") return "is-in-transit";
  if (status === "closed") return "is-complete";
  if (Number(rack.qty || 0) > 0) return "has-items";
  return "is-empty";
}

function rackComputedStatus(rack) {
  const status = String(rack?.status || "").toLowerCase();
  const qty = Number(rack?.qty || 0);

  if (status === "in transit") return "in-transit";
  if (status === "closed") return "complete";
  if (qty > 0) return "open";
  return "empty";
}

function rackSortNumber(value) {
  const match = String(value || "").match(/\d+/);
  return match ? Number(match[0]) : 0;
}

function filteredSortedRacks(racks = []) {
  const statusFilter = state.rackStatusFilter || "all";
  const sortMode = state.rackSort || "code-asc";

  const filtered = racks.filter((rack) => statusFilter === "all" || rackComputedStatus(rack) === statusFilter);

  return filtered.slice().sort((a, b) => {
    if (sortMode === "code-desc") {
      return String(b.code || "").localeCompare(String(a.code || ""), undefined, { numeric: true });
    }

    if (sortMode === "pieces-desc") {
      return Number(b.qty || 0) - Number(a.qty || 0) || String(a.code || "").localeCompare(String(b.code || ""), undefined, { numeric: true });
    }

    if (sortMode === "status") {
      const order = { open: 1, complete: 2, "in-transit": 3, empty: 4 };
      return (order[rackComputedStatus(a)] || 9) - (order[rackComputedStatus(b)] || 9) || String(a.code || "").localeCompare(String(b.code || ""), undefined, { numeric: true });
    }

    return String(a.code || "").localeCompare(String(b.code || ""), undefined, { numeric: true });
  });
}

function renderRacksPage() {
  renderRackSelects();

  const summary = state.rackSummary || {};

  if (els.rackSummary) {
    els.rackSummary.innerHTML = [
      miniStat("Rack Pieces", summary.rackQty || 0),
      miniStat("Truck Pieces", summary.truckQty || 0),
      miniStat("Active Racks", summary.rackCount || 0),
    ].join("");
  }

  if (!els.rackGrid) return;

  const rackGroups = new Map();

  for (const rack of state.racks) {
    const label = rack.code === "T" || /truck/i.test(rack.type) ? "Truck" : rack.type || "Racks";

    if (!rackGroups.has(label)) {
      rackGroups.set(label, []);
    }

    rackGroups.get(label).push(rack);
  }

  const groups = [...rackGroups.entries()].sort(([a], [b]) => {
    if (a === "Truck") return 1;
    if (b === "Truck") return -1;

    const order = { Steel: 1, Wood: 2 };
    return (order[a] || 50) - (order[b] || 50) || a.localeCompare(b);
  });

  const renderRackItem = (item, currentRackCode = "") => {
    const rackItemId = String(item.rackItemId || "");
    const moveOpen = state.rackMoveItemId === rackItemId;

    const destinationOptions = state.racks
      .filter((target) => target.code !== currentRackCode)
      .map((target) => `<option value="${escapeHtml(target.code)}">${rackOptionLabel(target)}</option>`)
      .join("");

    return `
      <article class="rack-item ${moveOpen ? "is-moving" : ""}">
        <div>
          <strong>${escapeHtml(item.order)}-${escapeHtml(item.item)} <span>${escapeHtml(item.customer || "")}</span></strong>
          <small>${escapeHtml(item.job || item.product || "")}</small>
          <small>${escapeHtml(item.product || item.job || "")} | ${escapeHtml(item.dimensions || "")} | Qty ${escapeHtml(item.rackQty || 1)}</small>
          <small class="rack-scan-time">${escapeHtml(item.deliveryLabel || "")}${item.rackAddedAt ? ` | Scanned ${escapeHtml(formatDateTime(item.rackAddedAt))}` : ""}</small>
        </div>

        ${
          hasPermission("manage_racks")
            ? `<div class="rack-item-actions">
                <button
                  type="button"
                  class="icon-only icon-move"
                  data-rack-move-open="${escapeHtml(rackItemId)}"
                  title="Move piece"
                  aria-label="Move ${escapeHtml(item.order)}-${escapeHtml(item.item)}"
                ></button>
                <button
                  type="button"
                  class="icon-only icon-trash danger"
                  data-rack-clear-item="${escapeHtml(rackItemId)}"
                  data-rack-clear-label="${escapeHtml(`${item.order}-${item.item}`)}"
                  title="Clear piece"
                  aria-label="Clear ${escapeHtml(item.order)}-${escapeHtml(item.item)}"
                ></button>
              </div>

              ${
                moveOpen
                  ? `<div class="rack-move-popover">
                      <div class="rack-move-title">
                        <strong>Move Piece</strong>
                        <span>${escapeHtml(item.order)}-${escapeHtml(item.item)}</span>
                      </div>

                      <label>
                        <span>Move to</span>
                        <select data-rack-target="${escapeHtml(rackItemId)}">
                          <option value="">Select destination...</option>
                          ${destinationOptions}
                        </select>
                      </label>

                      <div class="rack-move-actions">
                        <button type="button" class="rack-move-cancel" data-rack-move-cancel="${escapeHtml(rackItemId)}">Cancel</button>
                        <button type="button" class="rack-move-confirm" data-rack-move="${escapeHtml(rackItemId)}" ${destinationOptions ? "" : "disabled"}>Confirm Move</button>
                      </div>
                    </div>`
                  : ""
              }`
            : ""
        }
      </article>
    `;
  };

  const renderRackItems = (rack) => {
    const items = rack.items || [];

    if (!items.length) {
      return `<p class="admin-empty">No pieces assigned.</p>`;
    }

    const isTruck = rack.code === "T" || /truck/i.test(rack.type || "");
    const rackState = String(rack.status || "").toLowerCase();
    const isComplete = rackState === "closed" || rackState === "in transit";

    if (!isTruck) {
      return items.map((item) => renderRackItem(item, rack.code)).join("");
    }

    const byDate = new Map();

    for (const item of items) {
      const key = item.deliveryDate || "No delivery date";

      if (!byDate.has(key)) {
        byDate.set(key, []);
      }

      byDate.get(key).push(item);
    }

    return [...byDate.entries()]
      .sort(([a], [b]) => String(a).localeCompare(String(b)))
      .map(([date, dateItems]) => {
        const dateHasMoveOpen = dateItems.some((item) => String(item.rackItemId || "") === state.rackMoveItemId);
        const dateQty = dateItems.reduce((sum, item) => sum + Number(item.rackQty || 1), 0);

        return `
          <details class="rack-date-group" ${dateHasMoveOpen ? "open" : ""}>
            <summary>
              <strong>${escapeHtml(formatDisplayDate(date))}</strong>
              <span>${escapeHtml(dateQty)} pcs</span>
              ${isComplete ? `<button type="button" data-rack-print="${escapeHtml(rack.code)}" data-rack-print-date="${escapeHtml(date)}">Print This Date</button>` : ""}
            </summary>
            <div>${dateItems.map((item) => renderRackItem(item, rack.code)).join("")}</div>
          </details>
        `;
      })
      .join("");
  };

  const renderRack = (rack) => {
    const hasItems = Number(rack.qty || 0) > 0;
    const isTruck = rack.code === "T" || /truck/i.test(rack.type || "");
    const rackState = String(rack.status || "").toLowerCase();
    const isComplete = rackState === "closed";
    const isInTransit = rackState === "in transit";
    const rackHasMoveOpen = (rack.items || []).some((item) => String(item.rackItemId || "") === state.rackMoveItemId);
    const rackOpen = state.expandedRackCodes.has(rack.code) || rackHasMoveOpen;

    const adminActions = hasPermission("manage_racks")
      ? `<span class="rack-summary-actions">
          <button
            type="button"
            class="icon-only icon-pencil"
            data-rack-edit="${escapeHtml(rack.code)}"
            title="Edit rack"
            aria-label="Edit ${escapeHtml(rack.code)}"
          ></button>
          <button
            type="button"
            class="icon-only icon-trash danger"
            data-rack-clear="${escapeHtml(rack.code)}"
            title="Clear rack"
            aria-label="Clear ${escapeHtml(rack.code)}"
          ></button>
        </span>`
      : "";

    const printLabel = isTruck ? "Print Truck Packing List" : "Print Packing List";
    const printAction =
      hasItems && (isComplete || isInTransit)
        ? `<button type="button" data-rack-print="${escapeHtml(rack.code)}">${printLabel}</button>`
        : "";

    return `
      <details class="rack-card ${rackVisualClass(rack)}" data-rack-code="${escapeHtml(rack.code)}" ${rackOpen ? "open" : ""}>
        <summary>
          <span class="rack-summary-main">
            <strong>${escapeHtml(rack.code)}</strong>
            <small>${escapeHtml(rack.name)}</small>
          </span>
          <span class="rack-summary-qty">${escapeHtml(rack.qty || 0)} pcs</span>
          ${adminActions}
        </summary>
        <div class="rack-card-actions">
          ${
            hasItems
              ? `${printAction}${
                  isInTransit
                    ? `<button type="button" data-rack-return="${escapeHtml(rack.code)}">Mark Returned</button><button type="button" data-rack-not-on-way="${escapeHtml(rack.code)}">Not On The Way</button>`
                    : isComplete
                      ? `<button type="button" data-rack-uncomplete="${escapeHtml(rack.code)}">Uncomplete Rack</button>`
                      : `<button type="button" data-rack-complete="${escapeHtml(rack.code)}">Complete Rack</button>`
                }`
              : ""
          }
        </div>
        <div class="rack-item-list">
          ${hasItems ? renderRackItems(rack) : `<p class="admin-empty">No pieces assigned.</p>`}
        </div>
      </details>
    `;
  };

  const renderRackColumnActions = (label) => {
    if (!hasPermission("manage_racks")) return "";

    if (label === "Truck") {
      return `
        <div class="rack-column-actions">
          <button
            type="button"
            class="icon-only icon-pencil light"
            data-rack-edit="T"
            title="Edit truck / no rack"
            aria-label="Edit truck / no rack"
          ></button>
        </div>
      `;
    }

    return `
      <div class="rack-column-actions">
        <button
          type="button"
          class="icon-only icon-pencil light"
          data-rack-set-edit="${escapeHtml(label)}"
          title="Edit rack set"
          aria-label="Edit ${escapeHtml(label)} rack set"
        ></button>
      </div>
    `;
  };

  const rackStatusText = (rack) => {
    const status = String(rack.status || "").toLowerCase();
    const qty = Number(rack.qty || 0);

    if (status === "in transit") return "On the way";
    if (status === "closed") return "Complete";
    if (qty > 0) return "Open";
    return "Empty";
  };

  const rackStatusClass = (rack) => {
    const status = String(rack.status || "").toLowerCase();
    const qty = Number(rack.qty || 0);

    if (status === "in transit") return "in-transit";
    if (status === "closed") return "complete";
    if (qty > 0) return "open";
    return "empty";
  };

  const renderRackBoardCard = (rack) => {
    const selected = state.selectedRackOverviewCode === rack.code;
    const statusText = rackStatusText(rack);
    const statusClass = rackStatusClass(rack);
    const isTruck = rack.code === "T" || /truck/i.test(rack.type || "");
    const destinationPill = rack.destination
      ? `<small class="rack-destination-pill ${escapeHtml(rackDestinationClass(rack.destination))}">${escapeHtml(rackDestinationLabel(rack.destination))}</small>`
      : "";

    return `
      <article
        class="rack-board-card ${rackVisualClass(rack)} ${selected ? "is-selected" : ""}"
        data-rack-select="${escapeHtml(rack.code)}"
        tabindex="0"
        role="button"
        aria-label="View ${escapeHtml(isTruck ? "Truck" : rack.code)} details"
      >
        ${destinationPill}
        <div class="rack-board-card-main">
          <strong>${escapeHtml(isTruck ? "Truck" : rack.code)}</strong>
          <span>${escapeHtml(rack.name || rack.type || "")}</span>
        </div>

        <div class="rack-board-card-meta">
          <b>${escapeHtml(rack.qty || 0)} pcs</b>
          <small class="rack-status-badge ${escapeHtml(statusClass)}">${escapeHtml(statusText)}</small>
          ${
            hasPermission("manage_racks")
              ? `<button type="button" class="icon-only icon-reset" data-rack-clear="${escapeHtml(rack.code)}" title="Clear rack" aria-label="Clear ${escapeHtml(rack.code)}"></button>`
              : ""
          }
        </div>
      </article>
    `;
  };

  const renderRackBoardGroup = ([label, racks]) => {
    const totalQty = racks.reduce((sum, rack) => sum + Number(rack.qty || 0), 0);
    const activeCount = racks.filter((rack) => Number(rack.qty || 0) > 0).length;
    const completeCount = racks.filter((rack) => String(rack.status || "").toLowerCase() === "closed").length;

    return `
      <section class="rack-board-group" data-rack-group="${escapeHtml(label)}">
        <header class="rack-board-group-header">
          <div>
            <h2>${escapeHtml(label)}</h2>
            <span>${escapeHtml(racks.length)} ${racks.length === 1 ? "rack" : "racks"} | ${escapeHtml(activeCount)} active | ${escapeHtml(completeCount)} complete</span>
          </div>

          <strong>${escapeHtml(totalQty)} pcs</strong>

          ${renderRackColumnActions(label)}
          ${
            hasPermission("manage_racks")
              ? `<button type="button" class="icon-only icon-reset light" data-rack-set-clear="${escapeHtml(label)}" title="Clear rack set" aria-label="Clear ${escapeHtml(label)} rack set"></button>`
              : ""
          }
        </header>

        <div class="rack-board-card-list">
          ${racks.map(renderRackBoardCard).join("") || `<p class="admin-empty">No ${escapeHtml(label.toLowerCase())} racks.</p>`}
        </div>
      </section>
    `;
  };

  const groupLabels = groups.map(([label]) => label);
  if (!state.selectedRackSetLabel || !groupLabels.includes(state.selectedRackSetLabel)) {
    state.selectedRackSetLabel = groupLabels.find((label) => label !== "Truck") || groupLabels[0] || "";
  }

  const selectedGroup = groups.find(([label]) => label === state.selectedRackSetLabel) || groups[0] || ["", []];
  const selectedGroupLabel = selectedGroup[0];
  const selectedGroupAllRacks = selectedGroup[1] || [];
  const selectedGroupRacks = filteredSortedRacks(selectedGroupAllRacks);

  if (!state.selectedRackOverviewCode || !selectedGroupAllRacks.some((rack) => rack.code === state.selectedRackOverviewCode)) {
    state.selectedRackOverviewCode =
      selectedGroupRacks.find((rack) => Number(rack.qty || 0) > 0)?.code ||
      selectedGroupRacks[0]?.code ||
      selectedGroupAllRacks.find((rack) => Number(rack.qty || 0) > 0)?.code ||
      selectedGroupAllRacks[0]?.code ||
      state.racks.find((rack) => Number(rack.qty || 0) > 0)?.code ||
      state.racks[0]?.code ||
      "";
  }

  const selectedRack = state.racks.find((rack) => rack.code === state.selectedRackOverviewCode) || selectedGroupRacks[0] || state.racks[0] || null;

  const renderRackSetCard = ([label, racks]) => {
    const selected = label === selectedGroupLabel;
    const totalQty = racks.reduce((sum, rack) => sum + Number(rack.qty || 0), 0);
    const activeCount = racks.filter((rack) => Number(rack.qty || 0) > 0).length;
    const completeCount = racks.filter((rack) => String(rack.status || "").toLowerCase() === "closed").length;
    const setClass = slugify(label || "rack-set") || "rack-set";

    return `
      <button type="button" class="rack-set-card ${escapeHtml(setClass)} ${selected ? "is-selected" : ""}" data-rack-set-select="${escapeHtml(label)}">
        <span class="rack-set-icon ${escapeHtml(setClass)}" aria-hidden="true"></span>
        <span class="rack-set-copy">
          <strong>${escapeHtml(label)}</strong>
          <small>${escapeHtml(racks.length)} rack${racks.length === 1 ? "" : "s"}</small>
          <b>${escapeHtml(totalQty)} piece${totalQty === 1 ? "" : "s"}</b>
        </span>
        <span class="rack-set-chevron">›</span>
        <span class="rack-set-meta">${escapeHtml(activeCount)} active | ${escapeHtml(completeCount)} complete</span>
        ${
          hasPermission("manage_racks")
            ? `<span class="rack-set-reset-inline icon-only icon-reset" data-rack-set-clear="${escapeHtml(label)}" title="Clear ${escapeHtml(label)}" aria-label="Clear ${escapeHtml(label)}"></span>`
            : ""
        }
      </button>
    `;
  };

  const renderSelectedRackDetails = (rack) => {
    if (!rack) {
      return `
        <section class="rack-detail-panel">
          <div class="admin-empty">No racks available. Create a rack to get started.</div>
        </section>
      `;
    }

    const hasItems = Number(rack.qty || 0) > 0;
    const isTruck = rack.code === "T" || /truck/i.test(rack.type || "");
    const rackState = String(rack.status || "").toLowerCase();
    const isComplete = rackState === "closed";
    const isInTransit = rackState === "in transit";
    const statusText = rackStatusText(rack);
    const statusClass = rackStatusClass(rack);
    const printLabel = isTruck ? "Print Truck Packing List" : "Print Packing List";

    return `
      <section class="rack-detail-panel ${escapeHtml(statusClass)}">
        <header class="rack-detail-header">
          <div>
            <span class="rack-detail-eyebrow">Selected Rack</span>
            <h2>${escapeHtml(isTruck ? "Truck / No Rack" : rack.code)}</h2>
            <p>${escapeHtml(rack.name || rack.type || "")}</p>
          </div>

          <div class="rack-detail-stats">
            <span><small>Pieces</small><strong>${escapeHtml(rack.qty || 0)}</strong></span>
            <span><small>Status</small><strong>${escapeHtml(statusText)}</strong></span>
          </div>
        </header>

        <div class="rack-detail-actions">
          ${
            hasItems
              ? isInTransit
                ? `<button type="button" data-rack-return="${escapeHtml(rack.code)}">Mark Returned</button><button type="button" data-rack-not-on-way="${escapeHtml(rack.code)}">Not On The Way</button>`
                : isComplete
                  ? `<button type="button" data-rack-uncomplete="${escapeHtml(rack.code)}">Uncomplete Rack</button>`
                  : `<button type="button" data-rack-complete="${escapeHtml(rack.code)}">Complete Rack</button>`
              : ""
          }

          <button type="button" data-rack-print="${escapeHtml(rack.code)}" ${hasItems && (isComplete || isInTransit) ? "" : "disabled"}>${printLabel}</button>
        </div>

        <div class="rack-detail-pieces">
          <div class="rack-detail-subheading">
            <strong>Pieces in ${escapeHtml(isTruck ? "Truck" : rack.code)}</strong>
            <span>${escapeHtml(rack.qty || 0)} pcs</span>
          </div>

          <div class="rack-item-list">
            ${hasItems ? renderRackItems(rack) : `<p class="admin-empty">No pieces assigned.</p>`}
          </div>
        </div>
      </section>
    `;
  };

  const selectedSetQty = selectedGroupAllRacks.reduce((sum, rack) => sum + Number(rack.qty || 0), 0);
  const visibleSetQty = selectedGroupRacks.reduce((sum, rack) => sum + Number(rack.qty || 0), 0);

  els.rackGrid.innerHTML = `
    <aside class="rack-sets-sidebar">
      <header>
        <h2>Rack Sets</h2>
        <span>All rack sets at a glance</span>
      </header>
      <div class="rack-set-list">
        ${groups.map(renderRackSetCard).join("") || `<div class="admin-empty">No rack sets found.</div>`}
      </div>
    </aside>

    <section class="rack-center-panel">
      <div class="rack-center-heading">
        <div>
          <h2>${escapeHtml(selectedGroupLabel || "Racks")}</h2>
          <span>${escapeHtml(selectedGroupAllRacks.length)} rack${selectedGroupAllRacks.length === 1 ? "" : "s"} | ${escapeHtml(selectedSetQty)} pieces${selectedGroupRacks.length !== selectedGroupAllRacks.length ? ` | Showing ${escapeHtml(selectedGroupRacks.length)} racks / ${escapeHtml(visibleSetQty)} pieces` : ""}</span>
        </div>
        <div class="rack-center-controls">
          <label class="rack-filter-control">
            <span>Status</span>
            <select data-rack-status-filter>
              <option value="all" ${state.rackStatusFilter === "all" ? "selected" : ""}>All</option>
              <option value="open" ${state.rackStatusFilter === "open" ? "selected" : ""}>Open</option>
              <option value="complete" ${state.rackStatusFilter === "complete" ? "selected" : ""}>Complete</option>
              <option value="in-transit" ${state.rackStatusFilter === "in-transit" ? "selected" : ""}>On the way</option>
              <option value="empty" ${state.rackStatusFilter === "empty" ? "selected" : ""}>Empty</option>
            </select>
          </label>
          <label class="rack-filter-control">
            <span>Sort</span>
            <select data-rack-sort>
              <option value="code-asc" ${state.rackSort === "code-asc" ? "selected" : ""}>Rack ID (A-Z)</option>
              <option value="code-desc" ${state.rackSort === "code-desc" ? "selected" : ""}>Rack ID (Z-A)</option>
              <option value="pieces-desc" ${state.rackSort === "pieces-desc" ? "selected" : ""}>Pieces (High-Low)</option>
              <option value="status" ${state.rackSort === "status" ? "selected" : ""}>Status</option>
            </select>
          </label>
          <button type="button" class="icon-only icon-reset" data-rack-set-clear="${escapeHtml(selectedGroupLabel)}" ${hasPermission("manage_racks") ? "" : "hidden"} title="Clear selected rack set" aria-label="Clear selected rack set"></button>
        </div>
      </div>

      <div class="rack-overview-card-grid">
        ${selectedGroupRacks.map(renderRackBoardCard).join("") || `<p class="admin-empty">No racks in this set.</p>`}
      </div>
    </section>

    ${renderSelectedRackDetails(selectedRack)}
  `;
}

async function submitRackScan() {
  const barcode = els.rackScanInput?.value || "";
  const rackCode = els.rackSelect?.value || state.selectedRackCode;
  const listId = els.rackListSelect?.value || state.rackScanListId;
  if (!barcode.trim() || !rackCode || !listId) {
    if (els.rackScanStatus) els.rackScanStatus.textContent = "Choose a staging list and rack, then scan a piece.";
    return;
  }
  const payload = await fetchJson("/api/racks/scan", {
    method: "POST",
    body: JSON.stringify({ listId, rackCode, barcode, ...requestContext() }),
  });
  state.racks = payload.racks || state.racks;
  state.rackSummary = payload.summary || state.rackSummary;
  if (els.rackScanStatus) els.rackScanStatus.textContent = payload.message || "Rack scan recorded.";
  if (els.rackScanInput) els.rackScanInput.value = "";
  renderRacksPage();
  if (listId === state.activeListId) await activateList(listId, false);
  els.rackScanInput?.focus();
}

async function chooseRackDestination(rack) {
  const currentDestination = rackDestinationLabel(rack?.destination || "Indian Trail");

  return new Promise((resolve) => {
    document.querySelector(".rack-destination-backdrop")?.remove();

    const shell = document.createElement("div");
    shell.className = "rack-destination-backdrop";
    shell.innerHTML = `
      <section class="rack-destination-dialog" role="dialog" aria-modal="true" aria-labelledby="rackDestinationTitle">
        <button class="modal-close-x rack-destination-close" type="button" data-rack-destination-cancel aria-label="Close">&times;</button>
        <div class="rack-destination-copy">
          <small>Complete rack</small>
          <h2 id="rackDestinationTitle">Where is ${escapeHtml(rack?.code || "this rack")} going?</h2>
          <p>Select the destination before printing the packing list. Indian Trail is the default.</p>
        </div>
        <label class="rack-destination-field">
          <span>Destination</span>
          <select id="rackDestinationSelect">
            ${["Indian Trail", "CPU", "Greenville", "DTC"].map((value) => `<option value="${escapeHtml(value)}" ${rackDestinationLabel(value) === currentDestination ? "selected" : ""}>${escapeHtml(value)}</option>`).join("")}
          </select>
        </label>
        <div class="rack-destination-actions">
          <button type="button" data-rack-destination-cancel>Cancel</button>
          <button type="button" data-rack-destination-confirm>Complete Rack</button>
        </div>
      </section>
    `;

    const close = (value = "") => {
      shell.remove();
      document.body.classList.remove("modal-scroll-locked");
      resolve(value);
    };

    shell.addEventListener("click", (event) => {
      if (event.target === shell || event.target.closest("[data-rack-destination-cancel]")) {
        close("");
        return;
      }
      if (event.target.closest("[data-rack-destination-confirm]")) {
        close(shell.querySelector("#rackDestinationSelect")?.value || "Indian Trail");
      }
    });

    document.body.appendChild(shell);
    document.body.classList.add("modal-scroll-locked");
    shell.querySelector("#rackDestinationSelect")?.focus();
  });
}

async function completeRack(code) {
  const payload = await fetchJson("/api/racks/complete", { method: "POST", body: JSON.stringify({ rackCode: code }) });
  state.racks = payload.racks || [];
  state.rackSummary = payload.summary || null;
  showFloatingNotice(payload.message || `Rack ${code} completed with automatic destination.`, "success");
  renderRacksPage();
  renderScanRackTools();
}

async function uncompleteRack(code) {
  const payload = await fetchJson("/api/racks/uncomplete", { method: "POST", body: JSON.stringify({ rackCode: code }) });
  state.racks = payload.racks || [];
  state.rackSummary = payload.summary || null;
  renderRacksPage();
  renderScanRackTools();
}

async function returnRack(code) {
  if (!window.confirm(`Mark ${code} returned and clear it for reuse? Active rack contents will be removed from the rack.`)) return;
  const payload = await fetchJson("/api/racks/return", { method: "POST", body: JSON.stringify({ rackCode: code }) });
  state.racks = payload.racks || [];
  state.rackSummary = payload.summary || null;
  renderRacksPage();
  renderScanRackTools();
}

async function markRackNotOnTheWay(code) {
  const confirmed = await confirmWebAppAction({
    title: "Mark rack Not On The Way?",
    message: `Reopen <strong>${escapeHtml(code)}</strong> and undo the outbound scans that were recorded from this rack barcode.`,
    details: "The pieces will stay assigned to the rack so staging can add more or correct the rack before it is sent again.",
    confirmLabel: "Not On The Way",
    requiredText: "NOT ON THE WAY",
    requiredTextLabel: "Type this exact phrase to undo the outbound rack scans",
  });

  if (!confirmed) return;

  const payload = await fetchJson("/api/racks/not-on-way", { method: "POST", body: JSON.stringify({ rackCode: code, confirmText: "NOT ON THE WAY" }) });
  state.racks = payload.racks || [];
  state.rackSummary = payload.summary || null;
  renderRacksPage();
  renderScanRackTools();
  showFloatingNotice(payload.message || `Rack ${code} is open again and outbound rack scans were reversed.`, "success");
}

async function assignLineItemToRack(lineItemId, rackCode) {
  const payload = await fetchJson("/api/racks/assign-line-item", {
    method: "POST",
    body: JSON.stringify({ lineItemId, rackCode }),
  });

  if (payload.racks) {
    state.racks = payload.racks;
    state.rackSummary = payload.rackSummary || state.rackSummary;
  }

  if (payload.meta?.id === state.activeListId) {
    applyBackendPayload(payload);
  } else if (state.activeListId) {
    await activateList(state.activeListId, false);
  }

  renderScanPage();
  renderRacksPage();
  showFloatingNotice(rackCode ? `Line item assigned to rack ${rackCode}.` : "Line item rack location cleared.", "success");
}

async function clearRack(code) {
  if (!window.confirm(`Clear all active pieces from ${code}?`)) return;
  const payload = await fetchJson("/api/racks/clear", { method: "POST", body: JSON.stringify({ rackCode: code }) });
  state.racks = payload.racks || [];
  state.rackSummary = payload.summary || null;
  renderRacksPage();
}

async function clearRackSet(label) {
  const racks = (state.racks || []).filter((rack) => rackGroupLabel(rack) === label);
  if (!racks.length) return;
  if (!window.confirm(`Clear all active pieces from every rack in ${label}? Individual pieces will be left as delivery-list scans.`)) return;
  let latestPayload = null;
  for (const rack of racks) {
    latestPayload = await fetchJson("/api/racks/clear", { method: "POST", body: JSON.stringify({ rackCode: rack.code }) });
  }
  if (latestPayload) {
    state.racks = latestPayload.racks || [];
    state.rackSummary = latestPayload.summary || null;
  }
  renderRacksPage();
}

async function moveRackItem(rackItemId) {
  const select = document.querySelector(`[data-rack-target="${CSS.escape(String(rackItemId))}"]`);
  const targetRackCode = select?.value || "";

  if (!targetRackCode) {
    showFloatingNotice("Choose a destination rack before confirming the move.", "notice");
    return;
  }

  const payload = await fetchJson("/api/racks/move-item", {
    method: "POST",
    body: JSON.stringify({ rackItemId, targetRackCode }),
  });

  state.racks = payload.racks || [];
  state.rackSummary = payload.summary || null;
  state.rackMoveItemId = "";

  renderRacksPage();
}

async function clearRackItem(rackItemId, label = "this piece") {
  if (!window.confirm(`Clear ${label} from its rack? This does not change scan quantities.`)) return;
  const payload = await fetchJson("/api/racks/clear-item", { method: "POST", body: JSON.stringify({ rackItemId }) });
  state.racks = payload.racks || [];
  state.rackSummary = payload.summary || null;
  renderRacksPage();
  renderScanRackTools();
}

function rackPackingListUrl(rackCode, deliveryDate = "") {
  const dateParam = deliveryDate ? `&deliveryDate=${encodeURIComponent(deliveryDate)}` : "";
  return `/api/racks/packing-list?rackCode=${encodeURIComponent(rackCode)}${dateParam}`;
}

function printSelectedRackPackingSlip() {
  if (!state.selectedRackCode) return;
  const rack = state.racks.find((item) => item.code === state.selectedRackCode);
  if (!rack || !["closed", "in transit"].includes(String(rack.status || "").toLowerCase())) {
    showFloatingNotice("Complete this rack before printing its packing list.", "notice");
    return;
  }
  const activeList = state.lists.find((list) => list.id === state.activeListId);
  const dateParam = isTruckRack(rack) && activeList?.deliveryDate ? activeList.deliveryDate : "";
  launchManagedPrint(rackPackingListUrl(state.selectedRackCode, dateParam));
}

async function saveRackDefinition() {
  const payload = await fetchJson("/api/racks", {
    method: "POST",
    body: JSON.stringify({
      oldRackCode: document.getElementById("rackModalOldCode")?.value || "",
      rackCode: document.getElementById("rackModalCode")?.value || "",
      name: document.getElementById("rackModalName")?.value || "",
      type: document.getElementById("rackModalType")?.value || "Steel",
    }),
  });
  state.racks = payload.racks || [];
  state.rackSummary = payload.summary || null;
  renderRacksPage();
  closeAdminModal();
}

function selectedRackManagerRack(code = state.rackManagerSelectedCode) {
  return state.racks.find((rack) => rack.code === code) || state.racks[0] || null;
}

function populateRackManagerQuickEdit(code = "") {
  const select = document.getElementById("rackManagerQuickRackSelect");
  const nameInput = document.getElementById("rackManagerQuickName");
  const typeInput = document.getElementById("rackManagerQuickType");
  const rack = selectedRackManagerRack(code || select?.value || state.rackManagerSelectedCode);

  if (!rack) return;

  state.rackManagerSelectedCode = rack.code || "";
  if (select) select.value = rack.code || "";
  if (nameInput) nameInput.value = rack.name || rack.type || rack.code || "";
  if (typeInput) typeInput.value = rack.type || "Steel";
}

async function saveRackQuickEdit() {
  const code = document.getElementById("rackManagerQuickRackSelect")?.value || state.rackManagerSelectedCode || "";
  if (!code) return;

  const payload = await fetchJson("/api/racks", {
    method: "POST",
    body: JSON.stringify({
      rackCode: code,
      name: document.getElementById("rackManagerQuickName")?.value || code,
      type: document.getElementById("rackManagerQuickType")?.value || "Steel",
    }),
  });

  state.racks = payload.racks || [];
  state.rackSummary = payload.summary || null;
  state.rackManagerSelectedCode = code;
  renderRacksPage();
  renderScanRackTools();

  if (!els.adminModal?.hidden && els.adminModalBody?.querySelector(".rack-manager-shell")) {
    els.adminModalBody.innerHTML = adminModalContent("racks");
  }

  showFloatingNotice(`Saved rack ${code}.`, "success");
}

async function deleteRackDefinition(rackCode = state.selectedRackCode) {
  if (!rackCode) return;
  const typed = window.prompt(`Delete rack ${rackCode}? Empty racks only. Type DELETE RACK to confirm.`);
  if (typed !== "DELETE RACK") return;
  const payload = await fetchJson("/api/racks/delete", { method: "POST", body: JSON.stringify({ rackCode }) });
  state.racks = payload.racks || [];
  state.rackSummary = payload.summary || null;
  if (state.selectedRackOverviewCode === rackCode) state.selectedRackOverviewCode = "";
  renderRacksPage();
  renderScanRackTools();
  if (!els.adminModal?.hidden && els.adminModalBody?.querySelector(".rack-manager-shell")) {
    els.adminModalBody.innerHTML = adminModalContent("racks");
  }
}

async function createRackSet() {
  const prefix = document.getElementById("rackSetModalPrefix")?.value || "";
  const nameRoot = document.getElementById("rackSetModalName")?.value || prefix || "Rack";
  const payload = await fetchJson("/api/racks/create-set", {
    method: "POST",
    body: JSON.stringify({
      prefix,
      nameRoot,
      type: nameRoot,
      count: document.getElementById("rackSetModalCount")?.value || 10,
      start: document.getElementById("rackSetModalStart")?.value || 1,
    }),
  });
  state.racks = payload.racks || [];
  state.rackSummary = payload.summary || null;
  renderRacksPage();
  renderScanRackTools();
  closeAdminModal();
  showFloatingNotice(`Created ${payload.created?.length || 0} rack(s).`, "success");
}

function openRackForm(rackCode = "", defaults = {}) {
  const existingRack = state.racks.find((item) => item.code === rackCode);
  const rack = existingRack ? { ...existingRack, oldCode: existingRack.code } : { ...defaults };
  state.rackModal = { rack };
  openAdminModal("rackForm");
}

function openRackSetForm(label = "") {
  const racks = state.racks.filter((rack) => (rack.code === "T" || /truck/i.test(rack.type || "") ? "Truck" : rack.type || "Racks") === label);
  state.rackModal = {
    set: {
      name: label && label !== "Truck" ? label : "",
      prefix: "",
      count: racks.length || 10,
      start: 1,
    },
  };
  openAdminModal("rackSetForm");
}

async function deleteRackSet(label) {
  const racks = state.racks.filter((rack) => (rack.code === "T" || /truck/i.test(rack.type || "") ? "Truck" : rack.type || "Racks") === label);
  const deletable = racks.filter((rack) => rack.code !== "T");
  if (!deletable.length) return;
  if (!window.confirm(`Delete ${deletable.length} rack(s) in ${label}? Empty racks only.`)) return;
  for (const rack of deletable) {
    await fetchJson("/api/racks/delete", { method: "POST", body: JSON.stringify({ rackCode: rack.code }) });
  }
  await ensureRacksLoaded();
  renderRacksPage();
  renderScanRackTools();
  if (!els.adminModal?.hidden && els.adminModalBody?.querySelector(".rack-manager-shell")) {
    els.adminModalBody.innerHTML = adminModalContent("racks");
  }
}

function renderMobileCards() {
  if (!els.mobileListCards) return;
  const { pageRows } = getPagedItems();
  els.mobileListCards.innerHTML = `
    <div class="section-heading">
      <h3>Delivery List</h3>
      <span>${state.items.length} items</span>
    </div>
    <div class="filter-tabs mobile-tabs">
      <button class="tab ${state.filter === "all" ? "is-active" : ""}" data-filter="all" type="button">All (${state.items.length})</button>
      <button class="tab ${state.filter === "remaining" ? "is-active" : ""}" data-filter="remaining" type="button">Remaining (${getStats().remainingItems})</button>
      <button class="tab ${state.filter === "partial" ? "is-active" : ""}" data-filter="partial" type="button">Partial (${getStats().partialItems})</button>
      <button class="tab ${state.filter === "complete" ? "is-active" : ""}" data-filter="complete" type="button">Complete (${getStats().completeItems})</button>
      <button class="tab ${state.filter === "remakes" ? "is-active" : ""}" data-filter="remakes" type="button">Remakes (${state.items.filter(isRemakeItem).length})</button>
      <button class="tab ${state.filter === "rushes" ? "is-active" : ""}" data-filter="rushes" type="button">Rushes (${state.items.filter(isRushItem).length})</button>
      <button class="tab ${state.filter === "updated" ? "is-active" : ""}" data-filter="updated" type="button">Updated (${state.items.filter(isNewOrUpdatedItem).length})</button>
      <button class="tab ${state.filter === "errors" ? "is-active" : ""}" data-filter="errors" type="button">Review (${state.errors.length})</button>
    </div>
    ${pageRows
      .slice(0, 12)
      .map((item) => {
        const status = itemStatus(item);
        const selected = item.id === state.selectedId;
        const mark = status === "complete" ? "&#10003;" : routeLabel(item) || "-";
        return `
          <article class="mobile-list-card ${selected ? "is-selected" : ""}" data-id="${escapeHtml(item.id)}">
            <span><small>Order #</small><b>${escapeHtml(item.order)}</b></span>
            <span><small>Item #</small><b>${escapeHtml(item.item)}</b></span>
            <span><small>Qty</small><b><span class="qty-pill ${status}">${item.scanned} / ${item.qty}</span></b></span>
            <span class="dims"><small>Dimensions</small><b>${escapeHtml(item.dimensions)}</b></span>
            <span class="card-status">${mark}</span>
            <span class="card-customer">${escapeHtml(item.customer)}</span>
          </article>
        `;
      })
      .join("")}
  `;
}

function setLastScan(entry) {
  if (!entry || !els.lastCard) return;
  state.lastScan = entry;
  els.lastCard.classList.remove("ok", "error");
  els.lastCard.classList.add(entry.ok ? "ok" : "error");
  if (els.lastScanTime) els.lastScanTime.textContent = entry.ok ? "Just now" : entry.eventType === "duplicate" ? "Notice" : "Needs review";
  const manualPrefix = scanEntryIsManual(entry) ? "Manual Scan - " : "";
  const scanMessage = [entry.message, entry.reason].filter(Boolean).join(" - ");
  if (els.lastJob) els.lastJob.textContent = scanMessage && !entry.ok ? `${manualPrefix}${scanMessage}` : entry.item ? `${manualPrefix}${entry.item.job || entry.item.product || ""}`.trim() : `${manualPrefix}${entry.message || ""}`.trim();
  if (els.lastOrder) els.lastOrder.textContent = entry.item ? entry.item.order : "-";
  if (els.lastItem) els.lastItem.textContent = entry.item ? entry.item.item : "-";
  if (els.lastQty) els.lastQty.textContent = entry.item ? String(entry.item.scanned) : "-";
  if (els.lastDims) els.lastDims.textContent = entry.item ? entry.item.dimensions : "-";
  if (els.lastCustomer) els.lastCustomer.textContent = entry.item ? entry.item.customer : "-";
}

function renderLastScan() {
  if (state.lastScan) {
    setLastScan(state.lastScan);
    return;
  }
  els.lastCard?.classList.remove("ok", "error");
  if (els.lastScanTime) els.lastScanTime.textContent = "Waiting";
  if (els.lastJob) els.lastJob.textContent = "No scans yet";
  if (els.lastOrder) els.lastOrder.textContent = "-";
  if (els.lastItem) els.lastItem.textContent = "-";
  if (els.lastQty) els.lastQty.textContent = "-";
  if (els.lastDims) els.lastDims.textContent = "-";
  if (els.lastCustomer) els.lastCustomer.textContent = "-";
}

function sameScanEntry(a, b) {
  if (!a || !b) return false;
  const itemA = a.item || {};
  const itemB = b.item || {};
  return String(a.time || "") === String(b.time || "") &&
    String(a.barcode || "") === String(b.barcode || "") &&
    String(a.eventType || "") === String(b.eventType || "") &&
    String(itemA.id || `${itemA.order || ""}-${itemA.item || ""}`) === String(itemB.id || `${itemB.order || ""}-${itemB.item || ""}`);
}

function scanEntryIsManual(entry) {
  return String(entry?.eventType || "").toLowerCase() === "manual_scan" || Boolean(entry?.isManual);
}

function recentRowsExcludingCurrentLastScan() {
  const recent = state.recent || [];
  if (!state.lastScan) return recent.slice(0, 2);
  return recent.filter((entry) => !sameScanEntry(entry, state.lastScan)).slice(0, 2);
}

function renderRecent() {
  if (!els.recentRows) return;
  const rows = recentRowsExcludingCurrentLastScan();
  els.recentRows.innerHTML = rows.length
    ? rows
        .map((entry) => {
          const item = entry.item;
          const time = new Date(entry.time);
          const note = [entry.message, entry.reason].filter(Boolean).join(" - ");
          const manualNote = scanEntryIsManual(entry) ? "Manual Scan" : "";
          const detailNote = [manualNote, note].filter(Boolean).join(" - ");
          return `
            <tr class="${entry.ok ? "ok" : "error"} ${scanEntryIsManual(entry) ? "manual" : ""}">
              <td><strong>${item ? escapeHtml(item.job || item.product || "-") : "-"}</strong>${detailNote ? `<small class="scan-row-note">${escapeHtml(detailNote)}</small>` : ""}</td>
              <td>${item ? escapeHtml(item.order) : "-"}</td>
              <td>${item ? escapeHtml(item.item) : "-"}</td>
              <td>${item ? item.scanned : "-"}</td>
              <td>${Number.isNaN(time.getTime()) ? "" : time.toLocaleString()}</td>
              <td><span class="check-dot ${entry.ok ? "" : "error"}">${entry.ok ? "&#10003;" : "!"}</span></td>
            </tr>
          `;
        })
        .join("")
    : `<tr><td colspan="6">No scans yet</td></tr>`;
}

function recentScansModalHtml() {
  const rows = state.recent || [];
  return `
    <div class="recent-scans-modal full-scans-modal">
      <div class="modal-list-heading">
        <strong>${escapeHtml(state.meta?.label || state.meta?.stage || "Current stage")}</strong>
        <span>${escapeHtml(rows.length)} recent scan${rows.length === 1 ? "" : "s"}</span>
      </div>
      <div class="recent-table-wrap expanded">
        <table class="recent-table">
          <thead>
            <tr>
              <th>Barcode</th>
              <th>Job Nr.</th>
              <th>Order Nr.</th>
              <th>Item Nr.</th>
              <th>Qty Scanned</th>
              <th>Customer</th>
              <th>Message</th>
              <th>Date & Time Scanned</th>
              <th>Check</th>
            </tr>
          </thead>
          <tbody>
            ${
              rows.length
                ? rows
                    .map((entry) => {
                      const item = entry.item;
                      const time = new Date(entry.time);
                      const note = [entry.message, entry.reason].filter(Boolean).join(" - ");
                      const manualNote = scanEntryIsManual(entry) ? "Manual Scan" : "";
                      const detailNote = [manualNote, note].filter(Boolean).join(" - ");
                      return `
                        <tr class="${entry.ok ? "ok" : "error"} ${scanEntryIsManual(entry) ? "manual" : ""}">
                          <td><strong>${escapeHtml(entry.barcode)}</strong>${detailNote ? `<small class="scan-row-note">${escapeHtml(detailNote)}</small>` : ""}</td>
                          <td>${item ? escapeHtml(item.job || item.product || "-") : "-"}</td>
                          <td>${item ? escapeHtml(item.order) : "-"}</td>
                          <td>${item ? escapeHtml(item.item) : "-"}</td>
                          <td>${item ? item.scanned : "-"}</td>
                          <td>${item ? escapeHtml(item.customer || "") : "-"}</td>
                          <td>${note ? escapeHtml(note) : escapeHtml(entry.message || "")}</td>
                          <td>${Number.isNaN(time.getTime()) ? "" : time.toLocaleString()}</td>
                          <td><span class="check-dot ${entry.ok ? "" : "error"}">${entry.ok ? "&#10003;" : "!"}</span></td>
                        </tr>
                      `;
                    })
                    .join("")
                : `<tr><td colspan="9">No scans yet</td></tr>`
            }
          </tbody>
        </table>
      </div>
    </div>
  `;
}

function renderMeta() {
  if (!state.meta) return;
  const dateText = formatDisplayDate(state.meta.deliveryDate);
  if (els.pageTitle) els.pageTitle.textContent = `Delivery List for ${dateText}`;
  if (els.stageSubtitle) els.stageSubtitle.textContent = state.meta.stage;
  if (els.stageHeading) els.stageHeading.textContent = state.meta.stage;
  if (els.scannerName) els.scannerName.textContent = state.meta.scanner;
  if (els.backendStatus) {
    els.backendStatus.textContent = state.backend ? "SQLite live" : "Local demo";
    els.backendStatus.classList.toggle("online", state.backend);
  }
  renderDeliveryListSelect();
}

function renderDeliveryListSelect() {
  const groups = listsByDeliveryDate();
  const activeDate = selectedDeliveryDate();
  if (els.deliveryDateSelect) {
    els.deliveryDateSelect.innerHTML = groups
      .map((group) => `<option value="${escapeHtml(group.date)}">${escapeHtml(formatDisplayDate(group.date))}</option>`)
      .join("");
    els.deliveryDateSelect.value = activeDate;
  }
  if (els.deliveryStageSelect) {
    const stageLists = (groups.find((group) => group.date === activeDate)?.lists || state.lists).filter((list) => list.deliveryDate === activeDate);
    els.deliveryStageSelect.innerHTML = stageLists
      .map((list) => `<option value="${escapeHtml(list.id)}">${escapeHtml(list.stage)} - ${escapeHtml(list.scanner)}</option>`)
      .join("");
    els.deliveryStageSelect.value = state.activeListId;
  }
  if (els.deliveryListSelect) {
    els.deliveryListSelect.innerHTML = state.lists
      .map((list) => `<option value="${escapeHtml(list.id)}">${escapeHtml(list.label)}</option>`)
      .join("");
    els.deliveryListSelect.value = state.activeListId;
  }
}

function applyPermissionUi() {
  const displayName = state.user ? state.user.displayName || state.user.username : "Demo";
  const roleText = state.user?.roles?.length ? state.user.roles.join(", ") : state.backend ? "Signed in" : "Local demo";
  const stationText = userAssignedStation(state.user) || currentScanStation() || "No assigned station";
  const initials = state.user ? userInitials(state.user) : "DM";
  const accentClass = state.user ? userAccentClass(state.user) : "accent-default";

  if (els.signedInUser) {
    els.signedInUser.textContent = displayName;
  }

  if (els.signedInRole) {
    els.signedInRole.textContent = roleText;
  }

  if (els.userMenuDisplayName) {
    els.userMenuDisplayName.textContent = displayName;
  }

  if (els.userMenuDetails) {
    els.userMenuDetails.textContent = `${roleText} • ${stationText}`;
  }

  document.querySelectorAll(".user-menu .user-avatar").forEach((avatar) => {
    avatar.textContent = initials;
    avatar.className = `user-avatar ${accentClass}${avatar.classList.contains("user-menu-large-avatar") ? " user-menu-large-avatar" : ""}`;
    avatar.setAttribute("aria-hidden", "true");
  });

  if (els.logoutBtn) els.logoutBtn.hidden = !state.backend || !state.user;
  document.querySelectorAll("[data-permission-any]").forEach((element) => {
    const permissions = element.dataset.permissionAny.split(",").map((value) => value.trim());
    element.hidden = !hasAnyPermission(permissions);
  });
  const canScan = hasPermission("scan") || hasPermission("indian_trail_receive");
  setControlAllowed(els.scanInput, canScan);
  setControlAllowed(els.globalPrintExportBtn, hasPermission("export_reports"), true);
  setControlAllowed(els.undoBtn, hasPermission("undo_scan"), true);
  setControlAllowed(els.redoBtn, hasPermission("undo_scan"), true);
  setControlAllowed(els.folderImportBtn, hasPermission("import_delivery_lists"), true);
  setControlAllowed(els.addStationBtn, hasPermission("manage_stations"));
  setControlAllowed(els.newStationInput, hasPermission("manage_stations"));
}

function renderScanPage() {
  renderMeta();
  renderCounts();
  renderTable();
  renderMobileCards();
  renderRecent();
  renderLastScan();
  renderManualAssignTools();
  renderScanRackTools();
  renderScanBayOverrideTools();
  applyPermissionUi();
}

function isStagingScanContext() {
  return /staging/i.test(`${state.meta?.stage || ""} ${state.meta?.scanner || ""}`);
}

async function ensureRacksLoaded() {
  if (!state.backend || state.racks.length) return;
  const payload = await fetchJson("/api/racks");
  state.racks = payload.racks || [];
  state.rackSummary = payload.summary || null;
  renderScanRackTools();
}

function renderScanRackTools() {
  if (!els.scanRackPanel) return;
  const visible = isStagingScanContext() && hasPermission("scan_racks");
  els.scanRackPanel.hidden = !visible;
  if (!visible) return;
  if (!state.racks.length) {
    els.scanRackPanel.classList.add("is-loading");
    void ensureRacksLoaded().catch((error) => showInlineError(error.message, true));
    return;
  }
  els.scanRackPanel.classList.remove("is-loading");
  if (!state.selectedRackCode || !state.racks.some((rack) => rack.code === state.selectedRackCode)) {
    state.selectedRackCode = state.racks.find((rack) => rack.code === "T")?.code || state.racks[0]?.code || "";
  }
  const selectedRack = state.racks.find((rack) => rack.code === state.selectedRackCode);
  const selectedRackState = String(selectedRack?.status || "").toLowerCase();
  const selectedClosed = selectedRackState === "closed";
  const selectedInTransit = selectedRackState === "in transit";
  els.scanRackPanel.classList.toggle("selected-rack-complete", selectedClosed);
  els.scanRackPanel.classList.toggle("selected-rack-in-transit", selectedInTransit);
  els.scanRackPanel.classList.toggle("selected-rack-loaded", Boolean(selectedRack && Number(selectedRack.qty || 0) > 0 && !selectedClosed && !selectedInTransit));
  if (els.scanRackSelect) {
    els.scanRackSelect.innerHTML = groupedRackOptionsHtml(state.racks, state.selectedRackCode);
    els.scanRackSelect.value = state.selectedRackCode;
    syncCustomSelect(els.scanRackSelect);
  }
  if (els.scanRackCompleteBtn) {
    els.scanRackCompleteBtn.textContent = selectedInTransit ? "Mark Returned" : selectedClosed ? "Uncomplete" : "Complete";
  }
  if (els.scanRackPrintBtn) {
    els.scanRackPrintBtn.textContent = selectedInTransit ? "Not On The Way" : "Print Packing List";
    els.scanRackPrintBtn.disabled = !selectedRack || (selectedInTransit ? false : !(selectedClosed || selectedInTransit) || Number(selectedRack.qty || 0) <= 0);
  }
  if (els.scanRackStatus) {
    els.scanRackStatus.textContent = selectedInTransit
      ? "This rack is marked on the way. Return it to clear it, or mark Not On The Way to reopen it and undo this rack's outbound scans."
      : "";
  }
}

function isIndianTrailScanContext() {
  return /indian trail|inbound/i.test(`${state.meta?.stage || ""} ${state.meta?.scanner || ""}`);
}

function renderManualAssignTools() {
  if (!els.manualAssignPanel) return;
  els.manualAssignPanel.hidden = true;
}


async function ensureScanBayOverrideBays() {
  if (!state.backend || state.bays.length) return;
  const payload = await fetchJson("/api/indian-trail/bays");
  state.bays = payload.bays || [];
  renderScanBayOverrideTools();
}

function scanBayOverrideVisible() {
  return state.backend && hasPermission("indian_trail_receive") && isIndianTrailScanContext();
}

function bayOverrideGroupLabel(bay) {
  return String(bay?.mapSection || bay?.area || bay?.bayCategory || bay?.bayType || "Other Bays").trim() || "Other Bays";
}

function bayOverrideSort(a, b) {
  return Number(a.layoutRow || 9999) - Number(b.layoutRow || 9999) ||
    Number(a.layoutCol || 9999) - Number(b.layoutCol || 9999) ||
    String(a.displayName || a.bayCode || "").localeCompare(String(b.displayName || b.bayCode || ""));
}

function renderScanBayOverrideTools() {
  if (!els.scanBayOverridePanel) return;
  const visible = scanBayOverrideVisible();
  els.scanBayOverridePanel.hidden = !visible;
  if (!visible) {
    state.selectedBayOverrideCode = "";
    state.bayOverrideMode = "auto";
    return;
  }

  if (!state.bays.length) {
    els.scanBayOverridePanel.classList.add("is-loading");
    if (els.scanBayOverrideSelected) els.scanBayOverrideSelected.textContent = "Loading Indian Trail bays...";
    if (els.scanBayOverrideSelect) {
      els.scanBayOverrideSelect.disabled = true;
      els.scanBayOverrideSelect.innerHTML = `<option value="">Loading bays...</option>`;
    }
    void ensureScanBayOverrideBays().catch((error) => showInlineError(error.message, true));
    return;
  }

  els.scanBayOverridePanel.classList.remove("is-loading");

  const availableBays = state.bays
    .filter((bay) => bay.active !== false)
    .filter((bay) => !/blocked|hold/i.test(`${bay.sourceStatus || ""} ${bay.status || ""}`))
    .sort(bayOverrideSort);
  const grouped = new Map();
  for (const bay of availableBays) {
    const label = bayOverrideGroupLabel(bay);
    if (!grouped.has(label)) grouped.set(label, []);
    grouped.get(label).push(bay);
  }

  const selectedBay = availableBays.find((bay) => bay.bayCode === state.selectedBayOverrideCode);
  if (!selectedBay && state.selectedBayOverrideCode) state.selectedBayOverrideCode = "";
  if (state.bayOverrideMode !== "manual") state.bayOverrideMode = "auto";

  if (els.scanBayOverrideMode) {
    els.scanBayOverrideMode.checked = state.bayOverrideMode === "manual";
  }

  if (els.scanBayOverrideSelect) {
    const options = [`<option value="">Use auto-suggested bay</option>`];
    for (const [label, bays] of grouped.entries()) {
      options.push(`
        <optgroup label="${escapeHtml(label)}">
          ${bays.map((bay) => {
            const name = bay.displayName || bay.bayCode;
            const status = bay.status ? ` - ${bay.status}` : "";
            return `<option value="${escapeHtml(bay.bayCode)}">${escapeHtml(name)}${escapeHtml(status)}</option>`;
          }).join("")}
        </optgroup>
      `);
    }
    els.scanBayOverrideSelect.innerHTML = options.join("");
    els.scanBayOverrideSelect.value = state.selectedBayOverrideCode || "";
    els.scanBayOverrideSelect.disabled = state.bayOverrideMode !== "manual";
  }

  if (els.scanBayOverrideSelected) {
    els.scanBayOverrideSelected.textContent = state.bayOverrideMode === "manual"
      ? (selectedBay ? `Manual bay: ${selectedBay.displayName || selectedBay.bayCode}` : "Manual mode - choose a bay")
      : "Auto suggested bay";
  }
}

function compatibleBayCandidates(item) {
  const suggested = String(item?.suggestedBay || item?.product || "").toLowerCase();
  const targetKind =
    suggested.includes("mirror") && suggested.includes("framed") ? "framed-mirror" :
    suggested.includes("mirror") ? "mirror" :
    suggested.includes("crl") ? "crl" :
    suggested.includes("shower") || suggested.includes("tempered") ? "showers" :
    "";
  return (state.bays || [])
    .filter((bay) => bayStatusKind(bay) === "available")
    .filter((bay) => !targetKind || bayCategoryKind(bay) === targetKind || bayCategoryKind(bay) === "standard")
    .slice(0, 16);
}

async function submitManualBayAssign() {
  const order = digitsOnly(els.manualAssignOrderInput?.value || "");
  const itemNo = digitsOnly(els.manualAssignItemInput?.value || "");
  const qty = Math.max(1, Number(els.manualAssignQtyInput?.value || 1));
  if (!order) {
    showInlineError("Manual bay assign needs an order number.", false);
    return;
  }
  if (!state.bays.length && state.backend) {
    const payload = await fetchJson("/api/indian-trail/bays");
    state.bays = payload.bays || [];
  }
  const matches = state.items.filter((item) => digitsOnly(item.order) === order && (!itemNo || digitsOnly(item.item) === itemNo));
  if (matches.length !== 1) {
    if (els.manualAssignStatus) {
      els.manualAssignStatus.innerHTML = `<article class="message-card review"><strong>${matches.length ? "Multiple matches" : "No match"}</strong><span>Enter an item number to pick one exact row.</span></article>`;
    }
    return;
  }
  const item = matches[0];
  const bays = compatibleBayCandidates(item);
  if (els.manualAssignStatus) {
    els.manualAssignStatus.innerHTML = bays.length
      ? `<article class="message-card notice"><strong>Choose a bay for ${escapeHtml(item.order)}-${escapeHtml(item.item)}</strong><span>${escapeHtml(item.customer)} - Qty ${qty}</span></article>
         <div class="bay-picker">${bays.map((bay) => `<button type="button" data-manual-assign-bay="${escapeHtml(bay.bayCode)}" data-line-item-id="${escapeHtml(item.id)}" data-assigned-qty="${escapeHtml(qty)}">${escapeHtml(bay.displayName || bay.bayCode)}</button>`).join("")}</div>`
      : `<article class="message-card review"><strong>No empty compatible bay found</strong><span>Use the Bay Map to free a bay or pick manually.</span></article>`;
  }
}

function miniStat(label, value, detail = "") {
  return `<div class="mini-stat"><small>${escapeHtml(label)}</small><strong>${escapeHtml(value)}</strong>${detail ? `<span>${escapeHtml(detail)}</span>` : ""}</div>`;
}

function aggregateListStats(lists) {
  const totalLists = lists.length;
  const totalItems = lists.reduce((sum, list) => sum + Number(list.itemCount || 0), 0);
  const totalQty = lists.reduce((sum, list) => sum + Number(list.totalQty || 0), 0);
  const pieceQty = lists.reduce((maxQty, list) => Math.max(maxQty, Number(list.totalQty || 0)), 0);
  const scannedQty = lists.reduce((sum, list) => sum + Number(list.scannedQty || 0), 0);
  const outboundLists = lists.filter((list) => stageCategory(list) === "outbound");
  const timingLists = outboundLists.length ? outboundLists : lists;
  const onTimeQty = timingLists.reduce((sum, list) => sum + Number(list.onTimeQty || 0), 0);
  const lateQty = timingLists.reduce((sum, list) => sum + Number(list.lateQty || 0), 0);
  const timedQty = onTimeQty + lateQty;
  return {
    totalLists,
    totalItems,
    totalQty,
    pieceQty,
    scannedQty,
    remainingQty: Math.max(totalQty - scannedQty, 0),
    deliveryPercent: totalQty ? (scannedQty / totalQty) * 100 : 0,
    onTimeQty,
    lateQty,
    onTimePercent: timedQty ? (onTimeQty / timedQty) * 100 : 0,
  };
}

function homeStageBreakdown(lists) {
  const buckets = new Map();
  for (const list of lists) {
    const key = stageCategory(list);
    const current = buckets.get(key) || {
      category: key,
      label: stageLabel(list),
      lists: 0,
      totalQty: 0,
      scannedQty: 0,
      remainingQty: 0,
    };
    current.lists += 1;
    current.totalQty += Number(list.totalQty || 0);
    current.scannedQty += Number(list.scannedQty || 0);
    current.remainingQty = Math.max(current.totalQty - current.scannedQty, 0);
    buckets.set(key, current);
  }
  const order = ["staged", "outbound", "received", "pickup", "greenville", "dtc"];
  return [...buckets.values()].sort((a, b) => order.indexOf(a.category) - order.indexOf(b.category));
}

function homeStatisticsRangeParts() {
  const label = els.overviewRangeSelect?.selectedOptions?.[0]?.textContent || "Current dashboard range";
  const lists = filterListsByOverviewRange(state.lists).map((list) => list.deliveryDate).filter(Boolean).sort();
  if (!lists.length) return { label, dates: "No active delivery dates" };
  return { label, dates: `${formatDisplayDate(lists[0])} through ${formatDisplayDate(lists[lists.length - 1])}` };
}

function homeStatisticsRangeLabel() {
  const parts = homeStatisticsRangeParts();
  return `${parts.label} - ${parts.dates}`;
}

function homeReportDateParams() {
  if (state.overviewRange === "all") return "";
  const days = Number(state.overviewRange || 30);
  if (!days) return "";
  const end = new Date();
  end.setHours(23, 59, 59, 999);
  const start = new Date(end);
  start.setDate(start.getDate() - days + 1);
  start.setHours(0, 0, 0, 0);
  return `?dateFrom=${encodeURIComponent(dateInputValue(start))}&dateTo=${encodeURIComponent(dateInputValue(end))}`;
}

function reportActionCount(action) {
  const report = state.homeReportSummary || {};
  const counts = report.actionCounts || {};
  return Number(counts[action] || 0);
}

function glassQuantitiesForStatistics(overviewLists) {
  const reportRows = state.homeReportSummary?.glassQuantityByType || [];
  if (reportRows.length) {
    return reportRows
      .map((row) => ({
        label: String(row.glassType || row.label || "Other Glass").trim() || "Other Glass",
        qty: Number(row.qty || 0),
      }))
      .filter((row) => row.qty > 0)
      .sort((a, b) => b.qty - a.qty || a.label.localeCompare(b.label));
  }

  // Local-demo fallback: backend list cards only carry totals, but local lists keep row data.
  // Keep this fallback here so the pie chart still works when running without the API.
  const counts = new Map();
  for (const list of overviewLists) {
    for (const item of list.items || []) {
      const label = glassTypeLabel(item);
      counts.set(label, (counts.get(label) || 0) + itemPieceQty(item));
    }
  }
  return [...counts.entries()]
    .map(([label, qty]) => ({ label, qty }))
    .filter((row) => row.qty > 0)
    .sort((a, b) => b.qty - a.qty || a.label.localeCompare(b.label));
}

function renderHomeStatsChart(overviewLists) {
  if (!els.homeStatsChart) return;
  const entries = glassQuantitiesForStatistics(overviewLists);
  const totalQty = entries.reduce((sum, row) => sum + Number(row.qty || 0), 0);

  if (!entries.length || !totalQty) {
    els.homeStatsChart.innerHTML = `
      <div class="statistics-chart-heading">
        <div>
          <strong>Glass types by quantity</strong>
          <span>No glass quantity data yet.</span>
        </div>
        <button class="statistics-chart-expand" type="button" data-open-statistics-chart>Open full chart</button>
      </div>
      <div class="statistics-chart-empty">Import delivery lists to populate the glass-type pie chart.</div>
    `;
    return;
  }

  let cursor = 0;
  const slices = entries.map((entry, index) => {
    const start = cursor;
    const percent = (Number(entry.qty || 0) / totalQty) * 100;
    cursor += percent;
    return `var(--pie-${(index % 8) + 1}) ${start.toFixed(3)}% ${cursor.toFixed(3)}%`;
  });

  const legendRows = entries
    .slice(0, 7)
    .map((entry, index) => {
      const percent = totalQty ? (Number(entry.qty || 0) / totalQty) * 100 : 0;
      return `
        <div class="statistics-pie-legend-row">
          <i style="--slice-color: var(--pie-${(index % 8) + 1})"></i>
          <span>${escapeHtml(entry.label)}</span>
          <strong>${escapeHtml(entry.qty)} pcs <em>${formatPercent(percent)}</em></strong>
        </div>
      `;
    })
    .join("");
  const extraCount = Math.max(entries.length - 7, 0);
  const topEntry = entries[0];
  const topPercent = topEntry && totalQty ? (Number(topEntry.qty || 0) / totalQty) * 100 : 0;

  els.homeStatsChart.innerHTML = `
    <div class="statistics-chart-heading">
      <div>
        <strong>Glass mix by quantity</strong>
        <span>${escapeHtml(totalQty)} total pieces in this range</span>
      </div>
      <div class="statistics-chart-heading-actions">
        <div class="statistics-chart-highlight">
          <small>Top type</small>
          <b>${escapeHtml(topEntry?.label || "-")}</b>
          <span>${topEntry ? `${escapeHtml(topEntry.qty)} pcs | ${formatPercent(topPercent)}` : "No data"}</span>
        </div>
        <button class="statistics-chart-expand" type="button" data-open-statistics-chart>Open full chart</button>
      </div>
    </div>
    <div class="statistics-pie-layout">
      <div class="statistics-pie" style="background: conic-gradient(${slices.join(", ")})">
        <span>${escapeHtml(totalQty)}<small>pieces</small></span>
      </div>
      <div class="statistics-pie-legend">
        ${legendRows}
        ${extraCount ? `<div class="statistics-pie-more">+${escapeHtml(extraCount)} more glass types</div>` : ""}
      </div>
    </div>
  `;
}


function statisticsChartDataset(metric = state.homeChartMetric) {
  const overviewLists = filterListsByOverviewRange(state.lists);
  const report = state.homeReportSummary || {};

  if (metric === "stages") {
    return {
      title: "Stage completion",
      subtitle: "Completion percentage for every stage in the selected dashboard range.",
      suffix: "%",
      entries: homeStageBreakdown(overviewLists).map((stage) => ({
        label: stage.label,
        value: stage.totalQty ? Math.round((stage.scannedQty / stage.totalQty) * 100) : 0,
        detail: `${stage.scannedQty} / ${stage.totalQty} pieces`,
      })),
    };
  }

  if (metric === "operators") {
    return {
      title: "Scans by operator",
      subtitle: "Recorded scan activity by user for the selected dashboard range.",
      suffix: "",
      entries: (report.scansByOperator || []).map((row) => ({
        label: row.user || "Unknown user",
        value: Number(row.scans || 0),
        detail: `${Number(row.scans || 0)} scans`,
      })),
    };
  }

  if (metric === "activity") {
    const entries = [
      ["Manual scans", Number(report.manualScanCount || 0)],
      ["Bad scans", Number(report.badScanCount || 0)],
      ["Duplicate scans", Number(report.duplicateScanCount || 0)],
      ["Rack actions", Number(report.rackActionCount || 0)],
      ["Bay actions", Number(report.bayActionCount || 0)],
      ["User actions", Number(report.userActionCount || 0)],
    ];
    return {
      title: "System activity",
      subtitle: "Scan exceptions and operational actions in the selected dashboard range.",
      suffix: "",
      entries: entries.map(([label, value]) => ({ label, value, detail: `${value} events` })),
    };
  }

  if (metric === "remakes") {
    const remake = selectedRangeRemakeStats(overviewLists);
    return {
      title: "Remakes in selected range",
      subtitle: "Remake pieces and distinct remake lines for the active dashboard filter.",
      suffix: "",
      entries: [
        { label: "Remake pieces", value: Number(remake.qty || 0), detail: `${Number(remake.qty || 0)} pieces` },
        { label: "Remake lines", value: Number(remake.rows || 0), detail: `${Number(remake.rows || 0)} lines` },
      ],
    };
  }

  if (metric === "work") {
    const stageRows = homeStageBreakdown(overviewLists);
    return {
      title: "Scanned and open work by stage",
      subtitle: "Piece counts completed versus still open for every stage in the selected dashboard range.",
      suffix: "",
      entries: stageRows.flatMap((stage) => [
        {
          label: `${stage.label} - Scanned`,
          value: Number(stage.scannedQty || 0),
          detail: `${Number(stage.scannedQty || 0)} scanned pieces`,
        },
        {
          label: `${stage.label} - Open`,
          value: Math.max(Number(stage.totalQty || 0) - Number(stage.scannedQty || 0), 0),
          detail: `${Math.max(Number(stage.totalQty || 0) - Number(stage.scannedQty || 0), 0)} open pieces`,
        },
      ]),
    };
  }

  return {
    title: "Glass mix by quantity",
    subtitle: "Piece quantity by glass type for the selected dashboard range.",
    suffix: "",
    entries: glassQuantitiesForStatistics(overviewLists).map((row) => ({
      label: row.label,
      value: Number(row.qty || 0),
      detail: `${Number(row.qty || 0)} pieces`,
    })),
  };
}

function filteredStatisticsChartEntries(dataset) {
  const query = String(state.homeChartQuery || "").trim().toLowerCase();
  const limitValue = String(state.homeChartLimit || "all");
  const sortMode = String(state.homeChartSort || "value-desc");

  let entries = (dataset.entries || []).filter((entry) => Number(entry.value || 0) >= 0);

  if (query) {
    entries = entries.filter((entry) =>
      `${entry.label || ""} ${entry.detail || ""}`.toLowerCase().includes(query),
    );
  }

  entries = entries.slice().sort((a, b) => {
    if (sortMode === "label-asc") return String(a.label || "").localeCompare(String(b.label || ""), undefined, { numeric: true });
    if (sortMode === "label-desc") return String(b.label || "").localeCompare(String(a.label || ""), undefined, { numeric: true });
    if (sortMode === "value-asc") return Number(a.value || 0) - Number(b.value || 0) || String(a.label || "").localeCompare(String(b.label || ""));
    return Number(b.value || 0) - Number(a.value || 0) || String(a.label || "").localeCompare(String(b.label || ""));
  });

  const totalMatches = entries.length;
  const numericLimit = limitValue === "all" ? 0 : Number(limitValue || 0);
  if (numericLimit > 0) entries = entries.slice(0, numericLimit);

  return { entries, totalMatches };
}

function renderStatisticsChartModal() {
  if (!els.statsChartModalCanvas) return;

  const dataset = statisticsChartDataset(state.homeChartMetric);
  const allEntryCount = (dataset.entries || []).length;
  const filtered = filteredStatisticsChartEntries(dataset);
  const entries = filtered.entries;
  const total = entries.reduce((sum, entry) => sum + Number(entry.value || 0), 0);
  const maxValue = Math.max(...entries.map((entry) => Number(entry.value || 0)), 1);

  if (els.statsChartModalTitle) els.statsChartModalTitle.textContent = dataset.title;
  if (els.statsChartModalSubtitle) {
    els.statsChartModalSubtitle.textContent = `${dataset.subtitle} ${homeStatisticsRangeLabel()}`;
  }
  if (els.statsChartMetricSelect) els.statsChartMetricSelect.value = state.homeChartMetric;
  if (els.statsChartViewSelect) els.statsChartViewSelect.value = state.homeChartView;
  if (els.statsChartSortSelect) els.statsChartSortSelect.value = state.homeChartSort;
  if (els.statsChartLimitSelect) els.statsChartLimitSelect.value = state.homeChartLimit;
  if (els.statsChartFilterInput && els.statsChartFilterInput.value !== state.homeChartQuery) {
    els.statsChartFilterInput.value = state.homeChartQuery;
  }
  if (els.statsChartResultCount) {
    els.statsChartResultCount.textContent = `Showing ${entries.length} of ${filtered.totalMatches} matching categories (${allEntryCount} total)`;
  }
  [els.statsChartMetricSelect, els.statsChartViewSelect, els.statsChartSortSelect, els.statsChartLimitSelect].forEach((select) => {
    if (select) syncCustomSelect(select);
  });

  if (!entries.length) {
    els.statsChartModalCanvas.innerHTML = `<div class="statistics-chart-modal-empty">No data is available for this chart in the selected range.</div>`;
    return;
  }

  if (state.homeChartView === "donut") {
    let cursor = 0;
    const slices = entries.map((entry, index) => {
      const start = cursor;
      const percent = total ? (Number(entry.value || 0) / total) * 100 : 0;
      cursor += percent;
      return `var(--pie-${(index % 8) + 1}) ${start.toFixed(3)}% ${cursor.toFixed(3)}%`;
    });

    els.statsChartModalCanvas.innerHTML = `
      <div class="statistics-chart-modal-donut-layout">
        <div class="statistics-chart-modal-donut" style="background: conic-gradient(${slices.join(", ")})">
          <span>${escapeHtml(total)}<small>Total</small></span>
        </div>
        <div class="statistics-chart-modal-legend">
          ${entries.map((entry, index) => {
            const percent = total ? (Number(entry.value || 0) / total) * 100 : 0;
            return `
              <div>
                <i style="--chart-color: var(--pie-${(index % 8) + 1})"></i>
                <span>${escapeHtml(entry.label)}</span>
                <strong>${escapeHtml(entry.value)}${escapeHtml(dataset.suffix)} <small>${formatPercent(percent)}</small></strong>
              </div>
            `;
          }).join("")}
        </div>
      </div>
    `;
    return;
  }

  els.statsChartModalCanvas.innerHTML = `
    <div class="statistics-chart-modal-bars">
      ${entries.map((entry, index) => {
        const width = Math.max((Number(entry.value || 0) / maxValue) * 100, Number(entry.value || 0) ? 3 : 0);
        return `
          <article>
            <header><strong>${escapeHtml(entry.label)}</strong><span>${escapeHtml(entry.value)}${escapeHtml(dataset.suffix)}</span></header>
            <div class="statistics-chart-modal-bar-track"><i style="width:${width}%; --chart-color: var(--pie-${(index % 8) + 1})"></i></div>
            <small>${escapeHtml(entry.detail || "")}</small>
          </article>
        `;
      }).join("")}
    </div>
  `;
}

function openStatisticsChartModal() {
  if (!els.statsChartModal || !els.statsChartBackdrop) return;
  els.statsChartModal.hidden = false;
  els.statsChartBackdrop.hidden = false;
  renderStatisticsChartModal();
  updateModalScrollLock();
}

function closeStatisticsChartModal() {
  if (els.statsChartModal) els.statsChartModal.hidden = true;
  if (els.statsChartBackdrop) els.statsChartBackdrop.hidden = true;
  updateModalScrollLock();
}

function selectedRangeRemakeStats(overviewLists = []) {
  const report = state.homeReportSummary || {};
  const backendQty = Number(report.rangeRemakeQty ?? report.remakeRangeQty ?? 0);
  const backendCount = Number(report.rangeRemakeCount ?? report.remakeRangeCount ?? 0);

  if (backendQty || backendCount) {
    return { qty: backendQty, rows: backendCount };
  }

  const seen = new Set();
  let qty = 0;
  let rows = 0;

  for (const list of overviewLists || []) {
    for (const item of list.items || []) {
      if (!isRemakeItem(item)) continue;
      const key = `${list.deliveryDate || ""}:${item.sourceId || item.id || item.order}-${item.item}`;
      if (seen.has(key)) continue;
      seen.add(key);
      rows += 1;
      qty += itemPieceQty(item);
    }
  }

  return { qty, rows };
}

function renderMonthlyRemakes(overviewLists = []) {
  if (!els.homeMonthlyRemakes) return;
  const stats = selectedRangeRemakeStats(overviewLists);
  const rangeParts = homeStatisticsRangeParts();
  els.homeMonthlyRemakes.innerHTML = `
    <div class="statistics-remake-card ${stats.qty ? "notice" : "ok"}">
      <small>Remakes</small>
      <strong>${escapeHtml(stats.qty)}</strong>
      <span>Filtered range</span>
      <em>${escapeHtml(stats.rows)} remake row${stats.rows === 1 ? "" : "s"}</em>
      <b>${escapeHtml(rangeParts.label)}</b>
    </div>
  `;
}

function renderHomeStatistics(overviewLists, overview) {
  const report = state.homeReportSummary || {};
  const stages = homeStageBreakdown(overviewLists);
  const badScans = Number(report.badScanCount || 0);
  const duplicateScans = Number(report.duplicateScanCount || 0);
  const sdiCount = Number(report.sdiCount || 0);
  const manualScans = Number(report.manualScanCount || reportActionCount("manual_scan") || 0);
  const bayOverrides = Number(report.bayOverrideCount || reportActionCount("indian_trail_receive_bay_override") || 0);
  const resetScans = reportActionCount("reset_scans");
  const manualEdits = Number(report.manualEditCount || reportActionCount("manual_edit") || 0);
  const rackActions = Number(report.rackActionCount || 0);
  const bayActions = Number(report.bayActionCount || 0);
  const userActions = Number(report.userActionCount || 0);
  const topOperator = (report.scansByOperator || [])[0];

  // Statistics panel is the single source for dashboard KPI boxes.
  // Keep the top page heading clean, and add future KPI cards here instead.
  if (els.homeStatisticsRangeText) {
    const rangeParts = homeStatisticsRangeParts();
    els.homeStatisticsRangeText.innerHTML = `<b>${escapeHtml(rangeParts.label)}</b><span>${escapeHtml(rangeParts.dates)}</span>`;
  }

  if (els.overviewStats) {
    els.overviewStats.innerHTML = [
      miniStat("Delivery Progress", formatPercent(overview.deliveryPercent), `${overview.scannedQty}/${overview.totalQty} pieces`),
      miniStat("On-Time / Late", `${formatPercent(overview.onTimePercent)} / ${overview.lateQty}`, `${overview.onTimeQty} on time`),
      miniStat("Open Work", overview.remainingQty, "Pieces remaining"),
      miniStat("Delivery Lists", overview.totalLists, "In selected range"),
    ].join("");
  }

  renderHomeStatsChart(overviewLists);
  renderMonthlyRemakes(overviewLists);

  if (els.homeUserCard) {
    els.homeUserCard.innerHTML = `
      <div class="statistics-snapshot-grid">
        ${miniStat("Pieces Scanned", `${overview.scannedQty}/${overview.totalQty}`, `${formatPercent(overview.deliveryPercent)} complete`)}
        ${miniStat("Remaining", overview.remainingQty, `${overview.totalLists} active lists`)}
        ${miniStat("Manual Scans", manualScans, "Typed order/item scans")}
        ${miniStat("Bay Overrides", bayOverrides, "Indian Trail receive")}
        ${miniStat("Rack Actions", rackActions, "Rack edits, clears, moves")}
        ${miniStat("Bay Actions", bayActions, "Assign, move, clear, SDI")}
      </div>
    `;
  }

  if (els.homeRecentLists) {
    els.homeRecentLists.innerHTML = stages.length
      ? stages
          .map((stage) => {
            const percent = stage.totalQty ? (stage.scannedQty / stage.totalQty) * 100 : 0;
            return `
              <article class="statistics-stage-card ${escapeHtml(stage.category)}">
                <div>
                  <strong>${escapeHtml(stage.label)}</strong>
                  <span>${escapeHtml(stage.lists)} lists</span>
                </div>
                <div class="list-card-progress"><span style="width:${Math.min(percent, 100)}%"></span></div>
                <small>${escapeHtml(stage.scannedQty)} / ${escapeHtml(stage.totalQty)} scanned - ${formatPercent(percent)}</small>
              </article>
            `;
          })
          .join("")
      : `<div><strong>No stage data</strong><span>Import delivery lists to populate statistics.</span></div>`;
  }

  if (els.homeActivity) {
    els.homeActivity.innerHTML = [
      `<article class="statistics-health-card ${badScans ? "warning" : "ok"}"><strong>${escapeHtml(badScans)}</strong><span>Bad scans</span></article>`,
      `<article class="statistics-health-card ${duplicateScans ? "notice" : "ok"}"><strong>${escapeHtml(duplicateScans)}</strong><span>Duplicate scans</span></article>`,
      `<article class="statistics-health-card"><strong>${escapeHtml(topOperator?.scans || 0)}</strong><span>${escapeHtml(topOperator?.user || "Top operator")}</span></article>`,
      `<article class="statistics-health-card ${resetScans ? "notice" : "ok"}"><strong>${escapeHtml(resetScans)}</strong><span>Reset scans</span></article>`,
      `<article class="statistics-health-card"><strong>${escapeHtml(manualEdits)}</strong><span>Manual edits</span></article>`,
      `<article class="statistics-health-card"><strong>${escapeHtml(userActions)}</strong><span>User actions</span></article>`,
    ].join("");
  }
}

async function loadHomeReportSummary() {
  if (!state.backend || !hasPermission("view_reports")) return;
  try {
    state.homeReportSummary = await fetchJson(`/api/reports/summary${homeReportDateParams()}`);
    if (state.page === "home") renderHome();
  } catch {
    // Reports are a nice-to-have on the dashboard. Keep the home page usable
    // even when a user lacks report access or the report query fails.
    state.homeReportSummary = null;
  }
}

function openHomeStatisticsReport() {
  const overviewLists = filterListsByOverviewRange(state.lists);
  const overview = aggregateListStats(overviewLists);
  const stages = homeStageBreakdown(overviewLists);
  const report = state.homeReportSummary || {};
  const manualScans = Number(report.manualScanCount || 0);
  const rackActions = Number(report.rackActionCount || 0);
  const bayActions = Number(report.bayActionCount || 0);
  const userActions = Number(report.userActionCount || 0);
  const generatedAt = new Date().toLocaleString();
  const rangeLabel = els.overviewRangeSelect?.selectedOptions?.[0]?.textContent || "Current dashboard range";
  const glassEntries = glassQuantitiesForStatistics(overviewLists);
  const glassRows = glassEntries
    .slice(0, 18)
    .map((row) => `<tr><td>${escapeHtml(row.label)}</td><td>${escapeHtml(row.qty)}</td></tr>`)
    .join("") || `<tr><td colspan="2">No glass type quantity data available.</td></tr>`;
  const monthlyRemakeQty = Number(report.monthlyRemakeQty || 0);
  const monthlyRemakeCount = Number(report.monthlyRemakeCount || 0);
  const monthlyRemakeMonth = report.monthlyRemakeMonth || new Date().toLocaleString(undefined, { month: "long", year: "numeric" });
  const operatorRows = (report.scansByOperator || [])
    .slice(0, 12)
    .map((row) => `<tr><td>${escapeHtml(row.user || "Unknown")}</td><td>${escapeHtml(row.scans || 0)}</td></tr>`)
    .join("") || `<tr><td colspan="2">No operator scan data available.</td></tr>`;
  const incompleteRows = (report.incompleteByDeliveryList || [])
    .slice(0, 12)
    .map((row) => `<tr><td>${escapeHtml(row.deliveryList || "")}</td><td>${escapeHtml(row.itemCount || 0)}</td><td>${escapeHtml(row.remainingQty || 0)}</td></tr>`)
    .join("") || `<tr><td colspan="3">No incomplete-list report data available.</td></tr>`;
  const stageRows = stages
    .map((stage) => {
      const percent = stage.totalQty ? (stage.scannedQty / stage.totalQty) * 100 : 0;
      return `<tr><td>${escapeHtml(stage.label)}</td><td>${escapeHtml(stage.lists)}</td><td>${escapeHtml(stage.scannedQty)} / ${escapeHtml(stage.totalQty)}</td><td>${formatPercent(percent)}</td></tr>`;
    })
    .join("") || `<tr><td colspan="4">No stage data available.</td></tr>`;

  const markup = `<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Delivery Scanner Statistics Report</title>
  <style>
    body { margin: 24px; color: #07122f; font-family: "Segoe UI", Arial, sans-serif; }
    header { border-bottom: 3px solid #072a63; padding-bottom: 12px; margin-bottom: 18px; }
    h1 { margin: 0; color: #041a3d; font-size: 28px; }
    h2 { margin: 20px 0 8px; color: #041a3d; font-size: 18px; }
    p { margin: 5px 0 0; color: #526078; font-weight: 700; }
    .kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 16px 0; }
    .kpis.secondary { margin-top: -6px; }
    .kpi { border: 1px solid #d9e1ee; border-radius: 8px; padding: 10px; background: #f8fafc; }
    .kpi small { display: block; color: #526078; font-weight: 800; }
    .kpi strong { display: block; margin-top: 4px; font-size: 22px; color: #041a3d; }
    table { width: 100%; border-collapse: collapse; font-size: 12px; }
    th, td { border: 1px solid #d9e1ee; padding: 7px 8px; text-align: left; }
    th { background: #eef3fa; color: #041a3d; }
    @media print { body { margin: 0.35in; } button { display: none; } }
  </style>
</head>
<body>
  <button onclick="window.print()">Print / Save PDF</button>
  <header>
    <h1>Delivery Scanner Statistics Report</h1>
    <p>${escapeHtml(rangeLabel)} - Generated ${escapeHtml(generatedAt)}</p>
  </header>
  <section class="kpis">
    <div class="kpi"><small>Delivery Progress</small><strong>${formatPercent(overview.deliveryPercent)}</strong><span>${escapeHtml(overview.scannedQty)} / ${escapeHtml(overview.totalQty)} pieces</span></div>
    <div class="kpi"><small>On-Time Delivery</small><strong>${formatPercent(overview.onTimePercent)}</strong><span>${escapeHtml(overview.onTimeQty)} on time / ${escapeHtml(overview.lateQty)} late</span></div>
    <div class="kpi"><small>Manual Scans</small><strong>${escapeHtml(manualScans)}</strong><span>Typed order/item scans</span></div>
    <div class="kpi"><small>Monthly Remakes</small><strong>${escapeHtml(monthlyRemakeQty)}</strong><span>${escapeHtml(monthlyRemakeCount)} rows - ${escapeHtml(monthlyRemakeMonth)}</span></div>
  </section>
  <section class="kpis secondary">
    <div class="kpi"><small>Bad Scans</small><strong>${escapeHtml(report.badScanCount || 0)}</strong><span>Needs review</span></div>
    <div class="kpi"><small>Duplicate Scans</small><strong>${escapeHtml(report.duplicateScanCount || 0)}</strong><span>Prevented by system</span></div>
    <div class="kpi"><small>Rack Actions</small><strong>${escapeHtml(rackActions)}</strong><span>Clears, moves, edits</span></div>
    <div class="kpi"><small>Bay / User Actions</small><strong>${escapeHtml(bayActions + userActions)}</strong><span>Admin and bay activity</span></div>
  </section>
  <h2>Glass Types by Quantity</h2>
  <table><thead><tr><th>Glass Type</th><th>Qty</th></tr></thead><tbody>${glassRows}</tbody></table>
  <h2>Stage Breakdown</h2>
  <table><thead><tr><th>Stage</th><th>Lists</th><th>Scanned Pieces</th><th>Complete</th></tr></thead><tbody>${stageRows}</tbody></table>
  <h2>Scans by Operator</h2>
  <table><thead><tr><th>Operator</th><th>Scans</th></tr></thead><tbody>${operatorRows}</tbody></table>
  <h2>Incomplete Delivery Lists</h2>
  <table><thead><tr><th>Delivery List</th><th>Rows</th><th>Remaining Qty</th></tr></thead><tbody>${incompleteRows}</tbody></table>
  <script>
    window.addEventListener("afterprint", () => {
      if (window.opener && !window.opener.closed) window.opener.postMessage({ type: "delivery-print-complete" }, window.opener.location.origin);
      setTimeout(() => window.close(), 100);
    });
    window.addEventListener("load", () => setTimeout(() => window.print(), 300));
  </script>
</body>
</html>`;

  state.restoreFullscreenAfterPrint = Boolean(document.fullscreenElement);
  const win = window.open("", "deliveryStatisticsPrintWindow", "popup=yes,width=1120,height=820,resizable=yes,scrollbars=yes");
  if (!win) {
    showInlineError("Allow popups to generate the statistics PDF report.");
    return;
  }
  win.document.open();
  win.document.write(markup);
  win.document.close();
}

function stageProgressSegments(lists) {
  const total = lists.reduce((sum, list) => sum + Number(list.totalQty || 0), 0);
  if (!total) return [];
  const order = ["staged", "outbound", "received", "pickup", "greenville", "dtc"];
  const buckets = new Map();
  for (const list of lists) {
    const category = stageCategory(list);
    const current = buckets.get(category) || { category, label: stageLabel(list), qty: 0 };
    current.qty += Number(list.scannedQty || 0);
    buckets.set(category, current);
  }
  return [...buckets.values()]
    .sort((a, b) => order.indexOf(a.category) - order.indexOf(b.category))
    .map((segment) => ({ ...segment, percent: Math.min((segment.qty / total) * 100, 100) }));
}

function progressWidth(percent) {
  const value = Math.min(Math.max(Number(percent || 0), 0), 100);
  return value > 0 ? Math.max(value, 1.25) : 0;
}

function renderStackedProgress(lists, stats) {
  const segments = stageProgressSegments(lists);
  const segmentHtml = segments.length
    ? segments.map((segment) => `<span class="stage-segment ${escapeHtml(segment.category)}" style="width:${progressWidth(segment.percent)}%;" title="${escapeHtml(segment.label)} ${segment.qty}"></span>`).join("")
    : `<span style="width:0%"></span>`;
  return `
    <div class="progress-line">
      <span>Progress:</span>
      <div class="list-card-progress stacked">${segmentHtml}</div>
      <strong>${formatPercent(stats.deliveryPercent)}</strong>
    </div>
  `;
}

function filteredDeliveryLists() {
  const search = state.homeSearch.trim().toLowerCase();
  return state.lists.filter((list) => {
    const matchesStage = state.homeStageFilter === "all" || `${list.stage} ${list.scanner}`.toLowerCase().includes(state.homeStageFilter.toLowerCase());
    if (!matchesStage) return false;
    if (!search) return true;
    return [list.label, list.stage, list.scanner, list.deliveryDate].join(" ").toLowerCase().includes(search);
  });
}

function deliveryListCard(list, extraClass = "") {
  const percent = progressPercent(list);
  const category = stageCategory(list);
  const onTime = Number(list.onTimePercent || 0);
  const title = stageLabel(list);
  const scannedQty = Number(list.scannedQty || 0);
  const totalQty = Number(list.totalQty || 0);
  const remainingQty = Math.max(totalQty - scannedQty, 0);
  const onTimeText = category === "outbound" ? `On-time ${formatPercent(onTime)}` : stageLabel(list);
  return `
    <article class="delivery-list-card ${escapeHtml(category)} ${escapeHtml(extraClass)}" data-open-list="${escapeHtml(list.id)}">
      <div class="delivery-card-main">
        <span class="delivery-stage-dot" aria-hidden="true"></span>
        <div class="delivery-card-title-copy">
          <strong>${escapeHtml(title)}</strong>
          <small>${escapeHtml(onTimeText)}</small>
        </div>
        <span class="delivery-card-action" aria-hidden="true">Open</span>
      </div>
      <div class="delivery-card-metrics">
        <span><b>${escapeHtml(scannedQty)}</b><small>Scanned</small></span>
        <span><b>${escapeHtml(remainingQty)}</b><small>Open</small></span>
        <span><b>${escapeHtml(totalQty)}</b><small>Pieces</small></span>
      </div>
      <div class="progress-line delivery-card-progress"><span>Progress</span><div class="list-card-progress"><span style="width:${progressWidth(percent)}%"></span></div><strong>${formatPercent(percent)}</strong></div>
    </article>
  `;
}

function renderTodayProgress() {
  if (!els.todayStageGrid) return;
  const key = dashboardDateKey();
  const isActualToday = key === todayKey();
  const lists = state.lists
    .filter((list) => list.deliveryDate === key)
    .sort((a, b) => {
      return stageSort(a) - stageSort(b) || a.label.localeCompare(b.label);
    });
  if (els.todayDateLabel) {
    els.todayDateLabel.textContent = formatDisplayDate(key);
  }
  els.todayStageGrid.innerHTML = lists.length
    ? lists
        .map((list) => {
          const percent = progressPercent(list);
          return `
            <article class="today-stage-card ${escapeHtml(stageCategory(list))}" data-open-list="${escapeHtml(list.id)}">
              <div>
                <span>${escapeHtml(stageLabel(list))}</span>
                <strong>${escapeHtml(list.scannedQty || 0)} / ${escapeHtml(list.totalQty || 0)}</strong>
              </div>
              <div class="list-card-progress"><span style="width:${Math.min(percent, 100)}%"></span></div>
              <small>${formatPercent(percent)}</small>
            </article>
          `;
        })
        .join("")
    : `<div class="admin-empty">No delivery lists are loaded for ${formatDisplayDate(key)}.</div>`;
}

function renderHomeStageFilter() {
  if (!els.homeStageFilter) return;
  const current = state.homeStageFilter || "all";
  const stageOptions = uniqueText(
    state.lists
      .map((list) => stageLabel(list) || list.stage || list.scanner || "")
      .filter(Boolean),
  ).sort((a, b) => a.localeCompare(b));

  els.homeStageFilter.innerHTML = [
    `<option value="all">All stages</option>`,
    ...stageOptions.map((stage) => `<option value="${escapeHtml(stage)}">${escapeHtml(stage)}</option>`),
  ].join("");
  els.homeStageFilter.value = stageOptions.some((stage) => stage.toLowerCase() === String(current).toLowerCase()) ? current : "all";
  state.homeStageFilter = els.homeStageFilter.value;
}

function renderHome() {
  if (!els.homePage) return;
  renderHomeStageFilter();
  const overviewLists = filterListsByOverviewRange(state.lists);
  const overview = aggregateListStats(overviewLists);
  if (els.homeWelcome) {
    els.homeWelcome.textContent = `Signed in as ${state.user?.displayName || state.user?.username || "Demo user"}`;
  }
  if (els.overviewRangeSelect && els.overviewRangeSelect.value !== state.overviewRange) {
    els.overviewRangeSelect.value = state.overviewRange;
  }
  renderHomeStatistics(overviewLists, overview);
  renderTodayProgress();
  const filtered = filteredDeliveryLists();
  const dateGroups = listsByDeliveryDate(filtered);
  const totalHomePages = Math.max(1, Math.ceil(dateGroups.length / state.homePageSize));
  state.homePageIndex = Math.min(Math.max(state.homePageIndex, 1), totalHomePages);
  const pageStart = (state.homePageIndex - 1) * state.homePageSize;
  const visibleDateGroups = dateGroups.slice(pageStart, pageStart + state.homePageSize);
  if (!dateGroups.some((group) => group.date === state.expandedDeliveryDate)) state.expandedDeliveryDate = "";
  if (els.homeListCount) els.homeListCount.textContent = `${dateGroups.length} dates / ${filtered.length} stages`;
  if (els.homeListGrid) {
    els.homeListGrid.innerHTML = visibleDateGroups.length
      ? visibleDateGroups
          .map((group) => {
            const stats = aggregateListStats(group.lists);
            return `
              <details class="delivery-date-group" data-delivery-date="${escapeHtml(group.date)}" ${group.date === state.expandedDeliveryDate ? "open" : ""}>
                <summary>
                  <span class="home-date-chevron" aria-hidden="true"></span>
                  <span class="home-date-summary-main">
                    <strong>${escapeHtml(formatDisplayDate(group.date))}</strong>
                    <small>${escapeHtml(group.lists.length)} stages - Delivery on-time ${formatPercent(stats.onTimePercent)}</small>
                    ${renderStackedProgress(group.lists, stats)}
                  </span>
                  <span class="delivery-date-total"><small>Pieces</small><strong>${escapeHtml(stats.pieceQty || stats.totalQty)}</strong></span>
                </summary>
                <div class="delivery-stage-list">
                  ${group.lists.map((list) => deliveryListCard(list, "date-grouped")).join("")}
                </div>
              </details>
            `;
          })
          .join("")
      : `<div class="admin-empty">No delivery lists match.</div>`;
    els.homeListGrid.querySelectorAll(".delivery-date-group").forEach((details) => {
      details.addEventListener("toggle", () => {
        details.classList.remove("is-expanding");
        if (!details.open) return;
        void details.offsetWidth;
        details.classList.add("is-expanding");
        state.expandedDeliveryDate = details.dataset.deliveryDate || "";
        els.homeListGrid.querySelectorAll(".delivery-date-group").forEach((other) => {
          if (other !== details) other.open = false;
        });
      });
      details.addEventListener("animationend", () => details.classList.remove("is-expanding"));
    });
  }
  if (els.homePager) {
    const pagerHtml = `
      <button type="button" data-home-page-action="prev" ${state.homePageIndex <= 1 ? "disabled" : ""}>&lt;</button>
      <span class="pager-summary">Page ${state.homePageIndex} of ${totalHomePages}</span>
      <button type="button" data-home-page-action="next" ${state.homePageIndex >= totalHomePages ? "disabled" : ""}>&gt;</button>
    `;
    els.homePager.innerHTML = pagerHtml;
    if (els.homePagerTop) els.homePagerTop.innerHTML = pagerHtml;
  }
  renderHomeStatistics(overviewLists, overview);
  applyPermissionUi();
}

function showPage(page) {
  if (state.bayEditMode && state.bayHoldingSections.size && page !== "bays") {
    showFloatingNotice("Move all grouped bays out of the temporary holding area before leaving the Bay Map.", "error");
    return;
  }
  if (page === "admin" && !hasAnyPermission(["view_admin", "manage_users", "manage_stations", "edit_delivery_lists"])) page = "home";
  if (page === "bays" && !hasAnyPermission(["view_bays", "view_indian_trail"])) page = "home";
  if (page === "racks" && !hasAnyPermission(["view_racks", "scan_racks", "manage_racks"])) page = "home";
  if (page === "home") state.expandedDeliveryDate = "";
  state.page = page;
  document.body.dataset.page = page;
  window.scrollTo({ top: 0, left: 0, behavior: "auto" });
  document.querySelectorAll(".page-view").forEach((view) => {
    view.hidden = view.id !== `${page === "bays" ? "bayMap" : page}Page`;
  });
  document.querySelectorAll("[data-page-target]").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.pageTarget === page);
  });
  if (page === "home") renderHome();
  if (page === "scan") renderScanPage();
  if (page === "racks") refreshRacksPage().catch((error) => showInlineError(error.message, true));
  if (page === "bays") refreshBayMapPage().catch((error) => showInlineError(error.message));
  if (page === "admin") refreshAdminPage().catch((error) => showInlineError(error.message));
  if (page === "scan") els.scanInput?.focus();
}

async function showOutboundOverrideDialog(payload, scanText, options = {}) {
  await ensureRacksLoaded().catch(() => {});
  const racks = (state.racks || []).filter((rack) => {
    const status = String(rack.status || "").toLowerCase();
    return rack.active !== false && !["closed", "complete", "completed", "in transit"].includes(status);
  });
  const defaultRack = state.selectedRackCode && racks.some((rack) => rack.code === state.selectedRackCode)
    ? state.selectedRackCode
    : (racks.find((rack) => rack.code === "T")?.code || racks[0]?.code || "");

  return new Promise((resolve) => {
    document.querySelector(".outbound-override-backdrop")?.remove();
    const item = payload.outboundItem || payload.lastScan?.item || {};
    const dialog = document.createElement("div");
    dialog.className = "outbound-override-backdrop";
    dialog.innerHTML = `
      <section class="outbound-override-dialog" role="dialog" aria-modal="true" aria-labelledby="outboundOverrideTitle">
        <button type="button" class="outbound-override-close" data-outbound-override-cancel aria-label="Close outbound override">&times;</button>
        <div class="outbound-override-icon" aria-hidden="true"></div>
        <div class="outbound-override-copy">
          <span class="outbound-override-eyebrow">Outbound safety check</span>
          <h2 id="outboundOverrideTitle">${escapeHtml(payload.outboundOverrideMessage || "Outbound scan needs review")}</h2>
          <p>${escapeHtml(payload.outboundOverrideReason || "Review this scan before allowing it to continue.")}</p>
        </div>
        <div class="outbound-override-item">
          <span><small>Order</small><strong>${escapeHtml(item.order || "-")}</strong></span>
          <span><small>Item</small><strong>${escapeHtml(item.item || "-")}</strong></span>
          <span><small>Customer</small><strong>${escapeHtml(item.customer || "-")}</strong></span>
          <span><small>Size</small><strong>${escapeHtml(item.dimensions || "-")}</strong></span>
        </div>
        <label class="outbound-override-field">
          <span>Transportation method for this piece</span>
          <select id="outboundOverrideRackSelect">
            <option value="">Choose an open rack or truck...</option>
            ${racks.map((rack) => `<option value="${escapeHtml(rack.code)}" ${rack.code === defaultRack ? "selected" : ""}>${rackOptionLabel(rack)}</option>`).join("")}
          </select>
        </label>
        <div class="outbound-override-actions">
          <button type="button" data-outbound-override-cancel>Cancel scan</button>
          <button type="button" data-outbound-override-confirm>Override and scan outbound</button>
        </div>
      </section>
    `;

    const close = (confirmed) => {
      dialog.remove();
      document.body.classList.remove("modal-scroll-locked");
      resolve(Boolean(confirmed));
    };

    dialog.addEventListener("click", (event) => {
      if (event.target === dialog || event.target.closest("[data-outbound-override-cancel]")) {
        close(false);
        return;
      }
      if (event.target.closest("[data-outbound-override-confirm]")) {
        const rackCode = dialog.querySelector("#outboundOverrideRackSelect")?.value || "";
        if (!rackCode) {
          showFloatingNotice("Choose a rack or truck before overriding outbound scan safety.", "error");
          dialog.querySelector("#outboundOverrideRackSelect")?.focus();
          return;
        }
        close(true);
        processScan(scanText, { ...options, outboundOverride: true, rackCode }).catch((error) => showInlineError(error.message, false));
      }
    });

    document.body.appendChild(dialog);
    document.body.classList.add("modal-scroll-locked");
    dialog.querySelector("#outboundOverrideRackSelect")?.focus();
  });
}

async function processScan(rawScan, options = {}) {
  const scanText = rawScan.trim();
  if (!scanText || !state.activeListId) return;
  if (state.backend) {
    const indianTrailReceive =
      hasPermission("indian_trail_receive") &&
      /indian trail/i.test(`${state.meta?.stage || ""} ${currentScanStation()}`);
    if (indianTrailReceive) {
      if (state.bayOverrideMode === "manual" && !state.selectedBayOverrideCode) {
        showFloatingNotice("Choose a manual Indian Trail bay before scanning, or switch bay assignment back to Auto.", "error");
        els.scanBayOverrideSelect?.focus();
        return;
      }
      const result = await fetchJson("/api/indian-trail/receive", {
        method: "POST",
        body: JSON.stringify({
          listId: state.activeListId,
          barcode: scanText,
          bayCode: state.bayOverrideMode === "manual" ? state.selectedBayOverrideCode || "" : "",
          isManual: Boolean(options.isManual),
          ...requestContext(),
        }),
      });
      await activateList(state.activeListId, false);
      state.lastScan = result.lastScan || state.lastScan;
      scanFlash(result.ok ? "success" : "error");
      if (result?.message) {
        const lastItem = result.lastScan?.item || {};
        const bayPrompt = result.ok && result.bayCode
          ? `Place order ${lastItem.order || ""}${lastItem.item ? `-${lastItem.item}` : ""} in Bay ${result.bayCode}.`
          : result.message;
        showFloatingNotice(bayPrompt, result.ok ? (/\bSDI|Rush\b/i.test(result.message) ? "notice" : "success") : "error");
      }
      renderScanPage();
      void refreshBayMapPage().catch(() => {});
      return;
    }
    const payload = await fetchJson("/api/scans", {
      method: "POST",
      body: JSON.stringify({
        listId: state.activeListId,
        barcode: scanText,
        rackCode: options.rackCode || (isStagingScanContext() ? state.selectedRackCode : ""),
        outboundOverride: Boolean(options.outboundOverride),
        isManual: Boolean(options.isManual),
        ...requestContext(),
      }),
    });
    applyBackendPayload(payload);
    if (payload.outboundOverrideRequired) {
      scanFlash("error");
      renderScanPage();
      await showOutboundOverrideDialog(payload, scanText, options);
      return;
    }
    if (payload.message) {
      showFloatingNotice(payload.message, payload.lastScan?.ok ? "success" : "notice");
    }
    if (payload.racks) {
      state.racks = payload.racks || state.racks;
      state.rackSummary = payload.rackSummary || state.rackSummary;
    } else if (isStagingScanContext() && state.racks.length) {
      void ensureRacksLoaded().catch(() => {});
    }
    scanFlash(payload.lastScan?.ok ? "success" : payload.lastScan?.eventType === "duplicate" || payload.lastScan?.eventType === "notice" ? "notice" : "error");
    renderScanPage();
    return;
  }
  processLocalScan(scanText, options);
}

async function submitManualScan() {
  const order = digitsOnly(els.manualOrderInput?.value || "");
  const item = digitsOnly(els.manualItemInput?.value || "");
  if (!order || !item) {
    showInlineError("Manual scan needs an order number and item number.", false);
    return;
  }
  await processScan(canonicalBarcode(order, item), { isManual: true });
  if (els.manualOrderInput) els.manualOrderInput.value = "";
  if (els.manualItemInput) els.manualItemInput.value = "";
  els.scanInput?.focus();
}

function processLocalScan(scanText, options = {}) {
  const recovered = recoverScan(scanText);
  const timestamp = new Date().toISOString();
  if (!recovered.ok) {
    const entry = { ok: false, eventType: "error", barcode: scanText, message: "BAD SCAN format", reason: recovered.reason, time: timestamp };
    state.errors.unshift(entry);
    state.recent.unshift(entry);
    state.lastScan = entry;
    scanFlash("error");
    showFloatingNotice(`${entry.message}: ${entry.reason}`, "error");
    saveState();
    renderScanPage();
    return;
  }
  const item = recovered.item;
  if (item.scanned >= item.qty) {
    const entry = { ok: false, eventType: "duplicate", barcode: recovered.barcode, item, message: "Item already complete", reason: "Quantity already scanned", time: timestamp };
    state.recent.unshift(entry);
    state.lastScan = entry;
    scanFlash("notice");
    showFloatingNotice(entry.reason, "notice");
    saveState();
    renderScanPage();
    return;
  }
  item.scanned += 1;
  state.selectedId = item.id;
  const entry = { ok: true, eventType: options.isManual ? "manual_scan" : "scan", isManual: Boolean(options.isManual), barcode: recovered.barcode, raw: scanText, item, message: recovered.reason, time: timestamp };  state.recent.unshift(entry);
  state.lastScan = entry;
  scanFlash("success");
  saveState();
  renderScanPage();
}

function buildIndexes() {
  const byOrderItem = new Map();
  const bySuffixItem = new Map();
  for (const item of state.items) {
    const orderItemKey = `${Number(item.order)}-${Number(item.item)}`;
    const orderMatches = byOrderItem.get(orderItemKey) || [];
    orderMatches.push(item);
    byOrderItem.set(orderItemKey, orderMatches);
    const suffixKey = `${pad(item.order, 6).slice(-3)}-${Number(item.item)}`;
    const suffixMatches = bySuffixItem.get(suffixKey) || [];
    suffixMatches.push(item);
    bySuffixItem.set(suffixKey, suffixMatches);
  }
  return { byOrderItem, bySuffixItem };
}

function recoverScan(rawScan) {
  const cleanText = cleanBarcode(rawScan);
  const { byOrderItem, bySuffixItem } = buildIndexes();
  if (/^T200\d{12}$/.test(cleanText)) {
    const order = Number(cleanText.slice(4, 10));
    const item = Number(cleanText.slice(10, 13));
    const matches = byOrderItem.get(`${order}-${item}`) || [];
    if (matches.length === 1) return { ok: true, item: matches[0], barcode: cleanText, reason: "Exact label" };
    if (matches.length > 1) return { ok: false, barcode: cleanText, reason: "Ambiguous delivery-list match" };
  }
  const numbers = digitsOnly(cleanText);
  for (let start = 0; start <= numbers.length - 12; start += 1) {
    const windowText = numbers.slice(start, start + 12);
    const order = Number(windowText.slice(0, 6));
    const item = Number(windowText.slice(6, 9));
    const matches = byOrderItem.get(`${order}-${item}`) || [];
    if (matches.length === 1) return { ok: true, item: matches[0], barcode: canonicalBarcode(order, item), reason: "Recovered order/item" };
    if (matches.length > 1) return { ok: false, barcode: canonicalBarcode(order, item), reason: "Ambiguous delivery-list match" };
  }
  for (let start = 0; start <= numbers.length - 9; start += 1) {
    const windowText = numbers.slice(start, start + 9);
    const suffix = windowText.slice(0, 3);
    const itemNumber = Number(windowText.slice(3, 6));
    const matches = bySuffixItem.get(`${suffix}-${itemNumber}`);
    if (matches && matches.length === 1) {
      const match = matches[0];
      return { ok: true, item: match, barcode: canonicalBarcode(match.order, itemNumber), reason: "Recovered suffix/item" };
    }
    if (matches && matches.length > 1) return { ok: false, barcode: cleanText, reason: "Ambiguous delivery-list match" };
  }
  return { ok: false, barcode: cleanText, reason: "No unique delivery-list match" };
}

async function resetState() {
  if (state.backend) {
    const payload = await fetchJson("/api/reset", {
      method: "POST",
      body: JSON.stringify({ listId: state.activeListId, confirmText: "RESET", ...requestContext() }),
    });
    applyBackendPayload(payload);
    renderScanPage();
    return;
  }
  for (const item of state.items) item.scanned = 0;
  state.recent = [];
  state.errors = [];
  state.selectedId = null;
  state.lastScan = null;
  saveState();
  renderScanPage();
}

function showInlineError(message, needsReview = false) {
  const entry = { ok: false, eventType: needsReview ? "error" : "notice", barcode: "SYSTEM", message: "System notice", reason: message, time: new Date().toISOString() };
  if (needsReview) state.errors.unshift(entry);
  state.recent.unshift(entry);
  state.lastScan = entry;
  scanFlash(needsReview ? "error" : "notice");
  showFloatingNotice(message, needsReview ? "error" : "notice");
  renderScanPage();
}

function showFloatingNotice(message, kind = "notice") {
  let notice = document.getElementById("floatingScanNotice");
  if (!notice) {
    notice = document.createElement("div");
    notice.id = "floatingScanNotice";
    notice.className = "floating-scan-notice";
    document.body.appendChild(notice);
  }
  notice.className = `floating-scan-notice ${kind}`;
  notice.innerHTML = `<strong>${escapeHtml(kind === "success" ? "Scan accepted" : kind === "error" ? "Needs review" : "Notice")}</strong><span>${escapeHtml(message)}</span>`;
  notice.classList.remove("is-hiding");
  window.clearTimeout(notice._hideTimer);
  notice._hideTimer = window.setTimeout(() => {
    notice.classList.add("is-hiding");
  }, 5200);
}

function closeActionFeedback() {
  document.getElementById("actionFeedbackShell")?.remove();
  updateModalScrollLock();
}

function showActionFeedback({
  kind = "success",
  eyebrow = "Update complete",
  title = "Saved successfully",
  message = "",
  details = [],
  primaryLabel = "",
  secondaryLabel = "Done",
  onPrimary = null,
  onSecondary = null,
} = {}) {
  closeActionFeedback();

  const shell = document.createElement("div");
  shell.id = "actionFeedbackShell";
  shell.className = `action-feedback-shell ${kind}`;
  const detailRows = details
    .filter((detail) => detail && detail.value !== undefined && detail.value !== null && String(detail.value).trim())
    .map((detail) => `
      <div class="action-feedback-detail">
        <small>${escapeHtml(detail.label || "Details")}</small>
        <strong>${escapeHtml(detail.value)}</strong>
      </div>
    `)
    .join("");

  shell.innerHTML = `
    <button class="action-feedback-backdrop" type="button" data-action-feedback-close aria-label="Close"></button>
    <section class="action-feedback-panel" role="dialog" aria-modal="true" aria-labelledby="actionFeedbackTitle">
      <div class="action-feedback-icon" aria-hidden="true"><i></i></div>
      <div class="action-feedback-copy">
        <small>${escapeHtml(eyebrow)}</small>
        <h2 id="actionFeedbackTitle">${escapeHtml(title)}</h2>
        ${message ? `<p>${escapeHtml(message)}</p>` : ""}
      </div>
      ${detailRows ? `<div class="action-feedback-details">${detailRows}</div>` : ""}
      <div class="action-feedback-actions">
        ${primaryLabel ? `<button class="action-feedback-primary" type="button" data-action-feedback-primary>${escapeHtml(primaryLabel)}</button>` : ""}
        <button class="action-feedback-secondary" type="button" data-action-feedback-secondary>${escapeHtml(secondaryLabel)}</button>
      </div>
    </section>
  `;

  document.body.appendChild(shell);
  applyLanguageToRoot(shell);
  updateModalScrollLock();

  const closeWithSecondary = async () => {
    try {
      if (typeof onSecondary === "function") await onSecondary();
    } finally {
      closeActionFeedback();
    }
  };

  shell.querySelector("[data-action-feedback-close]")?.addEventListener("click", closeWithSecondary);
  shell.querySelector("[data-action-feedback-secondary]")?.addEventListener("click", closeWithSecondary);
  shell.querySelector("[data-action-feedback-primary]")?.addEventListener("click", async () => {
    try {
      if (typeof onPrimary === "function") await onPrimary();
    } finally {
      closeActionFeedback();
    }
  });
  shell.querySelector("[data-action-feedback-primary], [data-action-feedback-secondary]")?.focus();
}

async function restoreFullscreenAfterManagedPrint() {
  const shouldRestore = Boolean(state.restoreFullscreenAfterPrint);
  state.restoreFullscreenAfterPrint = false;
  window.focus();
  if (!shouldRestore || document.fullscreenElement || !document.fullscreenEnabled) return;

  try {
    await document.documentElement.requestFullscreen();
  } catch {
    showActionFeedback({
      kind: "success",
      eyebrow: "Print complete",
      title: "Return to fullscreen",
      message: "The print window closed. Your browser requires one click to enter fullscreen again.",
      primaryLabel: "Return to fullscreen",
      secondaryLabel: "Stay in windowed mode",
      onPrimary: async () => {
        if (!document.fullscreenElement && document.fullscreenEnabled) {
          await document.documentElement.requestFullscreen();
        }
      },
    });
  }
}

function launchManagedPrint(url, windowName = "deliveryListPrintWindow") {
  state.restoreFullscreenAfterPrint = Boolean(document.fullscreenElement);
  const printWindow = window.open(url, windowName, "popup=yes,width=1180,height=860,resizable=yes,scrollbars=yes");
  if (!printWindow) {
    state.restoreFullscreenAfterPrint = false;
    showInlineError("Allow popups to open the print preview.", false);
    return null;
  }
  printWindow.focus();
  return printWindow;
}

function printCurrentPageManaged() {
  state.restoreFullscreenAfterPrint = Boolean(document.fullscreenElement);
  const afterPrint = () => {
    window.removeEventListener("afterprint", afterPrint);
    restoreFullscreenAfterManagedPrint();
  };
  window.addEventListener("afterprint", afterPrint);
  window.print();
}

async function runGlobalSearch() {
  if (!hasPermission("global_search")) return [];
  const query = els.headerGlobalSearchInput?.value.trim() || "";
  if (query.length < 2) {
    renderGlobalSearchResults([]);
    return [];
  }
  const payload = await fetchJson(`/api/search?q=${encodeURIComponent(query)}`);
  renderGlobalSearchResults(payload.results || []);
  return payload.results || [];
}

function globalSearchProcessClass(text, result = {}) {
  const signal = `${text || ""} ${result.stage || ""} ${result.scanner || ""} ${result.bayCode || ""} ${result.bay || ""} ${result.rackCode || ""} ${result.rackType || ""}`.toLowerCase();
  if (signal.includes("bay")) return "bay";
  if (signal.includes("truck") || result.rackCode === "T" || /^T\d+$/i.test(String(result.rackCode || ""))) return "truck";
  if (signal.includes("rack") || result.rackCode) return "rack";
  if (signal.includes("not scanned") || signal.includes("not started")) return "not-started";
  if (signal.includes("partial") || /\b\d+\s*\/\s*\d+\b/.test(signal)) return "partial";
  if (signal.includes("complete") || signal.includes("received") || signal.includes("inbound")) return "received";
  if (signal.includes("outbound")) return "outbound";
  if (signal.includes("staging")) return "staging";
  if (signal.includes("customer pickup") || /\bcpu\b/.test(signal)) return "cpu";
  if (signal.includes("greenville") || /\bgnv\b/.test(signal)) return "greenville";
  if (signal.includes("dtc") || signal.includes("deliver to customer")) return "dtc";
  return "default";
}

function globalSearchStatusBadges(result) {
  // Global Search should show one current location/process state, not every stage
  // on the delivery date. The backend resolves locationText from latest scan state.
  const label = String(result.locationText || "Not Scanned Yet").trim() || "Not Scanned Yet";
  return `<small class="global-result-status ${globalSearchProcessClass(label, result)}">${escapeHtml(label)}</small>`;
}

function renderGlobalSearchResults(results) {
  if (!els.headerGlobalSearchResults) return;
  if (!results.length) {
    els.headerGlobalSearchResults.hidden = false;
    els.headerGlobalSearchResults.innerHTML = `<div class="no-search-results"><strong>No results</strong><span>No order, item, customer, rack, bay, or route matched that search.</span></div>`;
    return;
  }
  els.headerGlobalSearchResults.hidden = false;
  els.headerGlobalSearchResults.innerHTML = results
    .slice(0, 8)
    .map(
      (result) => {
        const openAttrs = result.bayCode
          ? `data-open-bay="${escapeHtml(result.bayCode)}"`
          : `data-open-list="${escapeHtml(result.deliveryListId)}" data-open-search="${escapeHtml([result.order, result.item].filter(Boolean).join(" "))}"`;
        const destinationLabel = result.bay
          ? `Bay ${result.bay}`
          : result.rackCode
            ? `${result.rackCode === "T" || /^T\d+$/i.test(String(result.rackCode || "")) || /truck/i.test(result.rackType || "") ? "Truck" : "Rack"} ${result.rackName || result.rackCode}`
            : result.stage || "";

        return `
        <button type="button" ${openAttrs}>
          <div class="global-result-main">
            <strong>${escapeHtml(result.order)}-${escapeHtml(result.item)}</strong>
            <span>${escapeHtml(result.customer || "No customer")}</span>
          </div>
          <span class="global-result-job">${escapeHtml(result.job || result.product || "No job/product")}</span>
          <span class="global-result-meta">${escapeHtml(destinationLabel)}${result.deliveryDate ? ` • ${escapeHtml(formatDisplayDate(result.deliveryDate))}` : ""}</span>
          <div class="global-result-status-row">${globalSearchStatusBadges(result)}</div>
        </button>
      `;
      },
    )
    .join("");
}

async function refreshBayMapPage() {
  if (!hasAnyPermission(["view_bays", "view_indian_trail"])) return;
  if (state.backend) {
    const [layout, baysPayload, summary, eventsPayload] = await Promise.all([
      fetchJson("/api/indian-trail/layout"),
      fetchJson("/api/indian-trail/bays"),
      hasPermission("view_indian_trail") ? fetchJson("/api/indian-trail/summary") : Promise.resolve(null),
      fetchJson("/api/indian-trail/events"),
    ]);
    state.bayLayout = layout;
    state.bays = baysPayload.bays || [];
    state.bayEvents = eventsPayload.events || [];
    renderIndianTrailSummary(summary);
    renderBayRouteFlow(summary);
  } else {
    const response = await fetch("data/indian-trail-bay-layout.json");
    state.bayLayout = await response.json();
    state.bays = (state.bayLayout.bays || []).map((bay) => ({ ...bay, assignedQty: 0, capacityQty: bay.autoAssignable ? 1 : 0, status: bay.autoAssignable ? "Empty" : "ManualHold", assignments: [] }));
    state.bayEvents = [];
    renderIndianTrailSummary(null);
    renderBayRouteFlow(null);
  }
  renderBayMapPage();
  maybeShowStaleBayAlert().catch(() => {});
}

function renderBayRouteFlow(summary) {
  if (!els.bayFlowPanel) return;

  const key = dashboardDateKey();
  const dayLists = state.lists.filter((list) => list.deliveryDate === key);
  const outbound = dayLists.find((list) => stageCategory(list) === "outbound");
  const inbound = dayLists.find((list) => stageCategory(list) === "received") || state.lists.find((list) => list.id === summary?.activeInboundListId);

  const inboundQty = Number(inbound?.scannedQty ?? summary?.receivedQty ?? 0);
  const inboundTotal = Number(inbound?.totalQty ?? summary?.indianTrailOutboundTotal ?? summary?.inboundToday ?? 0);

  const outboundQty = Number(summary?.indianTrailOutboundScanned ?? outbound?.scannedQty ?? 0);
  const outboundTotal = inboundTotal || Number(summary?.indianTrailOutboundTotal ?? outbound?.totalQty ?? 0);

  // In Transit is the live count of Indian Trail pieces scanned outbound
  // but not yet received inbound. The backend calculates this item-by-item
  // so the total stays accurate even when partial quantities are received.
  const inTransitQty = Number(summary?.inTransitQty ?? Math.max(outboundQty - inboundQty, 0));
  const inTransitJobCount = Number(summary?.inTransitJobCount || 0);
  const truckQty = Number(summary?.truckInTransitQty || 0);
  const rackQty = Number(summary?.rackInTransitQty || 0);
  const percent = outboundTotal ? Math.min((inboundQty / outboundTotal) * 100, 100) : 0;
  const rackLine = (summary?.racksInTransit || [])
    .slice(0, 5)
    .map((rack) => `${rack.code}: ${rack.qty}`)
    .join(" | ");

  const inTransitPieceLabel = `${inTransitQty} piece${inTransitQty === 1 ? "" : "s"} on the way`;
  const outboundStageLabel = outbound ? outbound.stage : "No outbound list";
  const inboundStageLabel = inbound ? inbound.stage : "No Indian Trail list";

  els.bayFlowPanel.innerHTML = `
    <button
      class="flow-card outbound flow-card-v2 bay-flow-side-card ${outbound ? "is-actionable" : "is-unavailable"}"
      type="button"
      ${outbound ? `data-open-list="${escapeHtml(outbound.id)}"` : "disabled"}
      title="${outbound ? "Open the current Outbound delivery list" : "No Outbound delivery list is available"}"
      aria-label="${outbound ? "Open Outbound delivery list" : "No Outbound delivery list available"}"
    >
      <span class="flow-card-icon outbound" aria-hidden="true"></span>
      <span class="flow-card-copy">
        <small>Outbound sent</small>
        <strong>${escapeHtml(outboundQty)}<span>/${escapeHtml(outboundTotal)}</span></strong>
        <em>${escapeHtml(outboundStageLabel)}</em>
      </span>
      <span class="flow-card-open" aria-hidden="true"><b>${outbound ? "Open list" : "Unavailable"}</b><i></i></span>
    </button>

    <button class="flow-lane flow-lane-v2 transit-lane-button transit-lane-polished" type="button" data-open-transit-manifest title="Open Indian Trail in-transit manifest">
      <span class="flow-truck"><b>${escapeHtml(inTransitPieceLabel)}</b></span>
      <span class="transit-animation transit-animation-v59 transit-animation-truck" aria-hidden="true">
        <span class="transit-route-node transit-route-node-start"></span>
        <span class="transit-route-line"></span>
        <span class="transit-moving-truck">
          <svg viewBox="0 0 92 44" focusable="false" aria-hidden="true">
            <rect class="transit-truck-cargo" x="7" y="7" width="49" height="27" rx="4"></rect>
            <path class="transit-truck-cab" d="M56 15h17l11 11v8H56V15Z"></path>
            <path class="transit-truck-window" d="M62 18h9l7 7H62v-7Z"></path>
            <rect class="transit-truck-bumper" x="82" y="30" width="7" height="4" rx="1.5"></rect>
            <circle class="transit-truck-wheel" cx="23" cy="36" r="6"></circle>
            <circle class="transit-truck-wheel" cx="70" cy="36" r="6"></circle>
            <circle class="transit-truck-hub" cx="23" cy="36" r="2.5"></circle>
            <circle class="transit-truck-hub" cx="70" cy="36" r="2.5"></circle>
          </svg>
        </span>
        <span class="transit-route-node transit-route-node-end"></span>
      </span>
      <span class="flow-progress-track" role="progressbar" aria-label="Indian Trail received progress" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${Math.round(percent)}"><i style="width:${percent}%"></i></span>
      ${rackLine ? `<span class="flow-rack-line flow-rack-line-v2"><b>Racks:</b><span>${escapeHtml(rackLine)}</span></span>` : ""}
      <span class="transit-open-action"><b>Open manifest</b><i aria-hidden="true"></i></span>
    </button>

    <button
      class="flow-card inbound flow-card-v2 bay-flow-side-card ${inbound ? "is-actionable" : "is-unavailable"}"
      type="button"
      ${inbound ? `data-open-list="${escapeHtml(inbound.id)}"` : "disabled"}
      title="${inbound ? "Open the current Indian Trail delivery list" : "No Indian Trail delivery list is available"}"
      aria-label="${inbound ? "Open Indian Trail delivery list" : "No Indian Trail delivery list available"}"
    >
      <span class="flow-card-icon inbound" aria-hidden="true"></span>
      <span class="flow-card-copy">
        <small>Received at Indian Trail</small>
        <strong>${escapeHtml(inboundQty)}<span>/${escapeHtml(inboundTotal)}</span></strong>
        <em>${escapeHtml(inboundStageLabel)}</em>
      </span>
      <span class="flow-card-open" aria-hidden="true"><b>${inbound ? "Open list" : "Unavailable"}</b><i></i></span>
    </button>
  `;

  const miniRoute = document.getElementById("bayPanelRouteMini");
  if (miniRoute) {
    miniRoute.innerHTML = `
      <div class="bay-panel-route-node outbound">
        <small>Outbound</small>
        <strong>${escapeHtml(outboundQty)}/${escapeHtml(outboundTotal)}</strong>
      </div>
      <div class="bay-panel-route-lane">
        <span>${escapeHtml(inTransitQty)} pieces on the way | Truck ${escapeHtml(truckQty)} | Racks ${escapeHtml(rackQty)}</span>
      </div>
      <div class="bay-panel-route-node inbound">
        <small>Received</small>
        <strong>${escapeHtml(inboundQty)}/${escapeHtml(inboundTotal)}</strong>
      </div>
    `;
  }
}


function transitManifestRowHtml(item) {
  const flags = [
    isRemakeItem(item) ? "RM" : "",
    isRushItem(item) ? "Rush" : "",
  ].filter(Boolean);
  const jobText = item.job || item.product || "No Job Nr.";

  return `
    <tr>
      <td>${escapeHtml(jobText)}</td>
      <td><strong>${escapeHtml(item.order)}-${escapeHtml(item.item)}</strong>${flags.length ? `<span class="transit-flags">${flags.map((flag) => `<i>${escapeHtml(flag)}</i>`).join("")}</span>` : ""}</td>
      <td>${escapeHtml(item.qty)}</td>
      <td>${escapeHtml(item.dimensions)}</td>
      <td>${escapeHtml(item.customer || "")}</td>
      <td>${escapeHtml(item.route)}</td>
      <td>${escapeHtml(item.outboundScannedQty)} sent / ${escapeHtml(item.receivedQty)} received</td>
    </tr>
  `;
}

function transitRackDisplayName(rack) {
  if (!rack) return "Needs transportation";
  if (rack.code === "T") return "Truck";
  if (/^T\d+$/i.test(String(rack.code || "")) || /truck/i.test(rack.type || "")) return rack.name || `Truck ${String(rack.code || "").replace(/^T/i, "")}`;
  if (rack.code === "UNASSIGNED") return "Needs transportation";
  return rack.code || rack.name || "Rack";
}

function transitRackSortValue(rack) {
  const code = String(rack?.code || "").toUpperCase();
  if (code === "T") return "0000-TRUCK";
  if (/^T\d+$/.test(code)) return `0001-${code.padStart(6, "0")}`;
  if (code === "UNASSIGNED" || !code) return "9999-UNASSIGNED";
  return `1000-${code}`;
}

function transitManifestGlassTypeClass(label) {
  const text = String(label || "").toLowerCase();

  if (/framed.*mirror|mirror.*framed/.test(text)) return "framed-mirror";
  if (/mirror/.test(text)) return "mirror";
  if (/shower/.test(text)) return "showers";
  if (/coral/.test(text)) return "coral";
  if (/\bcrl\b/.test(text)) return "crl";
  if (/\blr\b|\brr\b|left.*right|right.*left/.test(text)) return "lr-rr";
  if (/door/.test(text)) return "door";
  return "other";
}

function transitManifestSourceRows(payload) {
  if (Array.isArray(payload.rows) && payload.rows.length) return payload.rows.slice();

  const rows = [];
  for (const job of payload.jobs || []) {
    for (const rack of job.racks || []) {
      for (const item of rack.items || []) {
        rows.push({
          ...item,
          job: item.job || job.job || "No Job Nr.",
          product: item.product || job.product || "",
          customer: item.customer || job.customer || "",
          rackCode: item.rackCode || rack.code || "UNASSIGNED",
          rackName: item.rackName || rack.name || "",
          rackType: item.rackType || rack.type || "",
        });
      }
    }
  }

  return rows;
}

function transitManifestRackGroups(payload) {
  const rackMap = new Map();

  for (const sourceItem of transitManifestSourceRows(payload)) {
    const rackCode = String(sourceItem.rackCode || "").trim() || "UNASSIGNED";
    const rackKey = rackCode || "UNASSIGNED";
    const rackName = String(sourceItem.rackName || "").trim();
    const rackType = String(sourceItem.rackType || "").trim();

    if (!rackMap.has(rackKey)) {
      rackMap.set(rackKey, {
        code: rackCode,
        name: rackCode === "UNASSIGNED" ? "Needs transportation method" : rackName,
        type: rackCode === "T" ? "Truck" : rackCode === "UNASSIGNED" ? "Unassigned" : rackType || "Rack",
        totalQty: 0,
        rowCount: 0,
        jobSet: new Set(),
        glassMap: new Map(),
      });
    }

    const rack = rackMap.get(rackKey);
    const item = { ...sourceItem, rackCode };
    const qty = Math.max(Number(item.qty || 0), 0);
    const jobText = String(item.job || item.product || item.order || "No Job Nr.").trim() || "No Job Nr.";
    const glassLabel = glassTypeLabel(item);
    const glassKey = glassLabel.toLowerCase();

    rack.name = rack.name || rackName;
    rack.type = rack.type || rackType || "Rack";
    rack.totalQty += qty;
    rack.rowCount += 1;
    rack.jobSet.add(jobText);

    if (!rack.glassMap.has(glassKey)) {
      rack.glassMap.set(glassKey, {
        label: glassLabel,
        typeClass: transitManifestGlassTypeClass(glassLabel),
        totalQty: 0,
        rowCount: 0,
        jobSet: new Set(),
        items: [],
      });
    }

    const glassGroup = rack.glassMap.get(glassKey);
    glassGroup.totalQty += qty;
    glassGroup.rowCount += 1;
    glassGroup.jobSet.add(jobText);
    glassGroup.items.push(item);
  }

  return [...rackMap.values()]
    .map((rack) => ({
      ...rack,
      jobCount: rack.jobSet.size,
      glassTypes: [...rack.glassMap.values()]
        .map((glass) => ({
          ...glass,
          jobCount: glass.jobSet.size,
          items: glass.items.slice().sort((a, b) =>
            String(a.job || "").localeCompare(String(b.job || "")) ||
            String(a.order || "").localeCompare(String(b.order || ""), undefined, { numeric: true }) ||
            String(a.item || "").localeCompare(String(b.item || ""), undefined, { numeric: true }),
          ),
        }))
        .sort((a, b) => String(a.label).localeCompare(String(b.label))),
    }))
    .sort((a, b) => transitRackSortValue(a).localeCompare(transitRackSortValue(b)));
}


function transitRackIconClass(rack) {
  const text = `${rack?.type || ""} ${rack?.name || ""} ${rack?.code || ""}`;
  if (String(rack?.code || "").toUpperCase() === "T" || /truck/i.test(text)) return "truck";
  if (/wood/i.test(text)) return "wood";
  if (/coral/i.test(text)) return "coral";
  if (/unassigned|needs transportation/i.test(text)) return "unassigned";
  return "steel";
}

function transitManifestHtml(payload) {
  const rackGroups = transitManifestRackGroups(payload);
  const manifestRows = transitManifestSourceRows(payload);
  const dateLabel = payload.deliveryDate ? formatDisplayDate(payload.deliveryDate) : "Current Indian Trail list";
  const glassGroupCount = rackGroups.reduce((sum, rack) => sum + rack.glassTypes.length, 0);
  const jobCount = new Set(manifestRows.map((item) => String(item.job || item.product || item.order || "No Job Nr.").trim() || "No Job Nr.")).size;
  const rackCards = rackGroups.length
    ? rackGroups
        .map((rack) => `
          <details class="transit-rack-card transit-rack-group-card ${rack.code === "UNASSIGNED" ? "needs-method" : ""}">
            <summary class="transit-rack-head transit-rack-group-head">
              <span class="rack-set-icon transit-rack-icon ${escapeHtml(transitRackIconClass(rack))}" aria-hidden="true"></span>
              <div>
                <strong>${escapeHtml(transitRackDisplayName(rack))}</strong>
                <small>${escapeHtml(rack.name && rack.name !== rack.code ? rack.name : rack.type || "Transportation method")}</small>
              </div>
              <b>${escapeHtml(rack.totalQty)} pcs</b>
              <em>${escapeHtml(rack.glassTypes.length)} glass type${rack.glassTypes.length === 1 ? "" : "s"}</em>
            </summary>
            <div class="transit-rack-glass-stack">
              ${rack.glassTypes
                .map((glass) => `
                  <details class="transit-glass-card transit-glass-details type-${escapeHtml(glass.typeClass)}">
                    <summary class="transit-glass-ribbon">
                      <span class="transit-glass-chevron"></span>
                      <div>
                        <strong>${escapeHtml(glass.label)}</strong>
                        <small>${escapeHtml(glass.jobCount)} Job Nr.${glass.jobCount === 1 ? "" : "s"} on this rack</small>
                      </div>
                      <b>${escapeHtml(glass.totalQty)} pcs</b>
                    </summary>
                    <div class="transit-table-wrap">
                      <table class="transit-table transit-glass-table">
                        <thead><tr><th>Job Nr.</th><th>Order / Item</th><th>Qty</th><th>Dimensions</th><th>Customer</th><th>Route</th><th>Scan status</th></tr></thead>
                        <tbody>${glass.items.map(transitManifestRowHtml).join("")}</tbody>
                      </table>
                    </div>
                  </details>
                `)
                .join("")}
            </div>
          </details>
        `)
        .join("")
    : `<div class="transit-empty"><strong>No pieces are currently in transit.</strong><span>When Outbound scans Indian Trail pieces and they have not been received yet, they will appear here grouped by rack and glass type.</span></div>`;

  return `
    <div class="modal-backdrop transit-manifest-backdrop" data-close-transit-manifest></div>
    <section class="modal-panel transit-manifest-panel" role="dialog" aria-modal="true" aria-label="Indian Trail in-transit manifest">
      <header class="transit-manifest-header">
        <div>
          <small>Indian Trail Receiving</small>
          <h2>In-Transit Manifest</h2>
          <span>${escapeHtml(dateLabel)} | grouped by rack, then glass type</span>
        </div>
        <button class="modal-close-x transit-manifest-close" type="button" data-close-transit-manifest aria-label="Close">&times;</button>
      </header>
      <div class="transit-summary-row transit-summary-row-v31">
        <article><small>Pieces on the way</small><strong>${escapeHtml(payload.totalQty || 0)}</strong></article>
        <article><small>Racks / truck groups</small><strong>${escapeHtml(rackGroups.length || 0)}</strong></article>
        <article><small>Glass groups</small><strong>${escapeHtml(glassGroupCount || 0)}</strong></article>
        <article><small>Job Nr. groups</small><strong>${escapeHtml(jobCount || payload.jobCount || 0)}</strong></article>
        <article><small>Line items</small><strong>${escapeHtml(payload.rowCount || 0)}</strong></article>
      </div>
      <div class="transit-manifest-body transit-manifest-body-v31">${rackCards}</div>
    </section>
  `;
}

async function openInTransitManifest() {
  if (!hasPermission("view_indian_trail")) return;
  closeInTransitManifest(false);
  const shell = document.createElement("div");
  shell.id = "transitManifestShell";
  shell.className = "transit-manifest-shell";
  shell.innerHTML = `
    <div class="modal-backdrop transit-manifest-backdrop" data-close-transit-manifest></div>
    <section class="modal-panel transit-manifest-panel is-loading" role="dialog" aria-modal="true" aria-label="Indian Trail in-transit manifest">
      <header class="transit-manifest-header">
        <div><small>Indian Trail Receiving</small><h2>Loading in-transit manifest...</h2><span>Checking outbound scans against received scans.</span></div>
        <button class="modal-close-x transit-manifest-close" type="button" data-close-transit-manifest aria-label="Close">&times;</button>
      </header>
      <div class="transit-empty"><strong>Loading</strong><span>Please wait while the current in-transit jobs are pulled together.</span></div>
    </section>
  `;
  document.body.appendChild(shell);
  document.body.classList.add("modal-scroll-locked");
  try {
    const payload = await fetchJson("/api/indian-trail/in-transit");
    shell.innerHTML = transitManifestHtml(payload);
  } catch (error) {
    shell.querySelector(".transit-empty")?.remove();
    shell.querySelector(".transit-manifest-panel")?.insertAdjacentHTML("beforeend", `<div class="transit-empty error"><strong>Unable to load manifest</strong><span>${escapeHtml(error.message)}</span></div>`);
  }
}

function closeInTransitManifest(updateLock = true) {
  document.getElementById("transitManifestShell")?.remove();
  if (updateLock) updateModalScrollLock();
}

function renderIndianTrailSummary(summary) {
  if (!els.indianTrailSummary) return;
  const overview = bayOverview();
  const assigned = overview.occupied + overview.preassigned + overview.sdi;
  const openPct = overview.total ? Math.round((overview.available / overview.total) * 100) : 0;

  els.indianTrailSummary.innerHTML = `
    <div class="bay-command-stat primary">
      <small>Bay availability</small>
      <strong>${escapeHtml(overview.available)} open</strong>
      <span>${escapeHtml(openPct)}% of ${escapeHtml(overview.total)} physical bays ready</span>
    </div>
    <div class="bay-command-stat">
      <small>Assigned / occupied</small>
      <strong>${escapeHtml(assigned)}</strong>
      <span>${escapeHtml(overview.occupied)} occupied | ${escapeHtml(overview.preassigned)} preassigned</span>
    </div>
    <div class="bay-command-stat warning">
      <small>Needs attention</small>
      <strong>${escapeHtml(Number(summary?.needsCheck ?? 0) + overview.sdi + overview.blocked)}</strong>
      <span>${escapeHtml(overview.sdi)} SDI | ${escapeHtml(overview.manual || 0)} manual assign | ${escapeHtml(overview.blocked)} blocked</span>
    </div>
  `;
}

function bayMatchesFilter(bay, text) {
  const search = state.baySearch.trim().toLowerCase();
  const status = String(bay?.status || "").toLowerCase();
  const statusKind = bayStatusKind(bay);
  const policyKind = bayPolicyKind(bay);
  const matchesCategory = state.bayCategoryFilter === "all" || bayCategoryKind(bay) === state.bayCategoryFilter;
  const matchesGlass =
    state.bayGlassFilter === "all" ||
    (bay.assignments || []).some((assignment) => normalizeFilterValue(assignment.product || assignment.job || "Other Glass") === state.bayGlassFilter) ||
    normalizeFilterValue(bayGlassLabel(bay)) === state.bayGlassFilter;
  const matchesSpecial =
    state.baySpecialFilter === "all" ||
    (state.baySpecialFilter === "old" && Number(bay.staleDays || 0) > 10) ||
    (state.baySpecialFilter === "sdi" && (statusKind === "picking" || (bay.assignments || []).some((assignment) => String(assignment.status || "").toLowerCase().includes("sdi")))) ||
    (state.baySpecialFilter === "new" && Boolean(bay.isNewToday || (bay.assignments || []).some((assignment) => assignment.isNewToday)));
  const matchesStatus =
    state.bayStatusFilter === "all" ||
    state.bayStatusFilter === statusKind ||
    state.bayStatusFilter === policyKind ||
    (state.bayStatusFilter === "empty" && (status.includes("empty") || status.includes("available"))) ||
    (state.bayStatusFilter === "error" && bayHasErrorState(bay));
  if (!matchesCategory || !matchesStatus || !matchesGlass || !matchesSpecial) return false;
  if (!search) return true;
  return text.toLowerCase().includes(search);
}

function bayHasErrorState(bay) {
  const haystack = [
    bay?.status,
    bay?.sourceStatus,
    bay?.reason,
    ...(bay?.assignments || []).flatMap((assignment) => [
      assignment.status,
      assignment.processState,
      assignment.queueState,
      assignment.reason,
      assignment.lastStage,
    ]),
  ].join(" ").toLowerCase();
  return /error|exception|conflict|needs\s*check|bad|scanblocked|blockedall|blocked\s+for\s+all/.test(haystack);
}

function filterOptionLabel(options, value, fallback = "") {
  const match = options.find(([optionValue]) => optionValue === value);
  return match ? match[1] : fallback || String(value || "");
}

function selectOptionLabel(select, value, fallback = "") {
  if (!select) return fallback || String(value || "");
  const option = [...select.options].find((item) => item.value === value);
  return option ? option.textContent.trim() : fallback || String(value || "");
}

function activeBayFilterChips() {
  const chips = [];
  const search = state.baySearch.trim();

  if (search) chips.push(["Search", search]);
  if (state.bayStatusFilter !== "all") chips.push(["Status", selectOptionLabel(els.bayStatusFilter, state.bayStatusFilter)]);
  if (state.bayGlassFilter !== "all") chips.push(["Glass", selectOptionLabel(els.bayGlassFilter, state.bayGlassFilter)]);
  if (state.baySpecialFilter !== "all") chips.push(["Orders", selectOptionLabel(els.baySpecialFilter, state.baySpecialFilter)]);
  if (state.bayCategoryFilter !== "all") chips.push(["Category", filterOptionLabel(bayCategoryFilterOptions(), state.bayCategoryFilter)]);

  return chips;
}

function resetBayFilters() {
  state.baySearch = "";
  state.bayStatusFilter = "all";
  state.bayCategoryFilter = "all";
  state.bayGlassFilter = "all";
  state.baySpecialFilter = "all";

  if (els.bayMapSearch) els.bayMapSearch.value = "";
  if (els.bayStatusFilter) els.bayStatusFilter.value = "all";
  if (els.bayGlassFilter) els.bayGlassFilter.value = "all";
  if (els.baySpecialFilter) els.baySpecialFilter.value = "all";
  if (els.bayFilterDrawer) els.bayFilterDrawer.open = false;

  collapseAllPhysicalBaySections();
  renderBayMapPage();
}

function renderBayFilterSummary() {
  if (!els.bayActiveFilterSummary && !els.bayActiveFilterCount && !els.bayClearFiltersBtn) return;

  const chips = activeBayFilterChips();
  const activeCount = chips.length;
  const countable = (state.bays || []).filter((bay) => bay.active !== false && bayCategoryKind(bay) !== "spacer");
  const visibleCount = countable.filter((bay) => bayMatchesFilter(bay, baySearchText(bay))).length;
  const summaryText = activeCount
    ? `${visibleCount} of ${countable.length} bays shown`
    : `Showing all ${countable.length} physical bays`;

  if (els.bayActiveFilterSummary) {
    const chipHtml = chips
      .map(([label, value]) => `<span class="bay-active-filter-chip"><small>${escapeHtml(label)}</small>${escapeHtml(value)}</span>`)
      .join("");

    els.bayActiveFilterSummary.innerHTML = `
      <strong>${escapeHtml(summaryText)}</strong>
      ${chipHtml ? `<div class="bay-active-filter-chips">${chipHtml}</div>` : `<span>Search and filter controls are tucked into one compact bar.</span>`}
    `;
  }

  if (els.bayActiveFilterCount) {
    els.bayActiveFilterCount.textContent = String(activeCount);
    els.bayActiveFilterCount.hidden = activeCount === 0;
  }

  if (els.bayClearFiltersBtn) els.bayClearFiltersBtn.hidden = activeCount === 0;
  els.bayActiveFilterBar?.classList.toggle("has-active-filters", activeCount > 0);
}

function normalizeFilterValue(value) {
  return String(value || "").trim().toLowerCase();
}

function bayGlassLabel(bay) {
  const assignment = (bay?.assignments || [])[0];
  return String(assignment?.product || assignment?.job || bay?.bayCategory || bay?.bayType || "Other Glass").trim() || "Other Glass";
}

function isWorkbookLegendCell(cell) {
  return Number(cell.row || 0) >= 11 && Number(cell.row || 0) <= 18 && Number(cell.col || 0) >= 17 && Number(cell.col || 0) <= 20;
}

function statusAbbreviation(status, bay) {
  if (!bay) return "";
  if (bayCategoryKind(bay) === "spacer") return "";
  const policy = bayPolicyKind(bay);
  if (policy === "manual") return "MAN";
  if (policy === "blocked") return "BLK";
  if (status === "SDI") return "SDI";
  if (/pre|assign/i.test(status)) return "PRE";
  if (status === "Full" || status === "Occupied") return "OCC";
  if (status === "Partial") return "PAR";
  if (status === "Empty" || status === "Available") return "AVL";
  return "";
}

function bayCategoryKind(bay) {
  const text = [bay?.bayCategory, bay?.bayType, bay?.mapSection, bay?.displayName, bay?.bayCode].join(" ").toLowerCase();
  if (text.includes("spacer")) return "spacer";
  if (text.includes("coral")) return "coral";
  if (/\blr\b/.test(text)) return "lr";
  if (/\brr\b/.test(text)) return "rr";
  if (text.includes("framed mirror") || /\bfm\b/.test(text)) return "framed-mirror";
  if (text.includes("bfs mir")) return "bfs-mirror";
  if (text.includes("mirror") || text.includes("annealed")) return "mirror";
  if (text.includes("crl") || text.includes("laurence")) return "crl";
  if (text.includes("shower") || text.includes("tempered") || /^t-bay/.test(String(bay?.bayCode || "").toLowerCase())) return "showers";
  return "standard";
}

function bayCategoryLabel(kind) {
  const labels = {
    coral: "Coral",
    lr: "LR",
    rr: "RR",
    showers: "Showers",
    mirror: "Mirrors",
    "bfs-mirror": "BFS Mirrors",
    "framed-mirror": "Framed Mirrors",
    crl: "CRL Laurence",
    spacer: "Spacers",
    standard: "Other Bays",
  };
  return labels[kind] || "Other Bays";
}

function bayCategoryOrder(kind) {
  return { coral: 1, lr: 2, rr: 3, showers: 4, mirror: 5, "bfs-mirror": 6, "framed-mirror": 7, crl: 8, standard: 9, spacer: 10 }[kind] || 9;
}

function bayRackLabel(bay) {
  return bay?.mapSection || (bay?.bayNumber ? `Bay ${bay.bayNumber}` : "Unmapped");
}

function baySearchText(bay) {
  return [
    bay?.displayName,
    bay?.bayCode,
    bay?.status,
    bay?.mapSection,
    bay?.bayCategory,
    bay?.bayType,
    ...(bay?.assignments || []).map((assignment) => `${assignment.order} ${assignment.item} ${assignment.customer} ${assignment.product} ${assignment.job} ${assignment.dimensions} ${assignment.deliveryDate}`),
  ].join(" ");
}

function bayPolicyKind(bay) {
  const status = String(bay?.status || "").toLowerCase().replace(/[^a-z]/g, "");
  const sourceStatus = String(bay?.sourceStatus || "").toLowerCase().replace(/[^a-z]/g, "");

  // Legacy Hold/Blocked bays are intentionally treated as Manual Assign.
  // Use ScanBlocked/BlockedAll when a bay should be blocked from every scan workflow.
  if (status.includes("scanblocked") || status.includes("blockedall") || sourceStatus.includes("scanblocked") || sourceStatus.includes("blockedall")) return "blocked";
  if (!bay?.active || status.includes("manual") || status.includes("hold") || status.includes("blocked")) return "manual";
  return "auto";
}

function bayStatusKind(bay) {
  const status = String(bay?.status || "").toLowerCase();
  const assigned = Number(bay?.assignedQty || 0);
  const policy = bayPolicyKind(bay);
  if (bayCategoryKind(bay) === "spacer") return "spacer";
  if (policy === "blocked") return "blocked";
  if (policy === "manual" && !assigned && !status.includes("pre") && !status.includes("sdi") && !status.includes("pick")) return "manual";
  if (status.includes("sdi") || status.includes("pick")) return "picking";
  if (status.includes("pre")) return "preassigned";
  if (assigned > 0 || status.includes("occupied") || status.includes("full") || status.includes("partial")) return "occupied";
  return "available";
}

function bayStatusLabel(bay) {
  const kind = bayStatusKind(bay);
  if (kind === "manual") return "Manual Assign";
  if (kind === "blocked") return "Blocked Scans";
  if (kind === "available") return bayPolicyKind(bay) === "auto" ? "Auto Assign" : "Available";
  if (kind === "picking") return "Picking / SDI";
  if (kind === "preassigned") return "Pre Assigned";
  if (kind === "occupied") return "Occupied";
  if (kind === "spacer") return "Spacer";
  return String(bay?.status || "Available");
}

function bayUtilization(bay) {
  const capacity = Number(bay?.capacityQty || 0);
  const assigned = Number(bay?.assignedQty || 0);
  if (!capacity) return assigned ? 100 : 0;
  return Math.min((assigned / capacity) * 100, 100);
}

function bayCategoryFilterOptions() {
  return [
    ["all", "All Bays"],
    ["showers", "Showers"],
    ["lr", "LR"],
    ["rr", "RR"],
    ["crl", "CRL Laurence"],
    ["framed-mirror", "Framed Mirrors"],
    ["mirror", "Mirrors"],
    ["bfs-mirror", "BFS Mirrors"],
    ["coral", "Coral"],
  ];
}

function bayGlassFilterOptions() {
  const values = new Map();
  for (const bay of state.bays || []) {
    for (const assignment of bay.assignments || []) {
      const label = String(assignment.product || assignment.job || "Other Glass").trim() || "Other Glass";
      values.set(normalizeFilterValue(label), label);
    }
  }
  return [["all", "All glass types"], ...[...values.entries()].sort((a, b) => a[1].localeCompare(b[1]))];
}

function bayOverview() {
  const countableBays = state.bays.filter((bay) => bay.active !== false && bayCategoryKind(bay) !== "spacer");

  const available = countableBays.filter((bay) => bayStatusKind(bay) === "available").length;
  const occupied = countableBays.filter((bay) => bayStatusKind(bay) === "occupied").length;
  const preassigned = countableBays.filter((bay) => bayStatusKind(bay) === "preassigned").length;
  const sdi = countableBays.filter((bay) => bayStatusKind(bay) === "picking").length;
  const blocked = countableBays.filter((bay) => bayPolicyKind(bay) === "blocked").length;
  const manual = countableBays.filter((bay) => bayPolicyKind(bay) === "manual").length;
  const auto = countableBays.filter((bay) => bayPolicyKind(bay) === "auto" && bayStatusKind(bay) === "available").length;

  return {
    total: countableBays.length,
    available,
    occupied,
    preassigned,
    sdi,
    blocked,
    manual,
    auto,
  };
}


function bayGroupPolicySummary(section) {
  const bays = (section?.bays || []).filter((bay) => bayCategoryKind(bay) !== "spacer");
  const counts = { auto: 0, manual: 0, blocked: 0 };

  for (const bay of bays) {
    counts[bayPolicyKind(bay)] = (counts[bayPolicyKind(bay)] || 0) + 1;
  }

  // Keep the grouped-bay policy labels intentionally short. The physical map
  // has compact bay cards, so long text like "Manual Assign" is shown through
  // the detail tooltip/CSS title behavior instead of being allowed to crowd the
  // bay group name.
  if (!bays.length) {
    return { kind: "empty", label: "Empty", detail: "0 bays" };
  }
  if (counts.blocked === bays.length) {
    return { kind: "blocked", label: "Blocked", detail: `${counts.blocked} blocked` };
  }
  if (counts.manual === bays.length) {
    return { kind: "manual", label: "Man", detail: `${counts.manual} manual` };
  }
  if (counts.auto === bays.length) {
    return { kind: "auto", label: "Auto", detail: `${counts.auto} auto` };
  }
  return {
    kind: "mixed",
    label: "Mixed",
    detail: `${counts.auto} auto / ${counts.manual} manual${counts.blocked ? ` / ${counts.blocked} blocked` : ""}`,
  };
}

function assignmentJobKey(assignment) {
  const job = String(assignment?.job || "").trim();
  if (job) return `job:${job.toLowerCase()}`;
  return `order:${assignment?.order || ""}`;
}

function assignmentJobLabel(assignment) {
  return String(assignment?.job || assignment?.order || assignment?.product || "No Job Nr.").trim() || "No Job Nr.";
}

function groupAssignmentsByJob(assignments = []) {
  const groups = new Map();
  for (const assignment of assignments || []) {
    const key = assignmentJobKey(assignment);
    if (!groups.has(key)) {
      groups.set(key, {
        key,
        label: assignmentJobLabel(assignment),
        customer: assignment.customer || "",
        dimensions: assignment.dimensions || "",
        assignments: [],
        totalQty: 0,
        scannedQty: 0,
      });
    }
    const group = groups.get(key);
    group.assignments.push(assignment);
    const assignmentTotal = Number(assignment.assignedQty || assignment.qty || 0);
    const assignmentScanned = Math.min(Number(assignment.scanned || 0), assignmentTotal || Number(assignment.qty || 0));
    group.totalQty += assignmentTotal;
    group.scannedQty += assignmentScanned;
    if (!group.customer && assignment.customer) group.customer = assignment.customer;
    if (!group.dimensions && assignment.dimensions) group.dimensions = assignment.dimensions;
  }
  return [...groups.values()].map((group) => ({
    ...group,
    itemCount: group.assignments.length,
    orderLine: group.assignments.map((assignment) => `${assignment.order}-${assignment.item}`).join(", "),
  }));
}

function renderBaySlotButton(bay, mode = "physical") {
  const assignments = bay.assignments || [];
  const assignment = assignments[0];
  const jobGroups = groupAssignmentsByJob(assignments);
  const primaryGroup = jobGroups[0];
  const status = bay.status || "ManualHold";
  const text = baySearchText(bay);
  const search = state.baySearch.trim().toLowerCase();
  const searchMatch = Boolean(search) && text.toLowerCase().includes(search);
  const dimmed = !bayMatchesFilter(bay, text);
  const abbreviation = statusAbbreviation(status, bay);
  const kind = bayCategoryKind(bay);
  const statusKind = bayStatusKind(bay);
  const label = bay.displayName || bay.bayCode;
  const assignedQty = assignments.reduce((sum, item) => sum + Number(item.assignedQty || item.qty || 0), 0) || Number(bay.assignedQty || 0);
  const capacity = Number(bay.capacityQty || 0);
  const utilization = bayUtilization(bay);
  const jobTotalQty = Number(primaryGroup?.totalQty || 0);
  const jobScannedQty = Number(primaryGroup?.scannedQty || 0);
  // Bay cards show job-based receive progress. A Job Nr. with 3 pieces reads 0/3,
  // then 1/3 after the first piece is scanned into that bay.
  const bayCardCounter = primaryGroup ? `${jobScannedQty}/${jobTotalQty || primaryGroup.itemCount || 0}` : capacity ? `${assignedQty}/${capacity}` : `${assignedQty}`;
  const orderLine = primaryGroup ? primaryGroup.label : "Empty";
  const customerLine = primaryGroup?.customer || bay.mapSection || bay.bayCategory || bay.bayType || "Ready";
  const sizeLine = primaryGroup ? `${primaryGroup.itemCount} item${primaryGroup.itemCount === 1 ? "" : "s"}${primaryGroup.dimensions ? ` • ${primaryGroup.dimensions}` : ""}` : bayCategoryLabel(kind);
  const extraCount = Math.max(jobGroups.length - 1, 0);
  const ribbons = [
    Number(bay.staleDays || 0) > 10 ? `<span class="bay-ribbon stale">${escapeHtml(bay.staleDays)}d</span>` : "",
    bay.isNewToday ? `<span class="bay-ribbon new">NEW</span>` : "",
    extraCount ? `<span class="bay-ribbon count">+${escapeHtml(extraCount)}</span>` : "",
  ].filter(Boolean).join("");
  const modeClass = mode === "physical" ? "physical-bay-slot" : "bay-slot";

  return `
    <button class="${modeClass} bay-slot-v2 bay-slot-v17 type-${escapeHtml(kind)} status-${escapeHtml(statusKind)} ${escapeHtml(String(status).toLowerCase())} ${dimmed ? "is-dimmed" : ""} ${searchMatch ? "is-search-match" : ""} ${state.selectedBayCode === bay.bayCode ? "is-selected" : ""}"
      type="button"
      data-bay-code="${escapeHtml(bay.bayCode)}"
      data-assignment-id="${escapeHtml(assignment?.id || "")}"
      ${state.bayEditMode && hasPermission("manage_bay_layout") ? 'draggable="true"' : ""}
      title="${escapeHtml(text)}">
      ${ribbons}
      <span class="bay-slot-head">
        <strong class="bay-code">${escapeHtml(label)}</strong>
        <span class="bay-state status-${escapeHtml(statusKind)}">${escapeHtml(abbreviation || statusKind.toUpperCase())}</span>
      </span>
      <span class="bay-slot-main-row">
        <span class="bay-slot-order">${escapeHtml(orderLine)}</span>
        <span class="bay-slot-qty">${escapeHtml(bayCardCounter)}</span>
      </span>
      <small class="bay-slot-customer">${escapeHtml(customerLine)}</small>
      <small class="bay-slot-size">${escapeHtml(sizeLine)}</small>
      <span class="bay-slot-foot">
        <i style="width:${utilization}%"></i>
      </span>
    </button>
  `;
}

function bayTypeSections() {
  const groups = new Map();
  for (const bay of state.bays || []) {
    if (bay.active === false) continue;
    const kind = bayCategoryKind(bay);
    if (!groups.has(kind)) groups.set(kind, []);
    groups.get(kind).push(bay);
  }
  return [...groups.entries()]
    .map(([kind, bays]) => {
      const racks = new Map();
      for (const bay of bays) {
        const rack = bayRackLabel(bay);
        if (!racks.has(rack)) racks.set(rack, []);
        racks.get(rack).push(bay);
      }
      return {
        kind,
        label: bayCategoryLabel(kind),
        bays,
        racks: [...racks.entries()]
          .map(([label, rackBays]) => ({
            label,
            bays: rackBays
              .slice()
              .sort((a, b) => Number(a.baySlot || a.layoutRow || 9999) - Number(b.baySlot || b.layoutRow || 9999) || Number(a.layoutCol || 9999) - Number(b.layoutCol || 9999)),
          }))
          .sort((a, b) => {
            const aNum = Number(String(a.label).match(/\d+/)?.[0] || 9999);
            const bNum = Number(String(b.label).match(/\d+/)?.[0] || 9999);
            return aNum - bNum || a.label.localeCompare(b.label);
          }),
      };
    })
    .sort((a, b) => bayCategoryOrder(a.kind) - bayCategoryOrder(b.kind) || a.label.localeCompare(b.label));
}

function bayPhysicalSections() {
  const sectionMap = new Map();
  for (const bay of state.bays || []) {
    if (bay.active === false) continue;
    const label = bayRackLabel(bay);
    if (!sectionMap.has(label)) sectionMap.set(label, []);
    sectionMap.get(label).push(bay);
  }
  return [...sectionMap.entries()]
    .map(([label, bays]) => {
      const positioned = bays.filter((bay) => Number(bay.layoutRow || 0) || Number(bay.layoutCol || 0));
      const row = positioned.reduce((sum, bay) => sum + Number(bay.layoutRow || 9999), 0) / Math.max(positioned.length, 1);
      const col = positioned.reduce((sum, bay) => sum + Number(bay.layoutCol || 9999), 0) / Math.max(positioned.length, 1);
      const kind = bayCategoryKind(bays[0]);
      return { label, bays, row, col, kind };
    })
    .sort((a, b) => a.col - b.col || a.row - b.row || a.label.localeCompare(b.label));
}

function initializeBayLayoutDraft() {
  const sections = bayPhysicalSections();
  const used = new Set();
  const nextRowByColumn = new Map();
  state.bayLayoutDraft = {};
  state.bayHoldingSections = new Set();

  // Edit Map mirrors the live physical columns. Rows are allowed to continue
  // past 7 so large columns do not get forced into Unmapped/Holding.
  sections.forEach((section, index) => {
    let col = Math.max(1, Math.min(7, Math.round(Number(section.col || 0)) || (index % 7) + 1));
    let row = Math.max(1, Math.round(Number(section.row || 0)) || (nextRowByColumn.get(col) || 1));

    while (used.has(`${row}:${col}`)) row += 1;

    used.add(`${row}:${col}`);
    nextRowByColumn.set(col, Math.max(nextRowByColumn.get(col) || 1, row + 1));
    state.bayLayoutDraft[section.label] = { row, col, holding: false };
  });
  state.bayLayoutOriginal = JSON.parse(JSON.stringify(state.bayLayoutDraft));
}

function normalizedBayGridPositions(sections) {
  const positions = {};
  sections.forEach((section, index) => {
    const row = Math.floor(index / 7) + 1;
    const col = (index % 7) + 1;
    if (row <= 7) {
      positions[section.label] = { row, col, holding: false };
    } else {
      positions[section.label] = { row: 0, col: 0, holding: true };
    }
  });
  return positions;
}

function renderBaySection(section) {
  const filtersActive = state.baySearch.trim() || state.bayStatusFilter !== "all" || state.bayCategoryFilter !== "all" || state.bayGlassFilter !== "all" || state.baySpecialFilter !== "all";
  const displayBays = filtersActive ? section.bays.filter((bay) => bayMatchesFilter(bay, baySearchText(bay))) : section.bays;
  const visible = displayBays.length;
  const dimmed = !visible && filtersActive;
  const occupied = section.bays.filter((bay) => Number(bay.assignedQty || 0) > 0).length;
  const attention = section.bays.filter((bay) => bayHasErrorState(bay) || Number(bay.staleDays || 0) > 10 || bayStatusKind(bay) === "picking").length;
  const available = section.bays.filter((bay) => bayStatusKind(bay) === "available").length;
  const blocked = section.bays.filter((bay) => bayPolicyKind(bay) === "blocked").length;
  const groupPolicy = bayGroupPolicySummary(section);
  const open = Boolean(filtersActive) || !state.collapsedBaySections.has(section.label);
  const cols = Math.max(1, Math.min(Number(state.bayGroupColumns[section.label] || 1), 2));
  return `
    <details ${open ? "open" : ""} class="physical-bay-section physical-bay-section-v17 type-${escapeHtml(section.kind)} cols-${cols} policy-${escapeHtml(groupPolicy.kind)} ${state.bayEditMode ? "is-editing" : ""} ${dimmed ? "is-dimmed" : ""}" data-bay-drop-section="${escapeHtml(section.label)}" data-bay-drop-category="${escapeHtml(section.kind)}">
      <summary ${state.bayEditMode && hasPermission("manage_bay_layout") ? 'draggable="true"' : ""} data-bay-group-drag="${escapeHtml(section.label)}">
        <span class="bay-section-title"><strong>${escapeHtml(section.label)}</strong><small>${escapeHtml(bayCategoryLabel(section.kind))}</small></span>
        <span class="bay-section-status status-${escapeHtml(groupPolicy.kind)}">
          <strong>${escapeHtml(groupPolicy.label)}</strong>
          <small>${escapeHtml(groupPolicy.detail)}</small>
        </span>
        <span class="bay-section-counts">
          <b>${escapeHtml(occupied)}</b>
          <i>${escapeHtml(available)} open</i>
          ${blocked ? `<em class="blocked">${escapeHtml(blocked)} blocked</em>` : ""}
          ${attention ? `<em>${escapeHtml(attention)} attention</em>` : ""}
        </span>
        <button class="bay-section-edit-btn" type="button" data-bay-editor-open="${escapeHtml(section.label)}" data-permission-any="manage_bay_layout">Edit</button>
        ${state.bayEditMode ? `<span class="bay-column-controls"><button type="button" data-bay-col-action="dec" data-bay-section="${escapeHtml(section.label)}">-</button><b>${cols} col</b><button type="button" data-bay-col-action="inc" data-bay-section="${escapeHtml(section.label)}">+</button></span>` : ""}
      </summary>
      <div class="physical-slot-grid physical-slot-grid-v17" style="--bay-section-cols:${cols}">
        ${displayBays.map((bay) => renderBaySlotButton(bay, "physical")).join("")}
      </div>
    </details>
  `;
}

function renderBayGrid(physicalSections) {
  if (state.bayEditMode && !state.bayLayoutDraft) initializeBayLayoutDraft();
  if (!state.bayEditMode) {
    const filtersActive = state.baySearch.trim() || state.bayStatusFilter !== "all" || state.bayCategoryFilter !== "all" || state.bayGlassFilter !== "all" || state.baySpecialFilter !== "all";
    const helper = `
      <div class="bay-map-helper-v17">
        <strong>${filtersActive ? "Filtered view" : "Physical floor view"}</strong>
        <span>${escapeHtml(physicalSections.length)} bay group${physicalSections.length === 1 ? "" : "s"} shown. Click a bay for tools or use Manage Items for bulk order work.</span>
        <button type="button" data-bay-action="item-management">Open Manage Items</button>
      </div>
    `;
    if (filtersActive) {
      return `
        ${helper}
        <section class="bay-dense-grid bay-dense-grid-v17">
          ${physicalSections.length ? physicalSections.map((section) => renderBaySection(section)).join("") : `<div class="admin-empty">No bays match those filters.</div>`}
        </section>
      `;
    }

    // Confirmed bay-map positions are preserved by column and top-to-bottom order.
    // The physical map intentionally renders each saved column as an independent stack,
    // so expanding one bay group only moves groups below it in the same column.
    const columns = Array.from({ length: 7 }, () => []);
    const used = new Set();
    physicalSections.forEach((section, index) => {
      let row = Math.max(1, Math.round(Number(section.row || 0)) || Math.floor(index / 7) + 1);
      let col = Math.max(1, Math.min(7, Math.round(Number(section.col || 0)) || (index % 7) + 1));
      while (used.has(`${row}:${col}`)) {
        row += 1;
      }
      used.add(`${row}:${col}`);
      columns[col - 1].push({ section, row });
    });
    const columnMarkup = columns
      .map((column, index) => {
        const cells = column
          .sort((a, b) => a.row - b.row || a.section.label.localeCompare(b.section.label))
          .map(({ section }) => `<div class="bay-floor-cell-v18">${renderBaySection(section)}</div>`)
          .join("");
        return `<div class="bay-floor-column-v19" data-bay-floor-column="${index + 1}">${cells}</div>`;
      })
      .join("");
    return `
      ${helper}
      <section class="bay-floor-grid-v18 bay-floor-grid-v19">
        ${physicalSections.length ? columnMarkup : `<div class="admin-empty">No bays match those filters.</div>`}
      </section>
    `;
  }
  const sectionByLabel = new Map(physicalSections.map((section) => [section.label, section]));
  const visibleSections = physicalSections
    .map((section) => {
      const draft = state.bayLayoutDraft?.[section.label] || {};
      return {
        section,
        row: Math.max(1, Math.round(Number(draft.row || section.row || 1))),
        col: Math.max(1, Math.min(7, Math.round(Number(draft.col || section.col || 1)))),
        holding: Boolean(draft.holding),
      };
    })
    .filter((entry) => !entry.holding);

  const columns = Array.from({ length: 7 }, () => []);
  const rowCounts = Array.from({ length: 7 }, () => 1);
  visibleSections.forEach((entry) => {
    columns[entry.col - 1].push(entry);
    rowCounts[entry.col - 1] = Math.max(rowCounts[entry.col - 1], entry.row + 1);
  });

  const columnMarkup = columns
    .map((column, index) => {
      const col = index + 1;
      const usedRows = new Set(column.map((entry) => entry.row));
      const sorted = column.sort((a, b) => a.row - b.row || a.section.label.localeCompare(b.section.label));
      const groupCells = sorted
        .map((entry) => `
          <div class="bay-edit-stack-cell has-section" data-grid-row="${entry.row}" data-grid-col="${col}" data-bay-drop-section="${escapeHtml(entry.section.label)}" data-bay-grid-cell="true">
            ${renderBaySection(entry.section)}
          </div>
        `)
        .join("");
      const emptyRow = Math.max(rowCounts[index], ...[...usedRows, 0]) + 1;
      return `
        <section class="bay-edit-stack-column" data-bay-edit-column="${col}">
          <header><strong>Column ${col}</strong><span>${escapeHtml(sorted.length)} grouped set${sorted.length === 1 ? "" : "s"}</span></header>
          <div class="bay-edit-stack-list">
            ${groupCells}
            <div class="bay-edit-stack-cell empty" data-grid-row="${emptyRow}" data-grid-col="${col}" data-bay-drop-section="grid-${emptyRow}-${col}" data-bay-grid-cell="true">
              <span class="empty-grid-slot">Drop group here</span>
            </div>
          </div>
        </section>
      `;
    })
    .join("");

  const holding = [...state.bayHoldingSections]
    .map((label) => sectionByLabel.get(label))
    .filter(Boolean);

  return `
    <section class="bay-edit-map-shell-v23">
      <div class="bay-edit-map-help-v23">
        <strong>Edit Map Layout</strong>
        <span>This view now matches the live physical bay map. Drag grouped bay set headers between columns, then Confirm Layout to save the exact floor-map position.</span>
      </div>
      <section class="bay-holding-area bay-holding-area-v23" data-bay-holding-area="true">
        <header><strong>Temporary Holding Area</strong><span>${escapeHtml(holding.length)} group${holding.length === 1 ? "" : "s"}</span></header>
        <div class="bay-holding-list" data-bay-drop-section="__holding" data-bay-holding-drop="true">
          ${holding.length ? holding.map((section) => renderBaySection(section)).join("") : `<div class="empty-grid-slot">Drop grouped bay sets here while reorganizing.</div>`}
        </div>
      </section>
      <section class="bay-edit-column-grid-v23">${columnMarkup}</section>
    </section>
  `;
}

function collapseAllPhysicalBaySections() {
  (state.bays || []).forEach((bay) => state.collapsedBaySections.add(bayRackLabel(bay)));
}

function syncBaySectionState(details, open) {
  const label = details.dataset.bayDropSection || "";
  if (!label) return;
  if (open) state.collapsedBaySections.delete(label);
  else state.collapsedBaySections.add(label);
}

function animateBaySectionToggle(details) {
  const body = details.querySelector(".physical-slot-grid-v17");
  if (!body || details.dataset.animating === "1") return;

  const isOpen = details.open;
  details.dataset.animating = "1";

  if (isOpen) {
    const startHeight = `${body.scrollHeight}px`;
    syncBaySectionState(details, false);
    const animation = body.animate(
      [
        { height: startHeight, opacity: 1, transform: "translateY(0)" },
        { height: "0px", opacity: 0, transform: "translateY(-6px)" },
      ],
      { duration: 170, easing: "ease" },
    );
    animation.onfinish = () => {
      details.open = false;
      delete details.dataset.animating;
    };
    animation.oncancel = () => delete details.dataset.animating;
    return;
  }

  details.open = true;
  syncBaySectionState(details, true);
  const endHeight = `${body.scrollHeight}px`;
  const animation = body.animate(
    [
      { height: "0px", opacity: 0, transform: "translateY(-6px)" },
      { height: endHeight, opacity: 1, transform: "translateY(0)" },
    ],
    { duration: 190, easing: "ease" },
  );
  animation.onfinish = () => delete details.dataset.animating;
  animation.oncancel = () => delete details.dataset.animating;
}

function renderBayMapPage() {
  if (!els.bayMapCanvas || !state.bayLayout) return;
  const filtersActive = state.baySearch.trim() || state.bayStatusFilter !== "all" || state.bayCategoryFilter !== "all" || state.bayGlassFilter !== "all" || state.baySpecialFilter !== "all";
  const physicalSections = bayPhysicalSections().filter((section) => !filtersActive || section.bays.some((bay) => bayMatchesFilter(bay, baySearchText(bay))));
  if (!state.baySectionsDefaultCollapsed && !state.bayEditMode) {
    physicalSections.forEach((section) => state.collapsedBaySections.add(section.label));
    state.baySectionsDefaultCollapsed = true;
  }
  els.bayMapCanvas.innerHTML = renderBayGrid(physicalSections);
  els.bayMapCanvas.querySelectorAll(".physical-bay-section").forEach((details) => {
    const summary = details.querySelector("summary");
    summary?.addEventListener("click", (event) => {
      if (event.target.closest("button")) return;
      event.preventDefault();
      animateBaySectionToggle(details);
    });
    details.addEventListener("toggle", () => {
      if (details.dataset.animating === "1") return;
      syncBaySectionState(details, details.open);
    });
  });
  const overview = bayOverview();
  if (els.bayOverviewStats) {
    els.bayOverviewStats.innerHTML = [
      miniStat("Total Bays", overview.total),
      miniStat("Available", overview.available),
      miniStat("Occupied", overview.occupied),
      miniStat("Pre Assigned", overview.preassigned),
      miniStat("Manual Assign", overview.manual || 0),
      miniStat("Blocked Scans", overview.blocked),
    ].join("");
  }
  if (els.baySelectedText) els.baySelectedText.textContent = state.selectedBayCode ? `Selected: ${state.selectedBayCode}` : "No bay selected";
  renderBaySidePanels();
  renderBayFilterSummary();
  renderBayRecentActions();
}

function renderBaySidePanels() {
  if (els.bayCategoryFilters) {
    els.bayCategoryFilters.innerHTML = bayCategoryFilterOptions()
      .map(([value, label]) => `<button class="tab ${state.bayCategoryFilter === value ? "is-active" : ""}" type="button" data-bay-category-filter="${escapeHtml(value)}">${escapeHtml(label)}</button>`)
      .join("");
  }
  if (els.bayStatusFilter) els.bayStatusFilter.value = state.bayStatusFilter;
  if (els.bayGlassFilter) {
    const options = bayGlassFilterOptions();
    if (state.bayGlassFilter !== "all" && !options.some(([value]) => value === state.bayGlassFilter)) state.bayGlassFilter = "all";
    els.bayGlassFilter.innerHTML = options.map(([value, label]) => `<option value="${escapeHtml(value)}">${escapeHtml(label)}</option>`).join("");
    els.bayGlassFilter.value = state.bayGlassFilter;
  }
  if (els.baySpecialFilter) els.baySpecialFilter.value = state.baySpecialFilter;
  const bay = selectedBay();
  if (els.baySelectedPanel) {
    if (!bay) {
      els.baySelectedPanel.innerHTML = `
        <div class="selected-bay-empty-state">
          <strong>Select a bay to manage it.</strong>
          <span>Click a bay on the map or in the directory. From there you can send the bay to the scanner, hold/block it, move glass, clear assignments, or mark SDI.</span>
        </div>
      `;
    } else {
      const assignments = bay.assignments || [];
      const jobGroups = groupAssignmentsByJob(assignments);
      const assignedQty = assignments.reduce((sum, item) => sum + Number(item.assignedQty || item.qty || 0), 0);
      const firstAssignment = assignments[0];
      const policyKind = bayPolicyKind(bay);
      const statusKind = bayStatusKind(bay);
      const policyLabel = policyKind === "manual" ? "Man" : policyKind === "blocked" ? "Blocked" : "Auto";
      const statusChip = ["available", "manual", "blocked"].includes(statusKind)
        ? ""
        : `<span class="status-chip status-${escapeHtml(statusKind)}">${escapeHtml(bayStatusLabel(bay))}</span>`;
      els.baySelectedPanel.innerHTML = `
        <div class="selected-bay-command-card selected-bay-command-card-v28 status-${escapeHtml(bayStatusKind(bay))} policy-${escapeHtml(policyKind)}">
          <div class="selected-bay-title-row selected-bay-title-row-v28">
            <div class="selected-bay-id-block">
              <span class="bay-status-dot status-${escapeHtml(bayStatusKind(bay))}"></span>
              <div class="selected-bay-title-copy">
                <small>${escapeHtml(bay.mapSection || bay.area || "Indian Trail")}</small>
                <strong>${escapeHtml(bay.displayName || bay.bayCode)}</strong>
              </div>
            </div>
            <div class="selected-bay-badge-stack">
              <span class="bay-policy-chip policy-${escapeHtml(policyKind)}" title="${escapeHtml(policyKind === "manual" ? "Manual Assign" : policyKind === "blocked" ? "Blocked Scans" : "Auto Assign")}">${escapeHtml(policyLabel)}</span>
              ${statusChip}
            </div>
          </div>

          <div class="selected-bay-metric-row selected-bay-metric-row-v28">
            <span><small>Category</small><strong>${escapeHtml(bayCategoryLabel(bayCategoryKind(bay)))}</strong></span>
            <span><small>Pieces</small><strong>${escapeHtml(assignedQty)}</strong></span>
            <span><small>Filled</small><strong>${escapeHtml(bayUtilization(bay).toFixed(0))}%</strong></span>
            <span><small>Primary Job</small><strong>${firstAssignment ? escapeHtml(assignmentJobLabel(firstAssignment)) : "None"}</strong></span>
          </div>

          <div class="capacity-meter selected-capacity-meter"><span style="width:${bayUtilization(bay)}%"></span></div>

          <div class="selected-bay-primary-actions selected-bay-primary-actions-v28">
            <button type="button" data-bay-action="scan-here">Use For Scanner</button>
            <button type="button" data-bay-action="hold" data-permission-any="clear_bay,move_bay">Manual Assign</button>
            <button type="button" data-bay-action="unblock" data-permission-any="clear_bay,move_bay">Auto Assign</button>
            <button type="button" class="danger-light" data-bay-action="block" data-permission-any="clear_bay,move_bay">Block Scans</button>
          </div>
        </div>

        <div class="selected-bay-jobs-header">
          <strong>Jobs in this bay</strong>
          <span>${escapeHtml(jobGroups.length)} job group${jobGroups.length === 1 ? "" : "s"}</span>
        </div>

        <div class="selected-assignment-list selected-assignment-list-v2 selected-bay-job-list">
          ${
            jobGroups.length
              ? jobGroups
                  .map(
                    (group) => {
                      const first = group.assignments[0];
                      return `
                      <article class="selected-bay-job-card" data-assignment-id="${escapeHtml(first.id)}">
                        <div class="selected-bay-job-main">
                          <div class="selected-bay-job-title">
                            ${group.assignments.some(isNewOrUpdatedItem) ? '<span class="bay-new-star" title="New or updated line">NEW</span>' : ""}
                            <strong>${escapeHtml(group.label)}</strong>
                          </div>
                          <span>${escapeHtml(group.customer || "No customer listed")}</span>
                          <small>${escapeHtml(group.itemCount)} item${group.itemCount === 1 ? "" : "s"} | ${escapeHtml(group.orderLine)} | Qty ${escapeHtml(group.totalQty)}</small>
                          <small>${escapeHtml(group.dimensions || "Mixed sizes")} | Delivery ${escapeHtml(formatDisplayDate(first.deliveryDate || ""))}</small>
                        </div>
                        <div class="assignment-actions assignment-actions-v2 selected-bay-job-actions">
                          <button type="button" title="Open manage workflow" data-assignment-action="manage" data-assignment-id="${escapeHtml(first.id)}">Manage</button>
                          <button type="button" title="Move this job" data-assignment-action="move" data-assignment-id="${escapeHtml(first.id)}">Move</button>
                          <button type="button" title="Clear this job from bay" data-assignment-action="clear" data-assignment-id="${escapeHtml(first.id)}">Clear</button>
                          <button type="button" title="Mark or clear SDI" data-assignment-action="sdi" data-assignment-id="${escapeHtml(first.id)}" data-order-no="${escapeHtml(first.order)}">SDI</button>
                        </div>
                      </article>
                    `;
                    }
                  )
                  .join("")
              : `<article class="selected-bay-empty-job"><strong>No assigned jobs</strong><small>This bay is available. Choose Use For Scanner, or manually assign an order from the bay scanner.</small></article>`
          }
        </div>
      `;
    }
  }
  if (els.bayAllBaysList) {
    const sections = bayTypeSections().filter((section) => state.bayCategoryFilter === "all" || section.kind === state.bayCategoryFilter);
    els.bayAllBaysList.innerHTML = sections
      .map((section) => {
        const sectionOpen = state.bayCategoryFilter !== "all" || section.bays.some((item) => item.bayCode === state.selectedBayCode);
        const occupiedBays = section.bays.filter((item) => Number(item.assignedQty || 0) > 0).length;
        return `
          <details class="bay-type-section type-${escapeHtml(section.kind)}" ${sectionOpen ? "open" : ""}>
            <summary><span><strong>${escapeHtml(section.label)} ${escapeHtml(section.bays.length)} bays</strong><small>${escapeHtml(occupiedBays)} / ${escapeHtml(section.bays.length)} occupied</small></span></summary>
            <div class="bay-rack-list">
              ${section.racks
                .map((rack) => {
                  const capacity = rack.bays.reduce((sum, item) => sum + Number(item.capacityQty || 0), 0);
                  const assigned = rack.bays.reduce((sum, item) => sum + Number(item.assignedQty || 0), 0);
                  const percent = capacity ? Math.min((assigned / capacity) * 100, 100) : assigned ? 100 : 0;
                  const rackHasSelected = rack.bays.some((item) => item.bayCode === state.selectedBayCode);
                  return `
                    <details class="bay-rack" ${state.bayCategoryFilter !== "all" || rackHasSelected ? "open" : ""} data-bay-drop-section="${escapeHtml(rack.label)}" data-bay-drop-category="${escapeHtml(section.kind)}">
                      <summary>
                        <strong>${escapeHtml(rack.label)}</strong>
                        <span>${escapeHtml(assigned)} / ${escapeHtml(capacity || rack.bays.length)}</span>
                      </summary>
                      <div class="capacity-meter"><span style="width:${percent}%"></span></div>
                      <div class="bay-slot-grid">${rack.bays.map((item) => renderBaySlotButton(item, "list")).join("")}</div>
                    </details>
                  `;
                })
                .join("")}
            </div>
          </details>
        `;
      })
      .join("");
  }
}

async function loadStaleBayOrders(includeSnoozed = false) {
  if (!state.backend) {
    state.staleBayOrders = [];
    return [];
  }
  const payload = await fetchJson(`/api/indian-trail/stale-bays${includeSnoozed ? "?includeSnoozed=1" : ""}`);
  state.staleBayOrders = payload.orders || [];
  return state.staleBayOrders;
}

async function maybeShowStaleBayAlert() {
  if (state.page !== "bays" || !hasPermission("view_bays")) return;
  const today = new Date().toISOString().slice(0, 10);
  const key = `staleBayAlertSeen:${state.user?.username || "user"}:${today}`;
  if (sessionStorage.getItem(key) === "1") return;
  const orders = await loadStaleBayOrders(false);
  if (!orders.length) return;
  sessionStorage.setItem(key, "1");
  openStaleBayPanel(orders);
}

function openStaleBayPanel(orders = state.staleBayOrders) {
  if (!els.staleBayPanel || !els.staleBayBackdrop) return;
  renderStaleBayPanel(orders || []);
  els.staleBayPanel.hidden = false;
  els.staleBayBackdrop.hidden = false;
  updateModalScrollLock();
}

function closeStaleBayPanel() {
  if (els.staleBayPanel) els.staleBayPanel.hidden = true;
  if (els.staleBayBackdrop) els.staleBayBackdrop.hidden = true;
  updateModalScrollLock();
}

function renderStaleBayPanel(orders) {
  if (!els.staleBayList) return;
  const list = Array.isArray(orders) ? orders : [];
  const oldestDays = list.reduce((max, order) => Math.max(max, Number(order.daysOld || 0)), 0);
  const bayCount = new Set(list.map((order) => order.bayCode || order.bayDisplay).filter(Boolean)).size;

  if (!list.length) {
    els.staleBayList.innerHTML = `
      <section class="stale-bay-summary-cards">
        <article><small>Old bay rows</small><strong>0</strong><span>Nothing needs review</span></article>
        <article><small>Bays affected</small><strong>0</strong><span>Clear right now</span></article>
        <article><small>Oldest row</small><strong>0 days</strong><span>No aged rows</span></article>
      </section>
      <div class="stale-bay-empty">
        <strong>No old bay orders right now.</strong>
        <span>Indian Trail bay assignments older than 10 days will appear here.</span>
      </div>
    `;
    return;
  }

  els.staleBayList.innerHTML = `
    <section class="stale-bay-summary-cards">
      <article><small>Old bay rows</small><strong>${escapeHtml(list.length)}</strong><span>Need walkthrough</span></article>
      <article><small>Bays affected</small><strong>${escapeHtml(bayCount)}</strong><span>Physical locations</span></article>
      <article><small>Oldest row</small><strong>${escapeHtml(oldestDays)} days</strong><span>Assigned age</span></article>
    </section>
    <div class="stale-bay-card-list">
      ${list
        .map((order) => `
          <article class="stale-bay-order">
            <div class="stale-bay-main">
              <div class="stale-bay-title-row">
                <div class="stale-bay-identity">
                  <span class="stale-bay-id-line">
                    <strong>${escapeHtml(order.order)}-${escapeHtml(order.item)}</strong>
                    <span class="stale-age-pill">${escapeHtml(order.daysOld)} days</span>
                  </span>
                  <span class="stale-bay-customer">${escapeHtml(order.customer || "No customer listed")}</span>
                </div>
                <span class="stale-bay-bay-pill">Bay ${escapeHtml(order.bayDisplay || order.bayCode)}</span>
              </div>
              <div class="stale-bay-meta-grid">
                <small><b>Glass</b>${escapeHtml(order.job || order.product || "-")}</small>
                <small><b>Size</b>${escapeHtml(order.dimensions || "-")}</small>
                <small><b>Delivery</b>${escapeHtml(formatDisplayDate(order.deliveryDate || ""))}</small>
                <small><b>Last scanned</b>${escapeHtml(formatDateTime(order.lastScannedAt) || "Not scanned")}</small>
              </div>
            </div>
            <div class="stale-snooze-row">
              <label>
                <span>Snooze</span>
                <select data-stale-days="${escapeHtml(order.assignmentId)}" aria-label="Snooze days">
                  <option value="1">1 day</option>
                  <option value="3">3 days</option>
                  <option value="7">1 week</option>
                  <option value="14">2 weeks</option>
                  <option value="30">30 days</option>
                </select>
              </label>
              <button type="button" data-stale-snooze="${escapeHtml(order.assignmentId)}">Snooze</button>
            </div>
          </article>
        `)
        .join("")}
    </div>
  `;
}

async function snoozeStaleBayOrders(assignmentIds, days) {
  const payload = await fetchJson("/api/indian-trail/stale-bays/snooze", {
    method: "POST",
    body: JSON.stringify({ assignmentIds, days }),
  });
  state.staleBayOrders = payload.orders || [];
  renderStaleBayPanel(state.staleBayOrders);
  await refreshBayMapPage();
}

function renderBayLegend() {
  if (!els.bayLegend) return;
  const legend = [
    ["Coral", "Reserved coral bays", "coral"],
    ["LR / RR", "Deep blue LR and RR bays", "lr-rr"],
    ["Showers", "Green shower bays", "showers"],
    ["Mirror", "Purple mirror and BFS mirror bays", "mirror"],
    ["Framed", "Teal framed mirror bays", "framed-mirror"],
    ["CRL", "Yellow CRL Laurence bays", "crl"],
    ["AVL", "Available bay", "empty"],
    ["OCC", "Occupied / assigned", "occupied"],
    ["SDI", "Needs special handling", "sdi"],
  ];
  els.bayLegend.innerHTML = legend
    .map(([abbr, label, kind]) => `<span class="legend-item ${escapeHtml(kind)}"><i></i><strong>${escapeHtml(abbr)}</strong>${escapeHtml(label)}</span>`)
    .join("");
}

function formatEventType(value) {
  return String(value || "")
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/_/g, " ");
}

function bayEventTone(event) {
  const text = `${event.eventType || ""} ${event.reason || ""}`.toLowerCase();
  if (text.includes("error") || text.includes("blocked") || text.includes("needs")) return "error";
  if (text.includes("hold") || text.includes("move") || text.includes("sdi") || text.includes("layout") || text.includes("available")) return "notice";
  return "ok";
}

function renderBayLastScanCard(event) {
  const hasEvent = Boolean(event);
  const tone = hasEvent ? bayEventTone(event) : "notice";
  const when = new Date(event?.time || event?.createdAt || "");
  const time = hasEvent && !Number.isNaN(when.getTime()) ? when.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }) : "-";
  const bay = event?.bayDisplay || event?.bayCode || event?.newBayDisplay || event?.newBayCode || event?.oldBayDisplay || event?.oldBayCode || "-";
  const order = event?.order ? `${event.order}-${event.item || ""}` : "-";
  const action = hasEvent ? formatEventType(event.eventType || event.reason || "Bay action") : "-";
  const title = hasEvent
    ? [action, event?.reason].filter(Boolean).join(" - ")
    : "No bay scans yet";

  els.bayLastCard?.classList.remove("ok", "notice", "error");
  els.bayLastCard?.classList.add(hasEvent ? tone : "notice");
  if (els.bayLastTitle) els.bayLastTitle.textContent = title;
  if (els.bayLastAction) els.bayLastAction.textContent = action;
  if (els.bayLastOrder) els.bayLastOrder.textContent = order;
  if (els.bayLastBay) els.bayLastBay.textContent = bay;
  if (els.bayLastTime) els.bayLastTime.textContent = time;
  if (els.bayScanOutStatus && !hasEvent) els.bayScanOutStatus.textContent = "Waiting";
  if (els.bayScanOutStatus && hasEvent) els.bayScanOutStatus.textContent = tone === "error" ? "Needs review" : tone === "notice" ? "Notice" : "Just now";
}

function renderBayRecentActions() {
  const events = state.bayEvents || [];
  renderBayLastScanCard(events[0] || null);
  if (!els.bayScanOutRecent) return;
  const recentRows = events.slice(1, 3);
  els.bayScanOutRecent.innerHTML = recentRows.length
    ? recentRows.map((event) => {
        const when = new Date(event.time || event.createdAt || "");
        const time = Number.isNaN(when.getTime()) ? "" : when.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
        const bay = event.bayDisplay || event.bayCode || event.newBayCode || event.oldBayCode || "Bay";
        const order = event.order ? `${event.order}-${event.item || ""}` : "Bay action";
        const tone = bayEventTone(event);
        return `
          <tr class="${escapeHtml(tone)}">
            <td>${escapeHtml(formatEventType(event.eventType || event.reason || "Bay action"))}</td>
            <td>${escapeHtml(order)}</td>
            <td>${escapeHtml(bay)}</td>
            <td>${escapeHtml(time)}</td>
            <td><span class="check-dot ${escapeHtml(tone)}">${escapeHtml(tone === "error" ? "!" : tone === "notice" ? "i" : "✓")}</span></td>
          </tr>
        `;
      }).join("")
    : `<tr><td colspan="5"><div class="bay-history-empty"><strong>Recent bay actions</strong><span>The next two actions will appear here.</span></div></td></tr>`;
}

function scrollToBaySearchMatch() {
  if (!els.bayMapCanvas) return;
  renderBayMapPage();
  const target =
    els.bayMapCanvas.querySelector(".physical-bay-slot.is-search-match:not(.is-dimmed), .physical-bay-slot.is-search-match") ||
    els.bayAllBaysList?.querySelector(".bay-slot.is-search-match:not(.is-dimmed), .bay-slot.is-search-match");
  if (!target) {
    showInlineError("No bay map match found for that search.", false);
    return;
  }
  target.classList.add("is-found");
  target.scrollIntoView({ behavior: "smooth", block: "center", inline: "center" });
  window.setTimeout(() => target.classList.remove("is-found"), 1800);
}

function selectedBay() {
  return state.bays.find((bay) => bay.bayCode === state.selectedBayCode) || null;
}

function selectBay(bayCode) {
  state.selectedBayCode = bayCode || "";
  renderBayMapPage();
  if (state.bayEditMode) {
    renderBayLayoutSelect();
    if (els.bayLayoutSelect) els.bayLayoutSelect.value = bayCode;
    populateBayLayoutForm();
  }
  if (bayCode && els.baySelectedModal) {
    els.baySelectedModal.hidden = false;
    if (els.baySelectedBackdrop) els.baySelectedBackdrop.hidden = false;
    updateModalScrollLock();
  }
}

function closeSelectedBayModal() {
  if (els.baySelectedModal) els.baySelectedModal.hidden = true;
  if (els.baySelectedBackdrop) els.baySelectedBackdrop.hidden = true;
  updateModalScrollLock();
}

function requireSelectedBay() {
  const bay = selectedBay();
  if (!bay) {
    showInlineError("Select a bay first.", false);
    return null;
  }
  return bay;
}

async function postBayAction(path, payload) {
  const result = await fetchJson(path, {
    method: "POST",
    body: JSON.stringify({ ...payload, ...requestContext() }),
  });
  await refreshBayMapPage();
  return result;
}

function pushBayHistory(entry) {
  if (!entry?.undo || !entry?.redo) return;
  state.bayActionUndoStack.push(entry);
  state.bayActionRedoStack = [];
}

async function runBayHistory(direction) {
  const from = direction === "undo" ? state.bayActionUndoStack : state.bayActionRedoStack;
  const to = direction === "undo" ? state.bayActionRedoStack : state.bayActionUndoStack;
  const entry = from.pop();
  if (!entry) {
    showFloatingNotice(`No bay action to ${direction}.`, "notice");
    return;
  }
  await (direction === "undo" ? entry.undo() : entry.redo());
  to.push(entry);
  await refreshBayMapPage();
  showFloatingNotice(`${direction === "undo" ? "Undid" : "Redid"} ${entry.label}.`, "success");
}

async function submitBayScanOut() {
  const barcode = els.bayScanOutInput?.value.trim() || "";
  if (!barcode) return;
  const bayCode = els.bayScanBayInput?.value.trim() || "";
  const adding = Boolean(els.bayScanModeToggle?.checked);
  const result = adding
    ? await postBayAction("/api/indian-trail/receive", { barcode, bayCode, reason: "Scanned into bay map" })
    : await postBayAction("/api/indian-trail/scan-out", { barcode, bayCode, reason: "Scanned out from bay map" });

  if (!adding && result.assignmentId) {
    pushBayHistory({
      label: `scan-out ${result.order}-${result.item}`,
      undo: () => postBayAction("/api/indian-trail/restore-assignment", { assignmentId: result.assignmentId, reason: "Undo bay scan-out" }),
      redo: () => postBayAction("/api/indian-trail/scan-out", { barcode, bayCode: result.bayCode || bayCode, reason: "Redo bay scan-out" }),
    });
  }

  if (adding && Array.isArray(result.assignmentIds) && result.assignmentIds.length) {
    const assignedIds = result.assignmentIds.slice();
    pushBayHistory({
      label: `bay receive ${barcode}`,
      undo: () => Promise.all(assignedIds.map((assignmentId) => postBayAction("/api/indian-trail/clear-assignment", { assignmentId, reason: "Undo bay receive/manual assign" }))),
      redo: () => postBayAction("/api/indian-trail/receive", { barcode, bayCode: result.bayCode || bayCode, reason: "Redo bay receive/manual assign" }),
    });
  }

  if (els.bayScanOutInput) els.bayScanOutInput.value = "";
  if (els.bayScanOutStatus) els.bayScanOutStatus.textContent = adding ? result.message : `Removed ${result.order}-${result.item} from ${result.bayDisplay || result.bayCode}`;
  scanFlash("success");
  showFloatingNotice(adding ? result.message : `Removed ${result.order}-${result.item} from ${result.bayDisplay || result.bayCode}`, "success");
}

function manualBayInputText() {
  return (els.bayManualOrderInput?.value || "").trim();
}

async function confirmManualBayUnknown(message, details) {
  return new Promise((resolve) => {
    const existing = document.querySelector(".manual-bay-confirm-backdrop");
    if (existing) existing.remove();
    const dialog = document.createElement("div");
    dialog.className = "manual-bay-confirm-backdrop action-confirm-backdrop";
    dialog.innerHTML = `
      <section class="action-confirm-dialog manual-bay-confirm-dialog" role="dialog" aria-modal="true">
        <button type="button" class="action-confirm-close" data-manual-bay-choice="no" aria-label="Close">&times;</button>
        <span class="action-confirm-icon" aria-hidden="true"></span>
        <div class="action-confirm-copy">
          <h2>Unrecognized manual assignment</h2>
          <p>${escapeHtml(message || "This does not match a known order, Job Nr., or accepted bay barcode rule.")}</p>
          ${details ? `<small>${escapeHtml(details)}</small>` : ""}
        </div>
        <div class="action-confirm-actions manual-bay-confirm-actions">
          <button type="button" class="action-confirm-cancel" data-manual-bay-choice="no">No</button>
          <button type="button" class="action-confirm-confirm" data-manual-bay-choice="yes">Yes, assign once</button>
          <button type="button" class="action-confirm-confirm remember" data-manual-bay-choice="remember">Yes, remember this</button>
        </div>
      </section>
    `;
    const close = (choice) => {
      dialog.remove();
      document.body.classList.remove("modal-scroll-locked");
      updateModalScrollLock();
      resolve(choice);
    };
    dialog.addEventListener("click", (event) => {
      const button = event.target.closest("[data-manual-bay-choice]");
      if (button) close(button.dataset.manualBayChoice || "no");
      else if (event.target === dialog) close("no");
    });
    document.body.appendChild(dialog);
    document.body.classList.add("modal-scroll-locked");
    dialog.querySelector("[data-manual-bay-choice='no']")?.focus();
  });
}

async function submitManualBayScan() {
  const scanText = manualBayInputText();
  const itemNo = (els.bayManualItemInput?.value || "").trim();
  const bayCode = (els.bayScanBayInput?.value || "").trim();
  if (!scanText) throw new Error("Enter an order, Job Nr., barcode, or manual wording.");
  if (!bayCode) throw new Error("Choose a target bay before manual assigning.");

  const payload = { scanText, itemNo, bayCode, confirmUnrecognized: false, rememberUnrecognized: false };
  let result = await postBayAction("/api/indian-trail/manual-assign", payload);

  if (result?.needsConfirmation) {
    const choice = await confirmManualBayUnknown(result.message, `Input: ${scanText} | Target bay: ${bayCode}`);
    if (choice === "no") return;
    result = await postBayAction("/api/indian-trail/manual-assign", {
      ...payload,
      confirmUnrecognized: true,
      rememberUnrecognized: choice === "remember",
    });
  }

  if (Array.isArray(result.assignmentIds) && result.assignmentIds.length) {
    const assignedIds = result.assignmentIds.slice();
    pushBayHistory({
      label: `manual assign ${scanText}`,
      undo: () => Promise.all(assignedIds.map((assignmentId) => postBayAction("/api/indian-trail/clear-assignment", { assignmentId, reason: "Undo manual bay assignment" }))),
      redo: () => postBayAction("/api/indian-trail/manual-assign", { scanText, itemNo, bayCode, confirmUnrecognized: true, rememberUnrecognized: false, reason: "Redo manual bay assignment" }),
    });
  }

  if (els.bayManualOrderInput) els.bayManualOrderInput.value = "";
  if (els.bayManualItemInput) els.bayManualItemInput.value = "";
  showFloatingNotice(result.message || "Manual bay assignment complete.", "success");
}

function selectedBayAssignment() {
  return selectedBay()?.assignments?.[0] || null;
}

function assignmentById(assignmentId) {
  const id = String(assignmentId || "");
  for (const bay of state.bays || []) {
    const match = (bay.assignments || []).find((assignment) => String(assignment.id) === id);
    if (match) return { bay, assignment: match };
  }
  return { bay: selectedBay(), assignment: selectedBayAssignment() };
}


function bayAssignmentRows() {
  const rows = [];
  for (const bay of state.bays || []) {
    const groups = groupAssignmentsByJob(bay.assignments || []);
    for (const group of groups) {
      const assignment = group.assignments[0];
      rows.push({ bay, assignment, assignments: group.assignments, jobKey: group.key, jobLabel: group.label, itemCount: group.itemCount, totalQty: group.totalQty, orderLine: group.orderLine });
    }
  }
  return rows.sort((a, b) => `${a.bay.displayName || a.bay.bayCode}`.localeCompare(`${b.bay.displayName || b.bay.bayCode}`) || `${a.jobLabel}`.localeCompare(`${b.jobLabel}`));
}

function selectedManageItem() {
  const rows = bayAssignmentRows();
  if (!state.manageItemsSelectedId && rows.length) state.manageItemsSelectedId = String(rows[0].assignment.id || "");
  return rows.find(({ assignment }) => String(assignment.id) === String(state.manageItemsSelectedId)) || rows[0] || null;
}

function bayOptionGroups(selectedValue = "") {
  const sections = bayPhysicalSections();
  return sections
    .map((section) => {
      const options = section.bays
        .filter((bay) => bayCategoryKind(bay) !== "spacer")
        .map((bay) => `<option value="${escapeHtml(bay.bayCode)}" ${bay.bayCode === selectedValue ? "selected" : ""}>${escapeHtml(bay.displayName || bay.bayCode)} - ${escapeHtml(bay.status || "Available")}</option>`)
        .join("");
      return options ? `<optgroup label="${escapeHtml(section.label)}">${options}</optgroup>` : "";
    })
    .join("");
}

function renderManageItemsPanel() {
  if (!els.manageItemsPanel) return;
  const query = String(state.manageItemsQuery || "").trim().toLowerCase();
  const rows = bayAssignmentRows().filter(({ bay, assignment }) => {
    if (!query) return true;
    return [
      bay.bayCode,
      bay.displayName,
      bay.mapSection,
      assignment.order,
      assignment.item,
      assignment.customer,
      assignment.product,
      assignment.job,
      assignment.dimensions,
      assignment.status,
    ].join(" ").toLowerCase().includes(query);
  });
  if (!rows.some(({ assignment }) => String(assignment.id) === String(state.manageItemsSelectedId))) {
    state.manageItemsSelectedId = rows[0]?.assignment.id ? String(rows[0].assignment.id) : "";
  }
  const selected = selectedManageItem();

  if (els.manageItemsSearch && els.manageItemsSearch.value !== state.manageItemsQuery) els.manageItemsSearch.value = state.manageItemsQuery;
  if (els.manageItemsList) {
    els.manageItemsList.innerHTML = rows.length
      ? rows.map(({ bay, assignment, jobLabel, itemCount, totalQty, orderLine }) => `
          <button type="button" class="manage-item-row ${String(assignment.id) === String(state.manageItemsSelectedId) ? "is-active" : ""}" data-manage-assignment-id="${escapeHtml(assignment.id)}">
            <span><strong>${escapeHtml(jobLabel)}</strong><small>${escapeHtml(itemCount)} item${itemCount === 1 ? "" : "s"} / Qty ${escapeHtml(totalQty)} - ${escapeHtml(assignment.customer || "No customer")}</small><small>${escapeHtml(orderLine)}</small></span>
            <em>${escapeHtml(bay.displayName || bay.bayCode)}</em>
          </button>
        `).join("")
      : `<div class="manage-items-empty"><strong>No bay items found.</strong><span>Adjust the search or filters and try again.</span></div>`;
  }
  if (els.manageItemsTargetBay) {
    const currentBay = selected?.bay?.bayCode || state.selectedBayCode || "";
    const selectedValue = els.manageItemsTargetBay.value || currentBay;
    els.manageItemsTargetBay.innerHTML = bayOptionGroups(selectedValue);
    if (selectedValue) els.manageItemsTargetBay.value = selectedValue;
  }
  if (els.manageItemsSelected) {
    if (!selected) {
      els.manageItemsSelected.innerHTML = `<div class="manage-items-empty"><strong>Select an item</strong><span>All active bay assignments will appear on the left.</span></div>`;
    } else {
      const { bay, assignment } = selected;
      const groupAssignments = selected.assignments || [assignment];
      els.manageItemsSelected.innerHTML = `
        <article class="manage-selected-card status-${escapeHtml(bayStatusKind(bay))}">
          <div>
            <span class="bay-page-eyebrow">Selected Job Nr.</span>
            <h3>${escapeHtml(selected.jobLabel || assignmentJobLabel(assignment))}</h3>
            <p>${escapeHtml(assignment.customer || "No customer listed")}</p>
          </div>
          <div class="manage-selected-stats">
            ${miniStat("Current Bay", bay.displayName || bay.bayCode)}
            ${miniStat("Items", groupAssignments.length)}
            ${miniStat("Total Qty", selected.totalQty || groupAssignments.reduce((sum, item) => sum + Number(item.assignedQty || item.qty || 0), 0))}
            ${miniStat("Status", assignment.status || bay.status || "Assigned")}
          </div>
          <small>${escapeHtml((selected.orderLine || groupAssignments.map((item) => `${item.order}-${item.item}`).join(", ")) || "No item list")}</small>
        </article>
      `;
    }
  }
  if (els.manageItemsStatus) {
    els.manageItemsStatus.textContent = selected ? `Ready to manage ${selected.jobLabel || `${selected.assignment.order}-${selected.assignment.item}`}.` : "Select an item to begin.";
  }
}

function openManageItemsPanel(assignmentId = "") {
  if (!els.manageItemsPanel || !els.manageItemsBackdrop) return;
  if (assignmentId) state.manageItemsSelectedId = String(assignmentId);
  else if (selectedBayAssignment()?.id) state.manageItemsSelectedId = String(selectedBayAssignment().id);
  renderManageItemsPanel();
  els.manageItemsPanel.hidden = false;
  els.manageItemsBackdrop.hidden = false;
  updateModalScrollLock();
  els.manageItemsSearch?.focus();
}

function closeManageItemsPanel() {
  if (els.manageItemsPanel) els.manageItemsPanel.hidden = true;
  if (els.manageItemsBackdrop) els.manageItemsBackdrop.hidden = true;
  updateModalScrollLock();
}

async function moveManagedItem() {
  const selected = selectedManageItem();
  const targetBay = els.manageItemsTargetBay?.value || "";
  const reason = els.manageItemsReason?.value || "Managed from Bay Map";
  if (!selected?.assignment?.id) throw new Error("Select a job to move.");
  if (!targetBay) throw new Error("Select a destination bay.");
  const groupAssignments = selected.assignments || [selected.assignment];
  for (const assignment of groupAssignments) {
    await fetchJson("/api/indian-trail/move", {
      method: "POST",
      body: JSON.stringify({ assignmentId: assignment.id, newBayCode: targetBay, reason, ...requestContext() }),
    });
  }
  await refreshBayMapPage();
  if (els.manageItemsStatus) els.manageItemsStatus.textContent = `Moved ${selected.jobLabel || `${selected.assignment.order}-${selected.assignment.item}`} to ${targetBay}.`;
  renderManageItemsPanel();
}

async function clearManagedItem() {
  const selected = selectedManageItem();
  const reason = els.manageItemsReason?.value || "Cleared from Manage Items";
  if (!selected?.assignment?.id) throw new Error("Select a job to clear.");
  const groupAssignments = selected.assignments || [selected.assignment];
  const label = selected.jobLabel || `${selected.assignment.order}-${selected.assignment.item}`;
  if (!window.confirm(`Clear ${label} (${groupAssignments.length} item${groupAssignments.length === 1 ? "" : "s"}) from ${selected.bay.displayName || selected.bay.bayCode}?`)) return;
  for (const assignment of groupAssignments) {
    await fetchJson("/api/indian-trail/clear-assignment", {
      method: "POST",
      body: JSON.stringify({ assignmentId: assignment.id, reason, ...requestContext() }),
    });
  }
  await refreshBayMapPage();
  if (els.manageItemsStatus) els.manageItemsStatus.textContent = `Cleared ${label}.`;
  renderManageItemsPanel();
}

function useManagedBayForScanner() {
  const targetBay = els.manageItemsTargetBay?.value || selectedManageItem()?.bay?.bayCode || "";
  if (!targetBay) {
    showInlineError("Select a bay before sending it to the scanner.", false);
    return;
  }
  if (els.bayScanBayInput) els.bayScanBayInput.value = targetBay;
  if (els.bayScanModeToggle) els.bayScanModeToggle.checked = true;
  if (els.bayScanOutInput) {
    els.bayScanOutInput.placeholder = `Scan order to add to ${targetBay}...`;
    els.bayScanOutInput.focus();
  }
  closeManageItemsPanel();
  showFloatingNotice(`${targetBay} is ready in the bay scanner.`, "success");
}

function bayEditorGroups() {
  return bayPhysicalSections().sort((a, b) => a.col - b.col || a.row - b.row || a.label.localeCompare(b.label));
}

function bayEditorSelectedGroupObject() {
  const groups = bayEditorGroups();
  if (!state.bayEditorSelectedGroup && groups.length) state.bayEditorSelectedGroup = groups[0].label;
  return groups.find((group) => group.label === state.bayEditorSelectedGroup) || groups[0] || null;
}

function bayEditorPolicyForGroup(group) {
  const policies = (group?.bays || []).map((bay) => bayPolicyKind(bay));
  if (policies.length && policies.every((policy) => policy === "blocked")) return "blocked";
  if (policies.length && policies.every((policy) => policy === "manual")) return "manual";
  return "auto";
}

function bayEditorStatusFromPolicy(policy) {
  if (policy === "blocked") return "ScanBlocked";
  if (policy === "manual") return "ManualAssign";
  return "Available";
}

function renderBayEditorPanel() {
  const groups = bayEditorGroups();
  const selectedGroup = bayEditorSelectedGroupObject();
  if (els.bayEditorGroupList) {
    els.bayEditorGroupList.innerHTML = groups.length
      ? groups.map((group) => {
          const active = group.label === selectedGroup?.label;
          const used = group.bays.filter((bay) => Number(bay.assignedQty || 0) > 0).length;
          const policy = bayEditorPolicyForGroup(group);
          return `
            <button type="button" class="bay-editor-group-row ${active ? "is-active" : ""}" data-bay-editor-group="${escapeHtml(group.label)}">
              <span><strong>${escapeHtml(group.label)}</strong><small>${escapeHtml(group.bays.length)} bays / ${escapeHtml(used)} used</small></span>
              <em class="policy-${escapeHtml(policy)}">${escapeHtml(policy === "blocked" ? "Blocked" : policy === "manual" ? "Man" : "Auto")}</em>
            </button>
          `;
        }).join("")
      : `<div class="bay-editor-empty"><strong>No bay groups found.</strong><span>Create a grouped set of bays to begin.</span></div>`;
  }

  if (!selectedGroup) {
    if (els.bayEditorGroupForm) {
      els.bayEditorGroupForm.innerHTML = bayEditorNewGroupFormMarkup();
    }
    if (els.bayEditorBayList) els.bayEditorBayList.innerHTML = "";
    return;
  }

  const firstBay = selectedGroup.bays[0] || {};
  const policy = bayEditorPolicyForGroup(selectedGroup);
  if (els.bayEditorGroupForm) {
    els.bayEditorGroupForm.innerHTML = `
      <div class="bay-editor-card bay-editor-group-card">
        <div>
          <span class="bay-page-eyebrow">Grouped bay set</span>
          <h3>${escapeHtml(selectedGroup.label)}</h3>
          <p>Rename this grouped set, set assign behavior, create more bays inside it, or delete the group after clearing active assignments.</p>
        </div>
        <div class="bay-editor-form-grid">
          <label><span>Group name</span><input id="bayEditorGroupNameInput" type="text" value="${escapeHtml(selectedGroup.label)}"></label>
          <label><span>Category</span><input id="bayEditorGroupCategoryInput" type="text" value="${escapeHtml(firstBay.bayCategory || selectedGroup.kind || "Standard")}"></label>
          <label><span>Assign behavior</span><select id="bayEditorGroupPolicyInput">
            <option value="auto" ${policy === "auto" ? "selected" : ""}>Auto assign / free for preassign</option>
            <option value="manual" ${policy === "manual" ? "selected" : ""}>Manual assign only</option>
            <option value="blocked" ${policy === "blocked" ? "selected" : ""}>Blocked for all scanning</option>
          </select></label>
          <label><span>Map row</span><input id="bayEditorGroupRowInput" type="number" min="1" max="7" value="${escapeHtml(Math.round(Number(selectedGroup.row || 1)))}"></label>
          <label><span>Map column</span><input id="bayEditorGroupColInput" type="number" min="1" max="7" value="${escapeHtml(Math.round(Number(selectedGroup.col || 1)))}"></label>
          <label><span>Add bay count</span><input id="bayEditorAddCountInput" type="number" min="1" max="50" value="1"></label>
          <label><span>New bay prefix</span><input id="bayEditorAddPrefixInput" type="text" value="${escapeHtml(selectedGroup.label)}"></label>
        </div>
        <div class="bay-editor-actions">
          <button type="button" data-bay-editor-action="save-group">Save Group</button>
          <button type="button" data-bay-editor-action="add-bays">Add Bays To Group</button>
          <button type="button" class="danger" data-bay-editor-action="delete-group">Delete Group</button>
        </div>
      </div>
      ${bayEditorNewGroupFormMarkup(false)}
    `;
  }

  if (els.bayEditorBayList) {
    const bays = selectedGroup.bays.slice().sort((a, b) => Number(a.sortOrder || a.layoutRow || 9999) - Number(b.sortOrder || b.layoutRow || 9999) || String(a.displayName || a.bayCode).localeCompare(String(b.displayName || b.bayCode)));
    els.bayEditorBayList.innerHTML = `
      <div class="bay-editor-bay-heading">
        <div><strong>Individual Bays</strong><span>Edit names, capacity, behavior, or remove empty bays.</span></div>
        <span>${escapeHtml(bays.length)} bay${bays.length === 1 ? "" : "s"}</span>
      </div>
      ${bays.map((bay) => bayEditorBayRowMarkup(bay)).join("")}
    `;
  }
}

function bayEditorNewGroupFormMarkup(standalone = true) {
  return `
    <div class="bay-editor-card bay-editor-new-card ${standalone ? "standalone" : ""}">
      <div>
        <span class="bay-page-eyebrow">Create grouped set</span>
        <h3>New Bay Group</h3>
        <p>Create a grouped set of bays, then move it into the exact map position in Edit Map.</p>
      </div>
      <div class="bay-editor-form-grid compact">
        <label><span>Group name</span><input id="bayEditorNewGroupNameInput" type="text" placeholder="Example: Showers A"></label>
        <label><span>Category</span><input id="bayEditorNewGroupCategoryInput" type="text" placeholder="Showers, Mirror, Coral..."></label>
        <label><span>Bay count</span><input id="bayEditorNewGroupCountInput" type="number" min="1" max="50" value="1"></label>
        <label><span>Bay prefix</span><input id="bayEditorNewGroupPrefixInput" type="text" placeholder="SHOWER-A"></label>
        <label><span>Map row</span><input id="bayEditorNewGroupRowInput" type="number" min="1" max="7" value="1"></label>
        <label><span>Map column</span><input id="bayEditorNewGroupColInput" type="number" min="1" max="7" value="1"></label>
      </div>
      <div class="bay-editor-actions">
        <button type="button" data-bay-editor-action="create-group">Create Group</button>
      </div>
    </div>
  `;
}

function bayEditorBayRowMarkup(bay) {
  const policy = bayPolicyKind(bay);
  const assigned = (bay.assignments || []).length;
  return `
    <article class="bay-editor-bay-row" data-editor-bay-code="${escapeHtml(bay.bayCode)}">
      <div class="bay-editor-bay-summary">
        <strong>${escapeHtml(bay.displayName || bay.bayCode)}</strong>
        <span>${escapeHtml(bay.bayCode)}${assigned ? ` / ${escapeHtml(assigned)} assigned job${assigned === 1 ? "" : "s"}` : " / empty"}</span>
      </div>
      <label><span>Name</span><input data-editor-field="displayName" type="text" value="${escapeHtml(bay.displayName || bay.bayCode)}"></label>
      <label><span>Group</span><input data-editor-field="mapSection" type="text" value="${escapeHtml(bay.mapSection || "")}"></label>
      <label><span>Category</span><input data-editor-field="bayCategory" type="text" value="${escapeHtml(bay.bayCategory || "")}"></label>
      <label><span>Capacity</span><input data-editor-field="capacityQty" type="number" min="0" value="${escapeHtml(bay.capacityQty || 0)}"></label>
      <label><span>Status</span><select data-editor-field="policy">
        <option value="auto" ${policy === "auto" ? "selected" : ""}>Auto assign</option>
        <option value="manual" ${policy === "manual" ? "selected" : ""}>Manual only</option>
        <option value="blocked" ${policy === "blocked" ? "selected" : ""}>Blocked</option>
      </select></label>
      <div class="bay-editor-row-actions">
        <button type="button" data-bay-editor-action="save-bay" data-bay-code="${escapeHtml(bay.bayCode)}">Save</button>
        <button type="button" class="danger" data-bay-editor-action="delete-bay" data-bay-code="${escapeHtml(bay.bayCode)}">Delete</button>
      </div>
    </article>
  `;
}

function openBayEditorPanel(groupLabel = "") {
  if (!els.bayEditorPanel || !els.bayEditorBackdrop) return;
  state.bayEditorSelectedGroup = groupLabel || state.bayEditorSelectedGroup || bayPhysicalSections()[0]?.label || "";
  renderBayEditorPanel();
  els.bayEditorPanel.hidden = false;
  els.bayEditorBackdrop.hidden = false;
  updateModalScrollLock();
}

function closeBayEditorPanel() {
  if (els.bayEditorPanel) els.bayEditorPanel.hidden = true;
  if (els.bayEditorBackdrop) els.bayEditorBackdrop.hidden = true;
  updateModalScrollLock();
}

async function refreshBayEditorAfter(payload) {
  if (payload?.bays) state.bays = payload.bays;
  await refreshBayMapPage();
  renderBayEditorPanel();
}

async function saveBayEditorGroup() {
  const group = bayEditorSelectedGroupObject();
  if (!group) throw new Error("Select a bay group first.");
  const groupName = document.getElementById("bayEditorGroupNameInput")?.value.trim() || group.label;
  const category = document.getElementById("bayEditorGroupCategoryInput")?.value.trim() || group.kind || "Standard";
  const policy = document.getElementById("bayEditorGroupPolicyInput")?.value || "auto";
  const row = Number(document.getElementById("bayEditorGroupRowInput")?.value || group.row || 1);
  const col = Number(document.getElementById("bayEditorGroupColInput")?.value || group.col || 1);

  for (const bay of group.bays) {
    await fetchJson("/api/indian-trail/layout", {
      method: "POST",
      body: JSON.stringify({
        bayCode: bay.bayCode,
        displayName: bay.displayName || bay.bayCode,
        mapSection: groupName,
        bayCategory: category,
        layoutRow: row,
        layoutCol: col,
        capacityQty: bay.capacityQty || 0,
        active: bay.active !== false,
        ...requestContext(),
      }),
    });
    await fetchJson("/api/indian-trail/bay-status", {
      method: "POST",
      body: JSON.stringify({ bayCode: bay.bayCode, status: bayEditorStatusFromPolicy(policy), reason: "Updated from Edit Bays", ...requestContext() }),
    });
  }
  state.bayEditorSelectedGroup = groupName;
  await refreshBayMapPage();
  renderBayEditorPanel();
  showFloatingNotice(`Saved ${groupName}.`, "success");
}

async function createBayEditorGroup() {
  const name = document.getElementById("bayEditorNewGroupNameInput")?.value.trim() || "";
  const category = document.getElementById("bayEditorNewGroupCategoryInput")?.value.trim() || "Standard";
  const count = Number(document.getElementById("bayEditorNewGroupCountInput")?.value || 1);
  const prefix = document.getElementById("bayEditorNewGroupPrefixInput")?.value.trim() || name;
  const row = Number(document.getElementById("bayEditorNewGroupRowInput")?.value || 1);
  const col = Number(document.getElementById("bayEditorNewGroupColInput")?.value || 1);
  if (!name) throw new Error("Enter a group name before creating bays.");
  const payload = await fetchJson("/api/indian-trail/bays/add", {
    method: "POST",
    body: JSON.stringify({ mapSection: name, bayCategory: category, prefix, count, layoutRow: row, layoutCol: col, ...requestContext() }),
  });
  state.bayEditorSelectedGroup = name;
  await refreshBayEditorAfter(payload);
  showFloatingNotice(`Created ${name}.`, "success");
}

async function addBaysToEditorGroup() {
  const group = bayEditorSelectedGroupObject();
  if (!group) throw new Error("Select a bay group first.");
  const count = Number(document.getElementById("bayEditorAddCountInput")?.value || 1);
  const prefix = document.getElementById("bayEditorAddPrefixInput")?.value.trim() || group.label;
  const category = document.getElementById("bayEditorGroupCategoryInput")?.value.trim() || group.kind || "Standard";
  const row = Number(document.getElementById("bayEditorGroupRowInput")?.value || group.row || 1);
  const col = Number(document.getElementById("bayEditorGroupColInput")?.value || group.col || 1);
  const payload = await fetchJson("/api/indian-trail/bays/add", {
    method: "POST",
    body: JSON.stringify({ mapSection: group.label, bayCategory: category, prefix, count, layoutRow: row, layoutCol: col, ...requestContext() }),
  });
  await refreshBayEditorAfter(payload);
  showFloatingNotice(`Added ${count} bay${count === 1 ? "" : "s"} to ${group.label}.`, "success");
}

async function deleteBayEditorGroup() {
  const group = bayEditorSelectedGroupObject();
  if (!group) throw new Error("Select a bay group first.");
  if (!window.confirm(`Delete bay group ${group.label}? Empty bays will be deactivated. Active assignments must be cleared or moved first.`)) return;
  const payload = await fetchJson("/api/indian-trail/bays/delete-group", {
    method: "POST",
    body: JSON.stringify({ mapSection: group.label, ...requestContext() }),
  });
  state.bayEditorSelectedGroup = "";
  await refreshBayEditorAfter(payload);
  showFloatingNotice(`Deleted ${group.label}.`, "success");
}

async function saveBayEditorBay(bayCode) {
  const row = els.bayEditorBayList?.querySelector(`[data-editor-bay-code="${CSS.escape(String(bayCode))}"]`);
  const bay = state.bays.find((item) => item.bayCode === bayCode);
  if (!row || !bay) throw new Error("Bay row not found.");
  const value = (field) => row.querySelector(`[data-editor-field="${field}"]`)?.value || "";
  const payload = await fetchJson("/api/indian-trail/layout", {
    method: "POST",
    body: JSON.stringify({
      bayCode,
      displayName: value("displayName") || bayCode,
      mapSection: value("mapSection") || bay.mapSection || "Unmapped",
      bayCategory: value("bayCategory") || bay.bayCategory || "Standard",
      layoutRow: bay.layoutRow || 1,
      layoutCol: bay.layoutCol || 1,
      capacityQty: Number(value("capacityQty") || 0),
      active: true,
      ...requestContext(),
    }),
  });
  await fetchJson("/api/indian-trail/bay-status", {
    method: "POST",
    body: JSON.stringify({ bayCode, status: bayEditorStatusFromPolicy(value("policy") || "auto"), reason: "Updated from Edit Bays", ...requestContext() }),
  });
  await refreshBayEditorAfter(payload);
  showFloatingNotice(`Saved ${bayCode}.`, "success");
}

async function deleteBayEditorBay(bayCode) {
  if (!window.confirm(`Delete bay ${bayCode}? Active assignments must be cleared or moved first.`)) return;
  const payload = await fetchJson("/api/indian-trail/bays/delete", {
    method: "POST",
    body: JSON.stringify({ bayCode, ...requestContext() }),
  });
  await refreshBayEditorAfter(payload);
  showFloatingNotice(`Deleted ${bayCode}.`, "success");
}

function openBayAllScansModal() {
  const events = state.bayEvents || [];
  const rows = events.length
    ? events.map((event) => {
        const when = new Date(event.time || event.createdAt || "");
        const time = Number.isNaN(when.getTime()) ? escapeHtml(event.time || "") : escapeHtml(when.toLocaleString());
        const bay = event.bayDisplay || event.bayCode || event.newBayDisplay || event.newBayCode || event.oldBayDisplay || event.oldBayCode || "";
        const order = event.order ? `${event.order}-${event.item || ""}` : "";
        return `<tr><td>${escapeHtml(formatEventType(event.eventType))}</td><td>${escapeHtml(order)}</td><td>${escapeHtml(bay)}</td><td>${escapeHtml(event.customer || "")}</td><td>${escapeHtml(event.reason || "")}</td><td>${escapeHtml(event.user || "")}</td><td>${time}</td></tr>`;
      }).join("")
    : `<tr><td colspan="7">No bay scan history is available yet.</td></tr>`;
  openAdminModal("custom", {
    title: "All Bay Scans",
    body: `
      <div class="full-scans-modal bay-full-scans-modal">
        <div class="section-heading"><h3>Indian Trail Bay Scan History</h3><span>${escapeHtml(events.length)} latest actions</span></div>
        <div class="admin-table full-scans-table"><table><thead><tr><th>Action</th><th>Order</th><th>Bay</th><th>Customer</th><th>Reason</th><th>User</th><th>Time</th></tr></thead><tbody>${rows}</tbody></table></div>
      </div>
    `,
  });
}

function openSdiPanel(assignmentId = "") {
  const found = assignmentById(assignmentId);
  if (found.bay?.bayCode) state.selectedBayCode = found.bay.bayCode;
  const bay = selectedBay();
  const assignment = found.assignment || selectedBayAssignment();
  const assignmentLookup = assignment?.job || assignment?.order || "";
  if (els.sdiPanel) {
    els.sdiPanel.dataset.assignmentId = assignment?.id || "";
    els.sdiPanel.dataset.originalLookup = assignmentLookup;
    els.sdiPanel.hidden = false;
  }
  if (els.sdiBackdrop) els.sdiBackdrop.hidden = false;
  updateModalScrollLock();
  if (els.sdiOrderInput) els.sdiOrderInput.value = assignmentLookup;
  if (els.sdiBayInput) els.sdiBayInput.value = bay?.bayCode || "";
  if (els.sdiReasonInput && !els.sdiReasonInput.value) els.sdiReasonInput.value = "Same-day install";
  if (els.sdiTypeInput) {
    els.sdiTypeInput.value = assignment && isRemakeItem(assignment)
      ? "Remake"
      : assignment && isRushItem(assignment)
        ? "Rush"
        : "";
    syncCustomSelect(els.sdiTypeInput);
  }
  renderSdiCurrentList();
  els.sdiOrderInput?.focus();
}

function renderSdiCurrentList() {
  if (!els.sdiCurrentList) return;
  const rows = [];
  for (const bay of state.bays || []) {
    for (const assignment of bay.assignments || []) {
      if (assignment.status === "SDIOverride") rows.push({ bay, assignment });
    }
  }
  els.sdiCurrentList.innerHTML = `
    <strong>Current Rush / Remake Orders</strong>
    <div>
      ${
        rows.length
          ? rows.slice(0, 30).map(({ bay, assignment }) => {
              const typeLabel = isRemakeItem(assignment) ? "Remake" : isRushItem(assignment) ? "Rush" : "SDI";
              const lookupLabel = assignment.job || `${assignment.order}-${assignment.item}`;
              return `<button type="button" data-assignment-action="sdi" data-assignment-id="${escapeHtml(assignment.id)}"><span>${escapeHtml(lookupLabel)} <b>${escapeHtml(typeLabel)}</b></span><small>${escapeHtml(bay.displayName || bay.bayCode)} - ${escapeHtml(assignment.customer || "")}</small></button>`;
            }).join("")
          : `<span class="admin-empty">No current Rush or Remake orders.</span>`
      }
    </div>
  `;
}

function closeSdiPanel() {
  if (els.sdiPanel) els.sdiPanel.hidden = true;
  if (els.sdiBackdrop) els.sdiBackdrop.hidden = true;
  updateModalScrollLock();
}

async function submitSdi(mark = true) {
  const assignment = assignmentById(els.sdiPanel?.dataset.assignmentId || "").assignment || selectedBayAssignment();
  const orderType = els.sdiTypeInput?.value || "";
  const lookupText = els.sdiOrderInput?.value.trim() || "";
  const originalLookup = els.sdiPanel?.dataset.originalLookup || "";
  const normalizeLookup = (value) => String(value || "").toUpperCase().replace(/[^A-Z0-9]+/g, "");
  const useSelectedAssignment = Boolean(
    assignment?.id &&
    (!lookupText || normalizeLookup(lookupText) === normalizeLookup(originalLookup))
  );
  const payload = {
    assignmentId: useSelectedAssignment ? assignment.id : "",
    orderNo: lookupText,
    job: lookupText,
    bayCode: els.sdiBayInput?.value || state.selectedBayCode || "",
    truckExempt: Boolean(els.sdiTruckExemptInput?.checked),
    orderType,
    reason: els.sdiReasonInput?.value || (mark ? "Same-day install" : "Rush / Remake cleared"),
  };
  if (mark && !orderType) {
    showInlineError("Select Rush or Remake before marking SDI.", false);
    return;
  }
  if (!useSelectedAssignment && !lookupText) {
    showInlineError("Enter a Job Nr., SO number, order number, or barcode.", false);
    return;
  }

  const result = await postBayAction(mark ? "/api/indian-trail/mark-sdi" : "/api/indian-trail/remove-sdi", payload);
  closeSdiPanel();

  const affectedItems = Number(result?.affectedItems || 0);
  const jobLabel = result?.matchedJob || lookupText;
  const customerLabel = result?.matchedCustomer || assignment?.customer || "";
  const listId = result?.listId || assignment?.deliveryListId || state.activeListId || selectedBay()?.assignments?.[0]?.deliveryListId || "";
  const printUrl = mark && listId
    ? `/api/print/package?listId=${encodeURIComponent(listId)}&${result?.remake ? "remakeOnly" : "rushOnly"}=1`
    : "";

  showActionFeedback({
    kind: "success",
    eyebrow: mark ? "Bay Map update complete" : "Bay Map update cleared",
    title: mark ? `${result?.orderType || orderType} marked` : "Rush / Remake cleared",
    message: result?.message || (mark ? `${orderType} was marked successfully.` : "The Rush / Remake mark was removed."),
    details: [
      { label: "Job Nr. / Order", value: jobLabel },
      { label: "Customer", value: customerLabel },
      { label: "Items updated", value: affectedItems ? String(affectedItems) : "1" },
    ],
    primaryLabel: printUrl ? (result?.remake ? "Print remake sheet" : "Print Rush sheet") : "",
    secondaryLabel: "Done",
    onPrimary: printUrl ? () => launchManagedPrint(printUrl) : null,
  });
}

async function runBayAction(action) {
  if (action === "scan-here") {
    const bay = requireSelectedBay();
    if (!bay) return;
    if (els.bayScanBayInput) els.bayScanBayInput.value = bay.bayCode;
    if (els.bayScanModeToggle) els.bayScanModeToggle.checked = true;
    if (els.bayScanOutInput) {
      els.bayScanOutInput.placeholder = `Scan order to add to ${bay.displayName || bay.bayCode}...`;
      els.bayScanOutInput.focus();
    }
    closeSelectedBayModal();
    showFloatingNotice(`${bay.displayName || bay.bayCode} is ready for manual bay scanning.`, "success");
    return;
  }
  if (action === "sdi") {
    openSdiPanel();
    return;
  }
  if (action === "layout") {
    openBayLayoutManager();
    return;
  }
  if (action === "item-management") {
    openManageItemsPanel();
    return;
  }
  if (action === "bay-editor") {
    openBayEditorPanel(state.selectedBayCode ? bayRackLabel(selectedBay()) : "");
    return;
  }
  if (action === "old-bays") {
    const orders = await loadStaleBayOrders(false);
    openStaleBayPanel(orders);
    return;
  }
  const bay = requireSelectedBay();
  if (!bay) return;
  const assignment = bay.assignments?.[0];
  if (action === "clear") {
    if (!window.confirm(`Clear ${bay.displayName || bay.bayCode}?`)) return;
    await postBayAction("/api/indian-trail/clear", { bayCode: bay.bayCode, reason: "Cleared from bay map" });
    return;
  }
  if (action === "move") {
    if (!assignment?.id) {
      showInlineError("That bay does not have an assignment to move.", false);
      return;
    }
    state.pendingBayMove = { assignmentId: assignment.id, fromBay: bay.bayCode, order: assignment.order, item: assignment.item };
    showFloatingNotice(`Select a destination bay for ${assignment.order}-${assignment.item}.`, "notice");
    document.body.classList.add("bay-move-mode");
    return;
  }
  if (action === "hold" || action === "block" || action === "unblock") {
    const status = action === "hold" ? "ManualAssign" : action === "block" ? "ScanBlocked" : "Available";
    const previousStatus = ["ManualAssign", "ScanBlocked", "Hold", "Blocked", "Available"].includes(String(bay.status || "")) ? bay.status : "Available";
    const result = await postBayAction("/api/indian-trail/bay-status", { bayCode: bay.bayCode, status, reason: `${status} from bay map` });
    pushBayHistory({
      label: `bay status ${bay.displayName || bay.bayCode}`,
      undo: () => postBayAction("/api/indian-trail/bay-status", { bayCode: bay.bayCode, status: previousStatus, reason: `Undo status change to ${previousStatus}` }),
      redo: () => postBayAction("/api/indian-trail/bay-status", { bayCode: bay.bayCode, status, reason: `Redo status change to ${status}` }),
    });
    state.bays = result.bays || state.bays;
    showFloatingNotice(`${bay.displayName || bay.bayCode} set to ${status === "ManualAssign" ? "Manual Assign" : status === "ScanBlocked" ? "Blocked Scans" : "Auto Assign"}.`, "success");
  }
}

function renderBayLayoutSelect() {
  if (!els.bayLayoutSelect) return;
  const current = els.bayLayoutSelect.value || state.selectedBayCode || state.bays[0]?.bayCode || "";
  els.bayLayoutSelect.innerHTML = (state.bays || [])
    .map((bay) => `<option value="${escapeHtml(bay.bayCode)}">${escapeHtml(bay.displayName || bay.bayCode)} - ${escapeHtml(bay.mapSection || "")}</option>`)
    .join("");
  els.bayLayoutSelect.value = state.bays.some((bay) => bay.bayCode === current) ? current : state.bays[0]?.bayCode || "";
}

function populateBayLayoutForm() {
  const bay = state.bays.find((item) => item.bayCode === els.bayLayoutSelect?.value) || selectedBay() || state.bays[0];
  if (!bay) return;
  state.selectedBayCode = bay.bayCode;
  if (els.bayLayoutDisplayInput) els.bayLayoutDisplayInput.value = bay.displayName || bay.bayCode;
  if (els.bayLayoutSectionInput) els.bayLayoutSectionInput.value = bay.mapSection || "";
  if (els.bayLayoutCategoryInput) els.bayLayoutCategoryInput.value = bay.bayCategory || "";
  if (els.bayLayoutRowInput) els.bayLayoutRowInput.value = bay.layoutRow || "";
  if (els.bayLayoutColInput) els.bayLayoutColInput.value = bay.layoutCol || "";
  if (els.bayLayoutCapacityInput) els.bayLayoutCapacityInput.value = bay.capacityQty || 0;
  if (els.bayLayoutActiveInput) els.bayLayoutActiveInput.checked = Boolean(bay.active);
}

function openBayLayoutManager() {
  if (!hasPermission("manage_bay_layout")) {
    showInlineError("Only admins can edit the bay map layout.", false);
    return;
  }
  state.bayEditMode = true;
  initializeBayLayoutDraft();
  state.bayLayoutUndoStack = [];
  state.bayLayoutRedoStack = [];
  if (els.bayLayoutManager) els.bayLayoutManager.hidden = false;
  renderBayLayoutSelect();
  populateBayLayoutForm();
  renderBayMapPage();
}

function closeBayLayoutManager() {
  if (state.bayHoldingSections.size) {
    showFloatingNotice("Move all grouped bays out of the temporary holding area before closing edit mode.", "error");
    return;
  }
  state.bayEditMode = false;
  state.bayLayoutDraft = null;
  state.bayLayoutOriginal = null;
  state.bayHoldingSections = new Set();
  if (els.bayLayoutManager) els.bayLayoutManager.hidden = true;
  renderBayMapPage();
}

function moveBaySectionDraft(sectionLabel, row, col, holding = false) {
  if (!sectionLabel || !state.bayLayoutDraft?.[sectionLabel]) return;
  const before = JSON.parse(JSON.stringify(state.bayLayoutDraft));
  if (holding) {
    state.bayHoldingSections.add(sectionLabel);
    state.collapsedBaySections.add(sectionLabel);
    state.bayLayoutDraft[sectionLabel] = { row: 0, col: 0, holding: true };
  } else {
    const displaced = Object.entries(state.bayLayoutDraft).find(([, pos]) => !pos.holding && pos.row === row && pos.col === col);
    if (displaced?.[0] && displaced[0] !== sectionLabel) {
      state.bayHoldingSections.add(displaced[0]);
      state.bayLayoutDraft[displaced[0]] = { row: 0, col: 0, holding: true };
    }
    state.bayHoldingSections.delete(sectionLabel);
    state.bayLayoutDraft[sectionLabel] = { row, col, holding: false };
  }
  const after = JSON.parse(JSON.stringify(state.bayLayoutDraft));
  state.bayLayoutUndoStack.push({ label: `move ${sectionLabel}`, beforeDraft: before, afterDraft: after });
  state.bayLayoutRedoStack = [];
  renderBayMapPage();
}

function holdAllBaySections() {
  if (!state.bayEditMode) return;
  const before = JSON.parse(JSON.stringify(state.bayLayoutDraft || {}));
  const sections = bayPhysicalSections();
  for (const section of sections) {
    state.bayHoldingSections.add(section.label);
    state.collapsedBaySections.add(section.label);
    state.bayLayoutDraft[section.label] = { row: 0, col: 0, holding: true };
  }
  const after = JSON.parse(JSON.stringify(state.bayLayoutDraft || {}));
  state.bayLayoutUndoStack.push({ label: "hold all bay groups", beforeDraft: before, afterDraft: after });
  state.bayLayoutRedoStack = [];
  renderBayMapPage();
}

function applyBayLayoutDraft(draft) {
  state.bayLayoutDraft = JSON.parse(JSON.stringify(draft || {}));
  state.bayHoldingSections = new Set(Object.entries(state.bayLayoutDraft).filter(([, pos]) => pos.holding).map(([label]) => label));
  renderBayMapPage();
}

async function confirmBayLayoutDraft() {
  if (!state.bayEditMode || !state.bayLayoutDraft) return;
  if (state.bayHoldingSections.size) {
    showFloatingNotice("Move all grouped bays out of the temporary holding area before confirming.", "error");
    return;
  }
  const sections = bayPhysicalSections();
  for (const section of sections) {
    const pos = state.bayLayoutDraft[section.label];
    if (!pos || pos.holding) continue;
    await fetchJson("/api/indian-trail/layout", {
      method: "POST",
      body: JSON.stringify({
        setGroupPosition: true,
        mapSection: section.label,
        layoutRow: pos.row,
        layoutCol: pos.col,
        ...requestContext(),
      }),
    });
  }
  state.bayEditMode = false;
  state.bayLayoutDraft = null;
  state.bayLayoutOriginal = null;
  state.bayHoldingSections = new Set();
  if (els.bayLayoutManager) els.bayLayoutManager.hidden = true;
  await refreshBayMapPage();
  showFloatingNotice("Bay map layout confirmed.", "success");
}

function cancelBayLayoutDraft() {
  state.bayEditMode = false;
  state.bayLayoutDraft = null;
  state.bayLayoutOriginal = null;
  state.bayHoldingSections = new Set();
  state.bayLayoutUndoStack = [];
  state.bayLayoutRedoStack = [];
  if (els.bayLayoutManager) els.bayLayoutManager.hidden = true;
  renderBayMapPage();
  showFloatingNotice("Bay map layout changes were cancelled.", "notice");
}

async function saveBayLayoutForm() {
  if (!els.bayLayoutSelect?.value) return;
  const payload = await fetchJson("/api/indian-trail/layout", {
    method: "POST",
    body: JSON.stringify({
      bayCode: els.bayLayoutSelect.value,
      displayName: els.bayLayoutDisplayInput?.value || "",
      mapSection: els.bayLayoutSectionInput?.value || "",
      bayCategory: els.bayLayoutCategoryInput?.value || "",
      layoutRow: els.bayLayoutRowInput?.value || "",
      layoutCol: els.bayLayoutColInput?.value || "",
      capacityQty: els.bayLayoutCapacityInput?.value || 0,
      active: Boolean(els.bayLayoutActiveInput?.checked),
      ...requestContext(),
    }),
  });
  state.bays = payload.bays || state.bays;
  renderBayMapPage();
}

function bayLayoutSnapshot(filter = () => true) {
  return (state.bays || [])
    .filter(filter)
    .map((bay) => ({
      bayCode: bay.bayCode,
      displayName: bay.displayName || bay.bayCode,
      mapSection: bay.mapSection || "",
      bayCategory: bay.bayCategory || bayCategoryKind(bay),
      layoutRow: bay.layoutRow || "",
      layoutCol: bay.layoutCol || "",
      capacityQty: bay.capacityQty || 0,
      active: Boolean(bay.active),
    }));
}

async function applyBayLayoutSnapshot(snapshot) {
  for (const bay of snapshot || []) {
    await fetchJson("/api/indian-trail/layout", {
      method: "POST",
      body: JSON.stringify({ ...bay, ...requestContext() }),
    });
  }
  await refreshBayMapPage();
  renderBayLayoutSelect();
  populateBayLayoutForm();
}

function pushBayLayoutHistory(label, before, after) {
  if (!before?.length || !after?.length) return;
  state.bayLayoutUndoStack.push({ label, before, after });
  state.bayLayoutRedoStack = [];
}

async function runBayLayoutHistory(direction) {
  const from = direction === "undo" ? state.bayLayoutUndoStack : state.bayLayoutRedoStack;
  const to = direction === "undo" ? state.bayLayoutRedoStack : state.bayLayoutUndoStack;
  const entry = from.pop();
  if (!entry) {
    showFloatingNotice(`No layout change to ${direction}.`, "notice");
    return;
  }
  if (entry.beforeDraft || entry.afterDraft) {
    applyBayLayoutDraft(direction === "undo" ? entry.beforeDraft : entry.afterDraft);
    to.push(entry);
    showFloatingNotice(`${direction === "undo" ? "Undid" : "Redid"} ${entry.label}.`, "success");
    return;
  }
  await applyBayLayoutSnapshot(direction === "undo" ? entry.before : entry.after);
  to.push(entry);
  showFloatingNotice(`${direction === "undo" ? "Undid" : "Redid"} ${entry.label}.`, "success");
}

async function moveBayToGroup(bayCode, mapSection, bayCategory = "", targetBayCode = "") {
  const bay = state.bays.find((item) => item.bayCode === bayCode);
  const targetBay = state.bays.find((item) => item.bayCode === targetBayCode);
  if (!bay || !mapSection) return;
  const impactedSections = new Set([bay.mapSection, mapSection, targetBay?.mapSection].filter(Boolean));
  const before = bayLayoutSnapshot((item) => impactedSections.has(item.mapSection || "") || item.bayCode === bayCode || item.bayCode === targetBayCode);
  const payload = await fetchJson("/api/indian-trail/layout", {
    method: "POST",
    body: JSON.stringify({
      bayCode,
      displayName: bay.displayName || bay.bayCode,
      mapSection,
      bayCategory: bayCategory || bay.bayCategory || bayCategoryKind(bay),
      layoutRow: targetBay?.layoutRow || bay.layoutRow || "",
      layoutCol: targetBay?.layoutCol || bay.layoutCol || "",
      insertBeforeBayCode: targetBayCode || "",
      capacityQty: bay.capacityQty || 0,
      active: Boolean(bay.active),
      ...requestContext(),
    }),
  });
  state.bays = payload.bays || state.bays;
  const after = bayLayoutSnapshot((item) => impactedSections.has(item.mapSection || "") || item.bayCode === bayCode || item.bayCode === targetBayCode);
  pushBayLayoutHistory(`move ${bayCode}`, before, after);
  state.selectedBayCode = bayCode;
  renderBayMapPage();
  renderBayLayoutSelect();
  populateBayLayoutForm();
  showFloatingNotice(`${bayCode} moved to ${mapSection}`, "success");
}

async function addBaysFromForm() {
  const result = await fetchJson("/api/indian-trail/bays/add", {
    method: "POST",
    body: JSON.stringify({
      mapSection: els.bayAddGroupInput?.value || "",
      bayCategory: els.bayAddCategoryInput?.value || "",
      prefix: els.bayAddPrefixInput?.value || "",
      count: els.bayAddCountInput?.value || 1,
      ...requestContext(),
    }),
  });
  state.bays = result.bays || state.bays;
  if (result.created?.[0]) state.selectedBayCode = result.created[0];
  renderBayMapPage();
  renderBayLayoutSelect();
  populateBayLayoutForm();
  showFloatingNotice(`Added ${result.created?.length || 0} bay(s)`, "success");
}

async function addSpacerBay() {
  const selected = selectedBay();
  const mapSection = window.prompt("Add spacer to which bay group?", selected?.mapSection || "");
  if (!mapSection) return;
  const before = bayLayoutSnapshot((bay) => bay.mapSection === mapSection);
  const result = await fetchJson("/api/indian-trail/bays/add", {
    method: "POST",
    body: JSON.stringify({
      mapSection,
      bayCategory: "Spacer",
      prefix: "Spacer",
      count: 1,
      spacer: true,
      ...requestContext(),
    }),
  });
  state.bays = result.bays || state.bays;
  const after = bayLayoutSnapshot((bay) => bay.mapSection === mapSection || result.created?.includes(bay.bayCode));
  pushBayLayoutHistory("add spacer", before, after);
  if (result.created?.[0]) state.selectedBayCode = result.created[0];
  renderBayMapPage();
  renderBayLayoutSelect();
  populateBayLayoutForm();
  showFloatingNotice("Spacer added to the bay map.", "success");
}

async function deleteSelectedBay() {
  const bayCode = els.bayLayoutSelect?.value || state.selectedBayCode;
  if (!bayCode) return;
  if (!window.confirm(`Delete bay ${bayCode}? Active assignments must be cleared first.`)) return;
  const result = await fetchJson("/api/indian-trail/bays/delete", {
    method: "POST",
    body: JSON.stringify({ bayCode, ...requestContext() }),
  });
  state.bays = result.bays || state.bays;
  state.selectedBayCode = "";
  renderBayMapPage();
  renderBayLayoutSelect();
  populateBayLayoutForm();
}

async function deleteSelectedBayGroup() {
  const mapSection = els.bayAddGroupInput?.value || els.bayLayoutSectionInput?.value || selectedBay()?.mapSection || "";
  if (!mapSection) return;
  if (!window.confirm(`Delete bay group ${mapSection}? Active assignments must be cleared first.`)) return;
  const result = await fetchJson("/api/indian-trail/bays/delete-group", {
    method: "POST",
    body: JSON.stringify({ mapSection, ...requestContext() }),
  });
  state.bays = result.bays || state.bays;
  state.selectedBayCode = "";
  renderBayMapPage();
  renderBayLayoutSelect();
  populateBayLayoutForm();
}

async function moveBayGroup(direction) {
  const section = els.bayLayoutSectionInput?.value || selectedBay()?.mapSection || "";
  const delta = {
    up: { rowDelta: -1, colDelta: 0 },
    down: { rowDelta: 1, colDelta: 0 },
    left: { rowDelta: 0, colDelta: -1 },
    right: { rowDelta: 0, colDelta: 1 },
  }[direction];
  if (!section || !delta) return;
  const payload = await fetchJson("/api/indian-trail/layout", {
    method: "POST",
    body: JSON.stringify({ moveGroup: true, mapSection: section, ...delta, ...requestContext() }),
  });
  state.bays = payload.bays || state.bays;
  renderBayMapPage();
  renderBayLayoutSelect();
  populateBayLayoutForm();
}

async function swapBayGroups(sourceSection, targetSection) {
  if (!sourceSection || !targetSection || sourceSection === targetSection) return;
  const before = bayLayoutSnapshot((bay) => bay.mapSection === sourceSection || bay.mapSection === targetSection);
  const payload = await fetchJson("/api/indian-trail/layout", {
    method: "POST",
    body: JSON.stringify({ moveGroup: true, mapSection: sourceSection, targetMapSection: targetSection, ...requestContext() }),
  });
  state.bays = payload.bays || state.bays;
  const after = bayLayoutSnapshot((bay) => bay.mapSection === sourceSection || bay.mapSection === targetSection);
  pushBayLayoutHistory(`swap ${sourceSection}`, before, after);
  renderBayMapPage();
  renderBayLayoutSelect();
  populateBayLayoutForm();
}

function openPrintPackage(printCandidates, filters = {}) {
  const listIds = [...new Set(printCandidates.flatMap((candidate) => candidate.listIds || []))];
  if (!listIds.length) return;
  const params = new URLSearchParams({ listId: listIds.join(",") });
  for (const [key, value] of Object.entries(filters)) {
    if (value) params.set(key, value);
  }
  launchManagedPrint(`/api/print/package?${params.toString()}`);
}

async function runAssignmentAction(action, assignmentId) {
  const found = assignmentById(assignmentId);
  const assignment = found.assignment;
  if (!assignment?.id) {
    showInlineError("Assignment not found.", true);
    return;
  }
  if (found.bay?.bayCode) state.selectedBayCode = found.bay.bayCode;
  if (action === "sdi") {
    openSdiPanel(assignment.id);
    return;
  }
  if (action === "manage") {
    openManageItemsPanel(assignment.id);
    return;
  }
  if (action === "clear" || action === "move") {
    // Clear and move now use the Manage Items workflow so a whole Job Nr. group moves together.
    openManageItemsPanel(assignment.id);
  }
}

function selectedPrintStageInputs() {
  return [...(els.printOptionsStages?.querySelectorAll('.print-stage-choice:not(.print-stage-all-choice) input[type="checkbox"]') || [])];
}

function selectedPrintListIds() {
  return selectedPrintStageInputs().filter((input) => input.checked).map((input) => input.value);
}

function updatePrintStageSelectState() {
  if (!els.printOptionsStages) return;

  const stageInputs = selectedPrintStageInputs();
  const checkedInputs = stageInputs.filter((input) => input.checked);
  const allInput = els.printOptionsStages.querySelector("[data-print-stage-select-all]");

  if (allInput) {
    allInput.checked = stageInputs.length > 0 && checkedInputs.length === stageInputs.length;
    allInput.indeterminate = checkedInputs.length > 0 && checkedInputs.length < stageInputs.length;
  }
}

function printGlassCategory(label) {
  const text = String(label || "").toLowerCase();

  if (/mirror|mirr|\bmir\b/.test(text)) return "Mirror";
  if (/tempered|temp\b|shower/.test(text)) return "Tempered";
  if (/annealed|anneal|\bann\b|plate|float/.test(text)) return "Annealed";

  return "Other";
}

function printGlassCategorySort(category) {
  return { Mirror: 1, Annealed: 2, Tempered: 3, Other: 4 }[category] || 9;
}

function selectedPrintGlassInputs() {
  return [...(els.printOptionsGlassType?.querySelectorAll('.print-glass-choice:not(.print-glass-all-choice) input[type="checkbox"]') || [])];
}

function updatePrintGlassSelectState() {
  if (!els.printOptionsGlassType) return;

  const glassInputs = selectedPrintGlassInputs();
  const checkedInputs = glassInputs.filter((input) => input.checked);
  const allInput = els.printOptionsGlassType.querySelector("[data-print-glass-select-all]");

  if (allInput) {
    allInput.checked = glassInputs.length > 0 && checkedInputs.length === glassInputs.length;
    allInput.indeterminate = checkedInputs.length > 0 && checkedInputs.length < glassInputs.length;
  }

  els.printOptionsGlassType.querySelectorAll("[data-print-glass-category]").forEach((categoryInput) => {
    const category = categoryInput.dataset.printGlassCategory || "";
    const categoryInputs = glassInputs.filter((input) => input.dataset.printGlassCategory === category);
    const checkedCategoryInputs = categoryInputs.filter((input) => input.checked);

    categoryInput.checked = categoryInputs.length > 0 && checkedCategoryInputs.length === categoryInputs.length;
    categoryInput.indeterminate = checkedCategoryInputs.length > 0 && checkedCategoryInputs.length < categoryInputs.length;
  });
}

async function ensurePrintListDetails(listIds) {
  if (!state.backend) return;

  const wanted = new Set(listIds);
  const listsToLoad = state.lists.filter((list) => {
    if (!wanted.has(list.id)) return false;
    if (list._printItemsLoaded) return false;
    return !Array.isArray(list.items) || !list.items.length;
  });

  if (!listsToLoad.length) return;

  await Promise.all(
    listsToLoad.map(async (list) => {
      const payload = await fetchJson(`/api/delivery-lists/${encodeURIComponent(list.id)}`);
      const items = cloneItems(payload.items || []);

      Object.assign(list, {
        items,
        itemCount: items.length || list.itemCount || 0,
        totalQty: items.length ? pieceCount(items) : list.totalQty,
        scannedQty: items.length ? items.reduce((sum, item) => sum + itemScannedPieceQty(item), 0) : list.scannedQty,
        _printItemsLoaded: true,
      });
    }),
  );
}

function printListIsFullCoverage(list) {
  const category = stageCategory(list);
  return category === "staged" || category === "outbound";
}

function printCountSourceLists(listIds) {
  const wanted = new Set(listIds);
  const selectedLists = state.lists.filter((list) => wanted.has(list.id));
  const fullCoverageLists = selectedLists
    .filter(printListIsFullCoverage)
    .sort((a, b) => stageSort(a) - stageSort(b));

  if (fullCoverageLists.length) {
    return [fullCoverageLists[0]];
  }

  return selectedLists;
}

function printItemsForCountList(list) {
  if (Array.isArray(list?.items) && list.items.length) {
    return list.items;
  }

  if (list?.id && list.id === state.activeListId) {
    return state.items;
  }

  return [];
}

function printGlassEntriesForLists(listIds) {
  const entries = new Map();
  const sourceLists = printCountSourceLists(listIds);

  const addEntry = (label, qty = 0) => {
    const cleanLabel = String(label || "").trim();

    if (!cleanLabel) return;

    const key = cleanLabel.toLowerCase();
    const existing = entries.get(key) || {
      label: cleanLabel,
      qty: 0,
      category: printGlassCategory(cleanLabel),
    };

    existing.qty += Math.max(Number(qty || 0), 0);
    entries.set(key, existing);
  };

  for (const list of sourceLists) {
    const items = printItemsForCountList(list);

    if (items.length) {
      for (const item of items) {
        addEntry(glassTypeLabel(item), itemPieceQty(item));
      }
    } else {
      for (const label of list.glassTypes || []) {
        addEntry(label, 0);
      }
    }
  }

  return [...entries.values()].sort((a, b) => {
    const categoryDiff = printGlassCategorySort(a.category) - printGlassCategorySort(b.category);
    if (categoryDiff) return categoryDiff;

    const qtyDiff = Number(b.qty || 0) - Number(a.qty || 0);
    if (qtyDiff) return qtyDiff;

    return a.label.localeCompare(b.label);
  });
}

function availableGlassTypesForLists(listIds) {
  return printGlassEntriesForLists(listIds).map((entry) => entry.label);
}

function ensurePrintGlassFieldWrapper() {
  if (!els.printOptionsGlassType) return null;

  const glassField = els.printOptionsGlassType.closest("label");

  if (!glassField) {
    return els.printOptionsGlassType.closest(".print-glass-field");
  }

  const wrapper = document.createElement("div");
  wrapper.className = `${glassField.className} print-glass-field`.trim();

  while (glassField.firstChild) {
    wrapper.appendChild(glassField.firstChild);
  }

  glassField.replaceWith(wrapper);
  return wrapper;
}

async function renderPrintGlassTypes() {
  if (!els.printOptionsGlassType) return;

  ensurePrintGlassFieldWrapper();

  const listIds = selectedPrintListIds();
  const renderToken = Symbol("print-glass-render");
  state.printGlassRenderToken = renderToken;

  const countSourceListIds = printCountSourceLists(listIds).map((list) => list.id);
  const detailIds = [...new Set([...listIds, ...countSourceListIds])];
  const needsDetails = state.backend && detailIds.some((listId) => {
    const list = state.lists.find((item) => item.id === listId);
    return list && !list._printItemsLoaded && (!Array.isArray(list.items) || !list.items.length);
  });

  if (needsDetails) {
    els.printOptionsGlassType.innerHTML = `<div class="admin-empty">Loading glass types...</div>`;

    try {
      await ensurePrintListDetails(detailIds);
    } catch (error) {
      els.printOptionsGlassType.innerHTML = `<div class="admin-empty review">Could not load glass type quantities. ${escapeHtml(error.message)}</div>`;
      return;
    }

    if (state.printGlassRenderToken === renderToken) {
      await renderPrintGlassTypes();
    }

    return;
  }

  const previousGroups = [...els.printOptionsGlassType.querySelectorAll(".print-glass-group[data-print-glass-group]")];
  const previousOpenCategories = new Set(previousGroups.filter((group) => group.open).map((group) => group.dataset.printGlassGroup));
  const hadPreviousGroups = previousGroups.length > 0;
  const currentInputs = selectedPrintGlassInputs();
  const current = new Set(currentInputs.filter((input) => input.checked).map((input) => input.value).filter(Boolean));
  const hadPrevious = currentInputs.length > 0;
  const entries = printGlassEntriesForLists(listIds);
  const groups = new Map();
  const checkedForEntry = (entry) => (hadPrevious ? current.has(entry.label) : !/mirror/i.test(entry.label));

  for (const entry of entries) {
    if (!groups.has(entry.category)) {
      groups.set(entry.category, []);
    }

    groups.get(entry.category).push(entry);
  }

  const selectedCount = entries.filter(checkedForEntry).length;
  const totalQty = entries.reduce((sum, entry) => sum + Number(entry.qty || 0), 0);

  els.printOptionsGlassType.innerHTML = entries.length
    ? `
        <div class="print-glass-toolbar">
          <span class="print-glass-choice print-glass-all-choice" data-print-glass-all-toggle>
            <input type="checkbox" data-print-glass-select-all ${selectedCount === entries.length ? "checked" : ""}>
            <span>All Glass Types</span>
            <small>${escapeHtml(selectedCount)} / ${escapeHtml(entries.length)} selected | ${escapeHtml(totalQty)} pcs</small>
          </span>
        </div>

        ${[...groups.entries()]
          .map(([category, groupEntries]) => {
            const groupQty = groupEntries.reduce((sum, entry) => sum + Number(entry.qty || 0), 0);
            const checkedGroupEntries = groupEntries.filter(checkedForEntry);
            const groupOpen = hadPreviousGroups ? previousOpenCategories.has(category) : false;

            return `
              <details
                class="print-glass-group print-glass-group-${escapeHtml(slugify(category))}"
                data-print-glass-group="${escapeHtml(category)}"
                ${groupOpen ? "open" : ""}
              >
                <summary>
                  <span class="print-glass-group-main">
                    <input
                      type="checkbox"
                      data-print-glass-category="${escapeHtml(category)}"
                      aria-label="Select all ${escapeHtml(category)} glass types"
                      ${checkedGroupEntries.length === groupEntries.length ? "checked" : ""}
                    >
                    <strong>${escapeHtml(category)}</strong>
                    <small>${escapeHtml(checkedGroupEntries.length)} / ${escapeHtml(groupEntries.length)} selected | ${escapeHtml(groupQty)} pcs</small>
                  </span>
                  <span class="print-glass-collapse-label">Expand / collapse</span>
                </summary>

                <div class="print-glass-group-options">
                  ${groupEntries
                    .map((entry) => {
                      const checked = checkedForEntry(entry);

                      return `
                        <span class="print-glass-choice">
                          <input
                            type="checkbox"
                            value="${escapeHtml(entry.label)}"
                            data-print-glass-category="${escapeHtml(category)}"
                            aria-label="Select ${escapeHtml(entry.label)}"
                            ${checked ? "checked" : ""}
                          >
                          <span title="${escapeHtml(entry.label)}">${escapeHtml(entry.label)}</span>
                          <small>${escapeHtml(entry.qty || 0)}</small>
                        </span>
                      `;
                    })
                    .join("")}
                </div>
              </details>
            `;
          })
          .join("")}
      `
    : `<div class="admin-empty">No glass types found for the selected stages.</div>`;

  updatePrintGlassSelectState();

  els.printOptionsGlassType.onclick = (event) => {
    const targetInput = event.target.closest('input[type="checkbox"]');

    if (targetInput && els.printOptionsGlassType.contains(targetInput)) {
      event.stopPropagation();

      window.setTimeout(() => {
        if (targetInput.matches("[data-print-glass-select-all]")) {
          selectedPrintGlassInputs().forEach((glassInput) => {
            glassInput.checked = targetInput.checked;
          });
        }

        if (targetInput.matches("[data-print-glass-category]")) {
          const category = targetInput.dataset.printGlassCategory || "";

          selectedPrintGlassInputs()
            .filter((input) => input.dataset.printGlassCategory === category)
            .forEach((input) => {
              input.checked = targetInput.checked;
            });
        }

        updatePrintGlassSelectState();
      }, 0);

      return;
    }

    const allToggle = event.target.closest("[data-print-glass-all-toggle]");

    if (allToggle && els.printOptionsGlassType.contains(allToggle)) {
      event.preventDefault();
      event.stopPropagation();

      const glassInputs = selectedPrintGlassInputs();
      const nextChecked = !glassInputs.length || glassInputs.some((input) => !input.checked);

      glassInputs.forEach((glassInput) => {
        glassInput.checked = nextChecked;
      });

      updatePrintGlassSelectState();
      return;
    }

    const choice = event.target.closest(".print-glass-choice:not(.print-glass-all-choice)");

    if (choice && els.printOptionsGlassType.contains(choice)) {
      event.preventDefault();
      event.stopPropagation();

      const input = choice.querySelector('input[type="checkbox"]');

      if (!input) return;

      input.checked = !input.checked;
      updatePrintGlassSelectState();
    }
  };
}

function printStageOptionLabel(list) {
  const category = stageCategory(list);

  if (category === "outbound") return "Outbound Airport";
  if (category === "received") return "Inbound IT";
  if (category === "greenville") return "BFS Greenville";
  if (category === "pickup") return "CPU";
  if (category === "dtc") return "DTC";

  return "Staging Airport";
}

function renderPrintOptionStages() {
  if (!els.printOptionsStages || !els.printOptionsDate) return;

  const date = els.printOptionsDate.value || selectedDeliveryDate() || dashboardDateKey();
  const lists = state.lists.filter((list) => list.deliveryDate === date).sort((a, b) => stageSort(a) - stageSort(b));
  const contextIds = new Set(state.printContext?.listIds || []);
  const hasContextIds = contextIds.size > 0;
  const checkedCount = lists.filter((list) => (hasContextIds ? contextIds.has(list.id) : false)).length;
  const fullCoverageList = lists.find(printListIsFullCoverage);
  const listQty = fullCoverageList?.totalQty || lists.reduce((maxQty, list) => Math.max(maxQty, Number(list.totalQty || 0)), 0);

  els.printOptionsStages.innerHTML = `
    <label class="print-stage-choice print-stage-all-choice">
      <input type="checkbox" data-print-stage-select-all ${lists.length && checkedCount === lists.length ? "checked" : ""}>
      <span>All Stages <small>${escapeHtml(lists.length)} stage${lists.length === 1 ? "" : "s"}${listQty ? ` | ${escapeHtml(listQty)} pcs` : ""}</small></span>
    </label>
    ${lists
      .map((list) => {
        const checked = hasContextIds ? contextIds.has(list.id) : false;

        return `
          <label class="print-stage-choice print-stage-${escapeHtml(stageCategory(list))}">
            <input type="checkbox" value="${escapeHtml(list.id)}" ${checked ? "checked" : ""}>
            <span>${escapeHtml(printStageOptionLabel(list))} <small>${escapeHtml(list.scannedQty || 0)} / ${escapeHtml(list.totalQty || 0)}</small></span>
          </label>
        `;
      })
      .join("")}
  `;

  updatePrintStageSelectState();
  void renderPrintGlassTypes();
}

function openPrintOptions(context = {}) {
  state.printContext = context;
  const groups = listsByDeliveryDate();
  if (!groups.length) {
    showInlineError("No delivery lists are available to print.", false);
    return;
  }
  const requestedDate = context.date || state.meta?.deliveryDate || selectedDeliveryDate() || groups[0].date;
  if (els.printOptionsDate) {
    els.printOptionsDate.innerHTML = groups.map((group) => `<option value="${escapeHtml(group.date)}">${escapeHtml(formatDisplayDate(group.date))}</option>`).join("");
    els.printOptionsDate.value = groups.some((group) => group.date === requestedDate) ? requestedDate : groups[0].date;
  }
  for (const input of [els.printUpdatedOnly, els.printRushOnly, els.printRemakeOnly]) {
    if (input) input.checked = false;
  }
  if (els.printUpdatedOnly) {
    els.printUpdatedOnly.checked = Boolean(context.updatedOnly);
  }
  if (els.printCustomerFilter) els.printCustomerFilter.value = "";
  if (els.printOrderFilter) els.printOrderFilter.value = "";
  renderPrintOptionStages();
  if (els.printOptionsBackdrop) els.printOptionsBackdrop.hidden = false;
  if (els.printOptionsPanel) els.printOptionsPanel.hidden = false;
  updateModalScrollLock();
}

function closePrintOptions() {
  if (els.printOptionsBackdrop) els.printOptionsBackdrop.hidden = true;
  if (els.printOptionsPanel) els.printOptionsPanel.hidden = true;
  updateModalScrollLock();
}

function submitPrintOptions() {
  let listIds = state.printContext?.fixedListIds ? [...(state.printContext.listIds || [])] : selectedPrintListIds();
  if (!listIds.length) {
    showInlineError("Select at least one stage to print or export.", false);
    return;
  }
  if (!state.backend) {
    closePrintOptions();
    printCurrentPageManaged();
    return;
  }
  const checkedGlassInputs = [...(els.printOptionsGlassType?.querySelectorAll('.print-glass-choice:not(.print-glass-all-choice) input[type="checkbox"]:checked') || [])];
  const selectedMirrorGlass = checkedGlassInputs.some((input) => (input.dataset.printGlassCategory || "") === "Mirror");
  const filters = {
    updatedOnly: els.printUpdatedOnly?.checked ? "1" : "",
    rushOnly: els.printRushOnly?.checked ? "1" : "",
    remakeOnly: els.printRemakeOnly?.checked ? "1" : "",
    glassType: checkedGlassInputs.map((input) => input.value.trim()).filter(Boolean).join(","),
    mirrorMode: selectedMirrorGlass ? "include" : "exclude",
    includeMirrorRemakes: selectedMirrorGlass ? "" : "1",
    customers: els.printCustomerFilter?.value.trim() || "",
    orders: els.printOrderFilter?.value.trim() || "",
  };
  const params = new URLSearchParams({ listId: listIds.join(",") });
  for (const [key, value] of Object.entries(filters)) {
    if (value) params.set(key, value);
  }
  const mode = document.querySelector('input[name="printExportMode"]:checked')?.value || "print";
  if (mode === "export") {
    window.open(`/api/export/package.xlsx?${params.toString()}`, "_blank", "noopener");
  } else {
    launchManagedPrint(`/api/print/package?${params.toString()}`);
  }
  closePrintOptions();
}

async function importTempDeliveryFolder() {
  const sourceFolder = els.tempFolderInput?.value.trim() || "";
  const { dateFrom, dateTo } = currentImportDateWindow();

  showImportStatusLoading("Importing Temp folder...", `Checking delivery dates from ${formatDisplayDate(dateFrom)} through the newest future list.`);
  await waitForNextPaint();

  const result = await fetchJson("/api/import/folder", {
    method: "POST",
    body: JSON.stringify({ ...requestContext(), sourceFolder, dateFrom, dateTo }),
  });
  state.lists = result.lists || state.lists;
  if (result.activeListId) await activateList(result.activeListId, false);
  renderHome();
  await refreshAdminPage();
  const imported = result.importedFiles?.length || 0;
  const updated = result.updatedFiles?.length || 0;
  const skipped = result.skippedFiles?.length || 0;
  const ignored = result.ignoredFiles?.length || 0;
  const failed = result.failedFiles?.length || 0;
  const checked = result.checkedFiles ?? result.scannedFiles ?? imported + updated + skipped + failed;
  const total = result.totalFolderFiles ?? checked + ignored;
  if (els.importPreviewBox) {
    els.importPreviewBox.hidden = false;
    els.importPreviewBox.classList.remove("loading");
    els.importPreviewBox.classList.add("import-status-compact");
    els.importPreviewBox.classList.toggle("success", !failed);
    els.importPreviewBox.classList.toggle("review", Boolean(failed));

    const noUpdates = !imported && !updated && skipped && !failed;
    const windowText = `Checked ${checked} file${checked === 1 ? "" : "s"} in the active import window. ${ignored ? `Skipped ${ignored} older file${ignored === 1 ? "" : "s"} outside the date window. ` : ""}${total ? `Folder total: ${total}.` : ""}`;

    els.importPreviewBox.innerHTML = failed
      ? `
        <strong>Import completed with issues.</strong>
        <span>${imported} new, ${updated} updated, ${skipped} unchanged, ${failed} failed.</span>
        <small>${escapeHtml(windowText)}</small>
        ${result.failedFiles?.length ? `<small>${escapeHtml(result.failedFiles.map((file) => `${file.fileName}: ${(file.errors || []).join("; ")}`).join(" | "))}</small>` : ""}
      `
      : noUpdates
        ? `
          <strong>No updates found.</strong>
          <span>${skipped} delivery list file${skipped === 1 ? "" : "s"} checked. Existing New/Updated markers were refreshed where applicable.</span>
          <small>${escapeHtml(windowText)}</small>
        `
        : `
          <strong>Import complete.</strong>
          <span>${imported} new, ${updated} updated, ${skipped} unchanged.</span>
          <small>${escapeHtml(windowText)}</small>
        `;
  }
}

async function refreshAdminPage() {
  if (!state.backend) return;
  const requests = [];
  requests.push(hasPermission("view_admin") ? fetchJson("/api/admin/summary") : Promise.resolve(null));
  requests.push(hasPermission("manage_users") ? fetchJson("/api/admin/users") : Promise.resolve(null));
  requests.push(hasPermission("view_active_sessions") ? fetchJson("/api/admin/sessions") : Promise.resolve(null));
  requests.push(hasPermission("manage_customer_route_rules") ? fetchJson("/api/admin/customer-route-rules") : Promise.resolve(null));
  requests.push(hasPermission("manage_customer_route_rules") ? fetchJson("/api/admin/customer-emails") : Promise.resolve(null));
  requests.push(hasPermission("manage_bay_layout") ? fetchJson("/api/admin/bay-scanner-rules") : Promise.resolve(null));
  requests.push(hasPermission("manage_bay_layout") ? fetchJson("/api/admin/bay-auto-assigner") : Promise.resolve(null));
  requests.push(hasPermission("manage_roles") ? fetchJson("/api/admin/roles") : Promise.resolve(null));
  const [summary, users, sessions, customerRules, customerEmails, bayScannerRules, bayAutoAssignSettings, roles] = await Promise.all(requests);
  if (summary) state.adminSummary = summary;
  if (summary && els.adminSummary) {
    els.adminSummary.innerHTML = [
      miniStat("Active Delivery Lists", summary.activeDeliveryDates ?? summary.activeDeliveryLists ?? 0, `${summary.activeDeliveryLists ?? 0} active stages`),
      miniStat("Scans Today", summary.scanEventsToday ?? summary.scanEvents ?? 0),
      miniStat("Line Items", summary.lineItems ?? 0),
      miniStat("Active Users", summary.activeUsers ?? 0),
    ].join("");
  }
  if (els.adminLastUpdated) els.adminLastUpdated.textContent = `Last updated: ${new Date().toLocaleString()}`;
  if (summary) {
    state.adminRecentImports = summary.recentImports || [];
    renderImportHistory(summary.recentImports || []);
    renderAdminDeleteControls();
    renderAdminResetControls();
    if (els.tempFolderInput && !els.tempFolderInput.value && summary.tempDeliveryListsDir) els.tempFolderInput.value = summary.tempDeliveryListsDir;
  }
  state.adminUsers = users?.users || [];
  state.activeSessions = sessions?.sessions || [];
  state.adminCustomerRouteRules = customerRules?.rules || [];
  state.customerEmailSettings = customerEmails || state.customerEmailSettings || { contacts: [], cc: [], outbox: [] };
  state.bayScannerSettings = bayScannerRules || state.bayScannerSettings || { manualRules: [], barcodeRules: [] };
  state.bayAutoAssignSettings = bayAutoAssignSettings || state.bayAutoAssignSettings;
  state.adminRoles = roles?.roles || state.adminRoles || [];
  state.allPermissions = roles?.permissions || state.allPermissions || [];
  renderAdminUsers();
  renderAdminStations();
  renderManualEditStageOptions();
  renderCustomerRouteRules();
  renderCustomerEmailOverview();
  renderBayScannerRuleOverview();
  renderBayAutoAssignOverview();
  renderActiveSessions();
}

function adminDeliveryListCutoffDate(pastDays = state.adminDeliveryListVisiblePastDays) {
  const cutoff = new Date();
  cutoff.setHours(0, 0, 0, 0);
  cutoff.setDate(cutoff.getDate() - Math.max(Number(pastDays || 0), 0));
  return cutoff;
}

function deliveryListIsInAdminWindow(list, pastDays = state.adminDeliveryListVisiblePastDays) {
  const deliveryDate = parseDateKey(list?.deliveryDate);

  if (!deliveryDate) return true;

  return deliveryDate >= adminDeliveryListCutoffDate(pastDays);
}

function adminDeliveryListHiddenOlderRows(lists = state.lists, pastDays = state.adminDeliveryListVisiblePastDays) {
  return lists.filter((list) => !deliveryListIsInAdminWindow(list, pastDays));
}

function adminDeliveryListWindowLabel(pastDays = state.adminDeliveryListVisiblePastDays) {
  const days = Math.max(Number(pastDays || 0), ADMIN_DELIVERY_LIST_DEFAULT_PAST_DAYS);

  if (days % 7 === 0) {
    const weeks = Math.max(Math.round(days / 7), 1);
    return `all future dates and the last ${weeks === 1 ? "week" : `${weeks} weeks`}`;
  }

  return `all future dates and the last ${days} days`;
}

function adminDeliveryListModalResultsHtml(lists = state.lists, query = "") {
  const cleanQuery = String(query || "").trim();

  return deliveryListAdminRows(lists, 0, true, {
    includeLoadMore: !cleanQuery,
    query: cleanQuery,
    visiblePastDays: state.adminDeliveryListVisiblePastDays,
    sourceCount: state.lists.length,
  });
}

function renderAdminDeliveryListModalResults(lists = state.lists, query = "") {
  const target = document.getElementById("adminDeliveryListModalResults");

  if (!target) return;

  target.innerHTML = adminDeliveryListModalResultsHtml(lists, query);
}

async function refreshAdminDeliveryListModal() {
  const searchInput = document.getElementById("adminDeliveryListModalSearch");
  const query = searchInput?.value.trim() || "";

  if (!query) {
    renderAdminDeliveryListModalResults(state.lists, "");
    return;
  }

  renderAdminDeliveryListModalResults(await searchAdminDeliveryLists(query), query);
}

function deliveryListAdminRows(lists = state.lists, limit = 7, editable = false, options = {}) {
  const cleanQuery = String(options.query || "").trim();
  const includeLoadMore = Boolean(options.includeLoadMore);
  const visiblePastDays = Number(options.visiblePastDays || state.adminDeliveryListVisiblePastDays || ADMIN_DELIVERY_LIST_DEFAULT_PAST_DAYS);

  const sortedRows = lists
    .slice()
    .sort((a, b) => String(b.deliveryDate || "").localeCompare(String(a.deliveryDate || "")) || stageSort(a) - stageSort(b));

  const hiddenOlderRows = includeLoadMore ? adminDeliveryListHiddenOlderRows(sortedRows, visiblePastDays) : [];
  const visibleRows = includeLoadMore ? sortedRows.filter((list) => deliveryListIsInAdminWindow(list, visiblePastDays)) : sortedRows;
  const limitedRows = limit ? visibleRows.slice(0, limit) : visibleRows;
  const hiddenOlderDates = new Set(hiddenOlderRows.map((list) => list.deliveryDate).filter(Boolean));
  const shownDates = new Set(limitedRows.map((list) => list.deliveryDate).filter(Boolean));

  const summaryHtml = editable
    ? `
      <div class="admin-delivery-window-note">
        <strong>${escapeHtml(cleanQuery ? `Search results for "${cleanQuery}"` : `Showing ${adminDeliveryListWindowLabel(visiblePastDays)}`)}</strong>
        <span>${escapeHtml(shownDates.size)} delivery date${shownDates.size === 1 ? "" : "s"} / ${escapeHtml(limitedRows.length)} stage${limitedRows.length === 1 ? "" : "s"}${cleanQuery ? " found. Search checks every active delivery list, including older dates." : "."}</span>
      </div>
    `
    : "";

  const loadMoreHtml = includeLoadMore && hiddenOlderRows.length
    ? `
      <div class="admin-delivery-load-more-wrap">
        <button class="admin-delivery-load-more" type="button" data-admin-delivery-load-more>
          Load more older delivery lists
        </button>
        <span>${escapeHtml(hiddenOlderDates.size)} older delivery date${hiddenOlderDates.size === 1 ? "" : "s"} hidden (${escapeHtml(hiddenOlderRows.length)} stage${hiddenOlderRows.length === 1 ? "" : "s"}).</span>
      </div>
    `
    : "";

  if (!limitedRows.length) {
    return `
      ${summaryHtml}
      <div class="admin-empty">${escapeHtml(cleanQuery ? "No delivery lists match that search." : "No delivery lists found in the current window.")}</div>
      ${loadMoreHtml}
    `;
  }

  const groups = listsByDeliveryDate(limitedRows);

  return `
    ${summaryHtml}
    <div class="admin-delivery-edit-list">
      ${groups
        .map((group, index) => {
          const totalQty = group.lists.reduce((sum, list) => sum + Number(list.totalQty ?? list.itemCount ?? 0), 0);
          const scannedQty = group.lists.reduce((sum, list) => sum + Number(list.scannedQty || 0), 0);
          const percent = totalQty ? Math.round((scannedQty / totalQty) * 100) : 0;

          return `
            <details class="admin-delivery-date-group">
              <summary class="admin-delivery-date-summary">
                <span class="admin-delivery-date-main">
                  <strong>${escapeHtml(formatDisplayDate(group.date))}</strong>
                  <small>${escapeHtml(group.lists.length)} stage${group.lists.length === 1 ? "" : "s"} | ${escapeHtml(scannedQty)} / ${escapeHtml(totalQty)} pcs | ${escapeHtml(percent)}%</small>
                </span>

                <span class="admin-delivery-date-progress">
                  <span class="progress-line"><i style="width: ${Math.min(percent, 100)}%"></i></span>
                </span>

                ${
                  editable
                    ? `<span class="admin-date-action-row">
                        <button
                          type="button"
                          class="icon-only icon-reset"
                          data-admin-date-reset="${escapeHtml(group.date)}"
                          title="Reset all stages for ${escapeHtml(formatDisplayDate(group.date))}"
                          aria-label="Reset all stages for ${escapeHtml(formatDisplayDate(group.date))}"
                        ></button>
                        <button
                          type="button"
                          class="icon-only icon-trash danger"
                          data-admin-date-delete="${escapeHtml(group.date)}"
                          title="Delete all stages for ${escapeHtml(formatDisplayDate(group.date))}"
                          aria-label="Delete all stages for ${escapeHtml(formatDisplayDate(group.date))}"
                        ></button>
                      </span>`
                    : ""
                }
              </summary>

              <div class="admin-delivery-stage-list">
                ${group.lists
                  .map((list) => {
                    const listTotalQty = Number(list.totalQty ?? list.itemCount ?? 0);
                    const listScannedQty = Number(list.scannedQty || 0);
                    const listPercent = listTotalQty ? Math.round((listScannedQty / listTotalQty) * 100) : 0;

                    return `
                      <article class="admin-delivery-stage-row">
                        <span class="admin-delivery-stage-main">
                          <strong>${escapeHtml(list.stage || list.label || list.id)}</strong>
                          <small>${escapeHtml(list.scanner || "")}</small>
                        </span>

                        <span class="admin-delivery-stage-qty">
                          ${escapeHtml(listScannedQty)} / ${escapeHtml(listTotalQty)} pcs
                          <span class="progress-line"><i style="width: ${Math.min(listPercent, 100)}%"></i></span>
                        </span>

                        ${
                          editable
                            ? `<span class="admin-action-cell">
                                <button
                                  type="button"
                                  class="icon-only icon-pencil"
                                  data-admin-list-edit="${escapeHtml(list.id)}"
                                  title="Edit ${escapeHtml(list.label || list.id)}"
                                  aria-label="Edit ${escapeHtml(list.label || list.id)}"
                                ></button>
                                <button
                                  type="button"
                                  class="icon-only icon-reset"
                                  data-admin-list-reset="${escapeHtml(list.id)}"
                                  title="Reset scans for ${escapeHtml(list.label || list.id)}"
                                  aria-label="Reset scans for ${escapeHtml(list.label || list.id)}"
                                ></button>
                                <button
                                  type="button"
                                  class="icon-only icon-trash danger"
                                  data-admin-list-delete="${escapeHtml(list.id)}"
                                  title="Delete ${escapeHtml(list.label || list.id)}"
                                  aria-label="Delete ${escapeHtml(list.label || list.id)}"
                                ></button>
                              </span>`
                            : ""
                        }
                      </article>
                    `;
                  })
                  .join("")}
              </div>
            </details>
          `;
        })
        .join("")}
    </div>
    ${loadMoreHtml}
  `;
}

async function searchAdminDeliveryLists(query) {
  const clean = String(query || "").trim();
  const local = state.lists.filter((list) =>
    [list.label, list.deliveryDate, formatDisplayDate(list.deliveryDate), list.stage, list.scanner]
      .some((value) => String(value || "").toLowerCase().includes(clean.toLowerCase())),
  );
  if (!state.backend || clean.length < 2) return local;
  try {
    const payload = await fetchJson(`/api/admin/line-items/search?q=${encodeURIComponent(clean)}`);
    const matchingIds = new Set((payload.results || []).map((item) => item.listId).filter(Boolean));
    const merged = [...local];
    for (const list of state.lists) {
      if (matchingIds.has(list.id) && !merged.some((existing) => existing.id === list.id)) merged.push(list);
    }
    return merged;
  } catch (error) {
    console.warn("Admin delivery-list search failed", error);
    return local;
  }
}

function activeRecentImports(imports = state.adminRecentImports || []) {
  const activeListIds = new Set(state.lists.map((list) => list.id));
  const activeByDate = listsByDeliveryDate(state.lists);
  const yesterday = new Date();
  yesterday.setDate(yesterday.getDate() - 1);
  yesterday.setHours(0, 0, 0, 0);

  const cleanedImports = imports
    .map((entry) => {
      const listIds = Array.isArray(entry.listIds)
        ? entry.listIds.filter((listId) => activeListIds.has(listId))
        : [];

      const stageSummaries = Array.isArray(entry.stageSummaries)
        ? entry.stageSummaries.filter((row) => row.listId && activeListIds.has(row.listId))
        : [];

      return {
        ...entry,
        listIds,
        stageSummaries,
      };
    })
    .filter((entry) => {
      const hasActiveListIds = Array.isArray(entry.listIds) && entry.listIds.length > 0;
      const hasActiveStageSummaries = Array.isArray(entry.stageSummaries) && entry.stageSummaries.length > 0;

      return hasActiveListIds || hasActiveStageSummaries;
    });

  const importedDateKeys = new Set(cleanedImports.map((entry) => String(entry.deliveryDate || "")).filter(Boolean));
  const liveDateEntries = activeByDate
    .filter((group) => {
      const date = parseDateKey(group.date);
      return date && date >= yesterday && !importedDateKeys.has(group.date);
    })
    .map((group) => ({
      id: `active-${group.date}`,
      batchId: `active-${group.date}`,
      deliveryDate: group.date,
      sourceName: "Active delivery lists",
      importKind: "active_window",
      rowCount: group.lists.reduce((sum, list) => sum + Number(list.itemCount || 0), 0),
      totalQty: group.lists.reduce((sum, list) => sum + Number(list.totalQty || 0), 0),
      importedAt: "",
      createdCount: 0,
      updatedCount: 0,
      addedPieceQty: 0,
      changedPieceQty: 0,
      stageSummaries: group.lists.map((list) => ({
        listId: list.id,
        stage: list.stage,
        stageProfile: list.scanner,
        totalQty: list.totalQty || 0,
        changedLineCount: 0,
        changedPieceQty: 0,
        addedPieceQty: 0,
        created: false,
      })),
      listIds: group.lists.map((list) => list.id),
    }));

  return [...cleanedImports, ...liveDateEntries];
}

function renderAdminDeliveryLists() {
  if (!els.adminDeliveryLists) return;
  els.adminDeliveryLists.innerHTML = importHistoryRows(activeRecentImports());
}

function openAdminModal(kind, options = null) {
  if (kind === "roles") {
  resetRolePermissionUiSession();
  }
  if (!els.adminModal || !els.adminModalBody || !els.adminModalTitle) return;
  const titleMap = {
    deliveryLists: "All Delivery Lists",
    deliveryActions: "Delivery List Actions",
    users: "All Users",
    roles: "Edit Role Permissions",
    sessions: "Active Sessions",
    stations: "Stations",
    customerRoutes: "Edit Customer Routes",
    customerEmails: "Customer Email Rules",
    bayScannerRules: "Bay Scanner Rules",
    bayAutoAssigner: "Bay Auto Assigner",
    manualEdit: "Manual Delivery List Edit",
    lookups: "Lookup Manager",
    rackForm: "Rack",
    rackSetForm: "Rack Set",
    racks: "Edit Racks",
    recentScans: "All Scans",
  };
  els.adminModalTitle.textContent = options?.title || titleMap[kind] || "Admin";
  els.adminModal.dataset.kind = kind;
  els.adminModalBody.innerHTML = options?.body ?? adminModalContent(kind);
  els.adminModal.hidden = false;
  if (els.adminModalBackdrop) els.adminModalBackdrop.hidden = false;
  updateModalScrollLock();
  if (kind === "roles" && (!state.adminRoles.length || !state.allPermissions.length) && hasPermission("manage_roles")) {
    fetchJson("/api/admin/roles")
      .then((payload) => {
        state.adminRoles = payload.roles || [];
        state.allPermissions = payload.permissions || [];
        if (!els.adminModal.hidden) els.adminModalBody.innerHTML = adminModalContent("roles");
      })
      .catch((error) => showInlineError(error.message, true));
  }
}

function closeAdminModal() {
  if (state.manualEditDirty && !window.confirm("You have unsaved manual delivery-list edits. Close without saving?")) return;

  if (!els.adminModal?.hidden && els.adminModalBody?.querySelector(".role-permission-editor")) {
    resetRolePermissionUiSession();
  }

  state.manualEditDirty = false;

  if (els.adminModal) {
    els.adminModal.hidden = true;
    delete els.adminModal.dataset.kind;
  }
  if (els.adminModalBackdrop) els.adminModalBackdrop.hidden = true;
  updateModalScrollLock();
}

function adminModalContent(kind) {
  if (kind === "deliveryLists") {
    state.adminDeliveryListVisiblePastDays = ADMIN_DELIVERY_LIST_DEFAULT_PAST_DAYS;
    return `
      <label class="search-box admin-modal-search">
        <span class="search-icon"></span>
        <input id="adminDeliveryListModalSearch" type="search" autocomplete="off" placeholder="Search date, Job Nr., order number, stage...">
      </label>
      <div class="admin-table" id="adminDeliveryListModalResults">${adminDeliveryListModalResultsHtml()}</div>
    `;
  }
  if (kind === "deliveryActions") {
    state.adminDeliveryListVisiblePastDays = ADMIN_DELIVERY_LIST_DEFAULT_PAST_DAYS;
    return `
      <label class="search-box admin-modal-search">
        <span class="search-icon"></span>
        <input id="adminDeliveryListModalSearch" type="search" autocomplete="off" placeholder="Search date, Job Nr., order number, stage...">
      </label>
      <div class="admin-table" id="adminDeliveryListModalResults">${adminDeliveryListModalResultsHtml()}</div>
    `;
  }
  if (kind === "users") {
    return `
      <section class="users-modal-shell">
        <form id="createUserFormModal" class="admin-form admin-modal-create-user users-create-card">
          <label>
            <span>BFS Email</span>
            <input id="newUserEmailModal" type="email" autocomplete="off" placeholder="name@bfs.local">
          </label>

          <label>
            <span>Username</span>
            <input id="newUserNameModal" type="text" autocomplete="off" placeholder="Defaults to BFS email">
          </label>

          <label>
            <span>Display Name</span>
            <input id="newUserDisplayModal" type="text" autocomplete="off" placeholder="Enter display name">
          </label>

          <label>
            <span>Password</span>
            <input id="newUserPasswordModal" type="password" autocomplete="new-password" placeholder="Enter password">
          </label>

          <label>
            <span>Role</span>
            <select id="newUserRoleModal">
              ${ROLE_OPTIONS.map((role) => `<option>${escapeHtml(role)}</option>`).join("")}
            </select>
          </label>

          <label>
            <span>Station</span>
            <select id="newUserStationModal">
              <option value="">No assigned station</option>
              ${state.stations.map((station) => `<option value="${escapeHtml(station)}">${escapeHtml(station)}</option>`).join("")}
            </select>
          </label>

          <button type="submit" class="users-add-button">
            <span class="user-action-icon icon-user-add" aria-hidden="true"></span>
            <strong>Add user</strong>
          </button>
        </form>

        <div class="users-table-wrap">
          ${renderAdminUsersTable(true, state.adminUsers.length || 1)}
        </div>
      </section>
    `;
  }
  if (kind === "roles") {
    return rolePermissionsModalHtml();
  }
  if (kind === "sessions") {
    return `<div class="compact-list modal-list">${state.activeSessions.length ? state.activeSessions.map((session) => `<div><strong>${escapeHtml(session.displayName)}</strong><span>${escapeHtml(session.role || "")} - ${escapeHtml(session.station || "No station")}</span><small>Last seen ${escapeHtml(session.lastSeenAt)}</small></div>`).join("") : `<div><strong>No active sessions</strong><span>Users appear here after login.</span></div>`}</div>`;
  }
  if (kind === "stations") {
    return `
      <div class="station-add-row">
        <input id="newStationInputModal" type="text" autocomplete="off" placeholder="New station">
        <button id="addStationBtnModal" type="button">Add</button>
      </div>
      <div class="compact-list modal-list">${renderAdminStationsList(true, state.stations.length || 1)}</div>
    `;
  }
  if (kind === "customerRoutes") {
    return customerRouteRulesModalHtml();
  }
  if (kind === "customerEmails") {
    return customerEmailRulesModalHtml();
  }
  if (kind === "bayScannerRules") {
    return bayScannerRulesModalHtml();
  }
  if (kind === "bayAutoAssigner") {
    return bayAutoAssignerModalHtml();
  }
  if (kind === "manualEdit") {
    return manualEditModalHtml();
  }
  if (kind === "lookups") {
    return lookupManagerModalHtml();
  }
  if (kind === "recentScans") {
    return recentScansModalHtml();
  }
  if (kind === "racks") {
    return rackManagerModalHtml();
  }
  if (kind === "rackForm") {
    return rackFormModalHtml();
  }
  if (kind === "rackSetForm") {
    return rackSetFormModalHtml();
  }
  return `<div class="admin-empty">Choose a dashboard section to view details.</div>`;
}

function lookupTypeMeta(title) {
  const clean = String(title || "").toLowerCase();

  if (clean.includes("product")) {
    return {
      className: "products",
      label: "Product names",
      description: "Glass/product descriptions used in manual delivery-list edits.",
    };
  }

  if (clean.includes("route")) {
    return {
      className: "routes",
      label: "Route codes",
      description: "Routing values such as CPU, DTC, GNV, or custom customer routes.",
    };
  }

  return {
    className: "processes",
    label: "Process states",
    description: "Status values such as New, Updated, Rush, Remake, and SDI.",
  };
}

function lookupListHtml(title, items = []) {
  const meta = lookupTypeMeta(title);

  return `
    <section class="lookup-manager-list ${escapeHtml(meta.className)}">
      <header>
        <span class="lookup-type-icon" aria-hidden="true"></span>
        <div>
          <h3>${escapeHtml(meta.label)}</h3>
          <p>${escapeHtml(meta.description)}</p>
        </div>
        <strong>${escapeHtml(items.length)}</strong>
      </header>

      <div class="lookup-row-list">
        ${
          items.length
            ? items
                .map((item) => `
                  <article class="lookup-row">
                    <div class="lookup-row-main">
                      <strong>${escapeHtml(item.label || item.value)}</strong>
                      <span>${escapeHtml(item.value || "")}${item.category ? ` | ${escapeHtml(item.category)}` : ""}</span>
                      ${item.matchTerms ? `<small>Matches: ${escapeHtml(item.matchTerms)}</small>` : ""}
                    </div>
                    <em>${escapeHtml(item.source || "manual")}</em>
                  </article>
                `)
                .join("")
            : `<div class="lookup-empty-state"><strong>No ${escapeHtml(title.toLowerCase())} yet</strong><span>Add one above to make manual edits faster and cleaner.</span></div>`
        }
      </div>
    </section>
  `;
}

function lookupManagerModalHtml() {
  const lookups = state.manualEditLookups || { products: [], routes: [], processes: [] };
  const productCount = (lookups.products || []).length;
  const routeCount = (lookups.routes || []).length;
  const processCount = (lookups.processes || []).length;

  return `
    <div class="lookup-manager-shell lookup-manager-modern">
      <section class="lookup-manager-hero">
        <div>
          <span class="lookup-hero-label">Lookup Manager</span>
          <strong>Edit dropdown choices used by manual list editing</strong>
          <span>Add clean product names, route codes, and process states so the manual editor stays consistent.</span>
        </div>
        <div class="lookup-manager-kpis">
          ${miniStat("Products", productCount)}
          ${miniStat("Routes", routeCount)}
          ${miniStat("Processes", processCount)}
        </div>
      </section>

      <section class="lookup-add-card">
        <div class="lookup-add-copy">
          <strong>Add lookup value</strong>
          <span>Use Value for the actual saved code. Use Display label for the cleaner name people see.</span>
        </div>

        <form id="manualLookupForm" class="lookup-manager-form">
          <label>
            <span>Lookup type</span>
            <select id="lookupTypeInput">
              <option value="product">Product</option>
              <option value="route">Route</option>
              <option value="process">Process</option>
            </select>
          </label>
          <label>
            <span>Value / code</span>
            <input id="lookupValueInput" type="text" autocomplete="off" placeholder="CPU, 1/4 Mirror, Rush">
          </label>
          <label>
            <span>Display label</span>
            <input id="lookupLabelInput" type="text" autocomplete="off" placeholder="Customer Pickup">
          </label>
          <label>
            <span>Category</span>
            <input id="lookupCategoryInput" type="text" autocomplete="off" placeholder="Pickup, delivery, branch">
          </label>
          <label class="wide">
            <span>Match terms</span>
            <input id="lookupMatchTermsInput" type="text" autocomplete="off" placeholder="CPU-Air, customer pickup, will call">
          </label>
          <button type="submit">Add Lookup</button>
        </form>
      </section>

      <div class="lookup-manager-grid">
        ${lookupListHtml("Products", lookups.products || [])}
        ${lookupListHtml("Routes", lookups.routes || [])}
        ${lookupListHtml("Processes", lookups.processes || [])}
      </div>
    </div>
  `;
}

function rackManagerRackEditHtml() {
  const code = state.rackManagerEditingRackCode || "";
  if (!code) return "";

  const rack = (state.racks || []).find((item) => item.code === code);
  if (!rack) return "";

  const legacyTruck = rack.code === "T";

  return `
    <form id="rackManagerInlineEditForm" class="rack-manager-set-edit rack-manager-rack-edit">
      <input id="rackManagerInlineOldCode" type="hidden" value="${escapeHtml(rack.code)}">
      <div class="rack-manager-quick-copy">
        <strong>Edit ${escapeHtml(legacyTruck ? "Truck / No Rack" : rack.code)}</strong>
        <span>Change the coded rack name, display name, or rack set/type from the same edit area used for rack sets.</span>
      </div>

      <label>
        <span>Rack code</span>
        <input id="rackManagerInlineCode" type="text" autocomplete="off" value="${escapeHtml(rack.code)}" ${legacyTruck ? "readonly" : ""} placeholder="R1S or T2">
      </label>

      <label>
        <span>Display name</span>
        <input id="rackManagerInlineName" type="text" autocomplete="off" value="${escapeHtml(rack.name || rack.type || rack.code || "")}" placeholder="Rack display name">
      </label>

      <label>
        <span>Rack set / type</span>
        <input id="rackManagerInlineType" type="text" list="rackManagerRackTypes" autocomplete="off" value="${escapeHtml(rack.type || "Steel")}" placeholder="Steel, Wood, Coral, Truck">
      </label>

      <div class="rack-manager-set-actions">
        <button type="button" class="secondary" data-rack-inline-cancel>Cancel</button>
        <button type="submit">Save Rack</button>
      </div>
    </form>
  `;
}

function rackManagerSetEditHtml() {
  const label = state.rackManagerEditingSetLabel || "";
  if (!label) return "";

  const racks = (state.racks || []).filter((rack) => rackGroupLabel(rack) === label);
  if (!racks.length) return "";

  const firstRack = racks[0] || {};
  const sampleName = String(firstRack.name || "");
  const firstNumber = rackSortNumber(firstRack.code);
  const nameRoot = label === "Truck"
    ? "Truck"
    : firstNumber
      ? sampleName.replace(new RegExp(`\\s*${firstNumber}\\s*$`), "").trim()
      : sampleName || label;

  return `
    <form id="rackManagerSetEditForm" class="rack-manager-set-edit">
      <div class="rack-manager-quick-copy">
        <strong>Edit ${escapeHtml(label)} set</strong>
        <span>Rename the rack set/type and optionally rebuild each rack display name from one shared name root.</span>
      </div>

      <label>
        <span>New rack set / type</span>
        <input id="rackManagerSetTypeInput" type="text" autocomplete="off" value="${escapeHtml(label === "Truck" ? "Truck" : label)}" ${label === "Truck" ? "readonly" : ""}>
      </label>

      <label>
        <span>Name root</span>
        <input id="rackManagerSetNameRootInput" type="text" autocomplete="off" value="${escapeHtml(nameRoot || label)}" placeholder="Example: Rack Steel">
      </label>

      <div class="rack-manager-set-actions">
        <button type="button" class="secondary" data-rack-manager-set-cancel>Cancel</button>
        <button type="submit">Save Set</button>
      </div>
    </form>
  `;
}

function focusRackManagerRackEdit(code) {
  openRackManagerRackInlineEdit(code);
}

function openRackManagerRackInlineEdit(code) {
  state.rackManagerEditingSetLabel = "";
  state.rackManagerEditingRackCode = code || "";
  state.rackManagerSelectedCode = code || state.rackManagerSelectedCode || "";

  if (!els.adminModal?.hidden && els.adminModalBody?.querySelector(".rack-manager-shell")) {
    els.adminModalBody.innerHTML = adminModalContent("racks");
    window.setTimeout(() => {
      const input = document.getElementById("rackManagerInlineName");
      input?.focus();
      input?.select?.();
    }, 30);
  }
}

async function saveRackInlineEdit() {
  const oldCode = state.rackManagerEditingRackCode || document.getElementById("rackManagerInlineOldCode")?.value || "";
  const code = document.getElementById("rackManagerInlineCode")?.value || oldCode;
  if (!oldCode || !code) return;

  const payload = await fetchJson("/api/racks", {
    method: "POST",
    body: JSON.stringify({
      oldRackCode: oldCode,
      rackCode: code,
      name: document.getElementById("rackManagerInlineName")?.value || code,
      type: document.getElementById("rackManagerInlineType")?.value || "Steel",
    }),
  });

  state.racks = payload.racks || [];
  state.rackSummary = payload.summary || null;
  const savedRack = payload.rack || state.racks.find((rack) => rack.code === code) || null;
  state.rackManagerSelectedCode = savedRack?.code || code;
  state.rackManagerEditingRackCode = "";
  renderRacksPage();
  renderScanRackTools();

  if (!els.adminModal?.hidden && els.adminModalBody?.querySelector(".rack-manager-shell")) {
    els.adminModalBody.innerHTML = adminModalContent("racks");
  }

  showFloatingNotice(`Saved rack ${code}.`, "success");
}

function openRackManagerSetEdit(label) {
  state.rackManagerEditingRackCode = "";
  state.rackManagerEditingSetLabel = label || "";

  if (!els.adminModal?.hidden && els.adminModalBody?.querySelector(".rack-manager-shell")) {
    els.adminModalBody.innerHTML = adminModalContent("racks");
    window.setTimeout(() => {
      const input = document.getElementById("rackManagerSetTypeInput");
      input?.focus();
      input?.select?.();
    }, 30);
  }
}

async function saveRackSetQuickEdit() {
  const oldLabel = state.rackManagerEditingSetLabel || "";
  const newType = String(document.getElementById("rackManagerSetTypeInput")?.value || oldLabel).trim() || oldLabel;
  const nameRoot = String(document.getElementById("rackManagerSetNameRootInput")?.value || newType).trim() || newType;
  const racks = (state.racks || []).filter((rack) => rackGroupLabel(rack) === oldLabel);

  if (!oldLabel || !racks.length) return;

  let latestPayload = null;

  for (const rack of racks) {
    const number = rackSortNumber(rack.code);
    const isTruck = isTruckRack(rack);
    const nextType = isTruck ? "Truck" : newType;
    const nextName = isTruck
      ? rack.code === "T"
        ? rack.name || "Truck / No Rack"
        : `${nameRoot || "Truck"}${number ? ` ${number}` : ""}`
      : `${nameRoot}${number ? ` ${number}` : ""}`;

    latestPayload = await fetchJson("/api/racks", {
      method: "POST",
      body: JSON.stringify({
        rackCode: rack.code,
        name: nextName,
        type: nextType,
      }),
    });
  }

  state.racks = latestPayload?.racks || state.racks || [];
  state.rackSummary = latestPayload?.summary || state.rackSummary || null;
  state.rackManagerEditingSetLabel = "";
  state.selectedRackSetLabel = newType;
  renderRacksPage();
  renderScanRackTools();

  if (!els.adminModal?.hidden && els.adminModalBody?.querySelector(".rack-manager-shell")) {
    els.adminModalBody.innerHTML = adminModalContent("racks");
  }

  showFloatingNotice(`Saved ${oldLabel} rack set.`, "success");
}

function rackManagerModalHtml() {
  const groups = new Map();
  for (const rack of state.racks || []) {
    const label = rackGroupLabel(rack);
    if (!groups.has(label)) groups.set(label, []);
    groups.get(label).push(rack);
  }

  const sortedGroups = [...groups.entries()].sort(([a], [b]) => {
    if (a === "Truck") return 1;
    if (b === "Truck") return -1;
    const order = { Steel: 1, Wood: 2, Coral: 3 };
    return (order[a] || 50) - (order[b] || 50) || a.localeCompare(b);
  });

  const selectedRack = selectedRackManagerRack(state.rackManagerSelectedCode) || state.racks[0] || null;
  state.rackManagerSelectedCode = selectedRack?.code || "";

  return `
    <div class="rack-manager-shell">
      <div class="rack-manager-topbar">
        <div>
          <strong>Rack Manager</strong>
          <span>Edit individual racks, add rack sets, delete empty racks, or delete empty rack sets.</span>
        </div>
        <div class="rack-manager-actions">
          <button type="button" data-rack-manager-new-rack>Create Rack</button>
          <button type="button" data-rack-manager-new-set>Create Rack Set</button>
        </div>
      </div>

      ${rackManagerRackEditHtml() || rackManagerSetEditHtml()}

      <div class="rack-manager-grid">
        ${
          sortedGroups.length
            ? sortedGroups
                .map(([label, racks]) => {
                  const totalQty = racks.reduce((sum, rack) => sum + Number(rack.qty || 0), 0);
                  const deletableCount = racks.filter((rack) => rack.code !== "T" && Number(rack.qty || 0) === 0).length;

                  return `
                    <section class="rack-manager-group">
                      <header>
                        <div>
                          <h3>${escapeHtml(label)}</h3>
                          <span>${escapeHtml(racks.length)} rack${racks.length === 1 ? "" : "s"} | ${escapeHtml(totalQty)} pcs</span>
                        </div>
                        <div class="rack-manager-group-actions">
                          <button type="button" class="icon-only icon-plus" data-rack-manager-add-to-set="${escapeHtml(label)}" title="Add ${label === "Truck" ? "another truck" : `rack to ${escapeHtml(label)}`}" aria-label="Add ${label === "Truck" ? "another truck" : `rack to ${escapeHtml(label)}`}"></button>
                          <button type="button" class="icon-only icon-pencil" data-rack-set-edit="${escapeHtml(label)}" title="Edit ${escapeHtml(label)} set" aria-label="Edit ${escapeHtml(label)} set"></button>
                          <button type="button" class="icon-only icon-trash danger" data-rack-set-delete="${escapeHtml(label)}" ${deletableCount ? "" : "disabled"} title="Delete empty racks in ${escapeHtml(label)}" aria-label="Delete empty racks in ${escapeHtml(label)}"></button>
                        </div>
                      </header>

                      <div class="rack-manager-rows">
                        ${racks
                          .slice()
                          .sort((a, b) => Number(a.sortOrder || 0) - Number(b.sortOrder || 0) || String(a.code).localeCompare(String(b.code), undefined, { numeric: true }))
                          .map((rack) => {
                            const qty = Number(rack.qty || 0);
                            const isTruck = isTruckRack(rack);
                            const legacyTruck = rack.code === "T";
                            const canDelete = !legacyTruck && qty === 0;
                            const status = String(rack.status || "Open").toLowerCase() === "closed" ? "Complete" : qty ? "Open" : "Empty";

                            const isEditing = state.rackManagerEditingRackCode === rack.code;

                            return `
                              <article class="rack-manager-row ${isEditing ? "is-editing" : ""}">
                                <div>
                                  <strong>${escapeHtml(legacyTruck ? "Truck / No Rack" : rack.code)}</strong>
                                  <span>${escapeHtml(rack.name || rack.type || "")}</span>
                                </div>
                                <span class="rack-status-badge ${escapeHtml(status.toLowerCase())}">${escapeHtml(status)}</span>
                                <b>${escapeHtml(qty)} pcs</b>
                                <button type="button" class="icon-only icon-pencil" data-rack-edit="${escapeHtml(rack.code)}" title="Edit rack" aria-label="Edit ${escapeHtml(rack.code)}"></button>
                                <button type="button" class="icon-only icon-trash danger" data-rack-delete="${escapeHtml(rack.code)}" ${canDelete ? "" : "disabled"} title="Delete empty rack" aria-label="Delete ${escapeHtml(rack.code)}"></button>
                              </article>
                            `;
                          })
                          .join("")}
                      </div>
                    </section>
                  `;
                })
                .join("")
            : `<div class="admin-empty">No racks available. Create a rack set to get started.</div>`
        }
      </div>
    </div>
  `;
}

function rackFormModalHtml() {
  const rack = state.rackModal?.rack || {};
  return `
    <form id="rackFormModal" class="admin-form rack-modal-form">
      <input id="rackModalOldCode" type="hidden" value="${escapeHtml(rack.oldCode || rack.code || "")}">
      <label><span>Rack code</span><input id="rackModalCode" type="text" autocomplete="off" value="${escapeHtml(rack.code || "")}" ${rack.code === "T" ? "readonly" : ""} placeholder="R11S"></label>
      <label><span>Rack name</span><input id="rackModalName" type="text" autocomplete="off" value="${escapeHtml(rack.name || "")}" placeholder="Rack 11 Steel"></label>
      <label>
        <span>Rack type</span>
        <select id="rackModalType">
          ${["Steel", "Wood", "Truck", "Aluminum", "Other"].map((type) => `<option ${String(rack.type || "Steel") === type ? "selected" : ""}>${escapeHtml(type)}</option>`).join("")}
        </select>
      </label>
      <footer class="modal-actions">${rack.code && rack.code !== "T" ? `<button type="button" class="danger" data-rack-delete="${escapeHtml(rack.code)}">Delete Rack</button>` : ""}<button type="submit">Confirm</button></footer>
    </form>
  `;
}

function rackSetFormModalHtml() {
  const set = state.rackModal?.set || {};
  return `
    <form id="rackSetFormModal" class="admin-form rack-modal-form">
      <label><span>Set suffix</span><input id="rackSetModalPrefix" type="text" autocomplete="off" value="${escapeHtml(set.prefix || "")}" placeholder="S"></label>
      <label><span>Set name</span><input id="rackSetModalName" type="text" autocomplete="off" value="${escapeHtml(set.name || "")}" placeholder="Steel"></label>
      <label><span>Rack count</span><input id="rackSetModalCount" type="number" min="1" max="100" value="${escapeHtml(set.count || 10)}"></label>
      <label><span>Starting rack number</span><input id="rackSetModalStart" type="number" min="1" max="999" value="${escapeHtml(set.start || 1)}"></label>
      <footer class="modal-actions"><button type="submit">Confirm</button></footer>
    </form>
  `;
}

function permissionLabel(permission) {
  return String(permission || "")
    .split("_")
    .map((part) => part ? part[0].toUpperCase() + part.slice(1) : "")
    .join(" ");
}

const PERMISSION_CATEGORIES = [
  {
    title: "Scanning",
    description: "Main scanner access, scan visibility, undo, and reset controls.",
    permissions: ["scan", "view_lists", "view_stations", "view_own_scans", "undo_scan", "reset_lists"],
  },
  {
    title: "Delivery Lists",
    description: "Importing, previewing, editing, printing, reports, and global search.",
    permissions: ["import_delivery_lists", "preview_import", "edit_delivery_lists", "export_reports", "view_reports", "global_search"],
  },
  {
    title: "Exceptions & Manual Fixes",
    description: "Manual adjustments and exception review/resolution.",
    permissions: ["manual_adjust", "view_exceptions", "resolve_exceptions"],
  },
  {
    title: "Admin & Users",
    description: "Admin dashboard, users, roles, active sessions, passwords, and updates.",
    permissions: [
      "view_admin",
      "manage_users",
      "manage_roles",
      "deactivate_users",
      "reactivate_users",
      "update_user_passwords",
      "view_active_sessions",
    ],
  },
  {
    title: "Stations & Rules",
    description: "Station setup and customer route rule management.",
    permissions: ["manage_stations", "remove_stations", "manage_customer_route_rules"],
  },
  {
    title: "Indian Trail / Bays",
    description: "Indian Trail receiving, bay map, bay actions, SDI, reports, and layout.",
    permissions: [
      "view_indian_trail",
      "indian_trail_receive",
      "view_bays",
      "assign_bay",
      "move_bay",
      "clear_bay",
      "mark_sdi",
      "remove_sdi",
      "bay_check",
      "indian_trail_reports",
      "manage_bay_layout",
    ],
  },
  {
    title: "Racks",
    description: "Rack overview, rack scanning, and rack management.",
    permissions: ["view_racks", "scan_racks", "manage_racks"],
  },
];

function categorizedPermissions(permissions = []) {
  const allPermissions = permissions || [];
  const assigned = new Set(PERMISSION_CATEGORIES.flatMap((category) => category.permissions));

  const categories = PERMISSION_CATEGORIES
    .map((category) => ({
      ...category,
      permissions: category.permissions.filter((permission) => allPermissions.includes(permission)),
    }))
    .filter((category) => category.permissions.length);

  const uncategorized = allPermissions.filter((permission) => !assigned.has(permission));

  if (uncategorized.length) {
    categories.push({
      title: "Other",
      description: "New or uncategorized permissions.",
      permissions: uncategorized,
    });
  }

  return categories;
}

function rolePermissionCategoryKey(roleName, categoryTitle) {
  return `${String(roleName || "").trim()}::${String(categoryTitle || "").trim()}`;
}

function resetRolePermissionUiSession() {
  state.rolePermissionOpenRoles = new Set();
  state.rolePermissionOpenCategories = new Set();
  state.rolePermissionScrollTop = 0;
}

function rememberRolePermissionUiState() {
  const editor = document.querySelector(".role-permission-editor");

  if (els.adminModalBody?.contains(editor)) {
    state.rolePermissionScrollTop = els.adminModalBody.scrollTop || 0;
  }

  document.querySelectorAll(".role-permission-card[data-role-card]").forEach((details) => {
    const roleName = details.dataset.roleCard || "";

    if (details.open) {
      state.rolePermissionOpenRoles.add(roleName);
    } else {
      state.rolePermissionOpenRoles.delete(roleName);
    }
  });

  document.querySelectorAll(".permission-category[data-role-name][data-category-title]").forEach((details) => {
    const key = rolePermissionCategoryKey(details.dataset.roleName, details.dataset.categoryTitle);

    if (details.open) {
      state.rolePermissionOpenCategories.add(key);
    } else {
      state.rolePermissionOpenCategories.delete(key);
    }
  });
}

function restoreRolePermissionUiScroll() {
  window.requestAnimationFrame(() => {
    if (els.adminModalBody) {
      els.adminModalBody.scrollTop = state.rolePermissionScrollTop || 0;
    }
  });
}

function rolePermissionCategoryHtml(roleName, category, selected) {
  const checkedCount = category.permissions.filter((permission) => selected.has(permission)).length;
  const categoryKey = rolePermissionCategoryKey(roleName, category.title);
  const open = state.rolePermissionOpenCategories.has(categoryKey);

  return `
    <details
      class="permission-category"
      data-role-name="${escapeHtml(roleName)}"
      data-category-title="${escapeHtml(category.title)}"
      ${open ? "open" : ""}
    >
      <summary>
        <span>
          <strong>${escapeHtml(category.title)}</strong>
          <small>${escapeHtml(category.description)}</small>
        </span>
        <b>${escapeHtml(checkedCount)} / ${escapeHtml(category.permissions.length)}</b>
      </summary>

      <div class="role-permission-grid">
        ${category.permissions
          .map(
            (permission) => `
              <label class="${selected.has(permission) ? "is-checked" : ""}">
                <input type="checkbox" value="${escapeHtml(permission)}" ${selected.has(permission) ? "checked" : ""}>
                <span>${escapeHtml(permissionLabel(permission))}</span>
              </label>
            `,
          )
          .join("")}
      </div>
    </details>
  `;
}

function rolePermissionCountText(role, permissions) {
  const selectedCount = Array.isArray(role.permissions) ? role.permissions.length : 0;
  const totalCount = Array.isArray(permissions) ? permissions.length : 0;

  return `${selectedCount} of ${totalCount} permissions`;
}

function rolePermissionsModalHtml() {
  const roles = state.adminRoles || [];
  const permissions = state.allPermissions || [];

  if (!roles.length || !permissions.length) {
    return `<div class="admin-empty">Role permissions are loading. Close and reopen this panel if they do not appear.</div>`;
  }

  const categories = categorizedPermissions(permissions);

  return `
    <div class="role-permission-editor">
      <div class="role-permission-intro">
        <strong>Role Permissions</strong>
        <span>Open a role, review permissions by page/action group, then save that role.</span>
      </div>

      ${roles
        .map((role) => {
          const selected = new Set(role.permissions || []);
          const roleOpen = state.rolePermissionOpenRoles.has(role.name);

          return `
            <details class="role-permission-card" data-role-card="${escapeHtml(role.name)}" ${roleOpen ? "open" : ""}>
              <summary class="role-permission-summary">
                <span class="role-collapse-icon" aria-hidden="true"></span>

                <span class="role-permission-title">
                  <strong>${escapeHtml(role.name)}</strong>
                  <small>${escapeHtml(role.description || permissionSummaryFromPermissions(role.permissions || []))}</small>
                </span>

                <span class="role-permission-count">${escapeHtml(rolePermissionCountText(role, permissions))}</span>

                <button
                  type="button"
                  class="role-permission-save"
                  data-save-role-permissions="${escapeHtml(role.name)}"
                  title="Save ${escapeHtml(role.name)} permissions"
                >Save</button>
              </summary>

              <div class="role-permission-body">
                ${categories.map((category) => rolePermissionCategoryHtml(role.name, category, selected)).join("")}
              </div>
            </details>
          `;
        })
        .join("")}
    </div>
  `;
}

function permissionSummaryFromPermissions(permissions) {
  const list = permissions || [];
  if (list.includes("view_admin")) return "Full admin access";
  if (list.includes("manage_users")) return "User and system management";
  if (list.includes("manage_racks")) return "Rack and scan management";
  if (list.includes("view_bays")) return "Indian Trail bay access";
  if (list.includes("scan")) return "Scanning and list access";
  return "Custom access";
}

function permissionSummaryForUser(user) {
  const directPermissions = Array.isArray(user?.permissions) ? user.permissions : [];

  if (directPermissions.length) {
    return permissionSummaryFromPermissions(directPermissions);
  }

  const rolePermissions = (state.adminRoles || [])
    .filter((role) => (user?.roles || []).includes(role.name))
    .flatMap((role) => role.permissions || []);

  if (rolePermissions.length) {
    return permissionSummaryFromPermissions(rolePermissions);
  }

  const roleText = (user?.roles || []).join(", ");
  return roleText ? `${roleText} access` : "Custom access";
}

async function saveRolePermissions(roleName) {
  rememberRolePermissionUiState();

  const card = document.querySelector(`[data-role-card="${CSS.escape(roleName)}"]`);

  if (!card) return;

  const permissions = [...card.querySelectorAll("input[type='checkbox']:checked")].map((input) => input.value);

  if (!permissions.length && !window.confirm(`Save ${roleName} with no permissions?`)) return;

  const payload = await fetchJson("/api/admin/roles/permissions", {
    method: "POST",
    body: JSON.stringify({ role: roleName, permissions }),
  });

  state.adminRoles = payload.roles || [];
  state.allPermissions = payload.permissions || state.allPermissions;

  if (els.adminModalBody) {
    els.adminModalBody.innerHTML = adminModalContent("roles");
    restoreRolePermissionUiScroll();
  }

  await refreshAdminPage();

  showFloatingNotice(`${roleName} permissions saved. Users with that role will sign in again to refresh access.`, "success");
}

function manualEditDeliveryDateForList(listId) {
  const selectedList = state.lists.find((item) => item.id === listId);

  return selectedList?.deliveryDate || state.lists[0]?.deliveryDate || "";
}

function manualEditStageListsForCurrentDelivery(selectedListId) {
  const deliveryDate = manualEditDeliveryDateForList(selectedListId);
  const stageLists = state.lists
    .filter((list) => list.deliveryDate === deliveryDate)
    .sort((a, b) => stageSort(a) - stageSort(b) || String(a.label || "").localeCompare(String(b.label || "")));

  return stageLists.length ? stageLists : state.lists.slice();
}

function manualEditStageSummary(listId) {
  const list = state.lists.find((item) => item.id === listId) || state.lists[0] || {};

  if (!list.id) {
    return "No stage selected";
  }

  return `${formatDisplayDate(list.deliveryDate)} - ${list.stage || "Stage"} - ${list.scanner || ""}`;
}

function manualEditModalHtml(resultsHtml = `<div class="admin-empty">Select a delivery list to load editable rows.</div>`) {
  const selected = state.manualEditListId || state.activeListId || state.lists[0]?.id || "";
  const stageLists = manualEditStageListsForCurrentDelivery(selected);

  return `
    <div class="manual-edit-shell">
      <div class="manual-edit-nav-row">
        <button class="manual-edit-back-button" type="button" data-manual-edit-back>
          <span aria-hidden="true">&larr;</span>
          Back to delivery lists
        </button>
        <span class="manual-edit-current-stage">${escapeHtml(manualEditStageSummary(selected))}</span>
      </div>

      <div class="manual-edit-modal-tools">
        <label class="manual-edit-control stage-control">
          <span>Delivery list stage</span>
          <select id="manualEditModalStage">
            ${stageLists
              .map(
                (list) =>
                  `<option value="${escapeHtml(list.id)}" ${list.id === selected ? "selected" : ""}>${escapeHtml(formatDisplayDate(list.deliveryDate))} - ${escapeHtml(list.stage)} - ${escapeHtml(list.scanner || "")}</option>`,
              )
              .join("")}
          </select>
        </label>

        <label class="manual-edit-control search-control">
          <span>Search within stage</span>
          <input id="manualEditModalSearch" type="search" autocomplete="off" value="${escapeHtml(state.manualEditQuery || "")}" placeholder="Order, customer, job, route...">
        </label>

        <div class="manual-edit-tool-actions">
          <button id="manualEditModalSearchBtn" type="button">Search</button>
          <button id="manualEditModalReloadBtn" class="secondary" type="button">Load All</button>
        </div>
      </div>

      <div id="manualEditModalResults" class="admin-table manual-edit-modal-results">${resultsHtml}</div>
    </div>
  `;
}

async function ensureManualEditLookupsLoaded() {
  if (!state.backend) return;

  const lookups = await Promise.allSettled([
    fetchJson("/api/racks"),
    fetchJson("/api/indian-trail/bays"),
    fetchJson("/api/admin/manual-edit-lookups"),
  ]);

  const rackResult = lookups[0];

  if (rackResult.status === "fulfilled") {
    state.racks = rackResult.value.racks || [];
    state.rackSummary = rackResult.value.summary || null;
  }

  const bayResult = lookups[1];

  if (bayResult.status === "fulfilled") {
    state.bays = bayResult.value.bays || [];
    state.bayEvents = bayResult.value.events || state.bayEvents || [];
  }

  const manualLookupResult = lookups[2];

  if (manualLookupResult.status === "fulfilled") {
    state.manualEditLookups = {
      products: manualLookupResult.value.products || [],
      routes: manualLookupResult.value.routes || [],
      processes: manualLookupResult.value.processes || [],
    };
  }
}

async function openManualEditForList(listId) {
  state.manualEditDirty = false;
  state.manualEditListId = listId || state.activeListId || state.lists[0]?.id || "";
  state.manualEditQuery = "";

  openAdminModal("manualEdit");

  await ensureManualEditLookupsLoaded();
  await runManualEditModalSearch(true);
}

async function fetchManualEditResults(query, listId) {
  const params = new URLSearchParams();
  if (query) params.set("q", query);
  if (listId) params.set("listId", listId);
  const payload = await fetchJson(`/api/admin/line-items/search?${params.toString()}`);
  return payload.results || [];
}

async function runManualEditModalSearch(loadAll = false) {
  const stage = document.getElementById("manualEditModalStage")?.value || state.manualEditListId || "";
  const query = loadAll ? "" : (document.getElementById("manualEditModalSearch")?.value.trim() || "");

  state.manualEditListId = stage;
  state.manualEditQuery = query;

  const currentStageLabel = document.querySelector(".manual-edit-current-stage");
  if (currentStageLabel) {
    currentStageLabel.textContent = manualEditStageSummary(stage);
  }

  const target = document.getElementById("manualEditModalResults");

  if (target) {
    target.innerHTML = `
      <div class="manual-edit-loading">
        <div class="admin-empty loading">
          <strong>Loading editable rows...</strong>
          <span class="loading-bar"><i></i></span>
        </div>
      </div>
    `;
  }

  const results = await fetchManualEditResults(query, stage);
  const html = manualEditResultsHtml(results);

  if (target) {
    target.innerHTML = html;
  }

  if (els.manualEditResults) {
    els.manualEditResults.innerHTML = html;
  }

  state.manualEditDirty = false;
}

function renderManualEditStageOptions() {
  if (!els.manualEditStageSelect) return;
  const current = els.manualEditStageSelect.value;
  const options = [`<option value="">All stages</option>`].concat(
    state.lists
      .slice()
      .sort((a, b) => String(b.deliveryDate || "").localeCompare(String(a.deliveryDate || "")) || String(a.stage || "").localeCompare(String(b.stage || "")))
      .map((list) => `<option value="${escapeHtml(list.id)}">${escapeHtml(formatDisplayDate(list.deliveryDate))} - ${escapeHtml(list.stage)}${list.scanner ? ` (${escapeHtml(list.scanner)})` : ""}</option>`),
  );
  els.manualEditStageSelect.innerHTML = options.join("");
  els.manualEditStageSelect.value = state.lists.some((list) => list.id === current) ? current : "";
}

function renderImportHistory(imports) {
  state.adminRecentImports = imports || [];

  const activeImports = activeRecentImports(state.adminRecentImports);

  if (els.adminDeliveryLists) {
    els.adminDeliveryLists.innerHTML = importHistoryRows(activeImports);
  }

  if (!els.importHistory) return;

  els.importHistory.innerHTML = importHistoryRows(activeImports);
}

function importHistoryRows(imports = []) {
  const seenImportGroups = new Set();
  const rows = imports
    .slice()
    .sort((a, b) =>
      String(b.deliveryDate || "").localeCompare(String(a.deliveryDate || "")) ||
      String(b.importedAt || "").localeCompare(String(a.importedAt || "")) ||
      String(a.stage || "").localeCompare(String(b.stage || "")),
    )
    .filter((entry) => {
    const key = entry.deliveryDate || entry.sourceName || entry.fileName || entry.importedAt || "unknown";
    if (seenImportGroups.has(key)) return false;
    seenImportGroups.add(key);
    return true;
  }).slice(0, 30);

  if (!rows.length) {
    return `<div class="admin-empty">No import history yet. Imports from the temp folder or single files will appear here.</div>`;
  }

  const stageNameForRow = (row, list) =>
    String(row.stage || row.stageProfile || row.stageSheetName || list?.stage || list?.label || row.listId || "Updated stage");

  const isStagingRow = (row, list) => /staging/i.test(stageNameForRow(row, list));

  const stageCategoryForImportRow = (row, list) =>
    stageCategory({
      stage: stageNameForRow(row, list),
      scanner: row.stageProfile || row.scanner || list?.scanner || "",
    });

  const updatedQtyForRow = (row, list) =>
    Number(row.totalQty ?? row.updatedQty ?? row.newQty ?? list?.totalQty ?? 0);

  const changedQtyForRow = (row, list) => {
    const updatedQty = updatedQtyForRow(row, list);
    const explicitAddedQty = Number(row.addedPieceQty ?? row.addedQty ?? 0);
    const explicitChangedQty = Number(row.changedPieceQty ?? row.changedQty ?? 0);

    if (row.created) return updatedQty;
    return explicitAddedQty || explicitChangedQty || 0;
  };

  const originalQtyForRow = (row, list) => {
    const updatedQty = updatedQtyForRow(row, list);
    const explicitAddedQty = Number(row.addedPieceQty ?? row.addedQty ?? 0);
    const explicitChangedQty = Number(row.changedPieceQty ?? row.changedQty ?? 0);
    const explicitOriginalQty = row.originalQty ?? row.originalPieceQty ?? row.previousQty ?? row.oldQty ?? row.beforeQty;

    if (row.created) return 0;

    if (explicitOriginalQty !== undefined && explicitOriginalQty !== null && explicitOriginalQty !== "") {
      const originalQty = Number(explicitOriginalQty || 0);

      // Older import-history records sometimes stored 0 even when an unchanged
      // stage already contained pieces. In that case, the current total is the
      // original quantity—not a newly-added quantity.
      if (originalQty <= 0 && updatedQty > 0 && !explicitAddedQty && !explicitChangedQty) {
        return updatedQty;
      }

      if (originalQty <= 0 && updatedQty > 0 && explicitAddedQty > 0) {
        return Math.max(updatedQty - explicitAddedQty, 0);
      }

      return originalQty;
    }

    return Math.max(updatedQty - explicitAddedQty, 0);
  };

  const isNewStageRow = (row, list) => {
    const originalQty = originalQtyForRow(row, list);
    const updatedQty = updatedQtyForRow(row, list);
    const hasRecordedChanges =
      Number(row.changedLineCount || 0) > 0 ||
      Number(row.changedPieceQty || 0) > 0 ||
      Number(row.addedPieceQty || 0) > 0;

    return Boolean(row.created) || (originalQty <= 0 && updatedQty > 0 && hasRecordedChanges);
  };

  const stageRowsForEntry = (entry) => {
    if (Array.isArray(entry.stageSummaries) && entry.stageSummaries.length) {
      return entry.stageSummaries;
    }

    return (entry.listIds || []).map((listId) => {
      const list = state.lists.find((item) => item.id === listId);

      return {
        listId,
        stage: list?.stage || listId,
        totalQty: list?.totalQty ?? entry.totalQty ?? 0,
        changedLineCount: entry.changedLineCount || 0,
        changedPieceQty: entry.changedPieceQty || entry.addedPieceQty || 0,
        addedPieceQty: entry.addedPieceQty || 0,
        created: Boolean(entry.createdCount),
      };
    });
  };

  const hasStageChanges = (row) =>
    row.created ||
    Number(row.changedLineCount || 0) ||
    Number(row.changedPieceQty || 0) ||
    Number(row.addedPieceQty || 0);

  const stageRowKey = (row) => {
    const list = state.lists.find((item) => item.id === row.listId);

    return String(row.listId || stageNameForRow(row, list))
      .trim()
      .toLowerCase()
      .replace(/\s+/g, " ");
  };

  const stageRowPriority = (row) => {
    const list = state.lists.find((item) => item.id === row.listId);
    const originalQty = originalQtyForRow(row, list);
    const updatedQty = updatedQtyForRow(row, list);
    const changedQty = changedQtyForRow(row, list);
    const changedLineCount = Number(row.changedLineCount || 0);
    const isNewStage = isNewStageRow(row, list);

    return (
      (originalQty > 0 ? 100000000 : 0) +
      (!isNewStage ? 10000000 : 0) +
      (changedLineCount * 100000) +
      (changedQty * 1000) +
      updatedQty
    );
  };

  const collapseDuplicateStageRows = (stageRows) => {
    const byStage = new Map();

    for (const row of stageRows) {
      const key = stageRowKey(row);

      if (!key) continue;

      const existing = byStage.get(key);

      if (!existing || stageRowPriority(row) > stageRowPriority(existing)) {
        byStage.set(key, row);
      }
    }

    return [...byStage.values()];
  };

  const stageSortForRow = (row) => {
    const list = state.lists.find((item) => item.id === row.listId);

    return stageSort(list || { stage: stageNameForRow(row, list), scanner: row.stageProfile || "" });
  };

  const allStageRowsForGroup = (group, changedStageRows) => {
    const byStage = new Map();

    const addRow = (row) => {
      const key = stageRowKey(row);

      if (!key || byStage.has(key)) return;

      byStage.set(key, row);
    };

    changedStageRows.forEach(addRow);

    state.lists
      .filter((list) => String(list.deliveryDate || "") === String(group.deliveryDate || ""))
      .forEach((list) => {
        addRow({
          listId: list.id,
          stage: list.stage,
          stageProfile: list.scanner,
          totalQty: list.totalQty || 0,
          changedLineCount: 0,
          changedPieceQty: 0,
          addedPieceQty: 0,
          created: false,
        });
      });

    return [...byStage.values()].sort((a, b) => {
      const sortDiff = stageSortForRow(a) - stageSortForRow(b);
      if (sortDiff) return sortDiff;

      const listA = state.lists.find((item) => item.id === a.listId);
      const listB = state.lists.find((item) => item.id === b.listId);

      return stageNameForRow(a, listA).localeCompare(stageNameForRow(b, listB));
    });
  };

  const groups = new Map();

  for (const entry of rows) {
    const groupKey = entry.deliveryDate || entry.sourceName || entry.fileName || entry.importedAt || "unknown";

    if (!groups.has(groupKey)) {
      groups.set(groupKey, {
        deliveryDate: entry.deliveryDate || "",
        sourceName: entry.sourceName || entry.fileName || "Imported delivery list",
        importedAt: entry.importedAt || entry.updatedAt || entry.createdAt || "",
        entries: [],
        stageRows: [],
        printableIds: new Set(),
      });
    }

    const group = groups.get(groupKey);
    const entryStageRows = stageRowsForEntry(entry);

    group.entries.push(entry);
    group.stageRows.push(...entryStageRows);

    for (const row of entryStageRows) {
      if (row.listId) {
        group.printableIds.add(row.listId);
      }
    }

    if (entry.importedAt || entry.updatedAt || entry.createdAt) {
      group.importedAt = entry.importedAt || entry.updatedAt || entry.createdAt;
    }
  }

  return `
    <div class="admin-import-date-list">
      ${[...groups.values()]
        .map((group, index) => {
          const changedStageRows = collapseDuplicateStageRows(group.stageRows.filter(hasStageChanges));
          const allStageRows = allStageRowsForGroup(group, changedStageRows);
          const stagingRows = allStageRows.filter((row) => {
            const list = state.lists.find((item) => item.id === row.listId);
            return isStagingRow(row, list);
          });

          const changedStagingRows = changedStageRows.filter((row) => {
            const list = state.lists.find((item) => item.id === row.listId);
            return isStagingRow(row, list);
          });

          const stagingOriginalQty = stagingRows.reduce((sum, row) => {
            const list = state.lists.find((item) => item.id === row.listId);
            return sum + originalQtyForRow(row, list);
          }, 0);

          const stagingChangedQty = changedStagingRows.reduce((sum, row) => {
            const list = state.lists.find((item) => item.id === row.listId);
            return sum + changedQtyForRow(row, list);
          }, 0);

          const stagingUpdatedQty = stagingRows.reduce((sum, row) => {
            const list = state.lists.find((item) => item.id === row.listId);
            return sum + updatedQtyForRow(row, list);
          }, 0);

          const newStageRows = changedStageRows.filter((row) => {
            const list = state.lists.find((item) => item.id === row.listId);
            return isNewStageRow(row, list);
          });

          const updatedStageRows = changedStageRows.filter((row) => {
            const list = state.lists.find((item) => item.id === row.listId);
            return !isNewStageRow(row, list);
          });

          const hasNewStages = newStageRows.length > 0;
          const hasUpdatedStages = updatedStageRows.length > 0;
          const isBrandNewDeliveryList = hasNewStages && !hasUpdatedStages;

          const newPrintableIds = [...new Set(newStageRows.map((row) => row.listId).filter(Boolean))];
          const updatedPrintableIds = [...new Set(updatedStageRows.map((row) => row.listId).filter(Boolean))];
          const printableIds = [...new Set([...updatedPrintableIds, ...newPrintableIds])];
          const printButtonLabel = isBrandNewDeliveryList
            ? "Print / Export New Delivery List"
            : hasNewStages && hasUpdatedStages
              ? "Print / Export Changed Stages"
              : "Print / Export Changed Stages";
          const hasAnyChanges = hasNewStages || hasUpdatedStages;
          const groupClass = !hasAnyChanges
            ? "is-no-update-batch"
            : isBrandNewDeliveryList
              ? "is-new-delivery-list"
              : hasNewStages && hasUpdatedStages
                ? "is-mixed-batch"
                : "is-updated-batch";
          const importedText = group.importedAt ? `Updated at: ${formatDateTime(group.importedAt)}` : "Updated at: --";
          const sourceFileText = group.sourceName ? `File: ${group.sourceName}` : "";
          const groupStatusHtml = hasAnyChanges
            ? `
              ${hasUpdatedStages ? `<span class="import-status-pill updated">Updated</span>` : ""}
              ${isBrandNewDeliveryList ? `<span class="import-status-pill new">New</span>` : ""}
              ${hasNewStages && hasUpdatedStages ? `<span class="import-status-pill new-stage">New Stage</span>` : ""}
            `
            : `<span class="import-status-pill no-change">No Updates</span>`;

          const stageHtml = allStageRows.length
            ? allStageRows
                .map((row) => {
                  const list = state.lists.find((item) => item.id === row.listId);
                  const stageName = stageNameForRow(row, list);
                  const originalQty = originalQtyForRow(row, list);
                  const changedQty = changedQtyForRow(row, list);
                  const updatedQty = updatedQtyForRow(row, list);
                  const rowHasChanges = hasStageChanges(row);
                  const rowIsNew = rowHasChanges && isNewStageRow(row, list);
                  const stageCategoryClass = `stage-row-${stageCategoryForImportRow(row, list)}`;
                  const rowChangeClass = rowIsNew ? "is-new-row" : rowHasChanges ? "is-updated-row" : "is-unchanged-row";
                  const rowClass = `${stageCategoryClass} ${rowChangeClass}`;
                  const kindLabel = rowIsNew ? "New Stage" : rowHasChanges ? "Updated" : "No Updates";
                  const kindClass = rowIsNew ? "new-stage" : rowHasChanges ? "updated" : "no-change";

                  return `
                    <tr class="${rowClass}">
                      <td><span class="stage-pill-admin">${escapeHtml(stageName)}</span></td>
                      <td><span class="qty-before">${escapeHtml(originalQty)} pcs</span></td>
                      <td><span class="qty-change ${rowHasChanges ? "" : "is-zero"}">${rowHasChanges ? `+${escapeHtml(changedQty)} pcs` : "0 pcs"}</span></td>
                      <td><strong>${escapeHtml(updatedQty)} pcs</strong></td>
                      <td><span class="import-status-pill ${kindClass}">${escapeHtml(kindLabel)}</span></td>
                      <td>
                        ${
                          row.listId
                            ? `<button
                                type="button"
                                class="admin-import-icon-button"
                                data-print-lists="${escapeHtml(row.listId)}"
                                data-print-date="${escapeHtml(group.deliveryDate)}"
                                data-print-updated-only="${rowHasChanges && !rowIsNew ? "1" : ""}"
                                aria-label="${rowIsNew ? "Print / Export New Stage" : rowHasChanges ? "Print / Export Stage" : "Print / Export Stage"}"
                                title="${rowIsNew ? "Print / Export New Stage" : rowHasChanges ? "Print / Export Stage" : "Print / Export Stage"}"
                              ><span class="admin-import-print-icon" aria-hidden="true"></span></button>`
                            : ""
                        }
                      </td>
                    </tr>
                  `;
                })
                .join("")
            : `
              <tr>
                <td colspan="6">No stages were found for this delivery date.</td>
              </tr>
            `;

          return `
            <details class="admin-import-date-group ${groupClass}">
<summary class="admin-import-date-summary">
  <span class="admin-import-expand-arrow" aria-hidden="true"></span>
  <span class="admin-import-date-main">
    <span class="admin-import-date-title">
      <strong>${escapeHtml(formatDisplayDate(group.deliveryDate))}</strong>
      <span class="admin-import-status-pills">
        ${groupStatusHtml}
      </span>
    </span>

    <span class="admin-import-date-meta">
      <small class="admin-import-updated-at">${escapeHtml(importedText)}</small>
      ${sourceFileText ? `<small class="admin-import-source-file">${escapeHtml(sourceFileText)}</small>` : ""}
    </span>
  </span>

  <span class="admin-import-date-qty">
    <span class="admin-import-qty-flow">
      <span class="qty-before">${escapeHtml(stagingOriginalQty)} pcs</span>
      <span class="qty-change ${stagingChangedQty ? "" : "is-zero"}">${stagingChangedQty ? `+${escapeHtml(stagingChangedQty)} pcs` : "0 pcs"}</span>
      <strong>${escapeHtml(stagingUpdatedQty)} pcs</strong>
    </span>
  </span>

  ${
    printableIds.length
      ? `<button
          type="button"
          class="admin-import-icon-button"
          data-print-lists="${escapeHtml(printableIds.join(","))}"
          data-print-date="${escapeHtml(group.deliveryDate)}"
          data-print-updated-only="${hasUpdatedStages && !isBrandNewDeliveryList ? "1" : ""}"
          aria-label="${escapeHtml(printButtonLabel)}"
          title="${escapeHtml(printButtonLabel)}"
        ><span class="admin-import-print-icon" aria-hidden="true"></span></button>`
      : ""
  }
</summary>

              <div class="admin-import-stage-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Stage</th>
                      <th>Original Qty</th>
                      <th>Changed Qty</th>
                      <th>Updated Qty</th>
                      <th>Status</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    ${stageHtml}
                  </tbody>
                </table>
              </div>
            </details>
          `;
        })
        .join("")}
    </div>
  `;
}

function renderAdminDeleteControls() {
  if (!els.deleteDateSelect || !els.deleteListSelect) return;
  const groups = listsByDeliveryDate();
  const selectedDate = els.deleteDateSelect.value || groups[0]?.date || "";
  els.deleteDateSelect.innerHTML = groups
    .map((group) => `<option value="${escapeHtml(group.date)}">${escapeHtml(formatDisplayDate(group.date))}</option>`)
    .join("");
  els.deleteDateSelect.value = groups.some((group) => group.date === selectedDate) ? selectedDate : groups[0]?.date || "";
  const lists = groups.find((group) => group.date === els.deleteDateSelect.value)?.lists || [];
  const selectedList = els.deleteListSelect.value || lists[0]?.id || "";
  els.deleteListSelect.innerHTML = lists
    .map((list) => `<option value="${escapeHtml(list.id)}">${escapeHtml(list.stage)} - ${escapeHtml(list.scanner)}</option>`)
    .join("");
  els.deleteListSelect.value = lists.some((list) => list.id === selectedList) ? selectedList : lists[0]?.id || "";
}

function renderAdminResetControls() {
  if (!els.resetListSelect) return;
  const selected = els.resetListSelect.value || state.activeListId || state.lists[0]?.id || "";
  els.resetListSelect.innerHTML = state.lists
    .map((list) => `<option value="${escapeHtml(list.id)}">${escapeHtml(formatDisplayDate(list.deliveryDate))} - ${escapeHtml(list.stage)} - ${escapeHtml(list.scanner)}</option>`)
    .join("");
  els.resetListSelect.value = state.lists.some((list) => list.id === selected) ? selected : state.lists[0]?.id || "";
}

async function resetSelectedAdminScans() {
  const listId = els.resetListSelect?.value || "";
  await resetAdminScansForList(listId);
}

async function resetAdminScansForList(listId) {
  const list = state.lists.find((item) => item.id === listId);
  if (!list) return;
  const confirmed = await confirmWebAppAction({
    title: "Reset scans?",
    message: `Reset all scan quantities and scan history for <strong>${escapeHtml(list.label)}</strong>.`,
    details: "This keeps the delivery-list rows but returns this stage to zero scanned quantity.",
    confirmLabel: "Reset scans",
    requiredText: "RESET",
    requiredTextLabel: "Type RESET to reset this delivery-list stage",
  });

  if (!confirmed) {
    if (els.resetScansStatus) els.resetScansStatus.innerHTML = `<strong>Reset cancelled</strong><span>No scan data was changed.</span>`;
    return;
  }
  const payload = await fetchJson("/api/reset", {
    method: "POST",
    body: JSON.stringify({ listId, confirmText: "RESET", ...requestContext() }),
  });
  if (payload.meta?.id === state.activeListId) applyBackendPayload(payload);
  await loadDeliveryLists(state.activeListId);
  if (els.resetScansStatus) els.resetScansStatus.innerHTML = `<strong>Scans reset</strong><span>${escapeHtml(list.label)} is back to zero scanned quantity.</span>`;
  renderAdminDeliveryLists();
}

async function resetAdminScansForDate(deliveryDate) {
  const lists = state.lists.filter((list) => list.deliveryDate === deliveryDate);

  if (!lists.length) return;

  const confirmed = await confirmWebAppAction({
    title: "Reset every stage for this date?",
    message: `Reset all scan quantities and scan history for every stage on <strong>${escapeHtml(formatDisplayDate(deliveryDate))}</strong>.`,
    details: `${lists.length} stage${lists.length === 1 ? "" : "s"} will be reset. Delivery-list rows will stay in place.`,
    confirmLabel: "Reset all stages",
    requiredText: "RESET",
    requiredTextLabel: "Type RESET to reset every stage for this date",
  });

  if (!confirmed) {
    if (els.resetScansStatus) {
      els.resetScansStatus.innerHTML = `<strong>Reset cancelled</strong><span>No scan data was changed.</span>`;
    }

    return;
  }

  for (const list of lists) {
    await fetchJson("/api/reset", {
      method: "POST",
      body: JSON.stringify({ listId: list.id, confirmText: "RESET", ...requestContext() }),
    });
  }

  await loadDeliveryLists(state.activeListId);
  if (state.activeListId && lists.some((list) => list.id === state.activeListId)) {
    await activateList(state.activeListId, false);
  }
  await refreshAdminPage();

  renderHome();
  renderScanPage();
  renderDeliveryListSelect();
  renderAdminDeleteControls();
  renderAdminResetControls();
  renderAdminDeliveryLists();

  await refreshAdminDeliveryListModal();

  if (els.resetScansStatus) {
    els.resetScansStatus.innerHTML = `<strong>Scans reset</strong><span>Every stage for ${escapeHtml(formatDisplayDate(deliveryDate))} is back to zero scanned quantity.</span>`;
  }
}

async function deleteAdminDeliveryDateByDate(deliveryDate) {
  if (!deliveryDate) return;

  const lists = state.lists.filter((list) => list.deliveryDate === deliveryDate);
  const confirmed = await confirmWebAppAction({
    title: "Delete every stage for this date?",
    message: `Delete every delivery-list stage for <strong>${escapeHtml(formatDisplayDate(deliveryDate))}</strong>.`,
    details: `${lists.length || "All matching"} stage${lists.length === 1 ? "" : "s"} will be removed. This cannot be undone from the web app.`,
    confirmLabel: "Delete date",
    requiredText: "DELETE",
    requiredTextLabel: "Type DELETE to remove every stage for this date",
  });

  if (!confirmed) return;

  const result = await fetchJson("/api/admin/delete-date", {
    method: "POST",
    body: JSON.stringify({ deliveryDate, confirmText: "DELETE", ...requestContext() }),
  });

  state.lists = result.lists || [];

  if (!state.lists.some((list) => list.id === state.activeListId)) {
    state.activeListId = state.lists[0]?.id || "";

    if (state.activeListId) {
      await activateList(state.activeListId, false);
    } else {
      state.meta = null;
      state.items = [];
      state.recent = [];
      state.errors = [];
      state.lastScan = null;
    }
  }

  await loadDeliveryLists(state.activeListId);
  await refreshAdminPage();

  renderHome();
  renderScanPage();
  renderDeliveryListSelect();
  renderAdminDeleteControls();
  renderAdminResetControls();
  renderAdminDeliveryLists();

  await refreshAdminDeliveryListModal();

  if (els.deleteListStatus) {
    els.deleteListStatus.innerHTML = `<strong>Deleted date</strong><span>${escapeHtml(result.deletedCount || 0)} stages removed.</span>`;
  }
}

async function deleteSelectedDeliveryList(deleteDate = false) {
  if (!state.backend) return;

  const deliveryDate = els.deleteDateSelect?.value || "";
  const listId = els.deleteListSelect?.value || "";

  if (deleteDate) {
    if (!deliveryDate) return;

    const lists = state.lists.filter((list) => list.deliveryDate === deliveryDate);
    const confirmed = await confirmWebAppAction({
      title: "Delete every stage for this date?",
      message: `Delete every delivery-list stage for <strong>${escapeHtml(formatDisplayDate(deliveryDate))}</strong>.`,
      details: `${lists.length || "All matching"} stage${lists.length === 1 ? "" : "s"} will be removed. This cannot be undone from the web app.`,
      confirmLabel: "Delete date",
      requiredText: "DELETE",
      requiredTextLabel: "Type DELETE to remove every stage for this date",
    });

    if (!confirmed) return;

    const result = await fetchJson("/api/admin/delete-date", {
      method: "POST",
      body: JSON.stringify({ deliveryDate, confirmText: "DELETE", ...requestContext() }),
    });
    state.lists = result.lists || [];
    if (els.deleteListStatus) els.deleteListStatus.innerHTML = `<strong>Deleted date</strong><span>${escapeHtml(result.deletedCount || 0)} stages removed.</span>`;
  } else {
    const list = state.lists.find((item) => item.id === listId);
    if (!list) return;

    const confirmed = await confirmWebAppAction({
      title: "Delete this delivery-list stage?",
      message: `Delete <strong>${escapeHtml(list.label)}</strong>.`,
      details: "This removes that stage and its rows from the active delivery-list set.",
      confirmLabel: "Delete stage",
      requiredText: "DELETE",
      requiredTextLabel: "Type DELETE to remove this delivery-list stage",
    });

    if (!confirmed) return;

    const result = await fetchJson("/api/admin/delete-list", {
      method: "POST",
      body: JSON.stringify({ listId, confirmText: "DELETE", ...requestContext() }),
    });
    state.lists = result.lists || [];
    if (els.deleteListStatus) els.deleteListStatus.innerHTML = `<strong>Deleted stage</strong><span>${escapeHtml(result.deletedListId || listId)} removed.</span>`;
  }

  if (!state.lists.some((list) => list.id === state.activeListId)) {
    state.activeListId = state.lists[0]?.id || "";

    if (state.activeListId) {
      await activateList(state.activeListId, false);
    } else {
      state.meta = null;
      state.items = [];
      state.recent = [];
      state.errors = [];
      state.lastScan = null;
    }
  }

  await loadDeliveryLists(state.activeListId);
  await refreshAdminPage();

  renderHome();
  renderScanPage();
  renderDeliveryListSelect();
  renderAdminDeleteControls();
  renderAdminDeliveryLists();
}

async function deleteAdminDeliveryListById(listId) {
  const list = state.lists.find((item) => item.id === listId);
  if (!list) return;

  const confirmed = await confirmWebAppAction({
    title: "Delete this delivery-list stage?",
    message: `Delete <strong>${escapeHtml(list.label)}</strong>.`,
    details: "This removes that stage and its rows from the active delivery-list set.",
    confirmLabel: "Delete stage",
    requiredText: "DELETE",
    requiredTextLabel: "Type DELETE to remove this delivery-list stage",
  });

  if (!confirmed) return;

  const result = await fetchJson("/api/admin/delete-list", {
    method: "POST",
    body: JSON.stringify({ listId, confirmText: "DELETE", ...requestContext() }),
  });
  state.lists = result.lists || [];
  if (!state.lists.some((item) => item.id === state.activeListId)) {
    state.activeListId = state.lists[0]?.id || "";

    if (state.activeListId) {
      await activateList(state.activeListId, false);
    } else {
      state.meta = null;
      state.items = [];
      state.recent = [];
      state.errors = [];
      state.lastScan = null;
    }
  }

  await loadDeliveryLists(state.activeListId);
  await refreshAdminPage();

  renderHome();
  renderScanPage();
  renderDeliveryListSelect();
  renderAdminDeleteControls();
  renderAdminDeliveryLists();
  openAdminModal("deliveryLists");
}

function userInitials(user) {
  const display = String(user?.displayName || user?.username || "?").trim();

  const parts = display
    .split(/\s+/)
    .map((part) => part[0])
    .filter(Boolean);

  if (parts.length >= 2) return `${parts[0]}${parts[1]}`.toUpperCase();

  return display.slice(0, 2).toUpperCase() || "?";
}

function userAccentClass(user) {
  const text = String(user?.username || user?.displayName || "").toLowerCase();

  if (/admin/.test(text)) return "accent-admin";
  if (/lead|supervisor/.test(text)) return "accent-lead";
  if (/manager/.test(text)) return "accent-manager";
  if (/operator/.test(text)) return "accent-operator";
  if (/trail|it/.test(text)) return "accent-trail";

  return "accent-default";
}

function userActionButtonHtml({ className = "", attr = "", label = "", icon = "", disabled = false }) {
  const safeLabel = escapeHtml(label);

  return `
    <button
      type="button"
      class="user-icon-action ${className}"
      ${attr}
      ${disabled ? "disabled" : ""}
      aria-label="${safeLabel}"
      title="${safeLabel}"
    >
      <span class="user-action-icon ${escapeHtml(icon)}" aria-hidden="true"></span>
    </button>
  `;
}

function generateTemporaryPassword(length = 12) {
  const alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%";
  const values = new Uint32Array(length);

  if (window.crypto?.getRandomValues) {
    window.crypto.getRandomValues(values);
  }

  return Array.from({ length }, (_, index) => {
    const value = values[index] || Math.floor(Math.random() * alphabet.length);
    return alphabet[value % alphabet.length];
  }).join("");
}

async function refreshAdminUsersUi() {
  const usersModalOpen = Boolean(els.adminModal && !els.adminModal.hidden && els.adminModalBody?.querySelector(".users-modal-shell"));

  await refreshAdminPage();

  if (usersModalOpen && els.adminModalBody) {
    els.adminModalBody.innerHTML = adminModalContent("users");
  }
}

function confirmWebAppAction({
  title,
  message,
  details = "",
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  danger = true,
  requiredText = "",
  requiredTextLabel = "Type the confirmation word to continue",
} = {}) {
  return new Promise((resolve) => {
    const existingDialog = document.querySelector(".action-confirm-backdrop");
    if (existingDialog) existingDialog.remove();

    const dialog = document.createElement("div");
    const requiredValue = String(requiredText || "").trim();
    const requiresTypedConfirmation = Boolean(requiredValue);
    let keyHandler = () => {};

    dialog.className = "action-confirm-backdrop";
    dialog.innerHTML = `
      <section class="action-confirm-dialog ${danger ? "is-danger" : ""}" role="dialog" aria-modal="true" aria-labelledby="actionConfirmTitle">
        <button type="button" class="action-confirm-close" data-action-confirm-cancel aria-label="Close confirmation">&times;</button>

        <span class="action-confirm-icon" aria-hidden="true"></span>

        <div class="action-confirm-copy">
          <h2 id="actionConfirmTitle">${escapeHtml(title || "Confirm action")}</h2>
          <p>${message || "Are you sure you want to continue?"}</p>
          ${details ? `<small>${escapeHtml(details)}</small>` : ""}
        </div>

        ${requiresTypedConfirmation ? `
          <label class="action-confirm-typed-field">
            <span>${escapeHtml(requiredTextLabel)}</span>
            <b>${escapeHtml(requiredValue)}</b>
            <input type="text" autocomplete="off" spellcheck="false" data-action-confirm-input aria-label="Type ${escapeHtml(requiredValue)} to confirm">
          </label>
        ` : ""}

        <div class="action-confirm-actions">
          <button type="button" class="action-confirm-cancel" data-action-confirm-cancel>${escapeHtml(cancelLabel)}</button>
          <button type="button" class="action-confirm-confirm" data-action-confirm-confirm ${requiresTypedConfirmation ? "disabled" : ""}>${escapeHtml(confirmLabel)}</button>
        </div>
      </section>
    `;

    const input = dialog.querySelector("[data-action-confirm-input]");
    const confirmButton = dialog.querySelector("[data-action-confirm-confirm]");

    const typedConfirmationMatches = () => !requiresTypedConfirmation || String(input?.value || "").trim() === requiredValue;

    const syncTypedConfirmation = () => {
      if (!confirmButton) return;
      confirmButton.disabled = !typedConfirmationMatches();
    };

    const close = (confirmed) => {
      document.removeEventListener("keydown", keyHandler);
      dialog.remove();
      document.body.classList.remove("modal-scroll-locked");
      updateModalScrollLock();
      resolve(Boolean(confirmed));
    };

    input?.addEventListener("input", syncTypedConfirmation);
    input?.addEventListener("keydown", (event) => {
      if (event.key !== "Enter") return;
      event.preventDefault();
      if (typedConfirmationMatches()) close(true);
    });

    dialog.addEventListener("click", (event) => {
      if (event.target === dialog || event.target.closest("[data-action-confirm-cancel]")) {
        close(false);
        return;
      }

      if (event.target.closest("[data-action-confirm-confirm]")) {
        if (!typedConfirmationMatches()) {
          input?.focus();
          return;
        }
        close(true);
      }
    });

    keyHandler = (event) => {
      if (event.key !== "Escape") return;
      close(false);
    };

    document.addEventListener("keydown", keyHandler);
    document.body.appendChild(dialog);
    document.body.classList.add("modal-scroll-locked");
    syncTypedConfirmation();
    (input || dialog.querySelector("[data-action-confirm-cancel]"))?.focus();
  });
}

function confirmDeactivateUser(username) {
  return new Promise((resolve) => {
    const existingDialog = document.querySelector(".user-deactivate-backdrop");
    if (existingDialog) existingDialog.remove();

    const dialog = document.createElement("div");
    let keyHandler = () => {};

    dialog.className = "user-deactivate-backdrop";
    dialog.innerHTML = `
      <section class="user-deactivate-dialog" role="dialog" aria-modal="true" aria-labelledby="deactivateUserTitle">
        <button type="button" class="user-deactivate-close" data-user-deactivate-cancel aria-label="Close deactivate user confirmation">&times;</button>

        <span class="user-deactivate-icon" aria-hidden="true"></span>

        <div class="user-deactivate-copy">
          <h2 id="deactivateUserTitle">Deactivate user?</h2>
          <p>Deactivate <strong>${escapeHtml(username)}</strong>? This keeps the profile and history, but the user will no longer be able to sign in until reactivated.</p>
        </div>

        <div class="user-deactivate-actions">
          <button type="button" class="user-deactivate-cancel" data-user-deactivate-cancel>Cancel</button>
          <button type="button" class="user-deactivate-confirm" data-user-deactivate-confirm>Deactivate User</button>
        </div>
      </section>
    `;

    const close = (confirmed) => {
      document.removeEventListener("keydown", keyHandler);
      dialog.remove();
      document.body.classList.remove("modal-scroll-locked");
      resolve(Boolean(confirmed));
    };

    dialog.addEventListener("click", (event) => {
      if (event.target === dialog || event.target.closest("[data-user-deactivate-cancel]")) {
        close(false);
        return;
      }

      if (event.target.closest("[data-user-deactivate-confirm]")) {
        close(true);
      }
    });

    keyHandler = (event) => {
      if (event.key !== "Escape") return;
      close(false);
    };

    document.addEventListener("keydown", keyHandler);
    document.body.appendChild(dialog);
    document.body.classList.add("modal-scroll-locked");
    dialog.querySelector("[data-user-deactivate-cancel]")?.focus();
  });
}

function renderAdminUsers() {
  if (!els.adminUsers) return;

  const previewLimit = 6;
  const totalUsers = state.adminUsers.length;
  const hiddenCount = Math.max(totalUsers - previewLimit, 0);

  els.adminUsers.innerHTML = `
    ${renderAdminUsersTable(false, previewLimit)}
    ${
      hiddenCount
        ? `<button type="button" class="link-button admin-preview-more-button" data-admin-modal="users">View ${escapeHtml(hiddenCount)} more user${hiddenCount === 1 ? "" : "s"}</button>`
        : ""
    }
  `;
}

function renderAdminUsersTable(editable = false, limit = 5) {
  const users = state.adminUsers.slice(0, limit);

  if (!users.length) return `<div class="admin-empty">No users loaded.</div>`;

  const activeSessionUsers = new Set((state.activeSessions || []).map((session) => String(session.username || "").toLowerCase()));

  if (!editable) {
    return `
      <div class="admin-user-preview-list">
        ${users
          .map((user) => {
            const loggedIn = activeSessionUsers.has(String(user.username || "").toLowerCase());

            return `
              <article class="admin-user-preview-row">
                <span class="user-avatar ${escapeHtml(userAccentClass(user))}">${escapeHtml(userInitials(user))}</span>

                <div>
                  <strong>${escapeHtml(user.displayName)}</strong>
                  <span>${escapeHtml(user.email || user.username)} · ${escapeHtml((user.roles || []).join(", ") || "No role")}</span>
                  <small>${escapeHtml(user.username)}${user.email ? ` · ${escapeHtml(user.email)}` : ""}</small>
                  <small>${escapeHtml(permissionSummaryForUser(user))}</small>
                  <small>Station: ${escapeHtml(userAssignedStation(user) || "No assigned station")}</small>
                </div>

                <span class="user-status-stack">
                  <span class="user-status-pill ${user.active ? "active" : "inactive"}">${user.active ? "Active profile" : "Inactive profile"}</span>
                  <span class="user-session-pill ${loggedIn ? "is-online" : "is-offline"}">${loggedIn ? "Signed in" : "Logged out"}</span>
                </span>
              </article>
            `;
          })
          .join("")}
      </div>
    `;
  }

  return `
    <div class="users-table">
      <div class="users-table-head">
        <span>User</span>
        <span>Email</span>
        <span>Role</span>
        <span>Station</span>
        <span>Permissions / Notes</span>
        <span>Password</span>
        <span>Status</span>
        <span>Actions</span>
      </div>

      <div class="users-table-body">
        ${users
          .map((user) => {
            const active = Boolean(user.active);
            const username = String(user.username || "");
            const roles = user.roles || [];
            const stageAccess = user.stageAccess || [];
            const assignedStations = userAssignedStations(user);
            const assignedStation = assignedStations[0] || "";
            const loggedIn = activeSessionUsers.has(username.toLowerCase());

            return `
              <article class="user-admin-row ${active ? "is-active-user" : "is-inactive-user"}">
                <div class="user-admin-main">
                  <span class="user-avatar ${escapeHtml(userAccentClass(user))}">${escapeHtml(userInitials(user))}</span>

                  <span class="user-admin-name">
                    <strong>${escapeHtml(user.displayName || username)}</strong>
                    <small>${escapeHtml(username)}</small>
                  </span>
                </div>

                <label class="user-admin-email user-admin-email-edit">
                  <span>BFS sign-in email</span>
                  <input data-user-email="${escapeHtml(username)}" type="email" autocomplete="off" value="${escapeHtml(user.email || "")}" placeholder="name@barefootandcompany.com">
                </label>

                <div class="user-admin-role">
                  ${
                    hasPermission("manage_roles")
                      ? `
                        <select data-user-role-select="${escapeHtml(username)}">
                          ${ROLE_OPTIONS.map((role) => `<option value="${escapeHtml(role)}" ${roles.includes(role) ? "selected" : ""}>${escapeHtml(role)}</option>`).join("")}
                        </select>
                      `
                      : `<span>${escapeHtml(roles.join(", ") || "No role")}</span>`
                  }
                </div>

                <div class="user-admin-station user-admin-station-list">
                  ${
                    hasPermission("manage_roles")
                      ? `
                        <div class="station-assignment-list" data-user-station-list="${escapeHtml(username)}">
                          ${state.stations
                            .map((station) => `
                              <label class="station-assignment-option">
                                <input type="checkbox" value="${escapeHtml(station)}" ${assignedStations.includes(station) ? "checked" : ""}>
                                <span>${escapeHtml(station)}</span>
                              </label>
                            `)
                            .join("")}
                        </div>
                      `
                      : `<span>${escapeHtml(assignedStations.join(", ") || "No assigned station")}</span>`
                  }
                </div>

                <div class="user-admin-permissions">
                  <strong>${escapeHtml(permissionSummaryForUser(user))}</strong>
                  <small>Stages: ${escapeHtml(stageAccess.join(", ") || "No stage access")}</small>
                </div>

                <div class="user-admin-password">
                  ${
                    hasPermission("update_user_passwords")
                      ? `
                        <div class="password-reset-row polished">
  <input data-user-password="${escapeHtml(username)}" type="password" placeholder="New password">
  ${userActionButtonHtml({
    className: "secondary",
    attr: `data-generate-user-password="${escapeHtml(username)}"`,
    label: "Generate temporary password",
    icon: "icon-key",
  })}
  ${userActionButtonHtml({
    className: "secondary",
    attr: `data-toggle-password="${escapeHtml(username)}"`,
    label: "Show password",
    icon: "icon-eye",
  })}
  ${userActionButtonHtml({
    className: "primary",
    attr: `data-update-user-password="${escapeHtml(username)}"`,
    label: "Save password",
    icon: "icon-save-user",
  })}
</div>
<small class="password-note">
  Existing password cannot be viewed.<br>
  Generate or enter a new one, then save it.
</small>
                      `
                      : `<span class="protected-pill">Protected</span>`
                  }
                </div>

                <div class="user-admin-status">
                  <span class="user-status-pill ${active ? "active" : "inactive"}">
                    <i></i>
                    ${active ? "Active profile" : "Inactive profile"}
                  </span>

                  <span class="user-session-pill ${loggedIn ? "is-online" : "is-offline"}">${loggedIn ? "Signed in" : "Logged out"}</span>
                </div>

                <div class="user-admin-actions">
                  ${
                    hasPermission("manage_roles")
                      ? userActionButtonHtml({
                          className: "secondary",
                          attr: `data-update-user-role="${escapeHtml(username)}"`,
                          label: "Save role",
                          icon: "icon-shield",
                        })
                      : ""
                  }

                  ${
                    active && hasPermission("deactivate_users")
                      ? userActionButtonHtml({
                          className: "danger",
                          attr: `data-deactivate-user="${escapeHtml(username)}"`,
                          label: "Deactivate",
                          icon: "icon-power",
                        })
                      : ""
                  }

                  ${
                    !active && hasPermission("reactivate_users")
                      ? userActionButtonHtml({
                          className: "success",
                          attr: `data-reactivate-user="${escapeHtml(username)}"`,
                          label: "Activate",
                          icon: "icon-power",
                        })
                      : ""
                  }

                  ${
                    hasPermission("manage_users")
                      ? userActionButtonHtml({
                          className: "danger",
                          attr: `data-delete-user="${escapeHtml(username)}"`,
                          label: "Delete user",
                          icon: "icon-trash",
                        })
                      : ""
                  }
                </div>
              </article>
            `;
          })
          .join("")}
      </div>
    </div>
  `;
}

function renderAdminStations() {
  if (!els.adminStations) return;
  els.adminStations.innerHTML = renderAdminStationsList(false, state.stations.length || 1);
}

function renderAdminStationsList(editable = false, limit = 6) {
  return state.stations
    .slice(0, limit)
    .map((station) => `
      <div class="station-row">
        ${editable ? `<input data-station-name="${escapeHtml(station)}" type="text" value="${escapeHtml(station)}">` : `<strong>${escapeHtml(station)}</strong><span>Online</span>`}
        ${editable && hasPermission("manage_stations") ? `<button type="button" data-rename-station="${escapeHtml(station)}">Save</button>` : ""}
        ${editable && hasPermission("remove_stations") && !DEFAULT_STATIONS.includes(station) ? `<button type="button" data-remove-station="${escapeHtml(station)}">Remove</button>` : ""}
      </div>
    `)
    .join("") || `<div class="admin-empty">No stations loaded.</div>`;
}

function customerRouteValue(route) {
  const raw = String(route || "").trim().toUpperCase();

  if (["GRN", "GNV", "GREENVILLE"].includes(raw)) return "GNV";
  if (raw === "DTC" || raw === "DELIVER TO CUSTOMER") return "DTC";
  if (raw === "CPU" || raw === "CUSTOMER PICKUP") return "CPU";

  const clean = raw.replace(/[^A-Z0-9_-]+/g, "-").replace(/^-+|-+$/g, "");

  if (["GRN", "GNV", "GREENVILLE"].includes(clean)) return "GNV";
  if (clean === "DTC") return "DTC";
  if (clean === "CPU" || clean === "CUSTOMER-PICKUP") return "CPU";

  return clean || "CPU";
}

function customerRouteDisplay(route) {
  const clean = customerRouteValue(route);

  if (clean === "CPU") return "CPU / Customer Pickup";
  if (clean === "DTC") return "DTC / Deliver to Customer";
  if (clean === "GNV") return "GNV / Greenville";

  return clean;
}

function customerRouteDefaultAddress(route) {
  return CUSTOMER_ROUTE_DEFAULT_ADDRESSES[customerRouteValue(route)] || "";
}

function customerRouteAddress(rule = {}) {
  const savedAddress = String(rule.customerAddress || rule.address || "").trim();
  return savedAddress || customerRouteDefaultAddress(rule.route);
}

function customerRouteAddressStatus(rule = {}) {
  const route = customerRouteValue(rule.route);
  const address = customerRouteAddress(rule);

  if (route === "DTC" && !address) return "DTC address required";
  if (!address) return "No address on file";
  return address;
}

function customerRouteOptionList() {
  const customRoutes = [...new Set((state.adminCustomerRouteRules || [])
    .map((rule) => customerRouteValue(rule.route))
    .filter((route) => route && !CUSTOMER_ROUTE_OPTIONS.some((option) => option.value === route)))]
    .sort();

  return [...CUSTOMER_ROUTE_OPTIONS, ...customRoutes.map((route) => ({ value: route, label: route }))];
}

function customerRouteOptionsHtml(selectedRoute = "CPU") {
  const selected = customerRouteValue(selectedRoute);

  return customerRouteOptionList()
    .map((option) => `
      <option value="${escapeHtml(option.value)}" ${selected === option.value ? "selected" : ""}>${escapeHtml(option.label)}</option>
    `)
    .join("");
}

function customerRouteRuleRowsHtml(editable = false, limit = 0) {
  const rules = limit ? state.adminCustomerRouteRules.slice(0, limit) : state.adminCustomerRouteRules;

  if (!rules.length) {
    return `
      <div class="customer-route-empty">
        <strong>No customer route rules</strong>
        <span>Add customer-to-route rules here. Custom route codes create custom route stages during import.</span>
      </div>
    `;
  }

  return rules
    .map((rule) => {
      const routeCode = customerRouteValue(rule.route);
      const routeLabel = customerRouteDisplay(rule.route);
      const addressText = customerRouteAddressStatus(rule);
      const addressClass = routeCode === "DTC" && !customerRouteAddress(rule) ? " needs-address" : "";

      return `
        <article class="customer-route-rule-row ${editable ? "is-editable" : ""}">
          <div class="customer-route-row-fields">
            <label class="customer-route-customer-field">
              <span>Customer / match text</span>
              ${
                editable
                  ? `<input data-customer-route-pattern="${escapeHtml(rule.id)}" type="text" value="${escapeHtml(rule.customerPattern)}" aria-label="Customer route customer">`
                  : `<strong>${escapeHtml(rule.customerPattern)}</strong>`
              }
            </label>

            <label class="customer-route-route-field">
              <span>Route</span>
              ${
                editable
                  ? `<select data-customer-route-route="${escapeHtml(rule.id)}" aria-label="Customer route code">
                      ${customerRouteOptionsHtml(rule.route)}
                    </select>`
                  : `<em class="customer-route-badge">${escapeHtml(routeLabel)}</em>`
              }
            </label>

            <label class="customer-route-address-field${addressClass}">
              <span>Destination address</span>
              ${
                editable
                  ? `<input data-customer-route-address="${escapeHtml(rule.id)}" type="text" value="${escapeHtml(customerRouteAddress(rule))}" aria-label="Customer route destination address" placeholder="Required for DTC customers">`
                  : `<small>${escapeHtml(addressText)}</small>`
              }
            </label>
          </div>

          ${
            editable
              ? `<div class="customer-route-row-actions">
                  <button type="button" class="icon-only icon-save" data-save-customer-route-rule="${escapeHtml(rule.id)}" title="Save route" aria-label="Save route"></button>
                  <button type="button" class="icon-only icon-trash danger" data-remove-customer-route-rule="${escapeHtml(rule.id)}" title="Delete route" aria-label="Delete route"></button>
                </div>`
              : ""
          }
        </article>
      `;
    })
    .join("");
}

function customerRouteRulesModalHtml() {
  const ruleCount = state.adminCustomerRouteRules.length;

  return `
    <div class="customer-route-modal-shell customer-route-modern">
      <section class="customer-route-modal-intro">
        <div>
          <span>Customer Route Rules</span>
          <strong>Match customers to the route they should import into.</strong>
          <p>New custom routes become their own stage during import when a customer matches that route.</p>
        </div>
        <b>${escapeHtml(ruleCount)} active rule${ruleCount === 1 ? "" : "s"}</b>
      </section>

      <form id="customerRouteRuleFormModal" class="customer-route-modal-form">
        <label>
          <span>New customer / job match text</span>
          <input id="customerRoutePatternInputModal" type="text" autocomplete="off" placeholder="Example: Lowe's, CPU AIR, Greenville">
        </label>

        <label>
          <span>New route code</span>
          <input id="customerRouteSelectModal" type="text" list="customerRouteCodes" autocomplete="off" placeholder="CPU, DTC, GNV, or custom route">
        </label>

        <label class="customer-route-form-address">
          <span>Destination address</span>
          <input id="customerRouteAddressInputModal" type="text" autocomplete="off" placeholder="Required for DTC customers">
        </label>
        <datalist id="customerRouteCodes">
          ${customerRouteOptionsHtml("CPU")}
        </datalist>

        <div class="customer-route-modal-actions">
          <button id="customerRouteSubmitBtnModal" type="submit">Add Customer Route</button>
        </div>
      </form>

      <div class="customer-route-modal-list">
        <div class="customer-route-modal-list-heading">
          <strong>Current customer rules</strong>
          <span>Change the route dropdown, then use the save icon on that row.</span>
        </div>

        ${customerRouteRuleRowsHtml(true)}
      </div>
    </div>
  `;
}

function setCustomerRouteEditForm(ruleId = "") {
  const form = document.getElementById("customerRouteRuleFormModal");
  if (!form) return;

  const rule = state.adminCustomerRouteRules.find((item) => String(item.id) === String(ruleId)) || null;
  const idInput = document.getElementById("customerRouteEditIdModal");
  const originalPatternInput = document.getElementById("customerRouteEditOriginalPatternModal");
  const patternInput = document.getElementById("customerRoutePatternInputModal");
  const routeInput = document.getElementById("customerRouteSelectModal");
  const addressInput = document.getElementById("customerRouteAddressInputModal");
  const submitButton = document.getElementById("customerRouteSubmitBtnModal");

  if (idInput) idInput.value = rule?.id || "";
  if (originalPatternInput) originalPatternInput.value = rule?.customerPattern || "";
  if (patternInput) patternInput.value = rule?.customerPattern || "";
  if (routeInput) routeInput.value = customerRouteValue(rule?.route || "CPU");
  if (addressInput) addressInput.value = rule ? customerRouteAddress(rule) : "";
  if (submitButton) submitButton.textContent = rule ? "Save Rule" : "Add Rule";

  patternInput?.focus();
}

function renderCustomerRouteRules() {
  if (!els.customerRouteRules) return;

  const rules = state.adminCustomerRouteRules || [];
  const previewLimit = 6;
  const hiddenCount = Math.max(rules.length - previewLimit, 0);

  const routeStats = customerRouteOptionList()
    .map((option) => {
      const count = rules.filter((rule) => customerRouteValue(rule.route) === option.value).length;
      if (!count) return "";

      return `
        <div class="customer-route-stat">
          <small>${escapeHtml(option.label)}</small>
          <strong>${escapeHtml(count)}</strong>
        </div>
      `;
    })
    .filter(Boolean)
    .join("");

  els.customerRouteRules.innerHTML = `
    <div class="customer-route-overview">
      <div class="customer-route-overview-heading">
        <strong>${escapeHtml(rules.length)} customer route rule${rules.length === 1 ? "" : "s"}</strong>
        <span>Quick view of customers that will be split to special/custom stages during import.</span>
      </div>

      <div class="customer-route-stat-grid">
        ${routeStats || `<div class="customer-route-stat"><small>No route rules yet</small><strong>0</strong></div>`}
      </div>

      <div class="customer-route-preview-list">
        ${customerRouteRuleRowsHtml(false, previewLimit)}
      </div>

      ${
        hiddenCount
          ? `<button type="button" class="link-button customer-route-more-button" data-admin-modal="customerRoutes">View ${escapeHtml(hiddenCount)} more rule${hiddenCount === 1 ? "" : "s"}</button>`
          : ""
      }
    </div>
  `;
}

function refreshCustomerRouteModal() {
  renderCustomerRouteRules();
  if (els.adminModal && !els.adminModal.hidden && els.adminModal.dataset.kind === "customerRoutes" && els.adminModalBody) {
    els.adminModalBody.innerHTML = customerRouteRulesModalHtml();
  }
}


function renderBayScannerRuleOverview() {
  if (!els.bayScannerRuleOverview) return;
  const settings = state.bayScannerSettings || { manualRules: [], barcodeRules: [] };
  const manualRules = settings.manualRules || [];
  const barcodeRules = settings.barcodeRules || [];
  els.bayScannerRuleOverview.innerHTML = `
    <div><strong>${escapeHtml(manualRules.length)} remembered manual input${manualRules.length === 1 ? "" : "s"}</strong><span>Known phrases and odd labels that will not ask for confirmation.</span></div>
    <div><strong>${escapeHtml(barcodeRules.length)} accepted bay barcode rule${barcodeRules.length === 1 ? "" : "s"}</strong><span>Extra barcode formats accepted only on the Bay Map scanner.</span></div>
  `;
}

function autoAssignTypeOptions(selected = "") {
  const values = ["Standard", "Tall", "Oversize", "Mirror", "Framed Mirror", "CPU"];
  return values.map((value) => `<option value="${escapeHtml(value)}" ${value === selected ? "selected" : ""}>${escapeHtml(value)}</option>`).join("");
}

function renderBayAutoAssignOverview() {
  if (!els.bayAutoAssignOverview) return;
  const settings = state.bayAutoAssignSettings || {};
  const manualTypes = settings.manualAssignTypes || [];
  els.bayAutoAssignOverview.innerHTML = `
    <div><strong>Tall starts at ${escapeHtml(settings.tallMinInches ?? 60)}"</strong><span>Oversize starts at ${escapeHtml(settings.oversizeMinInches ?? 96)}".</span></div>
    <div><strong>${escapeHtml(manualTypes.length ? manualTypes.join(", ") : "None")} manual</strong><span>These categories will not be auto-preassigned.</span></div>
  `;
}

function bayAutoAssignerModalHtml() {
  const settings = state.bayAutoAssignSettings || {};
  const manual = new Set(settings.manualAssignTypes || []);
  const typeRows = [
    ["standardBayType", "Standard glass", settings.standardBayType || "Standard"],
    ["tallBayType", "Tall glass", settings.tallBayType || "Tall"],
    ["oversizeBayType", "Oversize glass", settings.oversizeBayType || "Oversize"],
    ["mirrorBayType", "Mirror", settings.mirrorBayType || "Mirror"],
    ["framedMirrorBayType", "Framed mirror", settings.framedMirrorBayType || "Framed Mirror"],
    ["cpuBayType", "CPU route", settings.cpuBayType || "CPU"],
  ];
  return `
    <div class="bay-auto-assigner-shell">
      <section class="customer-email-intro">
        <div>
          <strong>Indian Trail bay auto-assigner</strong>
          <p>Control how the system classifies glass for bay preassignment. Categories marked Manual Assign will be left for a user to place instead of being auto-assigned.</p>
        </div>
        <span class="email-smtp-badge is-live">Indian Trail</span>
      </section>

      <form id="bayAutoAssignerForm" class="bay-auto-assigner-form">
        <section class="bay-auto-card">
          <header><strong>Size thresholds</strong><span>Largest glass dimension controls Standard / Tall / Oversize.</span></header>
          <div class="bay-auto-grid">
            <label><span>Tall starts at inches</span><input id="bayAutoTallMin" type="number" min="1" step="0.01" value="${escapeHtml(settings.tallMinInches ?? 60)}"></label>
            <label><span>Oversize starts at inches</span><input id="bayAutoOversizeMin" type="number" min="1" step="0.01" value="${escapeHtml(settings.oversizeMinInches ?? 96)}"></label>
          </div>
        </section>

        <section class="bay-auto-card">
          <header><strong>Bay type mapping</strong><span>Match each classification to one of your bay groups/types.</span></header>
          <div class="bay-auto-type-list">
            ${typeRows.map(([field, label, selected]) => `
              <label>
                <span>${escapeHtml(label)}</span>
                <select data-bay-auto-field="${escapeHtml(field)}">${autoAssignTypeOptions(selected)}</select>
              </label>
            `).join("")}
          </div>
        </section>

        <section class="bay-auto-card">
          <header><strong>Manual assignment categories</strong><span>Checked categories will not be auto-preassigned. They will require manual placement.</span></header>
          <div class="bay-auto-manual-list">
            ${["Standard", "Tall", "Oversize", "Mirror", "Framed Mirror", "CPU"].map((type) => `
              <label><input type="checkbox" value="${escapeHtml(type)}" ${manual.has(type) ? "checked" : ""}> <span>${escapeHtml(type)}</span></label>
            `).join("")}
          </div>
        </section>

        <div class="bay-auto-actions">
          <button type="submit">Save Auto Assigner</button>
        </div>
      </form>
    </div>
  `;
}

async function refreshBayAutoAssigner(openModal = false) {
  const payload = await fetchJson("/api/admin/bay-auto-assigner");
  state.bayAutoAssignSettings = payload || state.bayAutoAssignSettings;
  renderBayAutoAssignOverview();
  if (openModal && els.adminModal && !els.adminModal.hidden && els.adminModal.dataset.kind === "bayAutoAssigner" && els.adminModalBody) {
    els.adminModalBody.innerHTML = bayAutoAssignerModalHtml();
  }
  return payload;
}

async function saveBayAutoAssignerSettings() {
  const payload = {
    tallMinInches: Number(document.getElementById("bayAutoTallMin")?.value || 60),
    oversizeMinInches: Number(document.getElementById("bayAutoOversizeMin")?.value || 96),
    manualAssignTypes: [...document.querySelectorAll(".bay-auto-manual-list input:checked")].map((input) => input.value),
  };
  document.querySelectorAll("[data-bay-auto-field]").forEach((select) => {
    payload[select.dataset.bayAutoField] = select.value;
  });
  const saved = await fetchJson("/api/admin/bay-auto-assigner", { method: "POST", body: JSON.stringify(payload) });
  state.bayAutoAssignSettings = saved || payload;
  renderBayAutoAssignOverview();
  if (els.adminModalBody) els.adminModalBody.innerHTML = bayAutoAssignerModalHtml();
  showInlineError("Bay auto-assigner settings saved.", false);
}

function bayScannerRulesModalHtml() {
  const settings = state.bayScannerSettings || { manualRules: [], barcodeRules: [] };
  const manualRules = settings.manualRules || [];
  const barcodeRules = settings.barcodeRules || [];
  return `
    <div class="bay-scanner-rules-shell">
      <section class="customer-email-intro">
        <div>
          <strong>Bay Map scanner and manual assignment rules</strong>
          <p>These rules only apply to Indian Trail Bay Map scanning/manual assign. They do not change the main delivery-list scanner.</p>
        </div>
        <span class="email-smtp-badge is-live">Bay Map only</span>
      </section>

      <section class="bay-rule-card">
        <header><strong>Remembered manual inputs</strong><span>Accepted without asking for confirmation.</span></header>
        <form id="bayManualRuleForm" class="bay-rule-form">
          <label><span>Match type</span><select id="bayManualRuleType"><option value="exact">Exact text</option><option value="contains">Contains text</option><option value="regex">Regex pattern</option></select></label>
          <label class="is-wide"><span>Text / pattern</span><input id="bayManualRulePattern" type="text" autocomplete="off" placeholder="Example: Sample rack label or ^WOOD-[0-9]+$"></label>
          <label><span>Label</span><input id="bayManualRuleLabel" type="text" autocomplete="off" placeholder="Optional label"></label>
          <button type="submit">Add Memory</button>
        </form>
        <div class="bay-rule-list">
          ${manualRules.length ? manualRules.map((rule) => `
            <article><div><strong>${escapeHtml(rule.pattern)}</strong><span>${escapeHtml(rule.matchType)}${rule.label ? ` - ${escapeHtml(rule.label)}` : ""}</span></div><button class="icon-only icon-trash danger" type="button" data-remove-bay-manual-rule="${escapeHtml(rule.id)}" aria-label="Remove remembered manual input"></button></article>
          `).join("") : `<div class="admin-empty">No remembered manual inputs yet.</div>`}
        </div>
      </section>

      <section class="bay-rule-card">
        <header><strong>Accepted bay scanner barcode formats</strong><span>Use regex for extra labels/barcodes that can be scanned into a target bay.</span></header>
        <form id="bayBarcodeRuleForm" class="bay-rule-form">
          <label class="is-wide"><span>Regex pattern</span><input id="bayBarcodeRulePattern" type="text" autocomplete="off" placeholder="Example: ^BOX-[A-Z0-9-]+$"></label>
          <label><span>Label</span><input id="bayBarcodeRuleLabel" type="text" autocomplete="off" placeholder="Box label"></label>
          <button type="submit">Add Barcode Rule</button>
        </form>
        <div class="bay-rule-list">
          ${barcodeRules.length ? barcodeRules.map((rule) => `
            <article><div><strong>${escapeHtml(rule.pattern)}</strong><span>${escapeHtml(rule.label || "Accepted bay barcode")}</span></div><button class="icon-only icon-trash danger" type="button" data-remove-bay-barcode-rule="${escapeHtml(rule.id)}" aria-label="Remove bay barcode rule"></button></article>
          `).join("") : `<div class="admin-empty">No extra bay barcode formats yet.</div>`}
        </div>
      </section>
    </div>
  `;
}

async function refreshBayScannerRules(openModal = false) {
  const payload = await fetchJson("/api/admin/bay-scanner-rules");
  state.bayScannerSettings = payload || { manualRules: [], barcodeRules: [] };
  renderBayScannerRuleOverview();
  if (openModal && els.adminModal && !els.adminModal.hidden && els.adminModal.dataset.kind === "bayScannerRules" && els.adminModalBody) {
    els.adminModalBody.innerHTML = bayScannerRulesModalHtml();
  }
  return payload;
}

async function saveBayManualRule() {
  const matchType = document.getElementById("bayManualRuleType")?.value || "exact";
  const pattern = document.getElementById("bayManualRulePattern")?.value.trim() || "";
  const label = document.getElementById("bayManualRuleLabel")?.value.trim() || "";
  const payload = await fetchJson("/api/admin/bay-scanner-rules/manual", { method: "POST", body: JSON.stringify({ matchType, pattern, label }) });
  state.bayScannerSettings = payload || state.bayScannerSettings;
  renderBayScannerRuleOverview();
  if (els.adminModalBody) els.adminModalBody.innerHTML = bayScannerRulesModalHtml();
}

async function saveBayBarcodeRule() {
  const pattern = document.getElementById("bayBarcodeRulePattern")?.value.trim() || "";
  const label = document.getElementById("bayBarcodeRuleLabel")?.value.trim() || "";
  const payload = await fetchJson("/api/admin/bay-scanner-rules/barcode", { method: "POST", body: JSON.stringify({ pattern, label }) });
  state.bayScannerSettings = payload || state.bayScannerSettings;
  renderBayScannerRuleOverview();
  if (els.adminModalBody) els.adminModalBody.innerHTML = bayScannerRulesModalHtml();
}

async function removeBayScannerRule(kind, id) {
  const payload = await fetchJson(`/api/admin/bay-scanner-rules/${kind}/remove`, { method: "POST", body: JSON.stringify({ id }) });
  state.bayScannerSettings = payload || state.bayScannerSettings;
  renderBayScannerRuleOverview();
  if (els.adminModalBody) els.adminModalBody.innerHTML = bayScannerRulesModalHtml();
}

function renderCustomerEmailOverview() {
  if (!els.customerEmailOverview) return;

  const settings = state.customerEmailSettings || { contacts: [], cc: [], outbox: [] };
  const contacts = settings.contacts || [];
  const cc = settings.cc || [];
  const outbox = settings.outbox || [];
  const sentCount = outbox.filter((email) => String(email.status || "").toLowerCase() === "sent").length;
  const draftCount = outbox.filter((email) => String(email.status || "").toLowerCase() === "draft").length;
  const failedCount = outbox.filter((email) => String(email.status || "").toLowerCase() === "failed").length;
  const previewContacts = contacts.slice(0, 7);

  els.customerEmailOverview.innerHTML = `
    <div class="customer-email-overview-card">
      <div>
        <strong>${escapeHtml(contacts.length)} email rule${contacts.length === 1 ? "" : "s"}</strong>
        <span>${escapeHtml(cc.length)} global CC ${cc.length === 1 ? "address" : "addresses"} | ${settings.smtpConfigured ? "SMTP live" : "Draft mode"}</span>
      </div>
      <div class="customer-email-overview-status">
        <span class="status-sent">${escapeHtml(sentCount)} sent</span>
        <span class="status-draft">${escapeHtml(draftCount)} draft</span>
        ${failedCount ? `<span class="status-failed">${escapeHtml(failedCount)} failed</span>` : ""}
      </div>
    </div>
    <div class="customer-email-overview-rules">
      ${previewContacts.length ? previewContacts.map((contact) => `
        <div><strong>${escapeHtml(contact.customerPattern)}</strong><span>${escapeHtml(contact.email)}</span></div>
      `).join("") : `<div><strong>No customer emails yet</strong><span>Add rules so manifests and ready notices know where to go.</span></div>`}
      ${contacts.length > previewContacts.length ? `<div><strong>+${escapeHtml(contacts.length - previewContacts.length)} more</strong><span>Open Edit emails to review all rules.</span></div>` : ""}
    </div>
  `;
}

function emailAddressListText(values = []) {
  return (values || []).filter(Boolean).join(", ");
}

function emailStatusLabel(status) {
  const clean = String(status || "draft").toLowerCase();
  if (clean === "sent") return "Sent";
  if (clean === "failed") return "Failed";
  if (clean === "queued") return "Queued";
  return "Draft";
}

function customerEmailRulesModalHtml() {
  const settings = state.customerEmailSettings || { contacts: [], cc: [], outbox: [], smtpConfig: {} };
  const contacts = settings.contacts || [];
  const cc = settings.cc || [];
  const outbox = settings.outbox || [];
  const drafts = outbox.filter((email) => ["draft", "queued", "failed"].includes(String(email.status || "").toLowerCase()));
  const sent = outbox.filter((email) => String(email.status || "").toLowerCase() === "sent");
  const smtp = settings.smtpConfig || {};

  return `
    <div class="customer-email-modal-shell customer-email-modal-shell-v34">
      <section class="customer-email-intro">
        <div>
          <strong>Customer manifest and ready-notice emails</strong>
          <p>Match customers to email addresses. Import/update creates a manifest draft, and staging completion creates a ready notice after all pieces for that customer/date are scanned.</p>
        </div>
        <span class="email-smtp-badge ${settings.smtpConfigured ? "is-live" : "is-draft"}">${settings.smtpConfigured ? "SMTP live" : "Draft mode"}</span>
      </section>

      <section class="customer-email-draft-control">
        <div>
          <strong>Email Drafts</strong>
          <span>${escapeHtml(drafts.length)} open draft${drafts.length === 1 ? "" : "s"} / ${escapeHtml(sent.length)} sent recently</span>
        </div>
        <p>Draft mode keeps every generated email inside this webapp until SMTP is configured. Open a draft to review, copy it, or launch it in the default email app.</p>
      </section>

      <section class="customer-email-smtp-section">
        <header>
          <div>
            <strong>SMTP setup readiness</strong>
            <span>Server-side only. Passwords never belong in app.js or the browser.</span>
          </div>
          <em class="email-smtp-badge ${settings.smtpConfigured ? "is-live" : "is-draft"}">${settings.smtpConfigured ? "Ready to send" : "Saving drafts"}</em>
        </header>
        <div class="smtp-config-grid">
          <span><small>Host</small><b>${escapeHtml(smtp.host || "Not set")}</b></span>
          <span><small>Port</small><b>${escapeHtml(smtp.port || "587")}</b></span>
          <span><small>From</small><b>${escapeHtml(smtp.from || "Not set")}</b></span>
          <span><small>User</small><b>${escapeHtml(smtp.user || "Not set")}</b></span>
          <span><small>SSL</small><b>${smtp.ssl ? "Yes" : "No / TLS"}</b></span>
        </div>
      </section>

      <section class="customer-email-test-section">
        <header><strong>Send test email</strong><span>If SMTP is not configured, this creates a draft you can open below.</span></header>
        <form id="customerEmailTestForm" class="customer-email-test-form">
          <label><span>Send test to</span><input id="customerEmailTestToInput" type="email" autocomplete="off" placeholder="you@example.com"></label>
          <label><span>CC optional</span><input id="customerEmailTestCcInput" type="text" autocomplete="off" placeholder="manager@example.com, lead@example.com"></label>
          <label><span>Subject</span><input id="customerEmailTestSubjectInput" type="text" autocomplete="off" value="Delivery Scanner test email"></label>
          <label class="is-wide"><span>Body</span><textarea id="customerEmailTestBodyInput" rows="4">This is a test email from the Delivery List Scanner customer email system.</textarea></label>
          <button type="submit">Send Test / Save Draft</button>
        </form>
      </section>

      <form id="customerEmailContactForm" class="customer-email-form">
        <input id="customerEmailEditIdInput" type="hidden">
        <label><span>Customer match text</span><input id="customerEmailPatternInput" type="text" autocomplete="off" placeholder="Example: LENNAR HOMES"></label>
        <label><span>Email address</span><input id="customerEmailAddressInput" type="email" autocomplete="off" placeholder="customer@example.com"></label>
        <button id="customerEmailSubmitBtn" type="submit">Add Customer Email</button>
      </form>

      <section class="customer-email-list-section">
        <header><strong>Customer email rules</strong><span>${escapeHtml(contacts.length)} active rule${contacts.length === 1 ? "" : "s"}</span></header>
        <div class="customer-email-rule-list">
          ${contacts.length ? contacts.map((contact) => `
            <article class="customer-email-row">
              <div><strong>${escapeHtml(contact.customerPattern)}</strong><span>${escapeHtml(contact.email)}</span></div>
              <span class="customer-email-row-actions">
                <button class="icon-only icon-pencil" type="button" data-edit-customer-email="${escapeHtml(contact.id)}" title="Edit customer email" aria-label="Edit customer email"></button>
                <button class="icon-only icon-trash danger" type="button" data-remove-customer-email="${escapeHtml(contact.id)}" title="Remove customer email" aria-label="Remove customer email"></button>
              </span>
            </article>
          `).join("") : `<div class="admin-empty">No customer emails yet.</div>`}
        </div>
      </section>

      <section class="customer-email-cc-section">
        <header><strong>CC on all customer emails</strong><span>These addresses receive every customer manifest and ready notice.</span></header>
        <form id="customerEmailCcForm" class="customer-email-cc-form">
          <input id="customerEmailCcInput" type="email" autocomplete="off" placeholder="manager@example.com">
          <button type="submit">Add CC</button>
        </form>
        <div class="customer-email-cc-list">
          ${cc.length ? cc.map((row) => `<span>${escapeHtml(row.email)} <button type="button" data-remove-customer-email-cc="${escapeHtml(row.id)}">&times;</button></span>`).join("") : `<em>No CC addresses configured.</em>`}
        </div>
      </section>

      <section class="customer-email-outbox-section email-drafts-section">
        <header><strong>Internal email drafts</strong><span>Open drafts here before SMTP is configured or after a send error.</span></header>
        <div class="customer-email-outbox-list email-draft-list">
          ${outbox.length ? outbox.map((email) => `
            <article class="email-outbox-row status-${escapeHtml(email.status)}">
              <div>
                <strong>${escapeHtml(email.subject)}</strong>
                <span>${escapeHtml(emailStatusLabel(email.status))} - ${escapeHtml(email.emailType)} - ${escapeHtml(email.customerName || "Customer email")} - ${escapeHtml(formatDisplayDate(email.deliveryDate))}</span>
                <small>To: ${escapeHtml(emailAddressListText(email.toEmails))}${email.ccEmails?.length ? ` | CC: ${escapeHtml(emailAddressListText(email.ccEmails))}` : ""}</small>
                ${email.error ? `<small class="email-error-text">${escapeHtml(email.error)}</small>` : ""}
              </div>
              <span class="email-outbox-actions">
                <em>${escapeHtml(emailStatusLabel(email.status))}</em>
                <button type="button" data-open-email-draft="${escapeHtml(email.id)}">Open</button>
                <button type="button" data-email-manifest-pdf="${escapeHtml(email.id)}">PDF</button>
              </span>
            </article>
          `).join("") : `<div class="admin-empty">No customer email drafts yet.</div>`}
        </div>
      </section>
    </div>
  `;
}

function emailDraftPreviewHtml(email) {
  if (!email) return "";
  return `
    <div class="modal-backdrop email-draft-preview-backdrop" data-close-email-draft></div>
    <section class="modal-panel email-draft-preview-panel" role="dialog" aria-modal="true" aria-label="Email draft preview">
      <header>
        <div>
          <small>${escapeHtml(emailStatusLabel(email.status))} email</small>
          <h2>${escapeHtml(email.subject || "Email draft")}</h2>
          <span>${escapeHtml(email.emailType || "email")} - ${escapeHtml(email.customerName || "Customer email")}</span>
        </div>
        <button class="modal-close-x" type="button" data-close-email-draft aria-label="Close">&times;</button>
      </header>
      <div class="email-draft-meta-grid">
        <span><small>To</small><b>${escapeHtml(emailAddressListText(email.toEmails) || "-")}</b></span>
        <span><small>CC</small><b>${escapeHtml(emailAddressListText(email.ccEmails) || "-")}</b></span>
        <span><small>Created</small><b>${escapeHtml(formatDateTime(email.createdAt) || "-")}</b></span>
        <span><small>Status</small><b>${escapeHtml(emailStatusLabel(email.status))}</b></span>
      </div>
      ${email.error ? `<div class="email-draft-error"><strong>Send status</strong><span>${escapeHtml(email.error)}</span></div>` : ""}
      <pre class="email-draft-body">${escapeHtml(email.body || "")}</pre>
      <footer class="email-draft-actions">
        <button type="button" data-email-manifest-pdf="${escapeHtml(email.id)}">Generate PDF</button>
        <button type="button" data-copy-email-draft="${escapeHtml(email.id)}">Copy Body</button>
        <button type="button" data-mailto-email-draft="${escapeHtml(email.id)}">Open in Email App</button>
        <button type="button" data-close-email-draft>Close</button>
      </footer>
    </section>
  `;
}

function openEmailDraftPreview(id) {
  const email = (state.customerEmailSettings?.outbox || []).find((row) => String(row.id) === String(id));
  if (!email) return;
  closeEmailDraftPreview();
  const shell = document.createElement("div");
  shell.id = "emailDraftPreviewShell";
  shell.className = "email-draft-preview-shell";
  shell.innerHTML = emailDraftPreviewHtml(email);
  document.body.appendChild(shell);
  updateModalScrollLock();
}

function closeEmailDraftPreview() {
  document.getElementById("emailDraftPreviewShell")?.remove();
  updateModalScrollLock();
}

async function copyEmailDraftBody(id) {
  const email = (state.customerEmailSettings?.outbox || []).find((row) => String(row.id) === String(id));
  if (!email) return;
  await navigator.clipboard.writeText(email.body || "");
  showInlineError("Email body copied.", false);
}

function mailtoParam(name, value) {
  // Do not use URLSearchParams for mailto body text. Some email clients keep
  // plus signs as literal characters, so spaces must be encoded as %20.
  return `${encodeURIComponent(name)}=${encodeURIComponent(value || "")}`;
}

function openEmailDraftMailto(id) {
  const email = (state.customerEmailSettings?.outbox || []).find((row) => String(row.id) === String(id));
  if (!email) return;
  const to = emailAddressListText(email.toEmails);
  const cc = emailAddressListText(email.ccEmails);
  const params = [
    mailtoParam("subject", email.subject || ""),
    mailtoParam("body", email.body || ""),
  ];
  if (cc) params.push(mailtoParam("cc", cc));
  window.location.href = `mailto:${encodeURIComponent(to)}?${params.join("&")}`;
}

async function refreshCustomerEmailSettings(openModal = false) {
  const payload = await fetchJson("/api/admin/customer-emails");
  state.customerEmailSettings = payload || { contacts: [], cc: [], outbox: [] };
  if (openModal && els.adminModal && !els.adminModal.hidden && els.adminModal.dataset.kind === "customerEmails" && els.adminModalBody) {
    els.adminModalBody.innerHTML = customerEmailRulesModalHtml();
  }
  return payload;
}

function startCustomerEmailEdit(id) {
  const contact = (state.customerEmailSettings?.contacts || []).find((row) => String(row.id) === String(id));
  if (!contact) return;
  const idInput = document.getElementById("customerEmailEditIdInput");
  const patternInput = document.getElementById("customerEmailPatternInput");
  const emailInput = document.getElementById("customerEmailAddressInput");
  const submitButton = document.getElementById("customerEmailSubmitBtn");
  if (idInput) idInput.value = contact.id;
  if (patternInput) patternInput.value = contact.customerPattern || "";
  if (emailInput) emailInput.value = contact.email || "";
  if (submitButton) submitButton.textContent = "Save Customer Email";
  patternInput?.focus();
}

async function saveCustomerEmailContact() {
  const id = document.getElementById("customerEmailEditIdInput")?.value.trim() || "";
  const pattern = document.getElementById("customerEmailPatternInput")?.value.trim() || "";
  const email = document.getElementById("customerEmailAddressInput")?.value.trim() || "";
  const payload = await fetchJson("/api/admin/customer-emails", {
    method: "POST",
    body: JSON.stringify({ id, customerPattern: pattern, email }),
  });
  state.customerEmailSettings = payload || state.customerEmailSettings;
  renderCustomerEmailOverview();
  if (els.adminModalBody) els.adminModalBody.innerHTML = customerEmailRulesModalHtml();
}

async function saveCustomerEmailCc() {
  const email = document.getElementById("customerEmailCcInput")?.value.trim() || "";
  const payload = await fetchJson("/api/admin/customer-emails/cc", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
  state.customerEmailSettings = payload || state.customerEmailSettings;
  renderCustomerEmailOverview();
  if (els.adminModalBody) els.adminModalBody.innerHTML = customerEmailRulesModalHtml();
}

async function sendCustomerEmailTest() {
  const toEmail = document.getElementById("customerEmailTestToInput")?.value.trim() || "";
  const ccEmails = document.getElementById("customerEmailTestCcInput")?.value.trim() || "";
  const subject = document.getElementById("customerEmailTestSubjectInput")?.value.trim() || "Delivery Scanner test email";
  const body = document.getElementById("customerEmailTestBodyInput")?.value.trim() || "This is a test email from the Delivery List Scanner customer email system.";
  const payload = await fetchJson("/api/admin/customer-emails/test", {
    method: "POST",
    body: JSON.stringify({ toEmail, ccEmails, subject, body }),
  });
  state.customerEmailSettings = payload || state.customerEmailSettings;
  renderCustomerEmailOverview();
  if (els.adminModalBody) els.adminModalBody.innerHTML = customerEmailRulesModalHtml();
  const result = payload.testResult || {};
  const message = result.status === "sent"
    ? `Test email sent to ${result.toEmail}.`
    : `Test email saved as ${result.status || "draft"}. Open it in Email Drafts.`;
  showFloatingNotice(message, result.status === "sent" ? "success" : "notice");
}

async function removeCustomerEmailContact(id) {
  const payload = await fetchJson("/api/admin/customer-emails/remove", {
    method: "POST",
    body: JSON.stringify({ id }),
  });
  state.customerEmailSettings = payload || state.customerEmailSettings;
  renderCustomerEmailOverview();
  if (els.adminModalBody) els.adminModalBody.innerHTML = customerEmailRulesModalHtml();
}

async function removeCustomerEmailCc(id) {
  const payload = await fetchJson("/api/admin/customer-emails/cc/remove", {
    method: "POST",
    body: JSON.stringify({ id }),
  });
  state.customerEmailSettings = payload || state.customerEmailSettings;
  renderCustomerEmailOverview();
  if (els.adminModalBody) els.adminModalBody.innerHTML = customerEmailRulesModalHtml();
}

function customerRouteFormValues() {
  const patternInput = document.getElementById("customerRoutePatternInputModal") || els.customerRoutePatternInput;
  const routeInput = document.getElementById("customerRouteSelectModal") || els.customerRouteSelect;
  const addressInput = document.getElementById("customerRouteAddressInputModal");
  const customerPattern = (patternInput?.value || "").trim();
  const route = customerRouteValue(routeInput?.value || "CPU");
  let customerAddress = (addressInput?.value || "").trim();

  if (!customerAddress && customerRouteDefaultAddress(route)) {
    customerAddress = customerRouteDefaultAddress(route);
    if (addressInput) addressInput.value = customerAddress;
  }

  if (!customerPattern) {
    patternInput?.focus();
    throw new Error("Enter a customer or job match text before adding the route.");
  }
  if (!route) {
    routeInput?.focus();
    throw new Error("Enter a route code before adding the customer route.");
  }
  if (route === "DTC" && !customerAddress) {
    addressInput?.focus();
    throw new Error("Enter a delivery address for DTC customer routes.");
  }

  return { customerPattern, route, customerAddress, patternInput, routeInput, addressInput };
}

async function saveCustomerRouteRule() {
  const { customerPattern, route, customerAddress, patternInput, routeInput, addressInput } = customerRouteFormValues();

  if (state.backend) {
    const payload = await fetchJson("/api/admin/customer-route-rules", {
      method: "POST",
      body: JSON.stringify({ customerPattern, route, customerAddress }),
    });
    state.adminCustomerRouteRules = payload.rules || [];
  } else {
    const existing = state.adminCustomerRouteRules.find(
      (rule) => String(rule.customerPattern || "").toLowerCase() === customerPattern.toLowerCase(),
    );
    if (existing) {
      existing.route = route;
      existing.customerAddress = customerAddress;
    } else {
      state.adminCustomerRouteRules.push({ id: Date.now(), customerPattern, route, customerAddress, active: true });
    }
  }

  if (patternInput) patternInput.value = "";
  if (routeInput) routeInput.value = "";
  if (addressInput) addressInput.value = "";
  refreshCustomerRouteModal();
  showFloatingNotice(`Customer route saved for ${customerPattern}.`, "success");
}

async function saveCustomerRouteRuleRow(ruleId) {
  const patternInput = document.querySelector(`[data-customer-route-pattern="${CSS.escape(String(ruleId))}"]`);
  const routeInput = document.querySelector(`[data-customer-route-route="${CSS.escape(String(ruleId))}"]`);
  const addressInput = document.querySelector(`[data-customer-route-address="${CSS.escape(String(ruleId))}"]`);
  const customerPattern = (patternInput?.value || "").trim();
  const route = customerRouteValue(routeInput?.value || "CPU");
  let customerAddress = (addressInput?.value || "").trim() || customerRouteDefaultAddress(route);

  if (!customerPattern) {
    patternInput?.focus();
    throw new Error("Customer match text is required.");
  }
  if (route === "DTC" && !customerAddress) {
    addressInput?.focus();
    throw new Error("DTC customer route rules require a delivery address.");
  }
  if (addressInput && !addressInput.value && customerAddress) addressInput.value = customerAddress;

  if (state.backend) {
    const payload = await fetchJson("/api/admin/customer-route-rules", {
      method: "POST",
      body: JSON.stringify({ ruleId, customerPattern, route, customerAddress }),
    });
    state.adminCustomerRouteRules = payload.rules || [];
  } else {
    const rule = state.adminCustomerRouteRules.find((item) => String(item.id) === String(ruleId));
    if (!rule) throw new Error("Customer route rule not found.");
    rule.customerPattern = customerPattern;
    rule.route = route;
    rule.customerAddress = customerAddress;
  }

  refreshCustomerRouteModal();
  showFloatingNotice(`Customer route updated for ${customerPattern}.`, "success");
}

async function removeCustomerRouteRule(ruleId) {
  const rule = state.adminCustomerRouteRules.find((item) => String(item.id) === String(ruleId));
  const label = rule?.customerPattern || "this customer route";

  if (!window.confirm(`Delete the customer route for ${label}?`)) return;

  if (state.backend) {
    const payload = await fetchJson("/api/admin/customer-route-rules/remove", {
      method: "POST",
      body: JSON.stringify({ ruleId }),
    });
    state.adminCustomerRouteRules = payload.rules || [];
  } else {
    state.adminCustomerRouteRules = state.adminCustomerRouteRules.filter((item) => String(item.id) !== String(ruleId));
  }

  refreshCustomerRouteModal();
  showFloatingNotice(`Customer route removed for ${label}.`, "success");
}

function renderActiveSessions() {
  if (!els.activeSessions) return;
  els.activeSessions.innerHTML = state.activeSessions.length
    ? state.activeSessions.map((session) => `<div><strong>${escapeHtml(session.displayName)}</strong><span>Last seen ${escapeHtml(session.lastSeenAt)}</span></div>`).join("")
    : `<div><strong>No active sessions</strong><span>Users appear here after login.</span></div>`;
}

async function createUserFromForm() {
  const usernameInput = document.getElementById("newUserNameModal") || els.newUserName;
  const displayInput = document.getElementById("newUserDisplayModal") || els.newUserDisplay;
  const emailInput = document.getElementById("newUserEmailModal") || els.newUserEmail;
  const passwordInput = document.getElementById("newUserPasswordModal") || els.newUserPassword;
  const roleInput = document.getElementById("newUserRoleModal") || els.newUserRole;
  const stationInput = document.getElementById("newUserStationModal");
  const email = emailInput?.value.trim() || "";
  const username = usernameInput?.value.trim() || email;
  const displayName = displayInput?.value.trim() || username;
  const password = passwordInput?.value || "";
  const role = roleInput?.value || "Operator";
  const station = stationInput?.value || "";
  if (!username || !password) throw new Error("BFS email/username and password are required");
  await fetchJson("/api/admin/users", {
    method: "POST",
    body: JSON.stringify({ username, email, displayName, password, roles: [role], station }),
  });
  if (usernameInput) usernameInput.value = "";
  if (displayInput) displayInput.value = "";
  if (emailInput) emailInput.value = "";
  if (passwordInput) passwordInput.value = "";
  if (stationInput) stationInput.value = "";
  await refreshAdminPage();
  if (!els.adminModal?.hidden) openAdminModal("users");
}


async function runManualEditSearch() {
  const query = els.manualEditSearch?.value.trim() || "";
  if (query.length < 2 && !els.manualEditStageSelect?.value) return;
  renderManualEditResults(await fetchManualEditResults(query, els.manualEditStageSelect?.value || ""));
}

function renderManualEditResults(results) {
  if (!els.manualEditResults) return;
  els.manualEditResults.innerHTML = manualEditResultsHtml(results);
}

const MANUAL_EDIT_CUSTOM_VALUE = "__manual_edit_custom__";

function manualEditOptionHasValue(options, value) {
  const cleanValue = String(value ?? "");

  return options.some(([optionValue]) => String(optionValue ?? "") === cleanValue);
}

function lookupOptions(items = [], blankLabel = "Blank") {
  const seen = new Set();
  const options = [["", blankLabel]];
  for (const item of items || []) {
    const value = String(item.value ?? "").trim();
    if (!value || seen.has(value)) continue;
    seen.add(value);
    options.push([value, item.label || value]);
  }
  return options;
}

function manualEditIsCustomChoice(options, value) {
  const cleanValue = String(value ?? "").trim();

  return Boolean(cleanValue) && !manualEditOptionHasValue(options, cleanValue);
}

function manualEditSelectOptions(options, selectedValue = "", customLabel = "Custom value...") {
  const selected = String(selectedValue ?? "");
  const selectedIsCustom = manualEditIsCustomChoice(options, selected);
  const seen = new Set();

  const optionHtml = options
    .filter(([value]) => {
      const key = String(value ?? "");

      if (seen.has(key)) return false;

      seen.add(key);
      return true;
    })
    .map(([value, label]) => {
      const cleanValue = String(value ?? "");
      const isSelected = !selectedIsCustom && cleanValue === selected;

      return `<option value="${escapeHtml(cleanValue)}" ${isSelected ? "selected" : ""}>${escapeHtml(label)}</option>`;
    })
    .join("");

  return `
    ${optionHtml}
    <option value="${MANUAL_EDIT_CUSTOM_VALUE}" ${selectedIsCustom ? "selected" : ""}>${escapeHtml(customLabel)}</option>
  `;
}

function manualEditChoiceFieldHtml({ field, label, value = "", options = [], customLabel = "", wide = false }) {
  const cleanField = String(field || "");
  const cleanLabel = String(label || cleanField);
  const cleanValue = String(value ?? "");
  const customText = customLabel || `Custom ${cleanLabel.toLowerCase()}...`;
  const isCustom = manualEditIsCustomChoice(options, cleanValue);

  return `
    <label class="manual-field has-custom ${wide ? "wide" : ""}">
      <span>${escapeHtml(cleanLabel)}</span>

      <div class="manual-choice-control ${isCustom ? "is-custom" : ""}" data-choice-control data-choice-field="${escapeHtml(cleanField)}">
        <select
          class="manual-edit-select manual-edit-choice-select"
          data-choice-field="${escapeHtml(cleanField)}"
          aria-label="${escapeHtml(cleanLabel)} dropdown"
          title="${escapeHtml(cleanValue || cleanLabel)}"
          ${isCustom ? "hidden" : ""}
        >
          ${manualEditSelectOptions(options, cleanValue, customText)}
        </select>

        <div class="manual-custom-control" ${isCustom ? "" : "hidden"}>
          <input
            class="manual-edit-input manual-edit-custom-input"
            data-custom-field="${escapeHtml(cleanField)}"
            type="text"
            value="${escapeHtml(isCustom ? cleanValue : "")}"
            placeholder="${escapeHtml(customText.replace("...", ""))}"
            aria-label="Custom ${escapeHtml(cleanLabel)}"
          >
          <button
            type="button"
            class="manual-custom-clear"
            data-manual-custom-clear="${escapeHtml(cleanField)}"
            title="Back to ${escapeHtml(cleanLabel)} dropdown"
            aria-label="Back to ${escapeHtml(cleanLabel)} dropdown"
          >×</button>
        </div>

        <input data-edit-field="${escapeHtml(cleanField)}" type="hidden" value="${escapeHtml(cleanValue)}">
      </div>
    </label>
  `;
}

function manualEditChoiceHiddenInput(control) {
  const field = control?.dataset?.choiceField || "";

  return control?.querySelector(`[data-edit-field="${CSS.escape(field)}"]`) || null;
}

function manualEditSetChoiceValue(control, value, markDirty = true) {
  const hiddenInput = manualEditChoiceHiddenInput(control);

  if (!hiddenInput) return;

  hiddenInput.value = value;

  if (markDirty) {
    state.manualEditDirty = true;
    hiddenInput.dispatchEvent(new Event("input", { bubbles: true }));
  }
}

function manualEditShowCustomChoice(control, startingValue = "") {
  if (!control) return;

  const select = control.querySelector(".manual-edit-choice-select");
  const customWrap = control.querySelector(".manual-custom-control");
  const customInput = control.querySelector(".manual-edit-custom-input");

  control.classList.add("is-custom");

  if (select) {
    select.hidden = true;
    select.value = MANUAL_EDIT_CUSTOM_VALUE;
  }

  if (customWrap) customWrap.hidden = false;

  if (customInput) {
    customInput.value = startingValue;
    manualEditSetChoiceValue(control, startingValue, false);
    window.setTimeout(() => customInput.focus(), 20);
  }
}

function manualEditShowSelectChoice(control) {
  if (!control) return;

  const select = control.querySelector(".manual-edit-choice-select");
  const customWrap = control.querySelector(".manual-custom-control");
  const customInput = control.querySelector(".manual-edit-custom-input");

  control.classList.remove("is-custom");

  if (customInput) customInput.value = "";
  if (customWrap) customWrap.hidden = true;

  if (select) {
    select.hidden = false;

    if (select.value === MANUAL_EDIT_CUSTOM_VALUE) {
      select.value = "";
    }

    manualEditSetChoiceValue(control, select.value, true);
    window.setTimeout(() => select.focus(), 20);
  }
}

function manualEditApplyChoiceSelect(select) {
  const control = select?.closest("[data-choice-control]");

  if (!control) return;

  if (select.value === MANUAL_EDIT_CUSTOM_VALUE) {
    manualEditShowCustomChoice(control, "");
    state.manualEditDirty = true;
    return;
  }

  manualEditSetChoiceValue(control, select.value, true);
}

function manualEditApplyCustomInput(customInput) {
  const control = customInput?.closest("[data-choice-control]");

  if (!control) return;

  manualEditSetChoiceValue(control, customInput.value, false);
  state.manualEditDirty = true;
}

function manualEditClearCustomChoice(button) {
  const control = button?.closest("[data-choice-control]");

  if (!control) return;

  manualEditShowSelectChoice(control);
  state.manualEditDirty = true;
}

function manualEditSyncChoiceSelect(input) {
  const field = input?.dataset?.editField || "";
  const row = input?.closest("[data-edit-row]");
  const control = row?.querySelector(`[data-choice-control][data-choice-field="${CSS.escape(field)}"]`);
  const select = control?.querySelector(".manual-edit-choice-select");

  if (!control || !select) return;

  const value = String(input.value ?? "");
  const hasMatchingOption = [...select.options].some((option) => option.value === value);

  if (value && !hasMatchingOption) {
    manualEditShowCustomChoice(control, value);
    return;
  }

  manualEditShowSelectChoice(control);
  select.value = hasMatchingOption ? value : "";
}

function manualEditCurrentLocationValue(item) {
  return String(item.location || item.rackCode || item.bayCode || "").trim();
}

function manualEditLocationOptions(item) {
  const options = [
    ["", "No location / clear"],
  ];

  const racks = (state.racks || [])
    .slice()
    .sort((a, b) => {
      if (a.code === "T") return -1;
      if (b.code === "T") return 1;

      return String(a.code || "").localeCompare(String(b.code || ""), undefined, { numeric: true });
    });

  for (const rack of racks) {
    const code = String(rack.code || "").trim();

    if (!code) continue;

    const name = rack.name || rack.type || "Rack";
    const qty = Number(rack.qty || 0);
    const status = String(rack.status || "Open");

    options.push([
      code,
      isTruckRack(rack)
        ? `${code} - ${name || (code === "T" ? "Truck / no rack" : `Truck ${code.replace(/^T/i, "")}`)} (${qty} pcs, ${status})`
        : `${code} - ${name} (${qty} pcs, ${status})`,
    ]);
  }

  const bays = (state.bays || [])
    .slice()
    .sort((a, b) => String(a.bayCode || a.code || "").localeCompare(String(b.bayCode || b.code || ""), undefined, { numeric: true }));

  for (const bay of bays) {
    const bayCode = String(bay.bayCode || bay.code || "").trim();

    if (!bayCode) continue;

    options.push([
      bayCode,
      `Bay ${bay.displayName || bayCode}`,
    ]);
  }

  return options;
}

function manualEditRouteOptions() {
  const lookupRoutes = lookupOptions(state.manualEditLookups?.routes || [], "Indian Trail / Standard");
  if (lookupRoutes.length > 1) return lookupRoutes;
  return [
    ["", "Indian Trail / Standard"],
    ["CPU", "Customer Pickup"],
    ["GNV", "Greenville"],
    ["DTC", "Deliver to Customer"],
  ];
}

function manualEditProcessOptions() {
  const lookupProcesses = lookupOptions(state.manualEditLookups?.processes || [], "Normal / blank");
  if (lookupProcesses.length > 1) return lookupProcesses;
  return [
    ["", "Normal / blank"],
    ["New", "New"],
    ["Updated", "Updated"],
    ["Rush", "Rush"],
    ["Remake", "Remake"],
    ["SDI", "SDI"],
    ["Review", "Needs Review"],
  ];
}

function manualEditProductOptions(results = []) {
  const productValues = uniqueText([
    ...(state.manualEditLookups?.products || []).map((item) => item.value),
    ...results.map((item) => item.product),
    ...state.items.map((item) => item.product),
    ...state.lists.flatMap((list) => list.items || []).map((item) => item.product),
  ]).sort((a, b) => a.localeCompare(b));

  return [
    ["", "Blank product"],
    ...productValues.map((value) => {
      const lookup = (state.manualEditLookups?.products || []).find((item) => String(item.value) === String(value));
      return [value, lookup?.label || value];
    }),
  ];
}

function manualEditSetRowError(row, message = "") {
  if (!row) return;

  const errorBox = row.querySelector(".manual-edit-row-error");

  row.classList.toggle("is-invalid", Boolean(message));

  row.querySelectorAll(".manual-edit-input.is-invalid, .manual-edit-select.is-invalid").forEach((field) => {
    field.classList.remove("is-invalid");
  });

  if (errorBox) {
    errorBox.hidden = !message;
    errorBox.textContent = message;
  }
}

function manualEditValidateRow(row) {
  if (!row) return false;

  const qtyInput = row.querySelector('[data-edit-field="qty"]');
  const scannedInput = row.querySelector('[data-edit-field="scanned"]');

  if (!qtyInput || !scannedInput) {
    manualEditSetRowError(row, "");
    return true;
  }

  const qty = Number(qtyInput.value || 0);
  const scanned = Number(scannedInput.value || 0);

  scannedInput.max = String(Math.max(qty, 0));

  if (!Number.isFinite(qty) || qty < 0) {
    qtyInput.classList.add("is-invalid");
    manualEditSetRowError(row, "Qty must be zero or greater.");
    return false;
  }

  if (!Number.isFinite(scanned) || scanned < 0) {
    scannedInput.classList.add("is-invalid");
    manualEditSetRowError(row, "Scanned quantity must be zero or greater.");
    return false;
  }

  if (scanned > qty) {
    scannedInput.classList.add("is-invalid");
    manualEditSetRowError(row, "Scanned quantity cannot be greater than Qty.");
    return false;
  }

  manualEditSetRowError(row, "");

  return true;
}

function manualEditResultsHtml(results) {
  const visibleRows = results.slice(0, 100);

  return results.length
    ? `
      <div class="manual-edit-result-summary">
        <span>Showing ${escapeHtml(visibleRows.length)} of ${escapeHtml(results.length)} row${results.length === 1 ? "" : "s"}</span>
        <small>Choose from dropdowns or type a custom value.</small>
      </div>

      <div class="manual-edit-card-list">
        ${visibleRows
          .map((item) => {
            const rowLabel = `${item.order || ""}-${item.item || ""}`;
            const stageText = item.stage || item.deliveryLabel || "";
            const qtyValue = Math.max(Number(item.qty || 0), 0);
            const scannedValue = Math.min(Math.max(Number(item.scanned || 0), 0), qtyValue);
            const locationValue = manualEditCurrentLocationValue(item);

            return `
              <article class="manual-edit-card" data-edit-row="${escapeHtml(item.lineItemId)}">
                <header class="manual-edit-card-header">
                  <div class="manual-edit-card-title">
                    <strong>${escapeHtml(item.order)}-${escapeHtml(item.item)}</strong>
                    <span>${escapeHtml(item.customer || "")}</span>
                  </div>

                  <div class="manual-edit-card-stage" title="${escapeHtml(stageText)}">
                    <span>Stage</span>
                    <strong>${escapeHtml(stageText || "No stage")}</strong>
                  </div>

                  <div class="manual-edit-row-actions">
                    <button
                      type="button"
                      class="icon-only icon-save manual-edit-action-button"
                      data-save-line-item="${escapeHtml(item.lineItemId)}"
                      title="Save ${escapeHtml(rowLabel)}"
                      aria-label="Save ${escapeHtml(rowLabel)}"
                    ></button>
                    <button
                      type="button"
                      class="icon-only icon-trash danger manual-edit-action-button"
                      data-delete-line-item="${escapeHtml(item.lineItemId)}"
                      title="Delete ${escapeHtml(rowLabel)}"
                      aria-label="Delete ${escapeHtml(rowLabel)}"
                    ></button>
                  </div>
                </header>

                <div class="manual-edit-card-grid">

                  <label class="manual-field">
                    <span>Order</span>
                    <input class="manual-edit-input" data-edit-field="order" type="text" value="${escapeHtml(item.order)}">
                  </label>

                  <label class="manual-field small">
                    <span>Item</span>
                    <input class="manual-edit-input" data-edit-field="item" type="text" value="${escapeHtml(item.item)}">
                  </label>

                  <label class="manual-field wide">
                    <span>Customer</span>
                    <input class="manual-edit-input" data-edit-field="customer" type="text" value="${escapeHtml(item.customer)}">
                  </label>

                  <label class="manual-field small">
                    <span>Qty</span>
                    <input class="manual-edit-input" data-edit-field="qty" type="number" min="0" value="${escapeHtml(qtyValue)}">
                  </label>

                  <label class="manual-field small">
                    <span>Scanned</span>
                    <input class="manual-edit-input" data-edit-field="scanned" type="number" min="0" max="${escapeHtml(qtyValue)}" value="${escapeHtml(scannedValue)}">
                  </label>

                  ${manualEditChoiceFieldHtml({
                    field: "location",
                    label: "Location",
                    value: locationValue,
                    options: manualEditLocationOptions(item),
                    customLabel: "Custom location...",
                  })}

                  ${manualEditChoiceFieldHtml({
                    field: "route",
                    label: "Route",
                    value: item.route || "",
                    options: manualEditRouteOptions(),
                    customLabel: "Custom route...",
                  })}

                  ${manualEditChoiceFieldHtml({
                    field: "processState",
                    label: "Process",
                    value: item.processState || "",
                    options: manualEditProcessOptions(),
                    customLabel: "Custom process...",
                  })}

                  ${manualEditChoiceFieldHtml({
                    field: "product",
                    label: "Product",
                    value: item.product || "",
                    options: manualEditProductOptions(visibleRows),
                    customLabel: "Custom product...",
                    wide: true,
                  })}

                  <label class="manual-field wide">
                    <span>Dimensions</span>
                    <input class="manual-edit-input" data-edit-field="dimensions" type="text" value="${escapeHtml(item.dimensions || "")}">
                  </label>

                  <label class="manual-field wide">
                    <span>Job</span>
                    <input class="manual-edit-input" data-edit-field="job" type="text" value="${escapeHtml(item.job || "")}">
                  </label>

                  <input data-edit-field="queueState" type="hidden" value="${escapeHtml(item.queueState || "")}">
                </div>

                <div class="manual-edit-row-error" hidden aria-live="polite"></div>
              </article>
            `;
          })
          .join("")}
      </div>
    `
    : `<div class="admin-empty">No editable rows found.</div>`;
}

async function saveManualLineItem(lineItemId) {
  const row = document.querySelector(`[data-edit-row="${CSS.escape(lineItemId)}"]`);

  if (!row) return;

  if (!manualEditValidateRow(row)) {
    row.querySelector(".is-invalid")?.focus();
    return;
  }

  const data = { lineItemId };

  row.querySelectorAll("[data-edit-field]").forEach((input) => {
    data[input.dataset.editField] = input.value;
  });

  const payload = await fetchJson("/api/admin/line-item", {
    method: "POST",
    body: JSON.stringify(data),
  });

  if (payload.meta?.id === state.activeListId) {
    applyBackendPayload(payload);
  }

  if (!els.adminModal?.hidden && state.manualEditListId) {
    await runManualEditModalSearch(!state.manualEditQuery);
  } else {
    await runManualEditSearch();
  }

  state.manualEditDirty = false;
  renderScanPage();
}

async function deleteManualLineItem(lineItemId) {
  if (!window.confirm("Delete this line item from its delivery list?")) return;
  const payload = await fetchJson("/api/admin/line-item/delete", {
    method: "POST",
    body: JSON.stringify({ lineItemId }),
  });
  if (payload.meta?.id === state.activeListId) applyBackendPayload(payload);
  await loadDeliveryLists(state.activeListId);
  if (!els.adminModal?.hidden && state.manualEditListId) await runManualEditModalSearch(!state.manualEditQuery);
  else await runManualEditSearch();
  state.manualEditDirty = false;
  renderScanPage();
}

function exportStaticCsv() {
  const header = ["barcode", "order", "item", "qty", "scanned", "remaining", "dimensions", "customer", "route", "job", "product", "suggestedBay"];
  const rows = state.items.map((item) => {
    const row = { ...item, barcode: canonicalBarcode(item.order, item.item), remaining: Math.max(Number(item.qty) - Number(item.scanned), 0) };
    return header.map((key) => JSON.stringify(row[key] ?? "")).join(",");
  });
  const blob = new Blob([[header.join(","), ...rows].join("\n")], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "delivery-list-export.csv";
  link.click();
  URL.revokeObjectURL(url);
}

function startPolling() {
  stopPolling();
  state.pollTimer = window.setInterval(async () => {
    if (!state.backend || state.page !== "scan" || !state.activeListId || document.hidden) return;
    const activeElement = document.activeElement;
    if (activeElement === els.manualOrderInput || activeElement === els.manualItemInput) return;
    try {
      await activateList(state.activeListId, false);
      if (activeElement === els.scanInput) els.scanInput.focus();
    } catch {
      // Keep polling quiet so scanning is not interrupted.
    }
  }, 38000);
}

function stopPolling() {
  if (state.pollTimer) window.clearInterval(state.pollTimer);
  state.pollTimer = null;
}

async function loadAuthenticatedApp(params = new URLSearchParams(window.location.search)) {
  await loadStations();
  await loadDeliveryLists(params.get("list") || "");
  loadHomeReportSummary();
  if (params.get("list")) {
    showPage("scan");
  } else {
    showPage("home");
  }
  startPolling();
}

async function init() {
  wireEvents();
  resetImportDateWindow();
  await detectBackend();
  if (state.backend) {
    await loadSession();
    if (!state.authenticated) {
      showLogin();
      return;
    }
    await loadAuthenticatedApp(new URLSearchParams(window.location.search));
    return;
  }
  loadLocalStations();
  renderStationOptions();
  const response = await fetch("data/sample-delivery-list.json");
  const payload = await response.json();
  state.lists = createDemoLists(payload);
  showPage("home");
}

function replayExpandableListAnimation(details) {
  if (!details?.open) return;

  const target = details.classList.contains("admin-import-date-group")
    ? details.querySelector(".admin-import-stage-wrap")
    : details.querySelector(".delivery-stage-list");

  if (!target) return;

  target.style.setProperty("animation", "none", "important");
  void target.offsetHeight;
  requestAnimationFrame(() => {
    target.style.setProperty("animation", "delivery-expand-replay-v023 0.28s cubic-bezier(0.2, 0.8, 0.2, 1) both", "important");
  });
}

function wireEvents() {
  if (state.eventsWired) return;
  state.eventsWired = true;
  initLanguageSystem();
  initCustomSelectSystem();
  syncFullscreenControl();

  document.addEventListener("toggle", (event) => {
    const details = event.target.closest?.(".delivery-date-group, .admin-import-date-group");
    if (!details || details !== event.target) return;
    replayExpandableListAnimation(details);
  }, true);

  els.loginForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      await login(els.loginUsername?.value || "", els.loginPassword?.value || "");
      await loadAuthenticatedApp();
    } catch (error) {
      if (els.loginError) {
        els.loginError.textContent = error.message;
        els.loginError.classList.remove("success");
      }
    }
  });

  els.logoutBtn?.addEventListener("click", () => logout().catch((error) => showInlineError(error.message)));
  els.languageToggleBtn?.addEventListener("click", () => toggleAppLanguage());
  els.loginLanguageToggleBtn?.addEventListener("click", () => toggleAppLanguage());
  els.fullscreenToggleBtn?.addEventListener("click", () => toggleFullscreen().catch((error) => showInlineError(error.message)));
  document.addEventListener("fullscreenchange", () => syncFullscreenControl());
  window.addEventListener("message", (event) => {
    if (event.origin !== window.location.origin || event.data?.type !== "delivery-print-complete") return;
    restoreFullscreenAfterManagedPrint().catch(() => {});
  });

  document.addEventListener("click", (event) => {
    document.querySelectorAll(".user-menu[open]").forEach((menu) => {
      if (!menu.contains(event.target)) menu.removeAttribute("open");
    });
  });
  document.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      els.headerGlobalSearchInput?.focus();
      els.headerGlobalSearchInput?.select();
      return;
    }
    if (event.key !== "Escape") return;
    document.querySelectorAll(".user-menu[open]").forEach((menu) => menu.removeAttribute("open"));
    if (els.headerGlobalSearchResults) els.headerGlobalSearchResults.hidden = true;
    if (document.getElementById("actionFeedbackShell")) closeActionFeedback();
  });

  els.homeStatsPdfBtn?.addEventListener("click", () => openHomeStatisticsReport());
  els.homeStatsChart?.addEventListener("click", (event) => {
    if (event.target.closest("[data-open-statistics-chart]")) openStatisticsChartModal();
  });
  els.statsChartCloseBtn?.addEventListener("click", () => closeStatisticsChartModal());
  els.statsChartBackdrop?.addEventListener("click", () => closeStatisticsChartModal());
  els.statsChartMetricSelect?.addEventListener("change", () => {
    state.homeChartMetric = els.statsChartMetricSelect.value || "glass";
    renderStatisticsChartModal();
  });
  els.statsChartViewSelect?.addEventListener("change", () => {
    state.homeChartView = els.statsChartViewSelect.value || "bar";
    renderStatisticsChartModal();
  });
  els.statsChartSortSelect?.addEventListener("change", () => {
    state.homeChartSort = els.statsChartSortSelect.value || "value-desc";
    renderStatisticsChartModal();
  });
  els.statsChartLimitSelect?.addEventListener("change", () => {
    state.homeChartLimit = els.statsChartLimitSelect.value || "all";
    renderStatisticsChartModal();
  });
  els.statsChartFilterInput?.addEventListener("input", () => {
    state.homeChartQuery = els.statsChartFilterInput.value || "";
    renderStatisticsChartModal();
  });
  els.statsChartResetBtn?.addEventListener("click", () => {
    state.homeChartMetric = "glass";
    state.homeChartView = "bar";
    state.homeChartQuery = "";
    state.homeChartLimit = "all";
    state.homeChartSort = "value-desc";
    renderStatisticsChartModal();
  });
  els.viewAllRecent?.addEventListener("click", () => openAdminModal("recentScans"));
  els.globalPrintExportBtn?.addEventListener("click", () => {
    const date = state.page === "scan" ? state.meta?.deliveryDate : dashboardDateKey();
    const listIds = state.lists.filter((list) => !date || list.deliveryDate === date).map((list) => list.id);
    openPrintOptions({ date, listIds });
  });
  els.headerGlobalSearchBtn?.addEventListener("click", () => runGlobalSearch().catch((error) => showInlineError(error.message)));
  els.headerGlobalSearchInput?.addEventListener("input", () => {
    window.clearTimeout(runGlobalSearch._timer);
    runGlobalSearch._timer = window.setTimeout(() => runGlobalSearch().catch((error) => showInlineError(error.message)), 180);
  });
  els.headerGlobalSearchInput?.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      runGlobalSearch().catch((error) => showInlineError(error.message));
    }
  });
  els.homeListSearch?.addEventListener("input", () => {
    state.homeSearch = els.homeListSearch.value;
    state.homePageIndex = 1;
    renderHome();
  });
  document.addEventListener("input", (event) => {
    const modalSearch = event.target.closest("#adminDeliveryListModalSearch");
    if (!modalSearch) return;

    const target = document.getElementById("adminDeliveryListModalResults");
    const searchBox = modalSearch.closest(".admin-modal-search");
    const query = modalSearch.value.trim();

    window.clearTimeout(state.adminListSearchTimer);

    searchBox?.classList.add("is-searching");
    target?.classList.add("is-searching");

    state.adminListSearchTimer = window.setTimeout(() => {
      if (!query) state.adminDeliveryListVisiblePastDays = ADMIN_DELIVERY_LIST_DEFAULT_PAST_DAYS;

      const searchPromise = query ? searchAdminDeliveryLists(query) : Promise.resolve(state.lists);

      searchPromise
        .then((filtered) => {
          const stillCurrent = document.getElementById("adminDeliveryListModalSearch")?.value.trim() === query;

          if (target && stillCurrent) {
            renderAdminDeliveryListModalResults(filtered, query);
          }
        })
        .catch((error) => {
          if (target) {
            target.innerHTML = `<div class="admin-empty">Search failed: ${escapeHtml(error.message)}</div>`;
          }
        })
        .finally(() => {
          const stillCurrent = document.getElementById("adminDeliveryListModalSearch")?.value.trim() === query;

          if (stillCurrent) {
            searchBox?.classList.remove("is-searching");
            target?.classList.remove("is-searching");
          }
        });
    }, 180);
  });
  els.homeStageFilter?.addEventListener("change", () => {
    state.homeStageFilter = els.homeStageFilter.value;
    state.homePageIndex = 1;
    renderHome();
  });
  els.overviewRangeSelect?.addEventListener("change", () => {
    state.overviewRange = els.overviewRangeSelect.value || "30";
    renderHome();
    void loadHomeReportSummary();
  });
  els.homePageSize?.addEventListener("change", () => {
    state.homePageSize = Number(els.homePageSize.value) || 25;
    state.homePageIndex = 1;
    renderHome();
  });
  els.searchInput?.addEventListener("input", () => {
    state.search = els.searchInput.value;
    state.pageIndex = 1;
    renderScanPage();
  });
  els.scanInput?.addEventListener("focus", () => clearSelectedLineItem());
  document.addEventListener("click", (event) => {
    if (state.page !== "scan" || !state.selectedId) return;
    const target = event.target instanceof Element ? event.target : null;
    if (!target) return;

    const clickedLineItem = target.closest("#listRows tr[data-id], #mobileListCards [data-id]");
    const clickedRackLocationControl = target.closest(".line-rack-location-control, [data-line-rack-select]");
    if (!clickedLineItem && !clickedRackLocationControl) clearSelectedLineItem();
  });
  document.addEventListener("change", (event) => {
    const rackSelect = event.target.closest("[data-line-rack-select]");
    if (!rackSelect) return;

    event.preventDefault();
    event.stopPropagation();
    assignLineItemToRack(rackSelect.dataset.lineRackSelect || "", rackSelect.value || "").catch((error) => showInlineError(error.message, true));
  });
  els.pageSize?.addEventListener("change", () => {
    state.pageSize = Number(els.pageSize.value) || 25;
    if (els.pageSizeBottom) els.pageSizeBottom.value = String(state.pageSize);
    state.pageIndex = 1;
    renderScanPage();
  });
  els.pageSizeBottom?.addEventListener("change", () => {
    state.pageSize = Number(els.pageSizeBottom.value) || 25;
    if (els.pageSize) els.pageSize.value = String(state.pageSize);
    state.pageIndex = 1;
    renderScanPage();
  });
  els.deliveryListSelect?.addEventListener("change", () => activateList(els.deliveryListSelect.value).catch((error) => showInlineError(error.message)));
  els.deliveryDateSelect?.addEventListener("change", () => {
    const date = els.deliveryDateSelect.value;
    const firstStage = listsByDeliveryDate().find((group) => group.date === date)?.lists?.[0];
    if (firstStage) activateList(firstStage.id).catch((error) => showInlineError(error.message));
  });
  els.deliveryStageSelect?.addEventListener("change", () => {
    activateList(els.deliveryStageSelect.value).catch((error) => showInlineError(error.message));
  });
  els.scanForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      await processScan(els.scanInput.value);
    } catch (error) {
      showInlineError(error.message, false);
    }
    els.scanInput.value = "";
    els.scanInput.focus();
  });
  els.manualScanForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      await submitManualScan();
    } catch (error) {
      showInlineError(error.message, false);
    }
  });
  els.manualAssignForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      await submitManualBayAssign();
    } catch (error) {
      showInlineError(error.message, true);
    }
  });
  els.printOptionsDate?.addEventListener("change", () => {
    state.printContext = { ...(state.printContext || {}), listIds: [] };
    renderPrintOptionStages();
  });
  els.printOptionsStages?.addEventListener("change", (event) => {
    const allInput = event.target.closest("[data-print-stage-select-all]");

    if (allInput && els.printOptionsStages.contains(allInput)) {
      selectedPrintStageInputs().forEach((stageInput) => {
        stageInput.checked = allInput.checked;
      });
    }

    updatePrintStageSelectState();
    void renderPrintGlassTypes();
  });
  els.printOptionsClose?.addEventListener("click", () => closePrintOptions());
  els.printOptionsBackdrop?.addEventListener("click", () => closePrintOptions());
  els.printOptionsSubmit?.addEventListener("click", () => submitPrintOptions());
  els.undoBtn?.addEventListener("click", async () => {
    const payload = await fetchJson("/api/undo", {
      method: "POST",
      body: JSON.stringify({ listId: state.activeListId, ...requestContext() }),
    });
    applyBackendPayload(payload);
    scanFlash(payload.lastScan?.ok ? "success" : "notice");
    renderScanPage();
  });
  els.redoBtn?.addEventListener("click", async () => {
    const payload = await fetchJson("/api/redo", {
      method: "POST",
      body: JSON.stringify({ listId: state.activeListId, ...requestContext() }),
    });
    applyBackendPayload(payload);
    scanFlash(payload.lastScan?.ok ? "success" : "notice");
    renderScanPage();
  });
  els.rackListSelect?.addEventListener("change", () => {
    state.rackScanListId = els.rackListSelect.value;
  });
  els.rackSelect?.addEventListener("change", () => {
    state.selectedRackCode = els.rackSelect.value;
  });
  els.scanRackSelect?.addEventListener("change", () => {
    state.selectedRackCode = els.scanRackSelect.value;
    renderScanRackTools();
  });
  els.scanBayOverrideMode?.addEventListener("change", () => {
    state.bayOverrideMode = els.scanBayOverrideMode.checked ? "manual" : "auto";
    if (state.bayOverrideMode === "auto") state.selectedBayOverrideCode = "";
    renderScanBayOverrideTools();
    els.scanInput?.focus();
  });
  els.scanBayOverrideSelect?.addEventListener("change", () => {
    state.selectedBayOverrideCode = els.scanBayOverrideSelect.value || "";
    state.bayOverrideMode = state.selectedBayOverrideCode ? "manual" : "auto";
    renderScanBayOverrideTools();
    els.scanInput?.focus();
  });
  els.scanRackCompleteBtn?.addEventListener("click", async () => {
    if (!state.selectedRackCode) return;
    try {
      const selectedRack = state.racks.find((rack) => rack.code === state.selectedRackCode);
      const selectedRackStatus = String(selectedRack?.status || "").toLowerCase();
      if (selectedRackStatus === "in transit") {
        await returnRack(state.selectedRackCode);
      } else if (selectedRackStatus === "closed") {
        await uncompleteRack(state.selectedRackCode);
      } else {
        await completeRack(state.selectedRackCode);
      }
      await ensureRacksLoaded();
      renderScanRackTools();
    } catch (error) {
      showInlineError(error.message, true);
    }
  });
  els.scanRackPrintBtn?.addEventListener("click", () => {
    const selectedRack = state.racks.find((rack) => rack.code === state.selectedRackCode);
    if (String(selectedRack?.status || "").toLowerCase() === "in transit") {
      markRackNotOnTheWay(state.selectedRackCode).catch((error) => showInlineError(error.message, true));
      return;
    }
    printSelectedRackPackingSlip();
  });
  els.rackScanForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      await submitRackScan();
    } catch (error) {
      showInlineError(error.message, true);
    }
  });
  els.rackGrid?.addEventListener("toggle", (event) => {
    const group = event.target.closest?.("[data-rack-group]");
    if (group && event.target === group) {
      const label = group.dataset.rackGroup || "";
      if (group.open) state.expandedRackGroups.add(label);
      else state.expandedRackGroups.delete(label);
      return;
    }
    const rack = event.target.closest?.("[data-rack-code]");
    if (rack && event.target === rack) {
      const code = rack.dataset.rackCode || "";
      if (rack.open) state.expandedRackCodes.add(code);
      else state.expandedRackCodes.delete(code);
    }
  }, true);
  els.rackGrid?.addEventListener("click", (event) => {
    const printButton = event.target.closest("[data-rack-print]");
    if (printButton) {
      event.preventDefault();
      event.stopPropagation();

      const rack = state.racks.find((item) => item.code === printButton.dataset.rackPrint);

      if (!rack || !["closed", "in transit"].includes(String(rack.status || "").toLowerCase())) {
        showFloatingNotice("Complete this rack before printing its packing list.", "notice");
        return;
      }

      launchManagedPrint(rackPackingListUrl(printButton.dataset.rackPrint, printButton.dataset.rackPrintDate || ""));

      return;
    }

    const completeButton = event.target.closest("[data-rack-complete]");
    if (completeButton) {
      event.preventDefault();
      event.stopPropagation();

      completeRack(completeButton.dataset.rackComplete).catch((error) => showInlineError(error.message, true));

      return;
    }

    const uncompleteButton = event.target.closest("[data-rack-uncomplete]");
    if (uncompleteButton) {
      event.preventDefault();
      event.stopPropagation();

      uncompleteRack(uncompleteButton.dataset.rackUncomplete).catch((error) => showInlineError(error.message, true));

      return;
    }

    const returnButton = event.target.closest("[data-rack-return]");
    if (returnButton) {
      event.preventDefault();
      event.stopPropagation();

      returnRack(returnButton.dataset.rackReturn).catch((error) => showInlineError(error.message, true));

      return;
    }

    const notOnWayButton = event.target.closest("[data-rack-not-on-way]");
    if (notOnWayButton) {
      event.preventDefault();
      event.stopPropagation();

      markRackNotOnTheWay(notOnWayButton.dataset.rackNotOnWay).catch((error) => showInlineError(error.message, true));

      return;
    }

    const clearButton = event.target.closest("[data-rack-clear]");
    if (clearButton) {
      event.preventDefault();
      event.stopPropagation();

      clearRack(clearButton.dataset.rackClear).catch((error) => showInlineError(error.message, true));

      return;
    }

    const rackManagerNewRackButton = event.target.closest("[data-rack-manager-new-rack]");
    if (rackManagerNewRackButton) {
      event.preventDefault();
      event.stopPropagation();

      openRackForm("");

      return;
    }

    const rackManagerNewSetButton = event.target.closest("[data-rack-manager-new-set]");
    if (rackManagerNewSetButton) {
      event.preventDefault();
      event.stopPropagation();

      openRackSetForm("");

      return;
    }

    const rackManagerAddToSetButton = event.target.closest("[data-rack-manager-add-to-set]");
    if (rackManagerAddToSetButton) {
      event.preventDefault();
      event.stopPropagation();
      const label = rackManagerAddToSetButton.dataset.rackManagerAddToSet || "";

      openRackForm("", { type: label, name: label ? `${label} Rack` : "" });

      return;
    }

    const deleteRackButton = event.target.closest("[data-rack-delete]");
    if (deleteRackButton) {
      event.preventDefault();
      event.stopPropagation();

      deleteRackDefinition(deleteRackButton.dataset.rackDelete || "").catch((error) => showInlineError(error.message, true));

      return;
    }

    const editRackButton = event.target.closest("[data-rack-edit]");
    if (editRackButton) {
      event.preventDefault();
      event.stopPropagation();

      openRackForm(editRackButton.dataset.rackEdit || "");

      return;
    }

    const editRackSetButton = event.target.closest("[data-rack-set-edit]");
    if (editRackSetButton) {
      event.preventDefault();
      event.stopPropagation();

      openRackSetForm(editRackSetButton.dataset.rackSetEdit || "");

      return;
    }

    const deleteRackSetButton = event.target.closest("[data-rack-set-delete]");
    if (deleteRackSetButton) {
      event.preventDefault();
      event.stopPropagation();

      deleteRackSet(deleteRackSetButton.dataset.rackSetDelete || "").catch((error) => showInlineError(error.message, true));

      return;
    }

    const clearRackSetButton = event.target.closest("[data-rack-set-clear]");
    if (clearRackSetButton) {
      event.preventDefault();
      event.stopPropagation();

      clearRackSet(clearRackSetButton.dataset.rackSetClear || "").catch((error) => showInlineError(error.message, true));

      return;
    }

    const moveOpenButton = event.target.closest("[data-rack-move-open]");
    if (moveOpenButton) {
      event.preventDefault();
      event.stopPropagation();

      const rackItemId = moveOpenButton.dataset.rackMoveOpen || "";
      state.rackMoveItemId = state.rackMoveItemId === rackItemId ? "" : rackItemId;

      renderRacksPage();

      return;
    }

    const moveCancelButton = event.target.closest("[data-rack-move-cancel]");
    if (moveCancelButton) {
      event.preventDefault();
      event.stopPropagation();

      state.rackMoveItemId = "";

      renderRacksPage();

      return;
    }

    const moveButton = event.target.closest("[data-rack-move]");
    if (moveButton) {
      event.preventDefault();
      event.stopPropagation();

      moveRackItem(moveButton.dataset.rackMove).catch((error) => showInlineError(error.message, true));

      return;
    }

    const clearItemButton = event.target.closest("[data-rack-clear-item]");
    if (clearItemButton) {
      event.preventDefault();
      event.stopPropagation();

      clearRackItem(clearItemButton.dataset.rackClearItem, clearItemButton.dataset.rackClearLabel).catch((error) => showInlineError(error.message, true));

      return;
    }

    const rackSetCard = event.target.closest("[data-rack-set-select]");
    if (rackSetCard) {
      event.preventDefault();
      if (event.target.closest("[data-rack-set-clear]")) return;

      state.selectedRackSetLabel = rackSetCard.dataset.rackSetSelect || "";
      const matchingRacks = state.racks.filter((rack) => rackGroupLabel(rack) === state.selectedRackSetLabel);
      state.selectedRackOverviewCode = matchingRacks.find((rack) => Number(rack.qty || 0) > 0)?.code || matchingRacks[0]?.code || "";
      state.rackMoveItemId = "";

      renderRacksPage();

      return;
    }

    const rackSelectCard = event.target.closest("[data-rack-select]");
    if (rackSelectCard) {
      event.preventDefault();

      state.selectedRackOverviewCode = rackSelectCard.dataset.rackSelect || "";
      state.rackMoveItemId = "";

      renderRacksPage();

      return;
    }
  });

  els.rackGrid?.addEventListener("keydown", (event) => {
    const rackSelectCard = event.target.closest("[data-rack-select]");

    if (!rackSelectCard) return;
    if (!["Enter", " "].includes(event.key)) return;

    event.preventDefault();

    state.selectedRackOverviewCode = rackSelectCard.dataset.rackSelect || "";
    state.rackMoveItemId = "";

    renderRacksPage();
  });

  els.rackCreateOpenBtn?.addEventListener("click", () => openRackForm(""));
  els.rackSetCreateOpenBtn?.addEventListener("click", () => openRackSetForm(""));
  els.rackEditOpenBtn?.addEventListener("click", () => openAdminModal("racks"));

  els.folderImportBtn?.addEventListener("click", () => {
    importTempDeliveryFolder().catch((error) => showInlineError(error.message, true));
  });

  els.importWindowResetBtn?.addEventListener("click", () => resetImportDateWindow());

  els.deleteDateSelect?.addEventListener("change", () => renderAdminDeleteControls());
  els.deleteListBtn?.addEventListener("click", () => deleteSelectedDeliveryList(false).catch((error) => showInlineError(error.message, true)));
  els.deleteDateBtn?.addEventListener("click", () => deleteSelectedDeliveryList(true).catch((error) => showInlineError(error.message, true)));
  els.adminResetScansBtn?.addEventListener("click", () => resetSelectedAdminScans().catch((error) => showInlineError(error.message, true)));
  els.addStationBtn?.addEventListener("click", () => addStationFromInput().catch((error) => showInlineError(error.message)));
  els.newStationInput?.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      addStationFromInput().catch((error) => showInlineError(error.message));
    }
  });
  els.forgotPasswordBtn?.addEventListener("click", () => showPasswordResetPanel(true));
  els.cancelPasswordResetBtn?.addEventListener("click", () => showPasswordResetPanel(false));
  els.requestResetCodeBtn?.addEventListener("click", () => requestPasswordResetCode().catch((error) => setPasswordResetMessage(error.message)));
  els.confirmPasswordResetBtn?.addEventListener("click", () => confirmPasswordReset().catch((error) => setPasswordResetMessage(error.message)));
  els.resetNewPasswordInput?.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      confirmPasswordReset().catch((error) => setPasswordResetMessage(error.message));
    }
  });

  els.createUserForm?.addEventListener("submit", (event) => {
    event.preventDefault();
    createUserFromForm().catch((error) => showInlineError(error.message));
  });
  document.addEventListener("submit", (event) => {
    if (event.target.closest("#createUserFormModal")) {
      event.preventDefault();
      createUserFromForm().catch((error) => showInlineError(error.message));
      return;
    }
    if (event.target.closest("#rackFormModal")) {
      event.preventDefault();
      saveRackDefinition().catch((error) => showInlineError(error.message, true));
      return;
    }
    if (event.target.closest("#rackSetFormModal")) {
      event.preventDefault();
      createRackSet().catch((error) => showInlineError(error.message, true));
      return;
    }
    if (event.target.closest("#rackManagerQuickEditForm")) {
      event.preventDefault();
      saveRackQuickEdit().catch((error) => showInlineError(error.message, true));
      return;
    }
    if (event.target.closest("#rackManagerSetEditForm")) {
      event.preventDefault();
      saveRackSetQuickEdit().catch((error) => showInlineError(error.message, true));
      return;
    }
    if (event.target.closest("#rackManagerInlineEditForm")) {
      event.preventDefault();
      saveRackInlineEdit().catch((error) => showInlineError(error.message, true));
      return;
    }
    if (event.target.closest("#manualLookupForm")) {
      event.preventDefault();
      saveManualEditLookup().catch((error) => showInlineError(error.message, true));
      return;
    }

    if (event.target.closest("#customerRouteRuleFormModal")) {
      event.preventDefault();
      saveCustomerRouteRule().catch((error) => showInlineError(error.message, true));
      return;
    }
    if (event.target.closest("#customerEmailContactForm")) {
      event.preventDefault();
      saveCustomerEmailContact().catch((error) => showInlineError(error.message, true));
      return;
    }
    if (event.target.closest("#customerEmailCcForm")) {
      event.preventDefault();
      saveCustomerEmailCc().catch((error) => showInlineError(error.message, true));
      return;
    }
    if (event.target.closest("#customerEmailTestForm")) {
      event.preventDefault();
      sendCustomerEmailTest().catch((error) => showInlineError(error.message, true));
      return;
    }
    if (event.target.closest("#bayManualRuleForm")) {
      event.preventDefault();
      saveBayManualRule().catch((error) => showInlineError(error.message, true));
      return;
    }
    if (event.target.closest("#bayBarcodeRuleForm")) {
      event.preventDefault();
      saveBayBarcodeRule().catch((error) => showInlineError(error.message, true));
      return;
    }
    if (event.target.closest("#bayAutoAssignerForm")) {
      event.preventDefault();
      saveBayAutoAssignerSettings().catch((error) => showInlineError(error.message, true));
      return;
    }
  });
  els.customerRouteRuleForm?.addEventListener("submit", (event) => {
    event.preventDefault();
    saveCustomerRouteRule().catch((error) => showInlineError(error.message, true));
  });
  els.manualEditSearchBtn?.addEventListener("click", () => runManualEditSearch().catch((error) => showInlineError(error.message)));
  els.manualEditStageSelect?.addEventListener("change", () => {
    if ((els.manualEditSearch?.value.trim() || "").length >= 2) runManualEditSearch().catch((error) => showInlineError(error.message));
  });
  els.manualEditSearch?.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      runManualEditSearch().catch((error) => showInlineError(error.message));
    }
  });
  document.addEventListener("input", (event) => {
    const customField = event.target.closest("#manualEditModalResults [data-custom-field]");

    if (customField) {
      manualEditApplyCustomInput(customField);
      return;
    }

    const editField = event.target.closest("#manualEditModalResults [data-edit-field]");

    if (!editField) return;

    state.manualEditDirty = true;

    const row = editField.closest("[data-edit-row]");

    if (editField.type !== "hidden") {
      manualEditSyncChoiceSelect(editField);
    }

    if (row && ["qty", "scanned"].includes(editField.dataset.editField)) {
      manualEditValidateRow(row);
    }
  });

  document.addEventListener("change", (event) => {
    const customerRouteCodeField = event.target.closest("#customerRouteSelectModal, [data-customer-route-route]");

    if (customerRouteCodeField) {
      const route = customerRouteValue(customerRouteCodeField.value || "CPU");
      const defaultAddress = customerRouteDefaultAddress(route);
      const row = customerRouteCodeField.closest(".customer-route-rule-row");
      const addressInput = row
        ? row.querySelector("[data-customer-route-address]")
        : document.getElementById("customerRouteAddressInputModal");

      if (addressInput && defaultAddress && !addressInput.value.trim()) {
        addressInput.value = defaultAddress;
      }
      return;
    }

    const rackQuickSelect = event.target.closest("#rackManagerQuickRackSelect");

    if (rackQuickSelect) {
      populateRackManagerQuickEdit(rackQuickSelect.value);
      return;
    }

    const rackStatusFilter = event.target.closest("[data-rack-status-filter]");

    if (rackStatusFilter) {
      state.rackStatusFilter = rackStatusFilter.value || "all";
      renderRacksPage();
      return;
    }

    const rackSortSelect = event.target.closest("[data-rack-sort]");

    if (rackSortSelect) {
      state.rackSort = rackSortSelect.value || "code-asc";
      renderRacksPage();
      return;
    }

    const choiceSelect = event.target.closest("#manualEditModalResults .manual-edit-choice-select");

    if (choiceSelect) {
      manualEditApplyChoiceSelect(choiceSelect);
      state.manualEditDirty = true;
      return;
    }

    const editField = event.target.closest("#manualEditModalResults [data-edit-field]");

    if (editField) {
      state.manualEditDirty = true;

      const row = editField.closest("[data-edit-row]");

      if (editField.type !== "hidden") {
        manualEditSyncChoiceSelect(editField);
      }

      if (row && ["qty", "scanned"].includes(editField.dataset.editField)) {
        manualEditValidateRow(row);
      }

      return;
    }

    if (event.target.closest("#manualEditModalStage")) {
      if (state.manualEditDirty && !window.confirm("You have unsaved manual delivery-list edits. Load another stage without saving?")) {
        event.target.value = state.manualEditListId || "";
        return;
      }

      state.manualEditDirty = false;
      runManualEditModalSearch(true).catch((error) => showInlineError(error.message, true));
    }
  });
  document.addEventListener("keydown", (event) => {
    if (event.target.closest("#manualEditModalSearch") && event.key === "Enter") {
      event.preventDefault();
      runManualEditModalSearch(false).catch((error) => showInlineError(error.message, true));
    }
  });
  els.bayMapSearch?.addEventListener("input", () => {
    const hadSearch = Boolean(state.baySearch.trim());
    state.baySearch = els.bayMapSearch.value;
    if (hadSearch && !state.baySearch.trim()) collapseAllPhysicalBaySections();
    renderBayMapPage();
  });
  els.bayMapSearch?.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      state.baySearch = els.bayMapSearch.value;
      scrollToBaySearchMatch();
    }
  });
  els.bayStatusFilter?.addEventListener("change", () => {
    state.bayStatusFilter = els.bayStatusFilter.value;
    if (state.bayStatusFilter === "all") collapseAllPhysicalBaySections();
    renderBayMapPage();
  });
  els.bayGlassFilter?.addEventListener("change", () => {
    state.bayGlassFilter = els.bayGlassFilter.value;
    renderBayMapPage();
  });
  els.baySpecialFilter?.addEventListener("change", () => {
    state.baySpecialFilter = els.baySpecialFilter.value;
    renderBayMapPage();
  });
  els.bayCategoryFilters?.addEventListener("click", (event) => {
    const target = event.target.closest("[data-bay-category-filter]");
    if (!target) return;
    state.bayCategoryFilter = target.dataset.bayCategoryFilter || "all";
    renderBayMapPage();
  });
  els.bayCheckBtn?.addEventListener("click", () => {
    state.baySearch = els.bayMapSearch?.value || "";
    scrollToBaySearchMatch();
  });
  els.bayClearFiltersBtn?.addEventListener("click", resetBayFilters);
  els.bayScanOutForm?.addEventListener("submit", (event) => {
    event.preventDefault();
    submitBayScanOut().catch((error) => showInlineError(error.message, true));
  });
  els.bayManualSubmitBtn?.addEventListener("click", () => submitManualBayScan().catch((error) => showInlineError(error.message, true)));
  const updateBayScanModeUi = () => {
    if (els.bayScanOutInput) els.bayScanOutInput.placeholder = els.bayScanModeToggle?.checked ? "Scan order to add to selected bay..." : "Scan order to remove from bay...";
  };
  document.querySelectorAll('input[name="bayScanVisualMode"]').forEach((input) => input.addEventListener("change", updateBayScanModeUi));
  document.getElementById("bayTargetClearBtn")?.addEventListener("click", () => {
    if (els.bayScanBayInput) els.bayScanBayInput.value = "";
    if (els.bayScanModeToggle) els.bayScanModeToggle.checked = false;
    if (els.bayScanOutInput) els.bayScanOutInput.placeholder = "Scan order to remove from bay...";
  });
  els.bayUndoBtn?.addEventListener("click", () => runBayHistory("undo").catch((error) => showInlineError(error.message, true)));
  els.bayRedoBtn?.addEventListener("click", () => runBayHistory("redo").catch((error) => showInlineError(error.message, true)));
  els.bayMapCanvas?.addEventListener("click", (event) => {
    const bayEditorOpenButton = event.target.closest("[data-bay-editor-open]");
    if (bayEditorOpenButton) {
      event.preventDefault();
      event.stopPropagation();
      openBayEditorPanel(bayEditorOpenButton.dataset.bayEditorOpen || "");
      return;
    }
    const columnButton = event.target.closest("[data-bay-col-action]");
    if (columnButton) {
      event.preventDefault();
      event.stopPropagation();
      const section = columnButton.dataset.baySection || "";
      const current = Math.max(1, Math.min(Number(state.bayGroupColumns[section] || 1), 2));
      state.bayGroupColumns[section] = columnButton.dataset.bayColAction === "inc" ? Math.min(current + 1, 2) : Math.max(current - 1, 1);
      renderBayMapPage();
      return;
    }
    const target = event.target.closest("[data-bay-code]");
    if (!target) return;
    if (state.pendingBayMove?.assignmentId) {
      const pendingMove = { ...state.pendingBayMove };
      const newBayCode = target.dataset.bayCode || "";
      const label = `${pendingMove.order}-${pendingMove.item}`;
      if (newBayCode && window.confirm(`Move ${label} to ${newBayCode}?`)) {
        postBayAction("/api/indian-trail/move", {
          assignmentId: pendingMove.assignmentId,
          newBayCode,
          reason: `Moved from ${pendingMove.fromBay}`,
        })
          .then(() => {
            if (pendingMove.fromBay) {
              pushBayHistory({
                label: `move ${label}`,
                undo: () => postBayAction("/api/indian-trail/move", { assignmentId: pendingMove.assignmentId, newBayCode: pendingMove.fromBay, reason: `Undo move from ${newBayCode}` }),
                redo: () => postBayAction("/api/indian-trail/move", { assignmentId: pendingMove.assignmentId, newBayCode, reason: `Redo move from ${pendingMove.fromBay}` }),
              });
            }
            showFloatingNotice(`Moved ${label} to ${newBayCode}.`, "success");
            scanFlash("success");
          })
          .catch((error) => showInlineError(error.message, true));
      }
      state.pendingBayMove = null;
      document.body.classList.remove("bay-move-mode");
      return;
    }
    selectBay(target.dataset.bayCode || "");
  });
  els.baySelectedCloseBtn?.addEventListener("click", () => closeSelectedBayModal());
  els.baySelectedBackdrop?.addEventListener("click", () => closeSelectedBayModal());
  els.bayActionButtons?.addEventListener("click", (event) => {
    const target = event.target.closest("[data-bay-action]");
    if (!target) return;
    runBayAction(target.dataset.bayAction).catch((error) => showInlineError(error.message, true));
  });
  els.sdiCloseBtn?.addEventListener("click", () => closeSdiPanel());
  els.sdiBackdrop?.addEventListener("click", () => closeSdiPanel());
  els.manageItemsCloseBtn?.addEventListener("click", () => closeManageItemsPanel());
  els.manageItemsBackdrop?.addEventListener("click", () => closeManageItemsPanel());
  els.bayEditorCloseBtn?.addEventListener("click", () => closeBayEditorPanel());
  els.bayEditorBackdrop?.addEventListener("click", () => closeBayEditorPanel());
  els.bayEditorNewGroupBtn?.addEventListener("click", () => {
    state.bayEditorSelectedGroup = "";
    renderBayEditorPanel();
    setTimeout(() => document.getElementById("bayEditorNewGroupNameInput")?.focus(), 0);
  });
  els.bayEditorGroupList?.addEventListener("click", (event) => {
    const row = event.target.closest("[data-bay-editor-group]");
    if (!row) return;
    state.bayEditorSelectedGroup = row.dataset.bayEditorGroup || "";
    renderBayEditorPanel();
  });
  els.bayEditorPanel?.addEventListener("click", (event) => {
    const actionButton = event.target.closest("[data-bay-editor-action]");
    if (!actionButton) return;
    event.preventDefault();
    const action = actionButton.dataset.bayEditorAction || "";
    const bayCode = actionButton.dataset.bayCode || "";
    const runner =
      action === "save-group" ? saveBayEditorGroup :
      action === "create-group" ? createBayEditorGroup :
      action === "add-bays" ? addBaysToEditorGroup :
      action === "delete-group" ? deleteBayEditorGroup :
      action === "save-bay" ? () => saveBayEditorBay(bayCode) :
      action === "delete-bay" ? () => deleteBayEditorBay(bayCode) : null;
    if (runner) runner().catch((error) => showInlineError(error.message, true));
  });
  els.bayAllScansBtn?.addEventListener("click", () => openBayAllScansModal());
  els.manageItemsSearch?.addEventListener("input", () => {
    state.manageItemsQuery = els.manageItemsSearch.value;
    renderManageItemsPanel();
  });
  els.manageItemsList?.addEventListener("click", (event) => {
    const row = event.target.closest("[data-manage-assignment-id]");
    if (!row) return;
    state.manageItemsSelectedId = row.dataset.manageAssignmentId || "";
    renderManageItemsPanel();
  });
  els.manageItemsMoveBtn?.addEventListener("click", () => moveManagedItem().catch((error) => showInlineError(error.message, true)));
  els.manageItemsClearBtn?.addEventListener("click", () => clearManagedItem().catch((error) => showInlineError(error.message, true)));
  els.manageItemsScannerBtn?.addEventListener("click", () => useManagedBayForScanner());
  els.manageItemsSdiBtn?.addEventListener("click", () => {
    const selected = selectedManageItem();
    if (!selected?.assignment?.id) {
      showInlineError("Select an item before opening SDI.", false);
      return;
    }
    closeManageItemsPanel();
    openSdiPanel(selected.assignment.id);
  });
  els.staleBayCloseBtn?.addEventListener("click", () => closeStaleBayPanel());
  els.staleBayOkBtn?.addEventListener("click", () => closeStaleBayPanel());
  els.staleBayBackdrop?.addEventListener("click", () => closeStaleBayPanel());
  els.staleBayPrintBtn?.addEventListener("click", () => launchManagedPrint("/api/indian-trail/stale-bays/print"));
  els.adminModalClose?.addEventListener("click", () => closeAdminModal());
  els.adminModalBackdrop?.addEventListener("click", () => closeAdminModal());
  els.staleBaySnoozeAllBtn?.addEventListener("click", () => {
    const ids = (state.staleBayOrders || []).map((order) => order.assignmentId).filter(Boolean);
    if (!ids.length) return;
    snoozeStaleBayOrders(ids, Number(els.staleBaySnoozeAllDays?.value || 1)).catch((error) => showInlineError(error.message, true));
  });
  els.staleBayList?.addEventListener("click", (event) => {
    const target = event.target.closest("[data-stale-snooze]");
    if (!target) return;
    const assignmentId = target.dataset.staleSnooze;
    const days = Number(els.staleBayList.querySelector(`[data-stale-days="${CSS.escape(String(assignmentId))}"]`)?.value || 1);
    snoozeStaleBayOrders([assignmentId], days).catch((error) => showInlineError(error.message, true));
  });
  els.sdiClearBtn?.addEventListener("click", () => submitSdi(false).catch((error) => showInlineError(error.message, true)));
  els.sdiForm?.addEventListener("submit", (event) => {
    event.preventDefault();
    submitSdi(true).catch((error) => showInlineError(error.message, true));
  });
  els.bayLayoutCloseBtn?.addEventListener("click", () => closeBayLayoutManager());
  els.bayLayoutSelect?.addEventListener("change", () => populateBayLayoutForm());
  els.bayLayoutSaveBtn?.addEventListener("click", () => saveBayLayoutForm().catch((error) => showInlineError(error.message, true)));
  els.bayLayoutDeleteBtn?.addEventListener("click", () => deleteSelectedBay().catch((error) => showInlineError(error.message, true)));
  els.bayLayoutUndoBtn?.addEventListener("click", () => runBayLayoutHistory("undo").catch((error) => showInlineError(error.message, true)));
  els.bayLayoutRedoBtn?.addEventListener("click", () => runBayLayoutHistory("redo").catch((error) => showInlineError(error.message, true)));
  els.bayLayoutConfirmBtn?.addEventListener("click", () => confirmBayLayoutDraft().catch((error) => showInlineError(error.message, true)));
  els.bayLayoutCancelBtn?.addEventListener("click", () => cancelBayLayoutDraft());
  els.bayCollapseAllBtn?.addEventListener("click", () => {
    collapseAllPhysicalBaySections();
    renderBayMapPage();
  });
  els.bayExpandAllBtn?.addEventListener("click", () => {
    state.collapsedBaySections.clear();
    renderBayMapPage();
  });
  els.bayHoldAllBtn?.addEventListener("click", () => holdAllBaySections());
  window.addEventListener("beforeunload", (event) => {
    if ((state.bayEditMode && state.bayHoldingSections.size) || state.manualEditDirty) {
      event.preventDefault();
      event.returnValue = "";
    }
  });
  for (const container of [els.bayMapCanvas, els.bayAllBaysList]) {
    container?.addEventListener("dragstart", (event) => {
      const groupTarget = event.target.closest("[data-bay-group-drag]");
      if (groupTarget && state.bayEditMode && hasPermission("manage_bay_layout")) {
        event.dataTransfer.setData("text/bay-group", groupTarget.dataset.bayGroupDrag || "");
        event.dataTransfer.effectAllowed = "move";
        return;
      }
      const target = event.target.closest("[data-bay-code]");
      if (!target || !state.bayEditMode || !hasPermission("manage_bay_layout")) return;
      event.dataTransfer.setData("text/plain", target.dataset.bayCode || "");
      event.dataTransfer.effectAllowed = "move";
    });
    container?.addEventListener("dragover", (event) => {
      const target = event.target.closest("[data-bay-holding-drop], [data-bay-grid-cell], [data-bay-drop-section]");
      if (!target || !state.bayEditMode || !hasPermission("manage_bay_layout")) return;
      event.preventDefault();
      if (event.clientY < 90) window.scrollBy({ top: -24, behavior: "auto" });
      if (window.innerHeight - event.clientY < 90) window.scrollBy({ top: 24, behavior: "auto" });
      event.dataTransfer.dropEffect = "move";
    });
    container?.addEventListener("drop", (event) => {
      const target = event.target.closest("[data-bay-holding-drop], [data-bay-grid-cell], [data-bay-drop-section]");
      if (!target || !state.bayEditMode || !hasPermission("manage_bay_layout")) return;
      event.preventDefault();
      const sourceGroup = event.dataTransfer.getData("text/bay-group");
      if (sourceGroup) {
        if (target.dataset.bayHoldingDrop === "true") {
          moveBaySectionDraft(sourceGroup, 0, 0, true);
          return;
        }
        if (target.dataset.bayGridCell === "true") {
          moveBaySectionDraft(sourceGroup, Number(target.dataset.gridRow || 1), Number(target.dataset.gridCol || 1), false);
          return;
        }
        swapBayGroups(sourceGroup, target.dataset.bayDropSection || "").catch((error) => showInlineError(error.message, true));
        return;
      }
      const bayCode = event.dataTransfer.getData("text/plain");
      if (target.dataset.bayGridCell === "true" || target.dataset.bayHoldingDrop === "true") {
        showFloatingNotice("Use the grouped bay header to move bay sets around the edit grid.", "notice");
        return;
      }
      const targetBay = event.target.closest("[data-bay-code]");
      moveBayToGroup(bayCode, target.dataset.bayDropSection || "", target.dataset.bayDropCategory || "", targetBay?.dataset.bayCode || "").catch((error) => showInlineError(error.message, true));
    });
  }

  document.addEventListener("click", (event) => {
    if (
      els.headerGlobalSearchResults &&
      !event.target.closest(".global-search") &&
      !event.target.closest("#headerGlobalSearchResults")
    ) {
      els.headerGlobalSearchResults.hidden = true;
    }

    const rackHeaderAction = event.target.closest(".rack-summary-actions button");

    if (rackHeaderAction) {
      event.preventDefault();
    }

     const openGlassMenu = event.target.closest(".glass-filter-more");

    document.querySelectorAll(".glass-filter-more[open]").forEach((menu) => {
      if (menu !== openGlassMenu) {
        menu.open = false;
      }
    });

    document.addEventListener("toggle", (event) => {
    const roleCard = event.target.closest?.(".role-permission-card[data-role-card]");

    if (roleCard && els.adminModalBody?.contains(roleCard)) {
      const roleName = roleCard.dataset.roleCard || "";

      if (roleCard.open) {
        state.rolePermissionOpenRoles.add(roleName);
      } else {
        state.rolePermissionOpenRoles.delete(roleName);
      }

      return;
    }

    const category = event.target.closest?.(".permission-category[data-role-name][data-category-title]");

    if (category && els.adminModalBody?.contains(category)) {
      const key = rolePermissionCategoryKey(category.dataset.roleName, category.dataset.categoryTitle);

      if (category.open) {
        state.rolePermissionOpenCategories.add(key);
      } else {
        state.rolePermissionOpenCategories.delete(key);
      }
    }
  }, true);

    const pageButton = event.target.closest("[data-page-target]");
    if (pageButton) {
      if (state.manualEditDirty && !window.confirm("You have unsaved manual delivery-list edits. Leave without saving?")) return;
      state.manualEditDirty = false;
      showPage(pageButton.dataset.pageTarget);
      return;
    }
    const adminModalButton = event.target.closest("[data-admin-modal]");
    if (adminModalButton) {
      const modalKind = adminModalButton.dataset.adminModal || "";

      if (modalKind === "lookups") {
        ensureManualEditLookupsLoaded()
          .then(() => openAdminModal("lookups"))
          .catch((error) => showInlineError(error.message, true));
      } else if (modalKind === "customerRoutes") {
        fetchJson("/api/admin/customer-route-rules")
          .then((payload) => {
            state.adminCustomerRouteRules = payload.rules || [];
            openAdminModal("customerRoutes");
          })
          .catch((error) => showInlineError(error.message, true));
      } else if (modalKind === "customerEmails") {
        refreshCustomerEmailSettings(false)
          .then(() => openAdminModal("customerEmails"))
          .catch((error) => showInlineError(error.message, true));
      } else if (modalKind === "deliveryLists" || modalKind === "deliveryActions") {
        loadDeliveryLists(state.activeListId)
          .then(() => openAdminModal(modalKind))
          .catch((error) => showInlineError(error.message, true));
      } else {
        openAdminModal(modalKind);
      }

      return;
    }
    const modalStationButton = event.target.closest("#addStationBtnModal");
    if (modalStationButton) {
      const input = document.getElementById("newStationInputModal");
      if (els.newStationInput && input) els.newStationInput.value = input.value;
      addStationFromInput()
        .then(() => openAdminModal("stations"))
        .catch((error) => showInlineError(error.message));
      return;
    }

    const rackManagerShell = event.target.closest(".rack-manager-shell");

    if (rackManagerShell) {
      const rackManagerNewRackButton = event.target.closest("[data-rack-manager-new-rack]");
      if (rackManagerNewRackButton) {
        event.preventDefault();
        openRackForm("");
        return;
      }

      const rackManagerNewSetButton = event.target.closest("[data-rack-manager-new-set]");
      if (rackManagerNewSetButton) {
        event.preventDefault();
        openRackSetForm("");
        return;
      }

      const rackManagerAddToSetButton = event.target.closest("[data-rack-manager-add-to-set]");
      if (rackManagerAddToSetButton) {
        event.preventDefault();
        const label = rackManagerAddToSetButton.dataset.rackManagerAddToSet || "";
        if (label === "Truck") {
          openRackForm("", nextTruckRackDefaults());
        } else {
          openRackForm("", { type: label, name: label ? `${label} Rack` : "" });
        }
        return;
      }

      const rackManagerEditButton = event.target.closest("[data-rack-edit]");
      if (rackManagerEditButton) {
        event.preventDefault();
        focusRackManagerRackEdit(rackManagerEditButton.dataset.rackEdit || "");
        return;
      }

      const rackManagerSetEditButton = event.target.closest("[data-rack-set-edit]");
      if (rackManagerSetEditButton) {
        event.preventDefault();
        openRackManagerSetEdit(rackManagerSetEditButton.dataset.rackSetEdit || "");
        return;
      }

      const rackManagerSetCancelButton = event.target.closest("[data-rack-manager-set-cancel]");
      if (rackManagerSetCancelButton) {
        event.preventDefault();
        state.rackManagerEditingSetLabel = "";
        els.adminModalBody.innerHTML = adminModalContent("racks");
        return;
      }

      const rackManagerInlineCancelButton = event.target.closest("[data-rack-inline-cancel]");
      if (rackManagerInlineCancelButton) {
        event.preventDefault();
        state.rackManagerEditingRackCode = "";
        els.adminModalBody.innerHTML = adminModalContent("racks");
        return;
      }

      const rackManagerDeleteButton = event.target.closest("[data-rack-delete]");
      if (rackManagerDeleteButton) {
        event.preventDefault();
        deleteRackDefinition(rackManagerDeleteButton.dataset.rackDelete || "").catch((error) => showInlineError(error.message, true));
        return;
      }

      const rackManagerSetDeleteButton = event.target.closest("[data-rack-set-delete]");
      if (rackManagerSetDeleteButton) {
        event.preventDefault();
        deleteRackSet(rackManagerSetDeleteButton.dataset.rackSetDelete || "").catch((error) => showInlineError(error.message, true));
        return;
      }
    }
    const manualCustomClearButton = event.target.closest("[data-manual-custom-clear]");
    if (manualCustomClearButton) {
      event.preventDefault();
      manualEditClearCustomChoice(manualCustomClearButton);
      return;
    }
    const manualEditBackButton = event.target.closest("[data-manual-edit-back]");
    if (manualEditBackButton) {
      event.preventDefault();

      if (state.manualEditDirty && !window.confirm("You have unsaved manual delivery-list edits. Go back without saving?")) {
        return;
      }

      state.manualEditDirty = false;
      openAdminModal("deliveryLists");

      return;
    }
    const manualModalSearchButton = event.target.closest("#manualEditModalSearchBtn");
    if (manualModalSearchButton) {
      runManualEditModalSearch(false).catch((error) => showInlineError(error.message, true));
      return;
    }
    const manualModalReloadButton = event.target.closest("#manualEditModalReloadBtn");
    if (manualModalReloadButton) {
      runManualEditModalSearch(true).catch((error) => showInlineError(error.message, true));
      return;
    }
    const adminReportButton = event.target.closest("[data-admin-report]");
    if (adminReportButton) {
      openPrintOptions({ date: dashboardDateKey(), listIds: state.lists.map((list) => list.id) });
      return;
    }
    const adminDeliveryLoadMoreButton = event.target.closest("[data-admin-delivery-load-more]");
    if (adminDeliveryLoadMoreButton) {
      state.adminDeliveryListVisiblePastDays += ADMIN_DELIVERY_LIST_LOAD_MORE_DAYS;
      renderAdminDeliveryListModalResults(state.lists, "");
      return;
    }
    const adminListEditButton = event.target.closest("[data-admin-list-edit]");
    if (adminListEditButton) {
      const listId = adminListEditButton.dataset.adminListEdit || "";
      if (els.manualEditStageSelect) els.manualEditStageSelect.value = listId;
      openManualEditForList(listId).catch((error) => showInlineError(error.message, true));
      return;
    }
    const adminDateResetButton = event.target.closest("[data-admin-date-reset]");
    if (adminDateResetButton) {
      event.preventDefault();
      event.stopPropagation();

      resetAdminScansForDate(adminDateResetButton.dataset.adminDateReset).catch((error) => showInlineError(error.message, true));

      return;
    }

    const adminDateDeleteButton = event.target.closest("[data-admin-date-delete]");
    if (adminDateDeleteButton) {
      event.preventDefault();
      event.stopPropagation();

      deleteAdminDeliveryDateByDate(adminDateDeleteButton.dataset.adminDateDelete).catch((error) => showInlineError(error.message, true));

      return;
    }
    const adminListResetButton = event.target.closest("[data-admin-list-reset]");
    if (adminListResetButton) {
      resetAdminScansForList(adminListResetButton.dataset.adminListReset).catch((error) => showInlineError(error.message, true));
      return;
    }
    const adminListDeleteButton = event.target.closest("[data-admin-list-delete]");
    if (adminListDeleteButton) {
      deleteAdminDeliveryListById(adminListDeleteButton.dataset.adminListDelete).catch((error) => showInlineError(error.message, true));
      return;
    }
    const openTransitButton = event.target.closest("[data-open-transit-manifest]");
    if (openTransitButton) {
      openInTransitManifest().catch((error) => showInlineError(error.message, true));
      return;
    }

    const closeTransitButton = event.target.closest("[data-close-transit-manifest]");
    if (closeTransitButton) {
      closeInTransitManifest();
      return;
    }

    const openListButton = event.target.closest("[data-open-list]");
    if (openListButton) {
      const searchText = openListButton.dataset.openSearch || "";
      activateList(openListButton.dataset.openList)
        .then(() => {
          if (searchText) {
            state.search = searchText;
            if (els.searchInput) els.searchInput.value = searchText;
            renderScanPage();
            window.setTimeout(() => document.querySelector("[data-id]")?.scrollIntoView({ behavior: "smooth", block: "center" }), 150);
          }
        })
        .catch((error) => showInlineError(error.message));
      if (els.headerGlobalSearchResults) els.headerGlobalSearchResults.hidden = true;
      return;
    }
    const openBayButton = event.target.closest("[data-open-bay]");
    if (openBayButton) {
      state.selectedBayCode = openBayButton.dataset.openBay || "";
      if (els.headerGlobalSearchResults) els.headerGlobalSearchResults.hidden = true;
      showPage("bays");
      window.setTimeout(() => {
        state.baySearch = state.selectedBayCode;
        scrollToBaySearchMatch();
      }, 350);
      return;
    }
    const filterButton = event.target.closest("[data-filter]");
    if (filterButton) {
      state.filter = filterButton.dataset.filter;
      state.pageIndex = 1;
      document.querySelectorAll("[data-filter]").forEach((button) => button.classList.toggle("is-active", button.dataset.filter === state.filter));
      renderScanPage();
      return;
    }
    const glassFilterButton = event.target.closest("[data-glass-filter]");
    if (glassFilterButton) {
      state.glassTypeFilter = glassFilterButton.dataset.glassFilter || "all";
      state.pageIndex = 1;
      renderScanPage();
      return;
    }
    const pageNumber = event.target.closest("[data-page-number]");
    if (pageNumber) {
      state.pageIndex = Number(pageNumber.dataset.pageNumber) || 1;
      renderScanPage();
      return;
    }
    const pageAction = event.target.closest("[data-page-action]");
    if (pageAction) {
      state.pageIndex += pageAction.dataset.pageAction === "next" ? 1 : -1;
      renderScanPage();
      return;
    }
    const homePageAction = event.target.closest("[data-home-page-action]");
    if (homePageAction) {
      state.homePageIndex += homePageAction.dataset.homePageAction === "next" ? 1 : -1;
      renderHome();
      return;
    }
    const glassToggle = event.target.closest("[data-toggle-glass-group]");
    if (glassToggle) {
      const label = glassToggle.dataset.toggleGlassGroup || "";
      if (state.collapsedGlassTypes.has(label)) state.collapsedGlassTypes.delete(label);
      else state.collapsedGlassTypes.add(label);
      renderScanPage();
      return;
    }
    if (event.target === els.scanBayOverrideClearBtn) {
      state.selectedBayOverrideCode = "";
      state.bayOverrideMode = "auto";
      renderScanBayOverrideTools();
      els.scanInput?.focus();
      return;
    }

    if (event.target.closest(".line-rack-location-control, [data-line-rack-select]")) {
      event.stopPropagation();
      return;
    }

    const row = event.target.closest("#listRows tr[data-id]");
    if (row) {
      if (state.selectedId === row.dataset.id) return;
      state.selectedId = row.dataset.id;
      saveState();
      if (canAssignRackLocation()) {
        ensureRacksLoaded()
          .then(() => renderScanPage())
          .catch((error) => showInlineError(error.message, true));
      } else {
        renderScanPage();
      }
      return;
    }
    const removeStationButton = event.target.closest("[data-remove-station]");
    if (removeStationButton) {
      removeStation(removeStationButton.dataset.removeStation).catch((error) => showInlineError(error.message));
      return;
    }
    const renameStationButton = event.target.closest("[data-rename-station]");
    if (renameStationButton) {
      const oldName = renameStationButton.dataset.renameStation;
      const input = document.querySelector(`[data-station-name="${CSS.escape(oldName)}"]`);
      fetchJson("/api/stations/rename", {
        method: "POST",
        body: JSON.stringify({ oldName, newName: input?.value || "" }),
      })
        .then((payload) => {
          state.stations = uniqueText([...(payload.stations || [])]);
          renderStationOptions();
          renderAdminStations();
        })
        .catch((error) => showInlineError(error.message));
      return;
    }
    const deactivateUserButton = event.target.closest("[data-deactivate-user]");
    if (deactivateUserButton) {
      const username = deactivateUserButton.dataset.deactivateUser || "";

      confirmDeactivateUser(username).then((confirmed) => {
        if (!confirmed) return;

        fetchJson("/api/admin/users/deactivate", {
          method: "POST",
          body: JSON.stringify({ username }),
        })
          .then(() => refreshAdminUsersUi())
          .catch((error) => showInlineError(error.message));
      });

      return;
    }

    const reactivateUserButton = event.target.closest("[data-reactivate-user]");
    if (reactivateUserButton) {
      const username = reactivateUserButton.dataset.reactivateUser || "";

      fetchJson("/api/admin/users/reactivate", {
        method: "POST",
        body: JSON.stringify({ username }),
      })
        .then(() => refreshAdminUsersUi())
        .catch((error) => showInlineError(error.message));

      return;
    }

    const deleteUserButton = event.target.closest("[data-delete-user]");
    if (deleteUserButton) {
      const username = deleteUserButton.dataset.deleteUser || "";

      confirmWebAppAction({
        title: "Delete user?",
        message: `Delete <strong>${escapeHtml(username)}</strong> from the scanner app.`,
        details: "This removes the login profile. Audit history stays attached to the saved username text.",
        confirmLabel: "Delete user",
      }).then((confirmed) => {
        if (!confirmed) return;

        fetchJson("/api/admin/users/delete", {
          method: "POST",
          body: JSON.stringify({ username }),
        })
          .then(() => refreshAdminUsersUi())
          .catch((error) => showInlineError(error.message));
      });

      return;
    }

    const generatePasswordButton = event.target.closest("[data-generate-user-password]");
    if (generatePasswordButton) {
      const username = generatePasswordButton.dataset.generateUserPassword;
      const input = document.querySelector(`[data-user-password="${CSS.escape(username)}"]`);

      if (input) {
        input.value = generateTemporaryPassword();
        input.type = "text";
        input.focus();
        input.select();
      }

      showFloatingNotice("Temporary password generated. Save it, then give it to the user.", "notice");

      return;
    }

    const togglePasswordButton = event.target.closest("[data-toggle-password]");
    if (togglePasswordButton) {
      const username = togglePasswordButton.dataset.togglePassword;
      const input = document.querySelector(`[data-user-password="${CSS.escape(username)}"]`);

      if (input) input.type = input.type === "password" ? "text" : "password";

      return;
    }

    const updatePasswordButton = event.target.closest("[data-update-user-password]");
    if (updatePasswordButton) {
      const username = updatePasswordButton.dataset.updateUserPassword;
      const input = document.querySelector(`[data-user-password="${CSS.escape(username)}"]`);
      const password = input?.value || "";

      if (!password.trim()) {
        showFloatingNotice("Enter or generate a new password before saving.", "notice");
        input?.focus();
        return;
      }

      fetchJson("/api/admin/users/password", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      })
        .then(() => {
          if (input) input.value = "";
          showFloatingNotice(`Password updated for ${username}.`, "success");
          return refreshAdminUsersUi();
        })
        .catch((error) => showInlineError(error.message));

      return;
    }

    const updateUserRoleButton = event.target.closest("[data-update-user-role]");
    if (updateUserRoleButton) {
      const username = updateUserRoleButton.dataset.updateUserRole;
      const select = document.querySelector(`[data-user-role-select="${CSS.escape(username)}"]`);
      const stationList = document.querySelector(`[data-user-station-list="${CSS.escape(username)}"]`);
      const assignedStations = Array.from(stationList?.querySelectorAll("input[type='checkbox']:checked") || [])
        .map((input) => input.value)
        .filter(Boolean);
      const emailInput = document.querySelector(`[data-user-email="${CSS.escape(username)}"]`);

      fetchJson("/api/admin/users/roles", {
        method: "POST",
        body: JSON.stringify({
          username,
          roles: [select?.value || "Operator"],
          station: assignedStations.join(", "),
          email: emailInput?.value || "",
        }),
      })
        .then(() => refreshAdminUsersUi())
        .catch((error) => showInlineError(error.message));

      return;
    }

    const saveRolePermissionsButton = event.target.closest("[data-save-role-permissions]");
    if (saveRolePermissionsButton) {
      event.preventDefault();
      event.stopPropagation();

      saveRolePermissions(saveRolePermissionsButton.dataset.saveRolePermissions).catch((error) => showInlineError(error.message, true));

      return;
    }
    const saveLineItemButton = event.target.closest("[data-save-line-item]");
    if (saveLineItemButton) {
      saveManualLineItem(saveLineItemButton.dataset.saveLineItem).catch((error) => showInlineError(error.message));
      return;
    }
    const deleteLineItemButton = event.target.closest("[data-delete-line-item]");
    if (deleteLineItemButton) {
      deleteManualLineItem(deleteLineItemButton.dataset.deleteLineItem).catch((error) => showInlineError(error.message, true));
      return;
    }
    const saveCustomerRouteButton = event.target.closest("[data-save-customer-route-rule]");
    if (saveCustomerRouteButton) {
      saveCustomerRouteRuleRow(saveCustomerRouteButton.dataset.saveCustomerRouteRule).catch((error) => showInlineError(error.message, true));
      return;
    }

    const removeCustomerRouteButton = event.target.closest("[data-remove-customer-route-rule]");
    if (removeCustomerRouteButton) {
      removeCustomerRouteRule(removeCustomerRouteButton.dataset.removeCustomerRouteRule).catch((error) => showInlineError(error.message, true));
      return;
    }

    const editCustomerEmailButton = event.target.closest("[data-edit-customer-email]");
    if (editCustomerEmailButton) {
      startCustomerEmailEdit(editCustomerEmailButton.dataset.editCustomerEmail);
      return;
    }

    const removeBayManualRuleButton = event.target.closest("[data-remove-bay-manual-rule]");
    if (removeBayManualRuleButton) {
      removeBayScannerRule("manual", removeBayManualRuleButton.dataset.removeBayManualRule).catch((error) => showInlineError(error.message, true));
      return;
    }

    const removeBayBarcodeRuleButton = event.target.closest("[data-remove-bay-barcode-rule]");
    if (removeBayBarcodeRuleButton) {
      removeBayScannerRule("barcode", removeBayBarcodeRuleButton.dataset.removeBayBarcodeRule).catch((error) => showInlineError(error.message, true));
      return;
    }

    const removeCustomerEmailButton = event.target.closest("[data-remove-customer-email]");
    if (removeCustomerEmailButton) {
      removeCustomerEmailContact(removeCustomerEmailButton.dataset.removeCustomerEmail).catch((error) => showInlineError(error.message, true));
      return;
    }

    const removeCustomerEmailCcButton = event.target.closest("[data-remove-customer-email-cc]");
    if (removeCustomerEmailCcButton) {
      removeCustomerEmailCc(removeCustomerEmailCcButton.dataset.removeCustomerEmailCc).catch((error) => showInlineError(error.message, true));
      return;
    }

    const openEmailDraftButton = event.target.closest("[data-open-email-draft]");
    if (openEmailDraftButton) {
      openEmailDraftPreview(openEmailDraftButton.dataset.openEmailDraft);
      return;
    }

    const closeEmailDraftButton = event.target.closest("[data-close-email-draft]");
    if (closeEmailDraftButton) {
      closeEmailDraftPreview();
      return;
    }

    const copyEmailDraftButton = event.target.closest("[data-copy-email-draft]");
    if (copyEmailDraftButton) {
      copyEmailDraftBody(copyEmailDraftButton.dataset.copyEmailDraft).catch((error) => showInlineError(error.message, true));
      return;
    }

    const mailtoEmailDraftButton = event.target.closest("[data-mailto-email-draft]");
    if (mailtoEmailDraftButton) {
      openEmailDraftMailto(mailtoEmailDraftButton.dataset.mailtoEmailDraft);
      return;
    }

    const emailManifestPdfButton = event.target.closest("[data-email-manifest-pdf]");
    if (emailManifestPdfButton) {
      const id = encodeURIComponent(emailManifestPdfButton.dataset.emailManifestPdf || "");
      if (id) launchManagedPrint(`/api/admin/customer-emails/${id}/manifest-pdf`);
      return;
    }

    const printListsButton = event.target.closest("[data-print-lists]");
    if (printListsButton) {
      event.preventDefault();
      event.stopPropagation();

      const listIds = String(printListsButton.dataset.printLists || "")
        .split(",")
        .filter(Boolean);
      const firstList = state.lists.find((list) => list.id === listIds[0]);
      const date = printListsButton.dataset.printDate || firstList?.deliveryDate || selectedDeliveryDate();
      const updatedOnly = printListsButton.dataset.printUpdatedOnly === "1";

      if (listIds.length) {
        openPrintOptions({ date, listIds, updatedOnly });
      }

      return;
    }
    const printActiveButton = event.target.closest("[data-print-active]");
    if (printActiveButton) {
      const date = printActiveButton.dataset.printActive === "home" || printActiveButton.dataset.printActive === "bays" ? dashboardDateKey() : state.meta?.deliveryDate;
      const listIds = state.lists.filter((list) => !date || list.deliveryDate === date).map((list) => list.id);
      openPrintOptions({ date, listIds });
      return;
    }
    const bayCell = event.target.closest("[data-bay-code]");
    if (bayCell?.dataset.bayCode) {
      if (els.bayMapCanvas?.contains(bayCell)) return;
      selectBay(bayCell.dataset.bayCode || "");
      return;
    }
    const manualAssignBay = event.target.closest("[data-manual-assign-bay]");
    if (manualAssignBay) {
      postBayAction("/api/indian-trail/assign", {
        lineItemId: manualAssignBay.dataset.lineItemId,
        bayCode: manualAssignBay.dataset.manualAssignBay,
        assignedQty: manualAssignBay.dataset.assignedQty || 1,
        reason: "Manual assignment from Indian Trail scan page",
      })
        .then(() => {
          if (els.manualAssignStatus) els.manualAssignStatus.innerHTML = `<article class="message-card ok"><strong>Assigned</strong><span>Bay ${escapeHtml(manualAssignBay.dataset.manualAssignBay)} selected.</span></article>`;
        })
        .catch((error) => showInlineError(error.message, true));
      return;
    }
    const assignmentAction = event.target.closest("[data-assignment-action]");
    if (assignmentAction) {
      runAssignmentAction(assignmentAction.dataset.assignmentAction, assignmentAction.dataset.assignmentId).catch((error) => showInlineError(error.message, true));
      return;
    }
    const bayAction = event.target.closest("[data-bay-action]");
    if (bayAction && !els.bayActionButtons?.contains(bayAction)) {
      runBayAction(bayAction.dataset.bayAction).catch((error) => showInlineError(error.message, true));
      return;
    }
    const navButton = event.target.closest("[data-mobile-target]");
    if (navButton) {
      showPage("scan");
      document.body.dataset.mobileView = navButton.dataset.mobileTarget;
      document.querySelectorAll("[data-mobile-target]").forEach((button) => button.classList.toggle("is-active", button === navButton));
    }
  });
}

init().catch((error) => {
  document.body.innerHTML = `<main class="app"><section class="last-card error"><strong>Unable to load delivery list</strong><p>${escapeHtml(error.message)}</p></section></main>`;
});

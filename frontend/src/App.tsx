import React, { useState, useEffect } from 'react';
import { 
  Plus, 
  Trash2, 
  Bell, 
  TrendingDown, 
  ExternalLink, 
  Globe, 
  RefreshCw, 
  AlertCircle, 
  CheckCircle2, 
  Activity, 
  Info,
  DollarSign
} from 'lucide-react';
import { 
  ResponsiveContainer, 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  Tooltip, 
  Legend, 
  CartesianGrid 
} from 'recharts';

// Types matching Backend Schemas
interface CompetitorURL {
  id: string;
  product_id: string;
  url: string;
  domain_selector_key: string;
  last_scraped_price: number | null;
  last_scraped_at: string | null;
  last_notified_price: number | null;
  error_count: number;
  last_error_message: string | null;
  is_active: boolean;
}

interface Product {
  id: string;
  name: string;
  target_price: number;
  alert_threshold_percent: number;
  is_active: boolean;
  created_at: string;
  competitor_urls: CompetitorURL[];
}

interface PriceHistoryNode {
  scraped_at: string;
  price: number;
  competitor_url: string;
}

interface SentAlert {
  id: string;
  product_id: string;
  competitor_url_id: string;
  previous_price: number | null;
  new_price: number;
  price_drop_percent: number;
  recipient_email: string;
  sent_at: string;
}

const API_BASE = "http://localhost:8000/api";

export default function App() {
  const [token, setToken] = useState<string | null>(localStorage.getItem("token"));
  const [products, setProducts] = useState<Product[]>([]);
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [priceHistory, setPriceHistory] = useState<PriceHistoryNode[]>([]);
  const [alerts, setAlerts] = useState<SentAlert[]>([]);
  
  // Form states
  const [newProductName, setNewProductName] = useState("");
  const [newProductTarget, setNewProductTarget] = useState("");
  const [newProductThreshold, setNewProductThreshold] = useState("5.00");
  const [newCompUrl, setNewCompUrl] = useState("");
  
  // Status states
  const [isScraping, setIsScraping] = useState(false);
  const [statusMessage, setStatusMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<'connected' | 'connecting' | 'disconnected'>('connecting');

  // Helper to show flash messages
  const showStatus = (text: string, type: 'success' | 'error' | 'info' = 'info') => {
    setStatusMessage({ text, type });
    setTimeout(() => setStatusMessage(null), 5000);
  };

  // 1. Authenticate Demo Account on mount
  useEffect(() => {
    const initAuth = async () => {
      try {
        const res = await fetch(`${API_BASE}/auth/demo`);
        if (!res.ok) throw new Error("Auth failed");
        const data = await res.json();
        localStorage.setItem("token", data.access_token);
        setToken(data.access_token);
        setConnectionStatus('connected');
      } catch (err) {
        console.error("Demo login failed:", err);
        setConnectionStatus('disconnected');
        showStatus("Could not connect to backend server. Make sure FastAPI app is running.", "error");
      }
    };

    if (!token) {
      initAuth();
    } else {
      setConnectionStatus('connected');
    }
  }, []);

  // 2. Fetch initial data once authenticated
  useEffect(() => {
    if (token) {
      fetchProducts();
      fetchAlerts();
    }
  }, [token]);

  // 3. Fetch price history when product selection changes
  useEffect(() => {
    if (token && selectedProduct) {
      fetchPriceHistory(selectedProduct.id);
    } else {
      setPriceHistory([]);
    }
  }, [selectedProduct]);

  // API Call: List Products
  const fetchProducts = async () => {
    try {
      const res = await fetch(`${API_BASE}/products/`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (!res.ok) throw new Error("Failed to load products");
      const data = await res.json();
      setProducts(data);
      // Update selected product reference if it exists
      if (selectedProduct) {
        const updated = data.find((p: Product) => p.id === selectedProduct.id);
        setSelectedProduct(updated || null);
      }
    } catch (err) {
      showStatus("Error loading products list", "error");
    }
  };

  // API Call: List Alerts
  const fetchAlerts = async () => {
    try {
      const res = await fetch(`${API_BASE}/alerts/`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (!res.ok) throw new Error("Failed to load alerts");
      const data = await res.json();
      setAlerts(data);
    } catch (err) {
      showStatus("Error loading alerts feed", "error");
    }
  };

  // API Call: Get Price History Nodes
  const fetchPriceHistory = async (productId: string) => {
    try {
      const res = await fetch(`${API_BASE}/analytics/price-history/${productId}/`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (!res.ok) throw new Error("Failed to load price history");
      const data = await res.json();
      setPriceHistory(data);
    } catch (err) {
      showStatus("Error loading price history analytics", "error");
    }
  };

  // Action: Add Tracked Product
  const handleAddProduct = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newProductName || !newProductTarget) return;

    try {
      const res = await fetch(`${API_BASE}/products/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          name: newProductName,
          target_price: parseFloat(newProductTarget),
          alert_threshold_percent: parseFloat(newProductThreshold)
        })
      });

      if (!res.ok) {
        const errDetail = await res.json();
        throw new Error(errDetail.detail || "Failed to create product");
      }

      showStatus("New product baseline added successfully", "success");
      setNewProductName("");
      setNewProductTarget("");
      setNewProductThreshold("5.00");
      fetchProducts();
    } catch (err: any) {
      showStatus(err.message, "error");
    }
  };

  // Action: Delete Tracked Product
  const handleDeleteProduct = async (id: string) => {
    if (!confirm("Are you sure you want to stop tracking this product and delete all history?")) return;
    try {
      const res = await fetch(`${API_BASE}/products/${id}`, {
        method: "DELETE",
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (!res.ok) throw new Error("Failed to delete product");
      
      showStatus("Product removed", "info");
      if (selectedProduct?.id === id) {
        setSelectedProduct(null);
      }
      fetchProducts();
      fetchAlerts();
    } catch (err) {
      showStatus("Error deleting product", "error");
    }
  };

  // Action: Add Competitor URL
  const handleAddCompetitor = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProduct || !newCompUrl) return;

    try {
      const res = await fetch(`${API_BASE}/products/${selectedProduct.id}/competitors/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ url: newCompUrl })
      });

      if (!res.ok) {
        const errDetail = await res.json();
        throw new Error(errDetail.detail || "Failed to add competitor link");
      }

      showStatus("Competitor URL registered and initial scrape executed", "success");
      setNewCompUrl("");
      fetchProducts();
      fetchAlerts();
    } catch (err: any) {
      showStatus(err.message, "error");
    }
  };

  // Action: Delete Competitor URL
  const handleDeleteCompetitor = async (id: string) => {
    try {
      const res = await fetch(`${API_BASE}/competitors/${id}`, {
        method: "DELETE",
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (!res.ok) throw new Error("Failed to delete competitor URL");
      
      showStatus("Competitor URL removed", "info");
      fetchProducts();
    } catch (err) {
      showStatus("Error removing competitor URL", "error");
    }
  };

  // Action: Trigger Scraper Loop
  const handleTriggerScrape = async () => {
    setIsScraping(true);
    showStatus("Scraping cycle initiated in background...", "info");
    try {
      const res = await fetch(`${API_BASE}/products/scrape-all`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${token}` }
      });
      const data = await res.json();
      
      setIsScraping(false);
      showStatus(
        `Scraping complete! Processed ${data.processed} links. ${data.alerts_triggered} alerts fired.`, 
        data.alerts_triggered > 0 ? "success" : "info"
      );
      fetchProducts();
      fetchAlerts();
      if (selectedProduct) {
        fetchPriceHistory(selectedProduct.id);
      }
    } catch (err) {
      setIsScraping(false);
      showStatus("Scrape cycle failed to execute", "error");
    }
  };

  // Format Recharts Chart Data
  const getChartData = () => {
    if (!selectedProduct || priceHistory.length === 0) return [];
    
    // Group nodes by scraped time (pivoting prices of multiple URLs into a single timestamp object)
    const timeGroups: { [key: string]: any } = {};
    
    priceHistory.forEach(node => {
      const dateStr = new Date(node.scraped_at).toLocaleString([], { 
        month: 'short', 
        day: 'numeric', 
        hour: '2-digit', 
        minute: '2-digit' 
      });
      
      if (!timeGroups[node.scraped_at]) {
        timeGroups[node.scraped_at] = {
          raw_time: node.scraped_at,
          formatted_time: dateStr,
          Baseline: parseFloat(selectedProduct.target_price.toString())
        };
      }
      
      // Use clean names for keys
      let displayName = "WebScraper.io";
      if (node.competitor_url.includes("books.toscrape")) {
        displayName = "Books To Scrape";
      } else if (node.competitor_url.includes("amazon")) {
        displayName = "Amazon";
      } else if (node.competitor_url.includes("flipkart")) {
        displayName = "Flipkart";
      }
      timeGroups[node.scraped_at][displayName] = parseFloat(node.price.toString());
    });

    return Object.values(timeGroups).sort((a, b) => a.raw_time.localeCompare(b.raw_time));
  };

  const chartData = getChartData();
  
  // Gather available lines for the chart (any key in chartData besides raw_time, formatted_time, and Baseline)
  const chartLines = chartData.length > 0 
    ? Object.keys(chartData[0]).filter(k => k !== 'raw_time' && k !== 'formatted_time' && k !== 'Baseline')
    : [];

  return (
    <div className="min-h-screen bg-[#0b0f19] text-gray-100 flex flex-col font-sans">
      {/* 1. Header Bar */}
      <header className="border-b border-gray-800 bg-[#0e1626] py-4 px-6 flex justify-between items-center shadow-md">
        <div className="flex items-center gap-3">
          <div className="bg-brand-600 p-2 rounded-lg text-white animate-pulse shadow-lg shadow-brand-500/20">
            <Activity size={24} />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
              PricePulse <span className="text-xs bg-brand-500/20 text-brand-400 border border-brand-500/30 px-2 py-0.5 rounded font-mono">MONITOR BOT</span>
            </h1>
            <p className="text-xs text-gray-400">Automated E-Commerce Price Scraping & Alerting</p>
          </div>
        </div>
        
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-xs">
            <span className="text-gray-400">Status:</span>
            {connectionStatus === 'connected' ? (
              <span className="flex items-center gap-1.5 text-emerald-400 bg-emerald-950/30 px-2 py-1 rounded-full border border-emerald-900/50">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400"></span> Connected to API
              </span>
            ) : connectionStatus === 'connecting' ? (
              <span className="flex items-center gap-1.5 text-amber-400 bg-amber-950/30 px-2 py-1 rounded-full border border-amber-900/50">
                <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-ping"></span> Connecting...
              </span>
            ) : (
              <span className="flex items-center gap-1.5 text-rose-400 bg-rose-950/30 px-2 py-1 rounded-full border border-rose-900/50">
                <span className="h-1.5 w-1.5 rounded-full bg-rose-400"></span> Disconnected
              </span>
            )}
          </div>
          
          <button 
            onClick={handleTriggerScrape}
            disabled={isScraping || connectionStatus !== 'connected'}
            className={`flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-brand-600 to-violet-600 hover:from-brand-700 hover:to-violet-700 text-white rounded-lg font-medium text-sm transition-all duration-200 shadow-md shadow-brand-500/10 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            <RefreshCw size={16} className={isScraping ? "animate-spin" : ""} />
            {isScraping ? "Scraping..." : "Run Scraper Now"}
          </button>
        </div>
      </header>

      {/* Flash Status Feed */}
      {statusMessage && (
        <div className={`mx-6 mt-4 p-3 rounded-lg border flex items-center gap-2 text-sm transition-all duration-300 animate-slide-in ${
          statusMessage.type === 'success' 
            ? 'bg-emerald-950/30 text-emerald-400 border-emerald-800/40' 
            : statusMessage.type === 'error' 
            ? 'bg-rose-950/30 text-rose-400 border-rose-800/40' 
            : 'bg-blue-950/30 text-blue-400 border-blue-800/40'
        }`}>
          {statusMessage.type === 'success' ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
          <span>{statusMessage.text}</span>
        </div>
      )}

      {/* Main Grid Dashboard */}
      <div className="flex-1 p-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* LEFT COLUMN: PRODUCT BASELINES & LIST */}
        <div className="bg-[#0e1626] border border-gray-800 rounded-xl p-5 flex flex-col gap-5 shadow-lg">
          <div>
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <DollarSign size={18} className="text-brand-400" /> Tracked Products
            </h2>
            <p className="text-xs text-gray-400 mt-1">Specify target baseline prices for your store's listings.</p>
          </div>

          {/* Form: Add Tracked Product */}
          <form onSubmit={handleAddProduct} className="flex flex-col gap-3 bg-[#131d31] p-4 rounded-lg border border-gray-800/60">
            <div>
              <label className="block text-xs font-semibold text-gray-300 mb-1.5">Product Name</label>
              <input 
                type="text" 
                placeholder="e.g. A Light in the Attic" 
                value={newProductName}
                onChange={(e) => setNewProductName(e.target.value)}
                className="w-full bg-[#0a0e17] border border-gray-700 rounded px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-brand-500"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-300 mb-1.5">Your Target Baseline Price (£/$)</label>
              <input 
                type="number" 
                step="0.01"
                placeholder="e.g. 55.00" 
                value={newProductTarget}
                onChange={(e) => setNewProductTarget(e.target.value)}
                className="w-full bg-[#0a0e17] border border-gray-700 rounded px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-brand-500"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-300 mb-1.5">Alert Trigger Threshold (%)</label>
              <div className="flex items-center gap-3">
                <input 
                  type="range" 
                  min="0" 
                  max="50" 
                  step="0.5"
                  value={newProductThreshold}
                  onChange={(e) => setNewProductThreshold(e.target.value)}
                  className="flex-1 accent-brand-500 bg-[#0a0e17] rounded h-1.5"
                />
                <span className="text-xs font-mono text-brand-400 w-12 text-right">{parseFloat(newProductThreshold).toFixed(1)}%</span>
              </div>
            </div>
            <button 
              type="submit"
              className="w-full bg-brand-600 hover:bg-brand-700 text-white rounded py-2 text-sm font-semibold transition-all flex items-center justify-center gap-1.5 cursor-pointer shadow-md shadow-brand-500/10"
            >
              <Plus size={16} /> Add Tracked Product
            </button>
          </form>

          {/* List of Tracked Products */}
          <div className="flex-1 overflow-y-auto flex flex-col gap-2 max-h-[350px] lg:max-h-none">
            {products.length === 0 ? (
              <div className="text-center py-8 text-gray-500 text-sm border border-dashed border-gray-800 rounded-lg">
                No products tracked yet. Add one above!
              </div>
            ) : (
              products.map((prod) => (
                <div 
                  key={prod.id}
                  onClick={() => setSelectedProduct(prod)}
                  className={`p-3 rounded-lg border transition-all cursor-pointer flex items-center justify-between group ${
                    selectedProduct?.id === prod.id 
                      ? 'bg-brand-950/20 border-brand-500/60 shadow-md shadow-brand-500/5' 
                      : 'bg-[#131d31]/50 border-gray-800/80 hover:bg-[#131d31] hover:border-gray-700'
                  }`}
                >
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-semibold text-white truncate">{prod.name}</div>
                    <div className="flex items-center gap-3 text-xs text-gray-400 mt-1">
                      <span>Baseline: <strong className="text-gray-300">${parseFloat(prod.target_price.toString()).toFixed(2)}</strong></span>
                      <span>•</span>
                      <span>{prod.competitor_urls.length} competitor links</span>
                    </div>
                  </div>
                  <button 
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteProduct(prod.id);
                    }}
                    className="p-1.5 text-gray-500 hover:text-rose-400 hover:bg-rose-950/30 rounded transition-all cursor-pointer opacity-0 group-hover:opacity-100 focus:opacity-100"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

        {/* MIDDLE & RIGHT COLUMNS: COMPETITOR LINKS & PRICE HISTORY ANALYTICS */}
        <div className="lg:col-span-2 flex flex-col gap-6">
          
          {/* Main Details Panel */}
          {selectedProduct ? (
            <div className="bg-[#0e1626] border border-gray-800 rounded-xl p-5 flex flex-col gap-6 shadow-lg flex-1">
              {/* Product Info Header */}
              <div className="flex justify-between items-start border-b border-gray-800 pb-4">
                <div>
                  <span className="text-xs font-semibold text-brand-400 uppercase tracking-wider">Currently Tracking Details</span>
                  <h2 className="text-xl font-bold text-white mt-1">{selectedProduct.name}</h2>
                  <p className="text-xs text-gray-400 mt-1">
                    Store Baseline Target Price: <strong className="text-white">${parseFloat(selectedProduct.target_price.toString()).toFixed(2)}</strong> (Alert threshold: <strong className="text-brand-400">{parseFloat(selectedProduct.alert_threshold_percent.toString()).toFixed(1)}%</strong> drop)
                  </p>
                </div>
              </div>

              {/* Grid: Competitor Link Manager & Live Chart */}
              <div className="grid grid-cols-1 xl:grid-cols-5 gap-6">
                
                {/* Competitor Links Management (2/5 size) */}
                <div className="xl:col-span-2 flex flex-col gap-4">
                  <h3 className="text-sm font-semibold text-gray-200 flex items-center gap-2">
                    <Globe size={16} className="text-brand-400" /> Competitor Websites
                  </h3>
                  
                  {/* Form: Add Competitor URL */}
                  <form onSubmit={handleAddCompetitor} className="flex gap-2">
                    <input 
                      type="url" 
                      placeholder="Enter competitor URL (e.g. books.toscrape, amazon, flipkart)" 
                      value={newCompUrl}
                      onChange={(e) => setNewCompUrl(e.target.value)}
                      className="flex-1 bg-[#0a0e17] border border-gray-700 rounded px-3 py-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-brand-500"
                      required
                    />
                    <button 
                      type="submit"
                      className="bg-brand-600 hover:bg-brand-700 text-white rounded px-3 py-2 text-xs font-semibold transition-all flex items-center gap-1 cursor-pointer"
                    >
                      <Plus size={14} /> Add
                    </button>
                  </form>

                  {/* Info Notice */}
                  <div className="bg-slate-900/40 border border-slate-800/80 rounded-lg p-3 text-[11px] text-gray-400 flex items-start gap-1.5">
                    <Info size={14} className="text-brand-400 shrink-0 mt-0.5" />
                    <p>
                      Supported sites: 
                      <br/>1. <strong>books.toscrape.com</strong>
                      <br/>2. <strong>webscraper.io e-commerce test site</strong>
                      <br/>3. <strong>Amazon</strong> & <strong>Flipkart</strong> (append <strong>?mock=true</strong> to bypass anti-bot blocks for demo testing)
                    </p>
                  </div>

                  {/* Competitors List */}
                  <div className="flex-1 overflow-y-auto flex flex-col gap-2 max-h-[220px]">
                    {selectedProduct.competitor_urls.length === 0 ? (
                      <div className="text-center py-6 text-gray-500 text-xs border border-dashed border-gray-800 rounded-lg">
                        No competitor URLs added yet.
                      </div>
                    ) : (
                      selectedProduct.competitor_urls.map((comp) => {
                        const price = comp.last_scraped_price ? parseFloat(comp.last_scraped_price.toString()) : null;
                        const baseline = parseFloat(selectedProduct.target_price.toString());
                        const dropPercent = price ? ((baseline - price) / baseline) * 100 : 0;
                        const isUnderBaseline = price && price <= baseline;

                        return (
                          <div key={comp.id} className="p-3 bg-[#131d31]/50 border border-gray-800/60 rounded-lg flex flex-col gap-2 relative group">
                            <div className="flex justify-between items-center">
                              <div className="flex items-center gap-1.5 min-w-0">
                                <span className="text-[10px] bg-slate-800 border border-slate-700 text-slate-300 px-1.5 py-0.5 rounded font-mono truncate max-w-[80px]">
                                  {comp.domain_selector_key}
                                </span>
                                {/* Status Badge */}
                                {!comp.is_active ? (
                                  <span className="text-[9px] font-bold bg-rose-950/40 text-rose-400 border border-rose-900/40 px-1.5 py-0.5 rounded-full flex items-center gap-0.5 cursor-help" title={comp.last_error_message || "URL disabled due to repeated failures"}>
                                    Disabled
                                  </span>
                                ) : comp.error_count > 0 ? (
                                  <span className="text-[9px] font-bold bg-amber-950/40 text-amber-400 border border-amber-900/40 px-1.5 py-0.5 rounded-full flex items-center gap-0.5 cursor-help" title={comp.last_error_message || "Temporary scrape failure"}>
                                    Failing ({comp.error_count})
                                  </span>
                                ) : (
                                  <span className="text-[9px] font-bold bg-emerald-950/40 text-emerald-400 border border-emerald-900/40 px-1.5 py-0.5 rounded-full flex items-center gap-0.5">
                                    Active
                                  </span>
                                )}
                              </div>
                              <div className="flex items-center gap-1">
                                <a 
                                  href={comp.url} 
                                  target="_blank" 
                                  rel="noopener noreferrer" 
                                  className="p-1 text-gray-400 hover:text-white rounded hover:bg-slate-800"
                                >
                                  <ExternalLink size={12} />
                                </a>
                                <button 
                                  onClick={() => handleDeleteCompetitor(comp.id)}
                                  className="p-1 text-gray-500 hover:text-rose-400 rounded hover:bg-rose-950/30 cursor-pointer"
                                >
                                  <Trash2 size={12} />
                                </button>
                              </div>
                            </div>
                            
                            <a 
                              href={comp.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-xs text-gray-400 truncate hover:text-brand-400 font-mono"
                            >
                              {comp.url}
                            </a>

                            <div className="flex justify-between items-center mt-1 border-t border-gray-800/50 pt-1.5">
                              <span className="text-[11px] text-gray-400">
                                Last Scraped: {comp.last_scraped_at ? new Date(comp.last_scraped_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Never'}
                              </span>
                              <div className="flex items-center gap-1.5">
                                <span className="text-xs font-bold text-white">
                                  {price ? `$${price.toFixed(2)}` : 'N/A'}
                                </span>
                                {price && isUnderBaseline && (
                                  <span className="text-[10px] font-semibold bg-emerald-950/40 text-emerald-400 border border-emerald-900/50 px-1.5 py-0.5 rounded-full flex items-center gap-0.5">
                                    <TrendingDown size={10} /> -{dropPercent.toFixed(1)}%
                                  </span>
                                )}
                              </div>
                            </div>
                          </div>
                        );
                      })
                    )}
                  </div>
                </div>

                {/* Price History Line Chart (3/5 size) */}
                <div className="xl:col-span-3 bg-[#131d31]/30 border border-gray-800/60 rounded-lg p-4 flex flex-col gap-4 min-h-[300px]">
                  <div className="flex justify-between items-center">
                    <h3 className="text-sm font-semibold text-gray-200">Price Timeline Comparison</h3>
                    <span className="text-[10px] text-gray-500">Horizontal red line represents your baseline</span>
                  </div>
                  
                  <div className="flex-1 w-full min-h-[220px]">
                    {priceHistory.length === 0 ? (
                      <div className="h-full flex flex-col items-center justify-center text-gray-500 text-xs border border-dashed border-gray-800 rounded">
                        No historical price points available. 
                        <br/>(Scrape data will display here)
                      </div>
                    ) : (
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                          <XAxis dataKey="formatted_time" stroke="#9ca3af" fontSize={10} />
                          <YAxis stroke="#9ca3af" fontSize={10} domain={['auto', 'auto']} />
                          <Tooltip 
                            contentStyle={{ backgroundColor: '#0f172a', borderColor: '#374151', color: '#f3f4f6', fontSize: 11 }}
                            labelClassName="text-brand-400 font-bold"
                          />
                          <Legend wrapperStyle={{ fontSize: 10, paddingTop: 10 }} />
                          {/* Target Price Baseline Line */}
                          <Line 
                            type="monotone" 
                            dataKey="Baseline" 
                            stroke="#ef4444" 
                            strokeWidth={2} 
                            strokeDasharray="5 5"
                            dot={false}
                          />
                          {/* Competitor lines dynamically */}
                          {chartLines.map((lineName, idx) => {
                            const colors = ['#8b5cf6', '#06b6d4', '#10b981', '#f59e0b'];
                            return (
                              <Line 
                                key={lineName}
                                type="monotone" 
                                dataKey={lineName} 
                                stroke={colors[idx % colors.length]} 
                                strokeWidth={2}
                                activeDot={{ r: 6 }}
                              />
                            );
                          })}
                        </LineChart>
                      </ResponsiveContainer>
                    )}
                  </div>
                </div>

              </div>
            </div>
          ) : (
            <div className="flex-1 bg-[#0e1626] border border-gray-800 rounded-xl p-8 flex flex-col items-center justify-center text-center shadow-lg">
              <div className="p-4 bg-slate-900 border border-gray-800 text-gray-500 rounded-full mb-4">
                <Globe size={32} />
              </div>
              <h3 className="text-lg font-bold text-white">No Product Selected</h3>
              <p className="text-sm text-gray-400 max-w-sm mt-1">
                Select a tracked product from the left panel to manage competitor URLs, view historical price charts, and monitor price trends.
              </p>
            </div>
          )}

          {/* BOTTOM ALERTS FEED PANEL */}
          <div className="bg-[#0e1626] border border-gray-800 rounded-xl p-5 shadow-lg flex flex-col gap-4">
            <div className="flex justify-between items-center border-b border-gray-800 pb-3">
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <Bell size={16} className="text-rose-500 animate-bounce" /> Sent Alerts Log
              </h3>
              <span className="text-[10px] text-gray-400">Total: {alerts.length} dispatched</span>
            </div>

            <div className="overflow-y-auto max-h-[160px] flex flex-col gap-2">
              {alerts.length === 0 ? (
                <div className="text-center py-6 text-gray-500 text-xs border border-dashed border-gray-800 rounded-lg">
                  No alerts fired yet. (They trigger automatically when competitor prices drop below baseline).
                </div>
              ) : (
                alerts.map((alert) => {
                  const product = products.find(p => p.id === alert.product_id);
                  const formattedTime = new Date(alert.sent_at).toLocaleString();
                  const prevStr = alert.previous_price ? `$${parseFloat(alert.previous_price.toString()).toFixed(2)}` : 'N/A';
                  
                  return (
                    <div key={alert.id} className="p-3 bg-rose-950/15 border border-rose-900/30 rounded-lg flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                      <div className="flex items-start gap-2.5">
                        <AlertCircle size={16} className="text-rose-500 shrink-0 mt-0.5" />
                        <div>
                          <div className="text-xs font-semibold text-white">
                            Price Alert: "{product?.name || 'Tracked Product'}"
                          </div>
                          <div className="text-[10px] text-gray-400 mt-0.5">
                            Competitor price dropped to <strong className="text-emerald-400">${parseFloat(alert.new_price.toString()).toFixed(2)}</strong> (Prev: {prevStr})
                          </div>
                        </div>
                      </div>
                      
                      <div className="flex items-center justify-between sm:justify-end gap-3 text-right">
                        <span className="text-[11px] font-bold text-rose-400 bg-rose-950/40 px-2 py-0.5 rounded border border-rose-900/50">
                          -{parseFloat(alert.price_drop_percent.toString()).toFixed(1)}%
                        </span>
                        <span className="text-[10px] text-gray-500 font-mono">
                          {formattedTime}
                        </span>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

        </div>

      </div>
    </div>
  );
}

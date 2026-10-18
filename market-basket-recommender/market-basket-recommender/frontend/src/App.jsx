import React, { useEffect, useState, useMemo } from 'react';
import { ShoppingCart, Search, Plus, X, Cpu, TrendingUp, ShieldCheck, Package, RefreshCw, Info, ArrowRight, Database, Sparkles } from 'lucide-react';

const API = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
const category = (name) => /camera/i.test(name) ? 'Cameras' : /detector|smoke|carbon|glassbreak/i.test(name) ? 'Detectors' : /NVR/i.test(name) ? 'Recorders' : 'Security Systems';
const CATEGORY_OPTIONS = ['All products','Cameras','Detectors','Recorders','Security Systems'];
const pct = v => `${(v * 100).toFixed(1)}%`;

async function getJSON(path, opts) {
  const res = await fetch(`${API}${path}`, opts);
  if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`);
  return res.json();
}

function ProductGlyph({ name, size = 22 }) {
  const kind = category(name);
  return <span className={`product-icon ${kind === 'Cameras' ? 'cam' : kind === 'Detectors' ? 'detect' : kind === 'Recorders' ? 'record' : 'system'}`}>
    {kind === 'Cameras' ? <Cpu size={size}/> : kind === 'Detectors' ? <ShieldCheck size={size}/> : kind === 'Recorders' ? <Database size={size}/> : <Package size={size}/>}
  </span>;
}

export default function App() {
  const [products, setProducts] = useState([]);
  const [cart, setCart] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('All products');
  const [status, setStatus] = useState('loading');
  const [message, setMessage] = useState('');
  const [model, setModel] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    Promise.all([getJSON('/products'), getJSON('/model-info')])
      .then(([data, info]) => { setProducts(data.products); setModel(info); setStatus('ready'); })
      .catch(e => { setMessage(e.message); setStatus('error'); });
  }, []);

  useEffect(() => {
    if (status !== 'ready') return;
    const controller = new AbortController();
    setBusy(true);
    getJSON('/recommend', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ cart }), signal: controller.signal })
      .then(data => { setRecommendations(data.recommendations); setMessage(data.message); })
      .catch(e => { if (e.name !== 'AbortError') setMessage(e.message); })
      .finally(() => { if (!controller.signal.aborted) setBusy(false); });
    return () => controller.abort();
  }, [cart, status]);

  const cartSet = useMemo(() => new Set(cart), [cart]);
  const bySku = useMemo(() => Object.fromEntries(products.map(p => [p.sku, p])), [products]);
  const filtered = useMemo(() => products.filter(p => {
    const haystack = `${p.name} ${p.sku}`.toLowerCase();
    return haystack.includes(search.toLowerCase()) && (categoryFilter === 'All products' || category(p.name) === categoryFilter);
  }), [products, search, categoryFilter]);
  const add = sku => setCart(prev => prev.includes(sku) ? prev : [...prev, sku]);
  const remove = sku => setCart(prev => prev.filter(x => x !== sku));

  return <div className="app-shell">
    <header className="topbar"><div className="top-inner">
      <div className="brand"><div className="brand-mark"><Cpu size={22}/></div><div><strong>Basket<span>IQ</span></strong><small>INTELLIGENT CHECKOUT</small></div></div>
      <div className="top-links"><span><span className="live-dot"/> LIVE RECOMMENDATION ENGINE</span><span className="top-cart"><ShoppingCart size={17}/> {cart.length} items</span></div>
    </div></header>
    <main>
      <section className="hero"><div><div className="eyebrow"><Sparkles size={13}/> AI-POWERED SHOPPING</div><h1>Smarter picks, <em>better together.</em></h1><p>Discover security electronics that customers purchase together, powered by real transaction patterns and association rule mining.</p></div><div className="hero-graphic"><div className="orbit orbit-a"/><div className="orbit orbit-b"/><div className="big-basket"><ShoppingCart size={46}/></div><div className="float-symbol symbol-1"><ShieldCheck size={20}/></div><div className="float-symbol symbol-2"><Cpu size={20}/></div><div className="float-symbol symbol-3"><Database size={20}/></div></div></section>
      {status === 'error' && <div className="error-banner">Cannot connect to FastAPI. Start the backend at {API}. Details: {message}</div>}
      <section className="metrics"><div><Database size={18}/><strong>{model?.transaction_count?.toLocaleString() || '—'}</strong><span>Historical orders</span></div><div><Package size={18}/><strong>{model?.product_count || '—'}</strong><span>Products analyzed</span></div><div><TrendingUp size={18}/><strong>{model?.rule_count?.toLocaleString() ?? '—'}</strong><span>Association rules</span></div><div><ShieldCheck size={18}/><strong>Apriori</strong><span>Mining algorithm</span></div></section>
      <div className="workspace">
        <section className="catalog panel"><div className="panel-heading"><div><div className="section-kicker">EXPLORE THE CATALOG</div><h2>Available products</h2><p>Choose an item to start discovering what pairs well.</p></div><div className="count-label">{filtered.length} products</div></div>
          <div className="searchbox"><Search size={19}/><input aria-label="Search products" placeholder="Search by product name or SKU..." value={search} onChange={e => setSearch(e.target.value)}/>{search && <button aria-label="Clear search" onClick={() => setSearch('')}><X size={16}/></button>}</div>
          <div className="filters">{CATEGORY_OPTIONS.map(c => <button key={c} className={categoryFilter === c ? 'active' : ''} onClick={() => setCategoryFilter(c)}>{c}</button>)}</div>
          <div className="product-list">{filtered.map(p => <div className="product-row" key={p.sku}><ProductGlyph name={p.name}/><div className="product-details"><strong>{p.name}</strong><span>SKU: {p.sku} <b>·</b> {category(p.name)}</span></div><button className={`add-btn ${cartSet.has(p.sku) ? 'added' : ''}`} disabled={cartSet.has(p.sku)} onClick={() => add(p.sku)} aria-label={`Add ${p.name} to cart`}>{cartSet.has(p.sku) ? 'Added' : <><Plus size={15}/> Add</>}</button></div>)}{filtered.length === 0 && <div className="empty-small">No products match your search.</div>}</div>
        </section>
        <aside className="sidebar"><section className="cart-panel panel"><div className="panel-heading compact"><div><div className="section-kicker">YOUR SELECTION</div><h2><ShoppingCart size={21}/> Shopping cart <span className="cart-number">{cart.length}</span></h2></div>{cart.length > 0 && <button className="clear-btn" onClick={() => setCart([])}>Clear all</button>}</div>
          {cart.length === 0 ? <div className="empty-cart"><div className="empty-icon"><ShoppingCart size={29}/></div><strong>Your cart is empty</strong><p>Add a product from the catalog to unlock personalized recommendations.</p></div> : <div className="cart-items">{cart.map((sku,i) => <div className="cart-item" key={sku}><span className="cart-index">{i+1}</span><div><strong>{bySku[sku]?.name || sku}</strong><small>{sku}</small></div><button aria-label={`Remove ${sku}`} onClick={() => remove(sku)}><X size={17}/></button></div>)}</div>}
          <div className="cart-footer"><span>{cart.length} unique item{cart.length !== 1 ? 's' : ''} selected</span><span>Demo cart · No payment</span></div>
        </section>
        <section className="recs-panel panel"><div className="panel-heading compact"><div><div className="section-kicker">BASED ON YOUR BASKET</div><h2><Sparkles size={21}/> Recommended for you</h2></div>{busy && <RefreshCw size={18} className="spinner"/>}</div>
          {cart.length === 0 ? <div className="no-recs"><div className="recommend-glow"><Sparkles size={27}/></div><strong>Your next great find starts here</strong><p>We'll recommend frequently bought-together items once you add your first product.</p></div> : recommendations.length === 0 ? <div className="no-recs"><div className="recommend-glow"><Info size={25}/></div><strong>No strong matches for this cart</strong><p>No historical purchase rules match the items currently in your cart. Try selecting another product.</p></div> : <div className="rec-list">{recommendations.map((p, index) => <div className="rec-item" key={p.sku}><div className="rec-top"><span className="rec-rank">#{index+1} MATCH</span><span className="confidence">{pct(p.confidence)} confidence</span></div><div className="rec-middle"><ProductGlyph name={p.name} size={20}/><div><strong>{p.name}</strong><small>SKU: {p.sku}</small></div></div><div className="rec-bottom"><span>Lift <b>{p.lift.toFixed(2)}×</b> · Support <b>{pct(p.support)}</b></span><button onClick={() => add(p.sku)}>Add to cart <ArrowRight size={15}/></button></div></div>)}</div>}
          <div className="method-note"><Info size={15}/> Rules consider all cart items and prioritize larger matching combinations. Suggestions are calculated from historical transactions, not from a generative AI model.</div>
        </section></aside>
      </div>
      <footer>CMPE 256 · Market Basket Recommendation System <span>Built using Apriori association rules + FastAPI + React</span></footer>
    </main>
  </div>;
}

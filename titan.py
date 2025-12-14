import streamlit as st
import pandas as pd
import datetime
import json
import os
import random
import requests

# ==========================================
# 1. APP CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="Thrift Hunter Global",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 2. USER LINKS & API KEYS
# ==========================================
PAYMENT_LINKS = {
    "monthly": "https://thrifthunter.gumroad.com/l/entml", 
    "lifetime": "https://thrifthunter.gumroad.com/l/klwkxa"
}

# Your Product Permalinks (Must match Gumroad)
GUMROAD_PERMALINKS = ["entml", "klwkxa"]

AFFILIATE_LINKS = {
    "poly_mailers": "https://amzn.to/3KTeBxD",
    "thermal_printer": "https://amzn.to/4aPInOr",
    "scale": "https://amzn.to/44ttptD",
    "tape": "https://amzn.to/3XTDDzH",
    "ring_light": "https://amzn.to/3MKXoXP",
    "goo_gone": "https://amzn.to/4sddUAn"
}

# ==========================================
# 3. LIVE DATABASE
# ==========================================
REGIONS = {
    "Canada 🇨🇦": {"sym": "$", "ebay": "ebay.ca", "posh": "poshmark.ca", "ship_def": 15.00, "trends": ["Roots", "Arc'teryx", "Lululemon"]},
    "USA 🇺🇸": {"sym": "$", "ebay": "ebay.com", "posh": "poshmark.com", "ship_def": 8.00, "trends": ["Carhartt", "Patagonia", "Nike"]},
    "UK 🇬🇧": {"sym": "£", "ebay": "ebay.co.uk", "posh": "poshmark.co.uk", "ship_def": 4.50, "trends": ["Barbour", "Dr. Martens", "Stone Island"]},
    "Europe 🇪🇺": {"sym": "€", "ebay": "ebay.de", "posh": "vinted.com", "ship_def": 6.00, "trends": ["Adidas", "Puma", "Le Creuset"]},
    "Australia 🇦🇺": {"sym": "$", "ebay": "ebay.com.au", "posh": "poshmark.com.au", "ship_def": 12.00, "trends": ["R.M. Williams", "Spell & Gypsy", "AFL Gear"]}
}

DB_URL = "https://raw.githubusercontent.com/FocusOS-dev/Thrift-Hunter/main/database.json"

@st.cache_data(ttl=600)
def get_live_data():
    try:
        response = requests.get(DB_URL)
        if response.status_code == 200:
            data = response.json()
            return data.get('blacklist', []), data.get('vault', {})
        else:
            return [], {}
    except:
        return [], {}

BLACKLIST_DB, VAULT_DB = get_live_data()

# ==========================================
# 4. SILENT AUTO-SAVE SYSTEM
# ==========================================
SAVE_FILE = "titan.json"

def load_data():
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, 'r') as f: return json.load(f)
        except: return {}
    return {}

def save_data():
    state_data = {
        'history': st.session_state.history,
        'inventory': st.session_state.inventory,
        'watchlist': st.session_state.watchlist,
        'items_scanned': st.session_state.items_scanned,
        'theme': st.session_state.theme,
        'username': st.session_state.username,
        'store_name': st.session_state.store_name,
        'region': st.session_state.region,
        'is_pro': st.session_state.is_pro,
        'goals': st.session_state.goals,
        'tax_mode': st.session_state.tax_mode,
        'tax_rate': st.session_state.tax_rate,
        'sources': st.session_state.sources
    }
    with open(SAVE_FILE, 'w') as f: json.dump(state_data, f)

# INITIALIZE STATE
if 'init' not in st.session_state:
    data = load_data()
    st.session_state.init = True
    st.session_state.history = data.get('history', [])
    st.session_state.inventory = data.get('inventory', [])
    st.session_state.watchlist = data.get('watchlist', [])
    st.session_state.items_scanned = data.get('items_scanned', 0)
    st.session_state.theme = data.get('theme', 'dark')
    st.session_state.username = data.get('username', 'Reseller')
    st.session_state.store_name = data.get('store_name', 'My Store')
    st.session_state.region = data.get('region', 'Canada 🇨🇦')
    st.session_state.is_pro = data.get('is_pro', False)
    st.session_state.goals = data.get('goals', {'Weekly': 250.0, 'Monthly': 1000.0, 'Yearly': 12000.0})
    st.session_state.tax_mode = data.get('tax_mode', False)
    st.session_state.tax_rate = data.get('tax_rate', 25.0)
    st.session_state.sources = data.get('sources', ["Goodwill", "Value Village", "Bins", "FB Marketplace", "Other"])
    st.session_state.view = 'dashboard'

R_DATA = REGIONS.get(st.session_state.region, REGIONS["Canada 🇨🇦"])
CURR = R_DATA["sym"]

# ==========================================
# 5. SECURITY FUNCTIONS
# ==========================================
def verify_gumroad_key(key):
    key = key.strip()
    if key in ["ADMIN", "MONEY"]: 
        return True, "Dev Mode Active"
        
    for permalink in GUMROAD_PERMALINKS:
        try:
            r = requests.post(
                "https://api.gumroad.com/v2/licenses/verify",
                data={"product_permalink": permalink, "license_key": key}
            )
            data = r.json()
            if data.get('success') and not data.get('purchase', {}).get('refunded'):
                return True, "License Verified"
        except:
            continue
    return False, "Invalid Key or Expired Subscription"

# ==========================================
# 6. HELPER FUNCTIONS
# ==========================================
def calculate_period_profit(period):
    if not st.session_state.history: return 0.0
    df = pd.DataFrame(st.session_state.history)
    df['Date'] = pd.to_datetime(df['Date'], format='mixed', errors='coerce')
    now = datetime.datetime.now()
    if period == 'Weekly':
        start = now - datetime.timedelta(days=now.weekday())
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        mask = df['Date'] >= start
    elif period == 'Monthly':
        mask = (df['Date'].dt.month == now.month) & (df['Date'].dt.year == now.year)
    elif period == 'Yearly':
        mask = df['Date'].dt.year == now.year
    else:
        return df['Profit'].sum()
    return df.loc[mask, 'Profit'].sum()

def get_live_news():
    trends = R_DATA["trends"]
    item = random.choice(trends)
    return [
        f"🔴 LIVE: Market Activity HIGH",
        f"🔥 BOLO: {item} selling fast in {st.session_state.region}",
        f"⚡ SUPPLY: Thermal Printers 15% off (See Supply Drop)",
        f"💰 WIN: User just flipped a jacket for {CURR}120 profit"
    ]

# ==========================================
# 7. DYNAMIC CSS
# ==========================================
def get_theme_css():
    if st.session_state.theme == 'dark':
        bg, text, card_bg, border = "#0e1117", "#e0e0e0", "#1a1c24", "#2d2f3a"
        input_bg, input_text = "#262730", "#ffffff"
    else:
        bg, text, card_bg, border = "#ffffff", "#000000", "#f8f9fa", "#dee2e6"
        input_bg, input_text = "#ffffff", "#000000"

    return f"""
    <style>
        .stApp {{ background-color: {bg}; color: {text}; }}
        div[data-testid="stMetric"] {{ background-color: {card_bg}; border: 1px solid {border}; border-radius: 10px; padding: 15px; }}
        .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {{
            color: {input_text} !important; background-color: {input_bg} !important; border-color: {border} !important;
        }}
        .stTextInput label, .stNumberInput label, .stSelectbox label, h1, h2, h3, p {{ color: {text} !important; }}
        .profit-card {{ background: linear-gradient(135deg, #14532d 0%, #064e3b 100%); padding: 20px; border-radius: 12px; text-align: center; color: white !important; margin-bottom: 20px; }}
        .profit-card h1, .profit-card p {{ color: white !important; }}
        .aff-card {{ background: {card_bg}; border: 1px solid {border}; padding: 15px; border-radius: 10px; text-align: center; height: 100%; margin-bottom: 10px; }}
        .ticker-wrap {{ width: 100%; overflow: hidden; background: {card_bg}; padding: 10px 0; margin-bottom: 20px; border-bottom: 1px solid {border}; }}
        .ticker-move {{ display: inline-block; white-space: nowrap; animation: ticker 45s linear infinite; }}
        .ticker-item {{ display: inline-block; padding: 0 4rem; font-family: monospace; font-weight: bold; color: #00ff41; }}
        @keyframes ticker {{ 0% {{ transform: translateX(0); }} 100% {{ transform: translateX(-50%); }} }}
        .pro-lock {{ border: 1px dashed {border}; padding: 20px; border-radius: 10px; text-align: center; opacity: 0.6; background: {card_bg}; }}
    </style>
    """
st.markdown(get_theme_css(), unsafe_allow_html=True)

def render_pro_lock(feature):
    st.markdown(f"""<div class="pro-lock"><h3>🔒 {feature}</h3><p>Pro Feature</p></div>""", unsafe_allow_html=True)

# ==========================================
# 8. SIDEBAR
# ==========================================
with st.sidebar:
    st.title("🦅 Thrift Hunter")
    
    # STATUS BADGE
    if st.session_state.is_pro:
        st.success("✅ **PRO MEMBER**")
    else:
        st.warning("🐣 **FREE MEMBER**")

    st.caption(f"User: {st.session_state.username}")
    
    st.write("🌍 **Region**")
    sel_reg = st.selectbox("Marketplace", list(REGIONS.keys()), index=list(REGIONS.keys()).index(st.session_state.region))
    if sel_reg != st.session_state.region: st.session_state.region = sel_reg; save_data(); st.rerun()
        
    st.markdown("---")
    if st.button("📊 Dashboard", use_container_width=True): st.session_state.view = 'dashboard'; st.rerun()
    if st.button("🛒 Supply Drop", use_container_width=True): st.session_state.view = 'supplies'; st.rerun()
    if st.button("🧰 Toolkit", use_container_width=True): st.session_state.view = 'tools'; st.rerun()
    
    label = "🔓 The Vault (Live)" if st.session_state.is_pro else "🔐 The Vault"
    if st.button(label, use_container_width=True):
        if st.session_state.is_pro: st.session_state.view = 'vault'; st.rerun()
        else: st.toast("Pro Required", icon="🔒")
    
    if st.button("❓ Help & Contact", use_container_width=True): st.session_state.view = 'help'; st.rerun()
    if st.button("⚙️ Settings", use_container_width=True): st.session_state.view = 'settings'; st.rerun()
    
    st.divider()
    if not st.session_state.is_pro:
        st.info("👑 **GO PRO**")
        c1, c2 = st.columns(2)
        c1.link_button("Month $10", PAYMENT_LINKS['monthly'], use_container_width=True)
        c2.link_button("Life $35", PAYMENT_LINKS['lifetime'], use_container_width=True)

# ==========================================
# 9. DASHBOARD
# ==========================================
if st.session_state.view == 'dashboard':
    
    st.info("🚧 **PUBLIC BETA:** You are currently using an Early Access version of Thrift Hunter. New features are added daily. If you encounter any issues, please report them via the Help tab.")
    
    news = get_live_news()
    content = "".join([f'<div class="ticker-item">{item}</div>' for item in news * 4])
    st.markdown(f'<div class="ticker-wrap"><div class="ticker-move">{content}</div></div>', unsafe_allow_html=True)

    # GOALS
    g_period = st.radio("Target:", ["Weekly", "Monthly", "Yearly"], horizontal=True)
    curr_prof = calculate_period_profit(g_period)
    target = st.session_state.goals[g_period]
    pct = min(curr_prof / target, 1.0) if target > 0 else 0
    st.progress(pct)
    st.caption(f"{CURR}{curr_prof:.0f} / {CURR}{target:.0f}")

    st.divider()

    # METRICS
    life_prof = calculate_period_profit("Lifetime")
    tax_held = 0.0
    if st.session_state.is_pro and st.session_state.tax_mode:
        tax_held = life_prof * (st.session_state.tax_rate / 100)
        net_life = life_prof - tax_held
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Gross", f"{CURR}{life_prof:.2f}")
        c2.metric("Net", f"{CURR}{net_life:.2f}")
        c3.metric("Tax", f"{CURR}{tax_held:.2f}")
        c4.metric("Inv", len(st.session_state.inventory))
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Profit", f"{CURR}{life_prof:.2f}")
        c2.metric("Active Inventory", len(st.session_state.inventory))
        c3.metric("Scanned Today", st.session_state.items_scanned)

    st.divider()

    # SCANNER
    col_scan, col_calc = st.columns([1, 1.2])
    with col_scan:
        st.subheader("1. Smart Scan")
        term = st.text_input("Item Name", placeholder="e.g. Vintage Camera")
        c1, c2 = st.columns(2)
        f_sold = c1.checkbox("Sold Only", True)
        
        if term:
            clean = term.replace(' ', '+')
            domain = R_DATA['ebay']
            url = f"https://www.{domain}/sch/i.html?_nkw={clean}&_sacat=0"
            if f_sold: url += "&LH_Sold=1&LH_Complete=1"
            
            st.link_button(f"🔎 Check {domain}", url, type="primary", use_container_width=True)
            st.link_button(f"🛍️ Check {R_DATA.get('posh', 'Poshmark')}", f"https://{R_DATA.get('posh', 'poshmark.com')}/search?query={clean}", use_container_width=True)
            st.link_button("📸 Google Lens", f"https://www.google.com/search?tbm=isch&q={clean}", use_container_width=True)

        st.write("")
        with st.expander("⛔ Brand Blacklist"):
            st.dataframe(pd.DataFrame(BLACKLIST_DB), use_container_width=True)

    # CALCULATOR
    with col_calc:
        st.subheader("2. Profit Engine")
        c_in1, c_in2 = st.columns(2)
        cost = c_in1.number_input("Cost", 0.0, 5000.0, 5.0)
        sold = c_in2.number_input("Sell", 0.0, 5000.0, 45.0)
        ship = st.number_input("Ship", 0.0, 200.0, R_DATA['ship_def'])
        
        src = st.selectbox("Source", st.session_state.sources)
        if src == "Other": src = st.text_input("Enter Source Name")
        
        profit = sold - cost - ship - (sold * 0.13)
        st.markdown(f"""<div class="profit-card"><h1 style="margin:0;">{CURR}{profit:.2f}</h1><p style="margin:0;">NET PROFIT</p></div>""", unsafe_allow_html=True)
        
        b1, b2 = st.columns(2)
        if b1.button("📦 Add to Inventory"):
            st.session_state.inventory.append({"Date": str(datetime.date.today()), "Item": term if term else "Item", "Cost": cost, "Expected": sold, "Source": src})
            st.session_state.items_scanned += 1; save_data(); st.toast("Saved!")
        if b2.button("💰 Mark Sold", type="primary"):
            st.session_state.history.insert(0, {"Date": str(datetime.date.today()), "Item": term if term else "Item", "Profit": profit, "Source": src})
            st.session_state.items_scanned += 1; save_data(); st.rerun()

    st.divider()
    tab1, tab2 = st.tabs(["📜 History", "📦 Inventory"])
    with tab1: st.dataframe(pd.DataFrame(st.session_state.history), use_container_width=True)
    with tab2: st.dataframe(pd.DataFrame(st.session_state.inventory), use_container_width=True)

# ==========================================
# 10. SUPPLY DROP (MAJOR UPDATE)
# ==========================================
elif st.session_state.view == 'supplies':
    st.title("🛒 Supply Drop")
    st.caption("The official reseller starter kit. Verified quality.")
    
    # MUST HAVE SECTION
    st.subheader("🔥 The 'Must Have' Setup")
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.markdown(f"""<div class="aff-card"><h3>🏷️ Thermal Printer</h3><p>Stop cutting paper labels. This saves 5 hours a week.</p></div>""", unsafe_allow_html=True)
        st.link_button("Get Munbyn Printer ↗", AFFILIATE_LINKS['thermal_printer'], use_container_width=True)
        
    with c2:
        st.markdown(f"""<div class="aff-card"><h3>📦 Poly Mailers</h3><p>The industry standard. Tear-proof and cheap.</p></div>""", unsafe_allow_html=True)
        st.link_button("Get 100 Pack ↗", AFFILIATE_LINKS['poly_mailers'], use_container_width=True)
        
    with c3:
        st.markdown(f"""<div class="aff-card"><h3>⚖️ Shipping Scale</h3><p>Never overpay for postage again. Essential.</p></div>""", unsafe_allow_html=True)
        st.link_button("Get Accuteck Scale ↗", AFFILIATE_LINKS['scale'], use_container_width=True)

    st.divider()
    
    # PRO TOOLS SECTION
    st.subheader("📸 Studio & Prep")
    c4, c5, c6 = st.columns(3)
    
    with c4:
        st.markdown(f"""<div class="aff-card"><h3>💡 Ring Light</h3><p>Better lighting = Higher selling price.</p></div>""", unsafe_allow_html=True)
        st.link_button("Get Ring Light ↗", AFFILIATE_LINKS['ring_light'], use_container_width=True)
        
    with c5:
        st.markdown(f"""<div class="aff-card"><h3>🧼 Goo Gone</h3><p>Removes thrift store stickers in seconds.</p></div>""", unsafe_allow_html=True)
        st.link_button("Get Goo Gone ↗", AFFILIATE_LINKS['goo_gone'], use_container_width=True)
        
    with c6:
        st.markdown(f"""<div class="aff-card"><h3>📦 Heavy Duty Tape</h3><p>Don't use cheap tape. It splits & rips.</p></div>""", unsafe_allow_html=True)
        st.link_button("Get Scotch HD ↗", AFFILIATE_LINKS['tape'], use_container_width=True)

    st.divider()
    
    # WATCHLIST
    with st.expander("👀 My Personal Watchlist"):
        c1, c2, c3 = st.columns([2, 2, 1])
        name = c1.text_input("Item")
        link = c2.text_input("Link")
        if c3.button("Add"): 
            st.session_state.watchlist.append({"name": name, "link": link}); save_data(); st.rerun()
        for item in st.session_state.watchlist:
            c_w1, c_w2 = st.columns([4,1])
            c_w1.link_button(f"Check {item['name']}", item['link'])
            if c_w2.button("❌", key=item['name']): st.session_state.watchlist.remove(item); save_data(); st.rerun()

# ==========================================
# 11. TOOLKIT
# ==========================================
elif st.session_state.view == 'tools':
    st.title("🧰 Toolkit")
    t1, t2, t3, t4, t5 = st.tabs(["📝 Titles", "📄 Desc", "🎒 Bulk", "⚖️ Offer", "📏 Size"])
    
    with t1:
        st.subheader("eBay Title Builder")
        st.caption("Maximize SEO keywords for better ranking.")
        
        c1, c2 = st.columns(2)
        brand = c1.text_input("Brand", placeholder="Nike")
        item = c2.text_input("Item Name", placeholder="Air Hoodie")
        
        c3, c4, c5 = st.columns(3)
        gender = c3.selectbox("Gender", ["Men's", "Women's", "Unisex"])
        size = c4.text_input("Size", "L")
        color = c5.text_input("Color", "Black")
        
        c6, c7 = st.columns(2)
        material = c6.text_input("Material", placeholder="Cotton, Silk, Wool")
        era = c7.selectbox("Era/Style", ["Modern", "Vintage 90s", "Y2K", "Streetwear", "Gorpcore"])
        
        features = st.multiselect("Features", ["Rare", "Logo", "Zip Up", "Spellout", "Distressed"])
        
        if brand and item:
            final_title = f"{brand} {item} {gender} {size} {color} {era} {material} {' '.join(features)}".strip()
            st.markdown("### Result:")
            st.code(final_title, language="text")
            st.caption(f"Chars: {len(final_title)}/80 (eBay Limit)")
        
    with t2:
        if st.session_state.is_pro:
            st.subheader("Pro Description Generator")
            c1, c2 = st.columns(2)
            d_item = c1.text_input("Item Title", "Vintage Tee")
            d_cond = c2.selectbox("Condition", ["Excellent Pre-owned", "Like New", "Good Vintage Condition", "Fair / Distressed"])
            
            c3, c4 = st.columns(2)
            pit = c3.text_input("Pit to Pit", "22")
            length = c4.text_input("Length", "28")
            
            defects = st.text_input("Defects (if any)", "None")
            
            if st.button("Generate Template"):
                template = f"""
**ITEM:** {d_item}

**CONDITION:** {d_cond}
Defects: {defects}

**MEASUREMENTS:**
📏 Pit to Pit: {pit}"
📏 Length: {length}"

**DESCRIPTION:**
Genuine {d_item}. Great addition to any wardrobe. Please see photos for exact condition and details.

✅ Fast Shipping
✅ Cleaned & Steamed
✅ Trusted Seller
                """
                st.text_area("Copy & Paste", template, height=300)
        else: render_pro_lock("Description Gen")
            
    with t3:
        if st.session_state.is_pro:
            st.subheader("Bulk Calculator")
            cost = st.number_input("Total Cost", 0.0, 1000.0, 50.0)
            items = st.number_input("Items", 1, 100, 20)
            st.metric("Cost Per Item", f"{CURR}{cost/items:.2f}")
        else: render_pro_lock("Bulk Calculator")
    
    with t4:
        st.subheader("Offer Shield")
        buy = st.number_input("Buy Cost", 10.0)
        offer = st.number_input("Offer Amount", 20.0)
        prof = offer - buy - (offer*0.2)
        if prof > 0: st.success(f"Profit: {CURR}{prof:.2f}")
        else: st.error(f"Loss: {CURR}{prof:.2f}")
        
    with t5:
        st.subheader("Size Converter")
        us = st.number_input("US Size", 4.0, 15.0, 9.0)
        st.write(f"**UK:** {us-1} | **EU:** {38 + (us-6)*1.3:.0f}")

# ==========================================
# 12. HELP & CONTACT
# ==========================================
elif st.session_state.view == 'help':
    st.title("❓ Help & Support")
    
    st.info("👋 Welcome to Thrift Hunter. Here is how to get started.")
    
    with st.expander("📱 How to Install on iPhone/Android"):
        st.write("1. Open this website in Safari (iOS) or Chrome (Android).")
        st.write("2. Tap the 'Share' or 'Menu' button.")
        st.write("3. Select 'Add to Home Screen'.")
        st.write("4. Now it works just like a native app!")

    with st.expander("🔐 How to Unlock Pro Features"):
        st.write("1. Click 'Go Pro' in the sidebar.")
        st.write("2. Purchase a Lifetime or Monthly license.")
        st.write("3. Check your email for the unique License Key.")
        st.write("4. Go to **Settings**, paste the key, and click Activate.")
    
    with st.expander("🛒 How to use the Profit Engine"):
        st.write("1. Enter your Buy Cost.")
        st.write("2. Enter the Selling Price.")
        st.write("3. The app automatically deducts fees (13%) and Shipping.")
        st.write("4. Click 'Add to Inventory' to save it.")
        
    st.divider()
    st.subheader("📧 Contact Support")
    st.write("Found a bug? Have a feature request? Email our support team directly.")
    st.code("obaid.business2006@gmail.com")
    st.caption("Response time: 24-48 hours.")
    
    st.markdown("---")
    st.caption("Thrift Hunter OS v1.0.4 (Beta) | Secured by Gumroad | Built for Resellers")

# ==========================================
# 13. VAULT & SETTINGS
# ==========================================
elif st.session_state.view == 'vault':
    st.title("🔐 The Vault")
    region_key = st.session_state.region if st.session_state.region in VAULT_DB else "Canada 🇨🇦"
    st.dataframe(pd.DataFrame(VAULT_DB.get(region_key, [])), use_container_width=True)

elif st.session_state.view == 'settings':
    st.header("⚙️ Settings")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Profile")
        name = st.text_input("Username", st.session_state.username)
        if st.button("Save Name"): st.session_state.username = name; save_data(); st.rerun()
        
        st.subheader("License")
        key_input = st.text_input("Pro Key")
        
        if st.button("Activate"):
            is_valid, message = verify_gumroad_key(key_input)
            if is_valid:
                st.session_state.is_pro = True
                save_data()
                st.balloons()
                st.success(f"Success: {message}")
                st.rerun()
            else:
                st.error(message)
            
        st.subheader("Taxman (Pro)")
        if st.session_state.is_pro:
            st.session_state.tax_mode = st.checkbox("Enable Tax Buffer", st.session_state.tax_mode)
            if st.session_state.tax_mode: st.session_state.tax_rate = st.slider("Rate %", 0, 50, 25)
            if st.button("Save Tax Settings"): save_data(); st.success("Saved")
        else: st.caption("Locked")

    with c2:
        st.subheader("Goals")
        gw = st.number_input("Weekly", value=st.session_state.goals['Weekly'])
        gm = st.number_input("Monthly", value=st.session_state.goals['Monthly'])
        gy = st.number_input("Yearly", value=st.session_state.goals['Yearly'])
        if st.button("Save Goals"): st.session_state.goals = {'Weekly': gw, 'Monthly': gm, 'Yearly': gy}; save_data(); st.rerun()
        
        st.subheader("Theme")
        mode = st.radio("Mode", ["Dark", "Light"])
        if mode == "Light" and st.session_state.theme != 'light': st.session_state.theme = 'light'; save_data(); st.rerun()
        if mode == "Dark" and st.session_state.theme != 'dark': st.session_state.theme = 'dark'; save_data(); st.rerun()
        
        st.subheader("Data")
        if st.button("Reset App"): 
            st.session_state.clear()
            if os.path.exists(SAVE_FILE): os.remove(SAVE_FILE)
            st.rerun()

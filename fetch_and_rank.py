import pandas as pd, yfinance as yf, time, logging, csv, json, re
from datetime import datetime

logging.basicConfig(filename='errors.log', level=logging.ERROR, format='%(asctime)s - %(message)s')

COLS = ['Ticker','Name','Market_Cap','Enterprise_Value','FCF_TTM','FCF_Y1','FCF_Y2','FCF_Y3','FCF_Y4','FCF_Avg','FCF_EV_Ratio_Pct','Revenue_Growth_Est_Pct','Analyst_Count']

# (?<!\w) and (?!\w) handle suffixes ending in '.' (e.g. S.A.) at end of string — \b fails there
FOREIGN = re.compile(r'(?<!\w)(Ltd\.?|plc\.?|S\.A\.|AG|N\.V\.|AB|ASA|SE|GmbH|S\.p\.A|S\.A\.B|S\.A\.P\.I|B\.V\.|KGaA|Oyj|A\/S|Tbk|Bhd)(?!\w)', re.IGNORECASE)
OTC_F   = re.compile(r'[A-Z]{4}F$')

def is_foreign(ticker, name):
    return bool(FOREIGN.search(name)) or bool(OTC_F.match(ticker))

def get_ev(sym):
    try: return yf.Ticker(sym).info.get('enterpriseValue')
    except: return None

def get_fcf(sym):
    try:
        t = yf.Ticker(sym)
        ttm = t.ttm_cashflow
        ttm_fcf = ttm.loc['Free Cash Flow'].iloc[0] if ttm is not None and not ttm.empty and 'Free Cash Flow' in ttm.index else None
        cf = t.cashflow
        if cf is None or cf.empty or 'Free Cash Flow' not in cf.index:
            return ttm_fcf, [None]*4
        return ttm_fcf, list(cf.loc['Free Cash Flow'].iloc[:4].values)
    except: return None, [None]*4

def get_analyst(sym):
    try:
        t = yf.Ticker(sym)
        mc = t.info.get('marketCap') or -999
        rev = t.revenue_estimate
        if rev is None or rev.empty or '+1y' not in rev.index: return mc, -999, -999
        row = rev.loc['+1y']
        n = int(row['numberOfAnalysts']) if row['numberOfAnalysts'] else -999
        g = row['growth']
        if not g or n <= 0: return mc, -999, -999
        return mc, round(float(g)*100, 1), n
    except: return -999, -999, -999

def compute(ttm, annual, ev):
    if not ttm or not ev: return None, None
    all_fcf = [ttm] + [x for x in annual if x is not None]
    avg = sum(all_fcf) / len(all_fcf)
    if any(x < 0 for x in all_fcf): return avg, -999
    return avg, round((avg/ev)*100, 1) if ev else None

def rank(data_file, ranked_file):
    with open(data_file) as f:
        rows = list(csv.DictReader(f))
    def valid(r):
        try: return float(r['FCF_EV_Ratio_Pct']) > 0
        except: return False
    ranked = [{'Rank': i, **r} for i, r in enumerate(sorted(filter(valid, rows), key=lambda r: float(r['FCF_EV_Ratio_Pct']), reverse=True), 1)]
    with open(ranked_file, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['Rank']+COLS)
        w.writeheader()
        w.writerows(ranked)
    with open('data.json', 'w') as f:
        json.dump({'updated': datetime.now().strftime('%a, %b %d, %Y'), 'rows': ranked}, f)
    print(f'Ranked {len(ranked)} tickers -> {ranked_file} + data.json')

def main():
    ts = datetime.now().strftime('%m%d%Y')
    data_file, ranked_file = f'data_{ts}.csv', f'processed_data_{ts}.csv'

    tickers = pd.read_csv('company_tickers.csv').rename(columns={'ticker':'Ticker','name':'Name'})
    blacklist = set(pd.read_csv('blacklisted_foreign_companies.csv')['Ticker'])
    tickers = tickers[~tickers['Ticker'].isin(blacklist) & ~tickers.apply(lambda r: is_foreign(r['Ticker'], r['Name']), axis=1)]
    print(f'Processing {len(tickers)} tickers (blacklist + foreign regex applied)...')

    with open(data_file, 'w', newline='') as f:
        csv.DictWriter(f, fieldnames=COLS).writeheader()

    for _, row in tickers.iterrows():
        sym, name = row['Ticker'], row['Name']
        ev = get_ev(sym)
        ttm, annual = get_fcf(sym)
        avg, ratio = compute(ttm, annual, ev)
        mc, growth, analysts = get_analyst(sym)
        with open(data_file, 'a', newline='') as f:
            csv.DictWriter(f, fieldnames=COLS).writerow({
                'Ticker':sym,'Name':name,'Market_Cap':mc,'Enterprise_Value':ev,
                'FCF_TTM':ttm,'FCF_Y1':annual[0],'FCF_Y2':annual[1],'FCF_Y3':annual[2],'FCF_Y4':annual[3],
                'FCF_Avg':avg,'FCF_EV_Ratio_Pct':ratio,'Revenue_Growth_Est_Pct':growth,'Analyst_Count':analysts
            })
        time.sleep(0.5)

    print(f'Data written -> {data_file}')
    rank(data_file, ranked_file)

if __name__ == '__main__':
    main()

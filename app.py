import io
import os
import re
import tempfile
from datetime import datetime, date
import numpy as np
import pandas as pd
import pyreadstat
import streamlit as st

# ==============================================================================
# PAGE CONFIGURATION & STYLING
# ==============================================================================
st.set_page_config(
    page_title="Growth CATI Verbatim Processor",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom sleek UI CSS matching modern dark dashboard aesthetic
st.markdown("""
<style>
    /* Metric Cards */
    .metric-container {
        background-color: #1a1e24;
        border-radius: 10px;
        padding: 16px 20px;
        border: 1px solid #2d3748;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2);
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #60a5fa;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    /* Date Selection Box Highlight */
    .date-card {
        background: linear-gradient(145deg, #161b22, #0d1117);
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 20px;
    }
    
    /* Custom alerts and tags */
    .status-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .badge-success {
        background-color: rgba(16, 185, 129, 0.2);
        color: #34d399;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    .badge-info {
        background-color: rgba(59, 130, 246, 0.2);
        color: #60a5fa;
        border: 1px solid rgba(59, 130, 246, 0.3);
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# EMBEDDED SPSS RULES & KEYWORDS (Extracted from "Growth CATI W20 Verbatims V3.sps")
# ==============================================================================
PEOPLE_KEYWORDS = [
    'ATTENDING', 'ATTEND ', 'BANKER', 'BANKERS', 'BM', 'BM/RM', "BM'S", "BM'S/RM'S",
    'BROKER', 'BROKERS', 'BUSINESS BANKER', 'BUSINESS BANKERS', "BUSINESS BANKER'S",
    'BUSINESS CONSULTANT', 'BUSINESS CONSULTANTS', 'BUSINESS MANAGER', 'BUSINESS MANAGERS',
    "BUSINESS MANAGER'S", 'COMMUNICATE', 'COMMUNICATES', 'COMMUNICATION', 'COMMUNICATIONS',
    'CONSULT', 'CONSULTANT', 'CONTACT', 'CONTACTS', 'CONTECTED', 'CUSTOMER SERVICE',
    'CUSTOMER SERVICES', 'HONESTLY', 'HONESTY', 'HUMAN', 'HUMANS', 'INTERACTION',
    'INTERACTIONS', 'MANAGEE', 'MANAGES', 'MANNER', 'MANNERS', 'PEOPLE', "PEOPLE'S",
    'PERSON', 'PERSONAL', 'PERSONALLY', 'PERSONS', 'PRIVATE BANKER', 'PRIVATE BANKERS',
    'PROMISED', 'PROMISES', 'RELATIONSHIP', 'RELATIONSHIP MANAGER', 'RELATIONSHIP MANANGERS',
    'RELATIONSHIPS', 'REPRESENT', 'REPRESENTATIVE', 'RM ', "RM'S", 'SOMEONE', 'SOMEONES',
    'STAFF', 'STAFFS', 'TELLER', 'TELLERS', 'TREAT', 'TREATED', 'TRUST', 'TRUSTED',
    'UNDERSTAND', 'UNDERSTANDING', 'WALK', 'WALKED', 'WELCOME', 'WELCOMES'
]

PROCESS_KEYWORDS = [
    'ACCESS', 'TRANSFERS', 'ACCESSES', 'ACCESSIBLE', 'ACCESSIBLES', 'ACTION', 'ACTIONS',
    'ALLOW', 'ALLOWS', 'APPROVALS', 'APPROVED', 'ASSIST', 'ASSISTS', 'ATTEND', 'ATTENDED',
    'ATTENTION', 'CHANGE', 'CHANGES', 'CLOSE', 'CLOSING', 'COMMUNICATION', 'COMMUNICATIONS',
    'CONNECTIONS', 'CONNECTIVITY', 'CONVENIENCES', 'CONVENIENT', 'CUSTOMER', 'CUSTOMERS',
    'DEBIT', 'DEBITS', 'DESK', 'DESKS', 'DISRUPTING', 'DISRUPTIONS', 'DOCUMENTATION',
    'DOCUMENTS', 'EASIER', 'EASILY', 'EFFICIENCY', 'EFFICIENT', 'ENQUIRIES', 'ENQUIRY',
    'EXPIRE', 'EXPIRED', 'FAST', 'FASTER', 'FEEDBACK', 'FINGER', 'FINGERS', 'FOLLOWING',
    'FRAUD', 'FUNCTIONALITIES', 'FUNCTIONALITY', 'FUNDING', 'FUNDINGS', 'GUARANTEE',
    'GUARANTEES', 'HELP', 'HELPS', 'INFORMATION', 'INQUIRIES', 'INQUIRY', 'ISSUE',
    'ISSUES', 'LENDING', 'LENDINGS', 'LETTER', 'LETTERS', 'LINK', 'LINKS', 'LONG',
    'NETWORK', 'NETWORKS', 'NOTIFICATION', 'NOTIFICATIONS', 'NOTIFIED', 'NOTIFY',
    'OPENING', 'ORDER', 'ORDERS', 'OTP', 'OTPs', 'PERIOD', 'PERIODS', 'POINT',
    'POINTS', 'PREVENT', 'PREVENTS', 'PROCESS', 'PROCESSES', 'PROMISE', 'PROMISES',
    'PROVIDE', 'PROVIDES', 'QUERIES', 'QUERY', 'QUEUE', 'QUEUES', 'QUICK', 'QUICKER',
    'QUICKLY', 'REGULATION', 'REGULATIONS', 'RESOLUTION', 'RESOLUTIONS', 'RESOLVE',
    'RETURN', 'RETURNS', 'REVERSE', 'SANITIZER', 'SATURDAY', 'SATURDAYS', 'SECURE',
    'SECURES', 'SECURITIES', 'SECURITY', 'SERVICE', 'SERVICES', 'SETUP', 'SETUPS',
    'SPAM', 'SPAMS', 'SPEED', 'SPEEDS', 'SUNDAY', 'SUNDAYS', 'SYSTEM', 'SYSTEMS ',
    'THROUGH', 'TIME', 'TIMES', 'TRANSACTION', 'TRANSACTIONS', 'TRANSFER', 'TURNAROUD',
    'TURNAROUND', 'UNAUTHORISED', 'URGENCY', 'URGENTLY', 'USER-FRIENDLY',
    'VERIFYING MY ACCOUNT', 'WAITING', 'WORKING'
]

PRODUCT1_KEYWORDS = [
    'ACCOUNT', 'ACCOUNTS', 'ADVICE', 'BANK CHARGE', 'BANK CHARGES', 'BANK FEE',
    'BANK FEES', 'BANKING', 'BANKING COST', 'BANKING COSTS', 'BANKS', 'BENEFIT',
    'BENEFITS', 'BUSINESS', 'BUSINESS ACCOUNT', 'BUSINESSES', 'CALL ACCOUNT',
    'CARD', 'CARDS', 'CASH', 'CASH WITHDRAWAL', 'CASH WITHDRAWALS', 'CHARGE',
    'CHARGES', 'CHEQUE', 'CHEQUES', 'COST', 'COSTS', 'COVID', 'CREDIT',
    'CREDIT APLICATIONS', 'CREDIT APPLICATION', 'CREDIT CARD', 'CREDIT CARDS',
    'CREDITS', 'CURRENCY', 'E BUCK', 'E BUCKS', 'EBACK', 'EBACKS', 'EBUCK',
    'E-BUCK', 'EBUCKS', 'E-BUCKS', 'EQUITIE', 'EQUITY', 'E-WALLET', 'E-WALLETS',
    'EXPENSIVE', 'FACILITIES', 'FACILITY', 'FEE', 'FEES', 'FICA', 'FINANCE',
    'FINANCING', 'FLEET', 'FLLEETS', 'FOREIGN', 'FOREIGNS', 'FOREX', 'INSURANCE',
    'INTEREST', 'INTERESTS', 'INTERNET', 'INVESTEMENT ACCOUNT', 'INVESTMENT',
    'INVESTMENT ACCOUNTS', 'INVESTMENTS', 'LEVIES', 'LEVY', 'LIMIT', 'LIMITS',
    'LOAN', 'LOANS', 'MERCHANT', 'MERCHANTS', 'MONEY', 'MONEY MARKERTS',
    'MONEY MARKET', 'MONEYS', 'NEW ACCOUNT', 'NEW ACCOUNTS', 'NOTIFICATION',
    'NOTIFICATIONS', 'ONLINE', 'ONLINE BANKING', 'ONLINE BANKINGS', 'OVERDRAFT',
    'OVERDRAFTS', 'PAY', 'PAYMANT', 'PAYMENTS', 'PRICING', 'PRIVATE BANKING',
    'PRODUCT', 'PRODUCTS', 'PROPERTY', 'RATE', 'RATES', 'REWARD', 'REWARDS',
    'SAVING', 'SAVINGS', 'SHARE', 'SHARER', 'SHARIAH', 'SOLUTION', 'SOLUTIONS',
    'SPEED POINT', 'STATEMENT', 'STATEMENTS', 'TRADE', 'TRAINING', 'TRAININGS',
    'TRANSACTION', 'TRANSACTIONS', 'UIF', 'VAF', 'VEHICLE', 'VIHICLES', 'WESBANK'
]

PRODUCT2_KEYWORDS = PRODUCT1_KEYWORDS.copy()

CHANNEL2_KEYWORDS = [
    'ATM', 'ATMs', 'APP', 'APPS', 'BRANCH', 'BRANCHES', 'BUSINESS BANKING',
    'CALL CENTRE', 'CALL CENTRES', 'CONTACT CENTRE', 'FNB BANKING APP',
    'INCONTACT', 'ONLINE', 'ERROR'
]

NONE_KEYWORDS = [
    'ALL FINE FROM MY SIDE', 'ALL GOOD', 'ALL HAPPY', 'ALL IN ORDER', 'ALL IS FINE',
    'ANY ISSUES', 'ANY PROBLEM', 'ANYTHING', "CANT THINK OF ANY", "DON’T KNOW",
    "DONT KNOW", 'EVERYTHING', 'EXCELLENT', 'FUCK', 'GOOD', 'HAPPY WITH EVERYTHING',
    'HAVE ANSWERS', 'I AM HAPPY', 'I AM SATISFIED', 'I DO NOT HAVE', 'I HAVE NO ISSUES',
    'KNOW', 'N/A', 'NA', 'NO COMMENT', 'NO COMPLAINT AT THE MOMENT', 'NO IMPROVEMENT',
    'NO IMPROVEMENTS', 'NONE', 'NOT APPLICABLE', 'NOT AT THE MOMENT', 'NOT MUCH',
    'NOT NOW', 'NOT SURE', 'NOT SURE OF ANY', 'NOT THAT I THINK OF', 'NOTHING',
    'NOTHING TO IMPROVE', 'SATISFIED', 'T HAVE', 'T THINK'
]

CHANNEL_RULES = {
    'CHAN_ONLINEBANKING': [('ONLINE', 'ONLINE BANKING')],
    'CHAN_BRANCH': [('BRANCH', 'BRANCH')],
    'CHAN_BUSINESSAPP': [('APP', 'BUSINESS APP')],
    'CHAN_CALLCENTRE': [('CALL CENTRE', 'CALL CENTRE'), ('CENTRE', 'CALL CENTRE')],
    'CHAN_BM_RM': [('BM', 'BM/RM'), ('RM', 'BM/RM'), ('MANAGER', 'BM/RM')],
    'CHAN_CREDIT': [('CREDIT', 'CREDIT')],
    'CHAN_BUSINESSMANAGER': [('BUSINESS MANAGER', 'BUSINESS MANAGER')],
    'CHAN_ATM': [('ATM', 'ATM')],
    'CHAN_FEES': [('FEES', 'FEES')],
    'CHAN_CARDS': [('CARD', 'CARDS')],
    'CHAN_E_BUCKS': [('E-BUCKS', 'E-BUCKS'), ('BUCK', 'E-BUCKS')],
    'CHAN_MERCHANT': [
        ('MERCHANT', 'MERCHANT SERVICE/SPEED POINT/S'),
        ('SPEED POINT', 'MERCHANT SERVICE/SPEED POINT/S'),
        ('POINT', 'MERCHANT SERVICE/SPEED POINT/S'),
        ('SWIPING ', 'MERCHANT SERVICE/SPEED POINT/S'),
        ('MACHINE', 'MERCHANT SERVICE/SPEED POINT/S')
    ],
    'CHAN_TRANSACTIONAL': [
        ('TRANSACTIONAL', 'TRANSACTIONAL ACCOUNTS/CHEQUE'),
        ('ACCOUNT', 'TRANSACTIONAL ACCOUNTS/CHEQUE'),
        (' BOARD', 'TRANSACTIONAL ACCOUNTS/CHEQUE')
    ],
    'CHAN_FOREX': [('FOREX', 'FOREX')],
    'CHAN_INSTANTACC': [('INSTANT', 'INSTANT ACCOUNTING'), ('ACCOUNTING', 'INSTANT ACCOUNTING')]
}

CHAN_COL_ORDER = [
    'CHAN_ONLINEBANKING', 'CHAN_BRANCH', 'CHAN_BUSINESSAPP', 'CHAN_CALLCENTRE',
    'CHAN_BM_RM', 'CHAN_CREDIT', 'CHAN_BUSINESSMANAGER', 'CHAN_ATM',
    'CHAN_FEES', 'CHAN_CARDS', 'CHAN_E_BUCKS', 'CHAN_MERCHANT',
    'CHAN_TRANSACTIONAL', 'CHAN_FOREX', 'CHAN_INSTANTACC'
]

# ==============================================================================
# TRANSFORMATION FUNCTION
# ==============================================================================
def process_growth_verbatims(df_raw, start_date=None, end_date=None, date_sep='/', column_preset='V3'):
    """
    Executes the exact logic of Growth CATI W20 Verbatims V3.sps on the dataset:
    1. Filter completed interviews (V9999 == 1)
    2. Filter STIME dates within start_date and end_date (inclusive)
    3. Generate all mapped fields, NPS buckets, and categorizations
    4. Replace all commas with '~' in verbatim variables
    5. Output the exact structure specified in SPSS V3 syntax
    """
    df = df_raw.copy()
    
    # 1. Filter completed interviews (V9999 == 1)
    if 'V9999' in df.columns:
        # Check numeric 1 or string '1' / 1.0
        df = df[df['V9999'].astype(str).str.strip().isin(['1', '1.0'])].copy()
    
    # 2. Date filtering via STIME
    if 'STIME' in df.columns:
        df['STIME_STR'] = df['STIME'].astype(str).str.strip().str[:8]
        if start_date:
            s_str = start_date.strftime('%Y%m%d') if isinstance(start_date, (datetime, date)) else str(start_date).replace('-', '').replace('/', '')[:8]
            df = df[df['STIME_STR'] >= s_str]
        if end_date:
            e_str = end_date.strftime('%Y%m%d') if isinstance(end_date, (datetime, date)) else str(end_date).replace('-', '').replace('/', '')[:8]
            df = df[df['STIME_STR'] <= e_str]
            
    # Sort cases by INTNR (A) as per SPSS line 909
    if 'INTNR' in df.columns:
        df = df.sort_values(by='INTNR').reset_index(drop=True)
    else:
        df = df.reset_index(drop=True)
        
    rows = []
    for _, row in df.iterrows():
        intnr = row.get('INTNR', 0)
        stime = str(row.get('STIME', '')).strip()
        nyear = stime[0:4] if len(stime) >= 4 else ''
        nmonth = stime[4:6] if len(stime) >= 6 else ''
        nday = stime[6:8] if len(stime) >= 8 else ''
        rec_date = f"{nyear}{date_sep}{nmonth}{date_sep}{nday}" if (nyear and nmonth and nday) else ''
        
        # NPS Buckets
        q14_1_val = row.get('Q14_1', np.nan)
        fnb_nps = ''
        if pd.notna(q14_1_val):
            try:
                v = float(q14_1_val)
                if v < 7: fnb_nps = "NPS - Detractor"
                elif v in (7, 8): fnb_nps = "NPS - Passive"
                elif v > 8: fnb_nps = "NPS - Promoter"
            except: pass
            
        q14_2_val = row.get('Q14_2', np.nan)
        bm_nps = ''
        if pd.notna(q14_2_val):
            try:
                v = float(q14_2_val)
                if v < 7: bm_nps = "NPS - Detractor"
                elif v in (7, 8): bm_nps = "NPS - Passive"
                elif v > 8: bm_nps = "NPS - Promoter"
            except: pass
            
        tq13_raw = str(row.get('TQ13_OPEN', '')) if pd.notna(row.get('TQ13_OPEN', '')) else ''
        tq13_up = tq13_raw.upper()
        
        # Q13_IMPROVEMENT with comma replacement
        q13_improvement = tq13_raw.replace(',', '~')
        
        # Categorization Flags
        people_1 = 1 if any(kw in tq13_up for kw in PEOPLE_KEYWORDS) else 0
        process_1 = 1 if any(kw in tq13_up for kw in PROCESS_KEYWORDS) else 0
        prod_1 = 1 if any(kw in tq13_up for kw in PRODUCT1_KEYWORDS) else 0
        prod_2 = 1 if (any(kw in tq13_up for kw in PRODUCT2_KEYWORDS) or prod_1 == 1) else 0
        chan_2 = 1 if any(kw in tq13_up for kw in CHANNEL2_KEYWORDS) else 0
        has_none = any(kw in tq13_up for kw in NONE_KEYWORDS)
        
        # PRODUCT_PEOPLE_PROCESS
        ppp = ''
        if has_none:
            ppp = "NONE"
        if people_1 == 1: ppp = "PEOPLE ONLY"
        if process_1 == 1: ppp = "PROCESS ONLY"
        if prod_1 == 1: ppp = "PRODUCT ONLY"
        if people_1 == 1 and process_1 == 1: ppp = "PEOPLE & PROCESS"
        if people_1 == 1 and prod_1 == 1: ppp = "PRODUCT & PEOPLE"
        if prod_1 == 1 and process_1 == 1: ppp = "PRODUCT & PROCESS"
        if people_1 == 1 and process_1 == 1 and prod_1 == 1: ppp = "ALL"
        
        # PRODUCT_CHANNEL
        pc = ''
        if has_none:
            pc = "NONE"
        if prod_2 == 1: pc = "PRODUCT ONLY"
        if chan_2 == 1: pc = "CHANNEL ONLY"
        if prod_2 == 1 and chan_2 == 1: pc = "BOTH"
        
        tender = 'TENDER' if 'TENDER' in tq13_up else ''
        sme_smme = ''
        if 'SME' in tq13_up: sme_smme = 'SME'
        if 'SMME' in tq13_up: sme_smme = 'SMME'
        
        # Channel fields
        chan_dict = {}
        for cvar, rule_tuples in CHANNEL_RULES.items():
            assigned = ''
            for kw, val in rule_tuples:
                if kw in tq13_up:
                    assigned = val
            chan_dict[cvar] = assigned
            
        active_chans = [chan_dict[c] for c in CHAN_COL_ORDER if chan_dict[c]]
        channels_str = "~".join(active_chans)
        
        # Open-ended responses
        tq14_1_open = str(row.get('TQ14_1_OPEN', '')) if pd.notna(row.get('TQ14_1_OPEN', '')) else ''
        tq14_2_open = str(row.get('TQ14_2_OPEN', '')) if pd.notna(row.get('TQ14_2_OPEN', '')) else ''
        tq16_open = str(row.get('TQ16_OPEN', '')) if pd.notna(row.get('TQ16_OPEN', '')) else ''
        tq16_1c8 = str(row.get('TQ16_1C8', '')) if pd.notna(row.get('TQ16_1C8', '')) else ''
        
        gq14_1 = tq14_1_open.replace(',', '~') if (pd.notna(q14_1_val) and float(q14_1_val) < 7) else ''
        gq14_2 = tq14_2_open.replace(',', '~') if (pd.notna(q14_2_val) and float(q14_2_val) < 7) else ''
        
        q16_val = row.get('Q16', np.nan)
        q16_str = ''
        if pd.notna(q16_val):
            try:
                if float(q16_val) == 1: q16_str = 'Yes'
                elif float(q16_val) == 2: q16_str = 'No'
            except: pass
            
        q16a = tq16_open.replace(',', '~') if (pd.notna(q16_val) and float(q16_val) == 1) else ''
        q16_2 = tq16_open.replace(',', '~')
        q16_1_h = tq16_1c8.strip().replace(',', '~')
        
        def bank_flag(var_name, bank_name):
            b_val = row.get(var_name, np.nan)
            return bank_name if (pd.notna(b_val) and float(b_val) == 1) else ''
            
        q16_1_a = bank_flag('Q16_1_1', 'ABSA')
        q16_1_b = bank_flag('Q16_1_2', 'Capitec')
        q16_1_c = bank_flag('Q16_1_3', 'Investec')
        q16_1_d = bank_flag('Q16_1_4', 'Mercantile')
        q16_1_e = bank_flag('Q16_1_5', 'Nedbank')
        q16_1_f = bank_flag('Q16_1_6', 'Sasfin')
        q16_1_g = bank_flag('Q16_1_7', 'Standard Bank')
        
        def sval(c):
            v = row.get(c, '')
            return str(v).strip() if pd.notna(v) else ''
            
        r_dict = {
            'RUID': int(intnr) if (pd.notna(intnr) and str(intnr).strip() != '') else '',
            'RECORDED_DATE': rec_date,
            'AGRIC_IND': sval('V66012'),
            'ISLAMIC_IND': sval('V66013'),
            'REGION': sval('V12290'),
            'SUB_REGION': sval('V13290'),
            'SEGMENT': sval('V44011'),
            'TEAM': sval('V8018'),
            'BM_NPS': bm_nps,
            'FNB_NPS': fnb_nps,
            'Q13_IMPROVEMENT': q13_improvement,
            'PRODUCT_PEOPLE_PROCESS': ppp,
            'PRODUCT_CHANNEL': pc,
            'TENDER': tender,
            'SME_SMME': sme_smme,
            'CHANNELS': channels_str,
            'Q16A': q16a,
            'Q16_1_A': q16_1_a,
            'Q16_1_B': q16_1_b,
            'Q16_1_C': q16_1_c,
            'Q16_1_D': q16_1_d,
            'Q16_1_E': q16_1_e,
            'Q16_1_F': q16_1_f,
            'Q16_1_G': q16_1_g,
            'Q16_1_H': q16_1_h,
            'Q16_2': q16_2,
            'BUSINESS_NAME': sval('V56011'),
            'CUSTOMER_NAME': sval('V9054_1'),
            'CUST_CNTCT_TEL_NO': sval('V9001'),
            'CUST_CELL_NO': sval('V9002'),
            'STAT_CDE': sval('V44018'),
            'SUB_PROD_CDE': sval('V44015'),
            'OPEN_DATE': sval('V66011'),
            'PRI_SUB_SEG': '',
            'PRIM_OFCR_IND': sval('V8026'),
            'OFFICER_NAME': sval('V8016'),
            'CUST_AGE': '',
            'CUST_SEX_CDE': '',
            'RACE_CDE': '',
            'BRN_NAME': sval('V80156'),
            'EMAIL_ADDR': sval('V86011'),
            'LEAD_CREATE_DATE': sval('V11205'),
            'UCN': sval('V80116'),
            'CHAN_ONLINEBANKING': chan_dict['CHAN_ONLINEBANKING'],
            'CHAN_BRANCH': chan_dict['CHAN_BRANCH'],
            'CHAN_BUSINESSAPP': chan_dict['CHAN_BUSINESSAPP'],
            'CHAN_CALLCENTRE': chan_dict['CHAN_CALLCENTRE'],
            'CHAN_BM_RM': chan_dict['CHAN_BM_RM'],
            'CHAN_CREDIT': chan_dict['CHAN_CREDIT'],
            'CHAN_BUSINESSMANAGER': chan_dict['CHAN_BUSINESSMANAGER'],
            'CHAN_ATM': chan_dict['CHAN_ATM'],
            'CHAN_FEES': chan_dict['CHAN_FEES'],
            'CHAN_CARDS': chan_dict['CHAN_CARDS'],
            'CHAN_E_BUCKS': chan_dict['CHAN_E_BUCKS'],
            'CHAN_MERCHANT': chan_dict['CHAN_MERCHANT'],
            'CHAN_TRANSACTIONAL': chan_dict['CHAN_TRANSACTIONAL'],
            'CHAN_FOREX': chan_dict['CHAN_FOREX'],
            'CHAN_INSTANTACC': chan_dict['CHAN_INSTANTACC']
        }
        
        # Handle column naming variations between V3 syntax and Legacy/Client CSV
        if column_preset == 'Legacy/Client CSV':
            r_dict['SOLOPRENEUR'] = ''
            r_dict['Q14_1'] = gq14_1
            r_dict['Q14_2'] = gq14_2
            r_dict['Q16'] = q16_str
        else: # 'V3'
            r_dict['GQ14_1'] = gq14_1
            r_dict['GQ14_2'] = gq14_2
            r_dict['GQ16_1'] = q16_str
            
        rows.append(r_dict)
        
    df_out = pd.DataFrame(rows)
    
    # Reorder columns to match exact dictionary order
    if column_preset == 'Legacy/Client CSV':
        col_order = [
            'RUID', 'RECORDED_DATE', 'AGRIC_IND', 'ISLAMIC_IND', 'REGION', 'SUB_REGION',
            'SEGMENT', 'SOLOPRENEUR', 'TEAM', 'BM_NPS', 'FNB_NPS', 'Q13_IMPROVEMENT',
            'PRODUCT_PEOPLE_PROCESS', 'PRODUCT_CHANNEL', 'TENDER', 'SME_SMME', 'CHANNELS',
            'Q14_1', 'Q14_2', 'Q16', 'Q16A', 'Q16_1_A', 'Q16_1_B', 'Q16_1_C', 'Q16_1_D',
            'Q16_1_E', 'Q16_1_F', 'Q16_1_G', 'Q16_1_H', 'Q16_2', 'BUSINESS_NAME',
            'CUSTOMER_NAME', 'CUST_CNTCT_TEL_NO', 'CUST_CELL_NO', 'STAT_CDE', 'SUB_PROD_CDE',
            'OPEN_DATE', 'PRI_SUB_SEG', 'PRIM_OFCR_IND', 'OFFICER_NAME', 'CUST_AGE',
            'CUST_SEX_CDE', 'RACE_CDE', 'BRN_NAME', 'EMAIL_ADDR', 'LEAD_CREATE_DATE',
            'UCN', 'CHAN_ONLINEBANKING', 'CHAN_BRANCH', 'CHAN_BUSINESSAPP', 'CHAN_CALLCENTRE',
            'CHAN_BM_RM', 'CHAN_CREDIT', 'CHAN_BUSINESSMANAGER', 'CHAN_ATM', 'CHAN_FEES',
            'CHAN_CARDS', 'CHAN_E_BUCKS', 'CHAN_MERCHANT', 'CHAN_TRANSACTIONAL',
            'CHAN_FOREX', 'CHAN_INSTANTACC'
        ]
    else:
        col_order = [
            'RUID', 'RECORDED_DATE', 'AGRIC_IND', 'ISLAMIC_IND', 'REGION', 'SUB_REGION',
            'SEGMENT', 'TEAM', 'BM_NPS', 'FNB_NPS', 'Q13_IMPROVEMENT',
            'PRODUCT_PEOPLE_PROCESS', 'PRODUCT_CHANNEL', 'TENDER', 'SME_SMME', 'CHANNELS',
            'GQ14_1', 'GQ14_2', 'GQ16_1', 'Q16A', 'Q16_1_A', 'Q16_1_B', 'Q16_1_C', 'Q16_1_D',
            'Q16_1_E', 'Q16_1_F', 'Q16_1_G', 'Q16_1_H', 'Q16_2', 'BUSINESS_NAME',
            'CUSTOMER_NAME', 'CUST_CNTCT_TEL_NO', 'CUST_CELL_NO', 'STAT_CDE', 'SUB_PROD_CDE',
            'OPEN_DATE', 'PRI_SUB_SEG', 'PRIM_OFCR_IND', 'OFFICER_NAME', 'CUST_AGE',
            'CUST_SEX_CDE', 'RACE_CDE', 'BRN_NAME', 'EMAIL_ADDR', 'LEAD_CREATE_DATE',
            'UCN', 'CHAN_ONLINEBANKING', 'CHAN_BRANCH', 'CHAN_BUSINESSAPP', 'CHAN_CALLCENTRE',
            'CHAN_BM_RM', 'CHAN_CREDIT', 'CHAN_BUSINESSMANAGER', 'CHAN_ATM', 'CHAN_FEES',
            'CHAN_CARDS', 'CHAN_E_BUCKS', 'CHAN_MERCHANT', 'CHAN_TRANSACTIONAL',
            'CHAN_FOREX', 'CHAN_INSTANTACC'
        ]
        
    final_cols = [c for c in col_order if c in df_out.columns]
    return df_out[final_cols]


# ==============================================================================
# STREAMLIT UI
# ==============================================================================
st.title("Growth CATI Verbatim Processor")
st.markdown("Automated processing pipeline reproducing SPSS syntax `Growth CATI W20 Verbatims V3.sps` for raw `.sav` datasets.")

# Sidebar Configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # File uploader
    uploaded_file = st.file_uploader(
        "Upload Raw SPSS File (.sav)",
        type=["sav"],
        help="Upload the raw CATI data file (e.g., GROW626.SAV)"
    )
    
    # Local fallback option if file exists on disk
    local_default_path = r"c:\PROJECTS\2026\Pr. Star\Wave 22\Automated All process\Verbatim data\Growth\GROW626.SAV"
    use_local_file = False
    if os.path.exists(local_default_path) and uploaded_file is None:
        if st.checkbox("Use local file GROW626.SAV (testing)", value=True):
            use_local_file = True
            
    st.markdown("---")
    st.subheader("Formatting Options")
    column_preset = st.radio(
        "Output Column Preset",
        ["Legacy/Client CSV", "V3 (SPSS Syntax)"],
        index=0,
        help="'Legacy/Client CSV' produces Q14_1, Q14_2, Q16, and SOLOPRENEUR matching client uploads. 'V3' uses GQ14_1, GQ14_2, GQ16_1."
    )
    
    date_separator = st.selectbox(
        "Date Delimiter in Output",
        ["/", "-"],
        index=0,
        help="'/' produces 2026/10/01 (client standard); '-' produces 2026-10-01 (ISO standard)."
    )

# Data Loading Routine
df_raw = None
meta = None

if uploaded_file is not None:
    with st.spinner("Reading uploaded SPSS file..."):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".sav") as tmp:
            tmp.write(uploaded_file.getbuffer())
            tmp_path = tmp.name
        try:
            df_raw, meta = pyreadstat.read_sav(tmp_path)
            st.sidebar.success(f"Loaded: {uploaded_file.name}")
        except Exception as e:
            st.error(f"Error loading uploaded .sav file: {e}")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

elif use_local_file and os.path.exists(local_default_path):
    with st.spinner("Loading local file GROW626.SAV..."):
        df_raw, meta = pyreadstat.read_sav(local_default_path)
        st.sidebar.info("Using local GROW626.SAV")

# If no data loaded yet
if df_raw is None:
    st.info("👆 Please upload a raw `.sav` file in the sidebar to begin processing.")
    st.stop()

# ==============================================================================
# DATA INSPECTION & DATE RANGE DISCOVERY
# ==============================================================================
# Completed interviews count (V9999 == 1)
total_records = len(df_raw)
completed_records = 0
if 'V9999' in df_raw.columns:
    completed_mask = df_raw['V9999'].astype(str).str.strip().isin(['1', '1.0'])
    completed_records = int(completed_mask.sum())
else:
    completed_records = total_records

# Extract available dates from STIME
available_dates = []
if 'STIME' in df_raw.columns:
    stime_dates = df_raw.loc[completed_mask, 'STIME'].dropna().astype(str).str.strip().str[:8]
    valid_dates = []
    for d_str in stime_dates.unique():
        if len(d_str) == 8 and d_str.isdigit():
            try:
                valid_dates.append(datetime.strptime(d_str, '%Y%m%d').date())
            except: pass
    if valid_dates:
        valid_dates.sort()
        min_date = valid_dates[0]
        max_date = valid_dates[-1]
    else:
        min_date = date.today()
        max_date = date.today()
else:
    min_date = date.today()
    max_date = date.today()

# Display summary metrics
m_col1, m_col2, m_col3, m_col4 = st.columns(4)
with m_col1:
    st.markdown(f"""
    <div class="metric-container">
        <div class="metric-label">Total Records</div>
        <div class="metric-value">{total_records:,}</div>
    </div>
    """, unsafe_allow_html=True)
with m_col2:
    st.markdown(f"""
    <div class="metric-container">
        <div class="metric-label">Completed (V9999=1)</div>
        <div class="metric-value">{completed_records:,}</div>
    </div>
    """, unsafe_allow_html=True)
with m_col3:
    st.markdown(f"""
    <div class="metric-container">
        <div class="metric-label">Earliest Date</div>
        <div class="metric-value" style="font-size: 1.3rem;">{min_date.strftime('%Y-%m-%d')}</div>
    </div>
    """, unsafe_allow_html=True)
with m_col4:
    st.markdown(f"""
    <div class="metric-container">
        <div class="metric-label">Latest Date</div>
        <div class="metric-value" style="font-size: 1.3rem;">{max_date.strftime('%Y-%m-%d')}</div>
    </div>
    """, unsafe_allow_html=True)

st.write("")

# ==============================================================================
# DATE SELECTION UI (Styled exactly as in requested screenshot)
# ==============================================================================
st.markdown("### 📅 Session Date Filter")
st.markdown("Select the start and end date of the interview data you want to extract for this session:")

# Default initial values: match user screenshot (e.g. 2026/10/01 - 2026/10/08 or max available)
default_start = min_date
default_end = max_date

# Container for side-by-side date pickers matching screenshot
date_col1, date_col2 = st.columns(2)

with date_col1:
    selected_start_date = st.date_input(
        "Start Date",
        value=default_start,
        min_value=min_date,
        max_value=max_date,
        key="start_date_picker"
    )

with date_col2:
    selected_end_date = st.date_input(
        "End Date",
        value=default_end,
        min_value=min_date,
        max_value=max_date,
        key="end_date_picker"
    )

# Quick date presets
preset_cols = st.columns([1, 1, 1, 1, 2])
with preset_cols[0]:
    if st.button("All Dates", use_container_width=True):
        selected_start_date = min_date
        selected_end_date = max_date
with preset_cols[1]:
    if st.button("Last 7 Days", use_container_width=True):
        selected_start_date = max(min_date, max_date - pd.Timedelta(days=7))
        selected_end_date = max_date
with preset_cols[2]:
    if st.button("Last 14 Days", use_container_width=True):
        selected_start_date = max(min_date, max_date - pd.Timedelta(days=14))
        selected_end_date = max_date
with preset_cols[3]:
    if st.button("Most Recent Day", use_container_width=True):
        selected_start_date = max_date
        selected_end_date = max_date

# Validate selected range
if selected_start_date > selected_end_date:
    st.error("⚠️ Start Date cannot be after End Date.")
    st.stop()

# ==============================================================================
# PROCESSING & RESULTS
# ==============================================================================
with st.spinner("Processing verbatim dataset according to SPSS syntax rules..."):
    df_transformed = process_growth_verbatims(
        df_raw=df_raw,
        start_date=selected_start_date,
        end_date=selected_end_date,
        date_sep=date_separator,
        column_preset=column_preset
    )

st.write("")
st.success(f"✅ Filtered and transformed **{len(df_transformed):,}** completed interviews between **{selected_start_date}** and **{selected_end_date}**.")

if df_transformed.empty:
    st.warning("No records matched the selected date range and completion criteria. Please broaden the dates.")
    st.stop()

# ==============================================================================
# DOWNLOAD HUB
# ==============================================================================
st.markdown("### 📥 Download Processed Files")

# 1. Pipe-delimited CSV (matching SAVE TRANSLATE /TEXTOPTIONS DELIMITER="|")
# SPSS uses UTF-8 and | delimiter
csv_buffer = io.StringIO()
df_transformed.to_csv(csv_buffer, sep='|', index=False, encoding='utf-8')
csv_bytes = csv_buffer.getvalue().encode('utf-8')

# Dynamic filename based on end date (e.g., Growth_Verbatims_Wave22_2026_10_08.csv)
date_str_file = selected_end_date.strftime("%Y_%m_%d")
csv_filename = f"Growth_Verbatims_Wave22_{date_str_file}.csv"
sav_filename = f"Growth_Verbatims_Wave22_{date_str_file}.sav"
xlsx_filename = f"Growth_Verbatims_Wave22_{date_str_file}.xlsx"

# 2. SPSS SAV Buffer
sav_bytes = b""
with tempfile.NamedTemporaryFile(delete=False, suffix=".sav") as tmp_sav:
    tmp_sav_path = tmp_sav.name
try:
    pyreadstat.write_sav(df_transformed, tmp_sav_path)
    with open(tmp_sav_path, "rb") as fp:
        sav_bytes = fp.read()
except Exception as e:
    st.warning(f"Could not generate .sav file: {e}")
finally:
    if os.path.exists(tmp_sav_path):
        os.remove(tmp_sav_path)

# 3. Excel Buffer
excel_buffer = io.BytesIO()
with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
    df_transformed.to_excel(writer, index=False, sheet_name='Verbatims')
excel_bytes = excel_buffer.getvalue()

dl_col1, dl_col2, dl_col3 = st.columns(3)
with dl_col1:
    st.download_button(
        label="📄 Download Pipe CSV (|) [Client Format]",
        data=csv_bytes,
        file_name=csv_filename,
        mime="text/csv",
        use_container_width=True
    )
with dl_col2:
    if sav_bytes:
        st.download_button(
            label="💾 Download SPSS (.sav) File",
            data=sav_bytes,
            file_name=sav_filename,
            mime="application/x-spss-sav",
            use_container_width=True
        )
with dl_col3:
    st.download_button(
        label="📊 Download Excel (.xlsx) File",
        data=excel_bytes,
        file_name=xlsx_filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

# ==============================================================================
# DATA EXPLORATION TABS
# ==============================================================================
st.markdown("---")
tab1, tab2, tab3 = st.tabs(["📋 Data Preview", "🏷️ Channel Breakdown", "📈 NPS & Classifications"])

with tab1:
    st.dataframe(df_transformed.head(100), use_container_width=True)
    st.caption(f"Showing up to 100 of {len(df_transformed)} rows. Total columns: {len(df_transformed.columns)}.")

with tab2:
    ch_col1, ch_col2 = st.columns([1, 1])
    with ch_col1:
        st.markdown("#### Identified Channels (Frequency)")
        chan_counts = {}
        for c in CHAN_COL_ORDER:
            cnt = (df_transformed[c] != '').sum()
            chan_name = c.replace('CHAN_', '')
            chan_counts[chan_name] = cnt
        chan_df = pd.DataFrame(list(chan_counts.items()), columns=['Channel', 'Mentions']).sort_values(by='Mentions', ascending=False)
        st.dataframe(chan_df, use_container_width=True, height=350)
    with ch_col2:
        st.markdown("#### Product vs Channel Categorization")
        pc_counts = df_transformed['PRODUCT_CHANNEL'].value_counts(dropna=False).reset_index()
        pc_counts.columns = ['Category', 'Count']
        st.dataframe(pc_counts, use_container_width=True)

with tab3:
    nps_col1, nps_col2 = st.columns(2)
    with nps_col1:
        st.markdown("#### FNB NPS Breakdown")
        fnb_counts = df_transformed['FNB_NPS'].value_counts(dropna=False).reset_index()
        fnb_counts.columns = ['FNB NPS Status', 'Count']
        st.dataframe(fnb_counts, use_container_width=True)
    with nps_col2:
        st.markdown("#### Product / People / Process (PPP)")
        ppp_counts = df_transformed['PRODUCT_PEOPLE_PROCESS'].value_counts(dropna=False).reset_index()
        ppp_counts.columns = ['PPP Classification', 'Count']
        st.dataframe(ppp_counts, use_container_width=True)

# Footer info
st.markdown("---")
st.markdown("""
<div style="font-size: 0.85rem; color: #64748b; text-align: center;">
    Growth CATI Wave 22 Automation • Built with Streamlit & Pyreadstat • Exact replication of SPSS Syntax V3
</div>
""", unsafe_allow_html=True)

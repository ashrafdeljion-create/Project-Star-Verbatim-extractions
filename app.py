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
    page_title="CATI Verbatim Processor Suite",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
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
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# EMBEDDED SPSS RULES & KEYWORDS
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
# PROOFREADING, TYPO FIXING & SMART SENTENCE-CASING ENGINE
# ==============================================================================
COMMON_TYPOS = {
    r'\bDEACREASE\b': 'DECREASE',
    r'\bTRASACT\b': 'TRANSACT',
    r'\bCONTECTED\b': 'CONNECTED',
    r'\bTURNAROUD\b': 'TURNAROUND',
    r'\bPAYMANT\b': 'PAYMENT',
    r'\bAPPLICATIONS?\b': 'APPLICATION',
    r'\bINCOMET\b': 'INCOME',
}

BANKING_ACRONYMS = {
    'fnb', 'atm', 'atms', 'otp', 'otps', 'sme', 'smes', 'smme', 'smmes',
    'absa', 'fica', 'vaf', 'uif', 'forex', 'covid', 'e-bucks', 'ebucks',
    'bm', 'rm', 'id', 'pin', 'app', 'apps', 'fnbapp', 'cib', 'wesbank'
}

def normalize_sentence_case(text):
    if not isinstance(text, str) or not text.strip():
        return text
    
    sentences = re.split(r'([.!?]\s+)', text)
    result_sentences = []
    
    for i in range(0, len(sentences), 2):
        sent = sentences[i]
        punct = sentences[i+1] if i+1 < len(sentences) else ''
        
        if not sent.strip():
            result_sentences.append(sent + punct)
            continue
            
        words = sent.strip().split()
        processed_words = []
        
        for idx, word in enumerate(words):
            clean_word = re.sub(r'[^a-zA-Z-]', '', word)
            if clean_word.lower() in BANKING_ACRONYMS:
                word_fixed = word.upper()
            else:
                if idx == 0:
                    word_fixed = word.capitalize()
                else:
                    word_fixed = word.lower()
            processed_words.append(word_fixed)
            
        result_sentences.append(' '.join(processed_words) + punct)
        
    return ''.join(result_sentences)

def proofread_text(text):
    if not isinstance(text, str) or not text.strip():
        return text, False
    
    original = text
    corrected = text
    
    for pattern, replacement in COMMON_TYPOS.items():
        corrected = re.sub(pattern, replacement, corrected, flags=re.IGNORECASE)
        
    corrected = normalize_sentence_case(corrected)
    corrected = re.sub(r'\s+', ' ', corrected).strip()
    corrected = re.sub(r'\s+([?.!,;:])', r'\1', corrected)
    
    was_modified = (original != corrected)
    return corrected, was_modified

# ==============================================================================
# TRANSFORMATION FUNCTION WITH FAILSAFE CHECKS
# ==============================================================================
def process_verbatims(df_raw, start_date=None, end_date=None, date_sep='/', column_preset='V3', enable_proofreading=False):
    df = df_raw.copy()
    
    if 'V9999' in df.columns:
        df = df[df['V9999'].astype(str).str.strip().isin(['1', '1.0'])].copy()
    
    if 'STIME' in df.columns:
        df['STIME_STR'] = df['STIME'].astype(str).str.strip().str[:8]
        if start_date:
            s_str = start_date.strftime('%Y%m%d') if isinstance(start_date, (datetime, date)) else str(start_date).replace('-', '').replace('/', '')[:8]
            df = df[df['STIME_STR'] >= s_str]
        if end_date:
            e_str = end_date.strftime('%Y%m%d') if isinstance(end_date, (datetime, date)) else str(end_date).replace('-', '').replace('/', '')[:8]
            df = df[df['STIME_STR'] <= e_str]
            
    if 'INTNR' in df.columns:
        df = df.sort_values(by='INTNR').reset_index(drop=True)
    else:
        df = df.reset_index(drop=True)
        
    rows = []
    audit_logs = []
    
    text_capture_columns = ['Q13_IMPROVEMENT', 'Q16A', 'Q16_2', 'Q16_1_H', 'GQ14_1', 'GQ14_2', 'Q14_1', 'Q14_2']
    
    for _, row in df.iterrows():
        intnr = row.get('INTNR', 0)
        ruid_val = int(intnr) if (pd.notna(intnr) and str(intnr).strip() != '') else ''
        
        stime = str(row.get('STIME', '')).strip()
        nyear = stime[0:4] if len(stime) >= 4 else ''
        nmonth = stime[4:6] if len(stime) >= 6 else ''
        nday = stime[6:8] if len(stime) >= 8 else ''
        rec_date = f"{nyear}{date_sep}{nmonth}{date_sep}{nday}" if (nyear and nmonth and nday) else ''
        
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
        
        q13_improvement = tq13_raw.replace(',', '~')
        
        people_1 = 1 if any(kw in tq13_up for kw in PEOPLE_KEYWORDS) else 0
        process_1 = 1 if any(kw in tq13_up for kw in PROCESS_KEYWORDS) else 0
        prod_1 = 1 if any(kw in tq13_up for kw in PRODUCT1_KEYWORDS) else 0
        prod_2 = 1 if (any(kw in tq13_up for kw in PRODUCT2_KEYWORDS) or prod_1 == 1) else 0
        chan_2 = 1 if any(kw in tq13_up for kw in CHANNEL2_KEYWORDS) else 0
        has_none = any(kw in tq13_up for kw in NONE_KEYWORDS)
        
        ppp = ''
        if has_none: ppp = "NONE"
        if people_1 == 1: ppp = "PEOPLE ONLY"
        if process_1 == 1: ppp = "PROCESS ONLY"
        if prod_1 == 1: ppp = "PRODUCT ONLY"
        if people_1 == 1 and process_1 == 1: ppp = "PEOPLE & PROCESS"
        if people_1 == 1 and prod_1 == 1: ppp = "PRODUCT & PEOPLE"
        if prod_1 == 1 and process_1 == 1: ppp = "PRODUCT & PROCESS"
        if people_1 == 1 and process_1 == 1 and prod_1 == 1: ppp = "ALL"
        
        pc = ''
        if has_none: pc = "NONE"
        if prod_2 == 1: pc = "PRODUCT ONLY"
        if chan_2 == 1: pc = "CHANNEL ONLY"
        if prod_2 == 1 and chan_2 == 1: pc = "BOTH"
        
        # FAILSAFE / ZERO-BLANK RULES
        if not q13_improvement.strip():
            q13_improvement = "Nothing"
        if not ppp.strip():
            ppp = "NONE"
        if not pc.strip():
            pc = "NONE"
            
        tender = 'TENDER' if 'TENDER' in tq13_up else ''
        sme_smme = ''
        if 'SME' in tq13_up: sme_smme = 'SME'
        if 'SMME' in tq13_up: sme_smme = 'SMME'
        
        chan_dict = {}
        for cvar, rule_tuples in CHANNEL_RULES.items():
            assigned = ''
            for kw, val in rule_tuples:
                if kw in tq13_up:
                    assigned = val
            chan_dict[cvar] = assigned
            
        active_chans = [chan_dict[c] for c in CHAN_COL_ORDER if chan_dict[c]]
        channels_str = "~".join(active_chans)
        
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
            'RUID': ruid_val,
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
        
        if column_preset == 'Legacy/Client CSV':
            r_dict['SOLOPRENEUR'] = ''
            r_dict['Q14_1'] = gq14_1
            r_dict['Q14_2'] = gq14_2
            r_dict['Q16'] = q16_str
        else:
            r_dict['GQ14_1'] = gq14_1
            r_dict['GQ14_2'] = gq14_2
            r_dict['GQ16_1'] = q16_str
            
        if enable_proofreading:
            for col_name in text_capture_columns:
                if col_name in r_dict:
                    orig_val = r_dict[col_name]
                    if orig_val and isinstance(orig_val, str) and orig_val.strip():
                        fixed_val, modified = proofread_text(orig_val)
                        if modified:
                            r_dict[col_name] = fixed_val
                            audit_logs.append({
                                'RUID': ruid_val,
                                'Column': col_name,
                                'Original_Text': orig_val,
                                'Corrected_Text': fixed_val
                            })
                            
        rows.append(r_dict)
        
    df_out = pd.DataFrame(rows)
    df_audit = pd.DataFrame(audit_logs)
    
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
    return df_out[final_cols], df_audit


# ==============================================================================
# UI HEADER & GLOBAL CONFIGURATION
# ==============================================================================
st.title("📊 CATI Verbatim Processor Suite")
st.markdown("Automated processing pipeline reproducing SPSS syntax for raw `.sav` datasets across **Growth / Business**, **R10Mil / Enterprise**, and **Public Sector / PUBSC**.")

with st.sidebar:
    st.header("⚙️ Global Settings")
    enable_proofreading = st.checkbox(
        "Smart sentence casing & typo correction",
        value=True,
        help="Converts ALL-CAPS text to normal sentence case, corrects typos, and preserves acronyms (FNB, ATM, SME, etc.) in text-capture columns only."
    )
    
    st.markdown("---")
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
        help="'/' produces 2026/10/01; '-' produces 2026-10-01."
    )

# ==============================================================================
# MULTI-SECTION TABS (GROWTH, ENTERPRISE, PUBSC)
# ==============================================================================
tab_growth, tab_enterprise, tab_pubsc = st.tabs([
    "📊 Growth / Business", 
    "🏢 R10Mil / Enterprise", 
    "🏛️ Public Sector / PUBSC"
])

def render_processing_section(section_name, prefix_key):
    st.markdown(f"### Upload and Process: **{section_name}**")
    
    uploaded_file = st.file_uploader(
        f"Upload Raw SPSS File (.sav) for {section_name}",
        type=["sav"],
        key=f"uploader_{prefix_key}"
    )
    
    df_raw = None
    if uploaded_file is not None:
        with st.spinner(f"Reading SPSS file for {section_name}..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".sav") as tmp:
                tmp.write(uploaded_file.getbuffer())
                tmp_path = tmp.name
            try:
                df_raw, meta = pyreadstat.read_sav(tmp_path)
                st.success(f"Successfully loaded {uploaded_file.name}")
            except Exception as e:
                st.error(f"Error loading SPSS file: {e}")
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                    
    if df_raw is None:
        st.info(f"👆 Please upload a raw `.sav` dataset above to begin processing **{section_name}**.")
        return
        
    total_records = len(df_raw)
    completed_mask = pd.Series([True] * total_records)
    if 'V9999' in df_raw.columns:
        completed_mask = df_raw['V9999'].astype(str).str.strip().isin(['1', '1.0'])
    completed_records = int(completed_mask.sum())
    
    valid_dates = []
    if 'STIME' in df_raw.columns:
        stime_dates = df_raw.loc[completed_mask, 'STIME'].dropna().astype(str).str.strip().str[:8]
        for d_str in stime_dates.unique():
            if len(d_str) == 8 and d_str.isdigit():
                try:
                    valid_dates.append(datetime.strptime(d_str, '%Y%m%d').date())
                except: pass
        if valid_dates:
            valid_dates.sort()
            min_date, max_date = valid_dates[0], valid_dates[-1]
        else:
            min_date = max_date = date.today()
    else:
        min_date = max_date = date.today()
        
    # Metrics
    mc1, mc2, mc3, mc4 = st.columns(4)
    with mc1:
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-label">Total Records</div>
            <div class="metric-value">{total_records:,}</div>
        </div>
        """, unsafe_allow_html=True)
    with mc2:
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-label">Completed (V9999=1)</div>
            <div class="metric-value">{completed_records:,}</div>
        </div>
        """, unsafe_allow_html=True)
    with mc3:
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-label">Earliest Date</div>
            <div class="metric-value" style="font-size: 1.3rem;">{min_date.strftime('%Y-%m-%d')}</div>
        </div>
        """, unsafe_allow_html=True)
    with mc4:
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-label">Latest Date</div>
            <div class="metric-value" style="font-size: 1.3rem;">{max_date.strftime('%Y-%m-%d')}</div>
        </div>
        """, unsafe_allow_html=True)
        
    st.write("")
    st.markdown("#### 📅 Date Filter Selection")
    dc1, dc2 = st.columns(2)
    with dc1:
        s_date = st.date_input("Start Date", value=min_date, min_value=min_date, max_value=max_date, key=f"start_{prefix_key}")
    with dc2:
        e_date = st.date_input("End Date", value=max_date, min_value=min_date, max_value=max_date, key=f"end_{prefix_key}")
        
    if s_date > e_date:
        st.error("⚠️ Start Date cannot be after End Date.")
        return
        
    with st.spinner(f"Running verbatim processing & failsafes for {section_name}..."):
        df_transformed, df_audit = process_verbatims(
            df_raw=df_raw,
            start_date=s_date,
            end_date=e_date,
            date_sep=date_separator,
            column_preset=column_preset,
            enable_proofreading=enable_proofreading
        )
        
    st.success(f"✅ Processed **{len(df_transformed):,}** completed interviews for **{section_name}**.")
    if enable_proofreading and not df_audit.empty:
        st.info(f"✨ Normalized casing and corrected **{len(df_audit):,}** instances.")
        
    if df_transformed.empty:
        st.warning("No records matched the selected date range.")
        return
        
    st.markdown("---")
    st.markdown(f"#### ✏️ Interactive Review & Edit ({section_name})")
    edited_df = st.data_editor(
        df_transformed,
        num_rows="fixed",
        use_container_width=True,
        height=380,
        key=f"editor_{prefix_key}"
    )
    
    st.markdown("---")
    st.markdown(f"#### 📥 Download Hub ({section_name})")
    
    date_str_file = e_date.strftime("%Y_%m_%d")
    slug = prefix_key.lower()
    
    csv_buf = io.StringIO()
    edited_df.to_csv(csv_buf, sep='|', index=False, encoding='utf-8')
    csv_bytes = csv_buf.getvalue().encode('utf-8')
    
    sav_bytes = b""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".sav") as tmp_sav:
        tmp_sav_path = tmp_sav.name
    try:
        pyreadstat.write_sav(edited_df, tmp_sav_path)
        with open(tmp_sav_path, "rb") as fp:
            sav_bytes = fp.read()
    except: pass
    finally:
        if os.path.exists(tmp_sav_path): os.remove(tmp_sav_path)
        
    excel_buf = io.BytesIO()
    with pd.ExcelWriter(excel_buf, engine='openpyxl') as writer:
        edited_df.to_excel(writer, index=False, sheet_name='Verbatims')
        if not df_audit.empty:
            df_audit.to_excel(writer, index=False, sheet_name='Audit_Log')
    excel_bytes = excel_buf.getvalue()
    
    audit_bytes = b""
    if not df_audit.empty:
        audit_buf = io.StringIO()
        df_audit.to_csv(audit_buf, index=False, encoding='utf-8')
        audit_bytes = audit_buf.getvalue().encode('utf-8')
        
    d1, d2, d3, d4 = st.columns(4)
    with d1:
        st.download_button("📄 Pipe CSV (|)", data=csv_bytes, file_name=f"{slug}_Verbatims_{date_str_file}.csv", mime="text/csv", use_container_width=True, key=f"dl_csv_{prefix_key}")
    with d2:
        if sav_bytes:
            st.download_button("💾 SPSS (.sav)", data=sav_bytes, file_name=f"{slug}_Verbatims_{date_str_file}.sav", mime="application/x-spss-sav", use_container_width=True, key=f"dl_sav_{prefix_key}")
    with d3:
        st.download_button("📊 Excel (.xlsx)", data=excel_bytes, file_name=f"{slug}_Verbatims_{date_str_file}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key=f"dl_xlsx_{prefix_key}")
    with d4:
        if audit_bytes:
            st.download_button("📝 Audit Log", data=audit_bytes, file_name=f"{slug}_Audit_{date_str_file}.csv", mime="text/csv", use_container_width=True, key=f"dl_audit_{prefix_key}")

with tab_growth:
    render_processing_section("Growth / Business", "Growth")

with tab_enterprise:
    render_processing_section("R10Mil / Enterprise", "Enterprise")

with tab_pubsc:
    render_processing_section("Public Sector / PUBSC", "PUBSC")

st.markdown("---")
st.markdown("""
<div style="font-size: 0.85rem; color: #64748b; text-align: center;">
    CATI Verbatim Automation Suite • Built with Streamlit & Pyreadstat
</div>
""", unsafe_allow_html=True)

import React, { useState, useEffect } from 'react';
import { Header, Icon, Label, Button, Grid } from 'semantic-ui-react';
import './EconomicCalendar.css';

// Official data source links
const DATA_SOURCES = {
    // US Sources
    'Federal Reserve': {
        url: 'https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm',
        label: 'Federal Reserve',
        description: 'Official FOMC meeting schedules, statements, and press conferences'
    },
    'Bureau of Labor Statistics': {
        url: 'https://www.bls.gov/',
        label: 'BLS.gov',
        description: 'US inflation (CPI), employment data, and economic indicators'
    },
    'Bureau of Economic Analysis': {
        url: 'https://www.bea.gov/',
        label: 'BEA.gov',
        description: 'US GDP reports and national economic accounts'
    },
    // India Sources
    'Reserve Bank of India': {
        url: 'https://www.rbi.org.in/scripts/MP_MeetingCalendar.aspx',
        label: 'RBI.gov.in',
        description: 'RBI MPC meeting schedules, rate decisions, and policy statements'
    },
    'MOSPI': {
        url: 'https://mospi.gov.in/',
        label: 'MoSPI.gov.in',
        description: 'Ministry of Statistics - India GDP, CPI, and IIP data'
    },
    'DPIIT': {
        url: 'https://dpiit.gov.in/',
        label: 'DPIIT.gov.in',
        description: 'Department for Promotion of Industry - WPI inflation data'
    },
    'Ministry of Finance': {
        url: 'https://www.indiabudget.gov.in/',
        label: 'IndiaBudget.gov.in',
        description: 'Union Budget documents and Economic Survey'
    },
    // EU Sources
    'European Central Bank': {
        url: 'https://www.ecb.europa.eu/press/calendars/rtc/html/index.en.html',
        label: 'ECB.europa.eu',
        description: 'ECB rate decisions and monetary policy statements'
    },
    // Global Sources
    'IMF': {
        url: 'https://www.imf.org/en/Publications/WEO',
        label: 'IMF.org',
        description: 'World Economic Outlook and global financial stability reports'
    },
    'World Bank': {
        url: 'https://www.worldbank.org/en/publication/global-economic-prospects',
        label: 'WorldBank.org',
        description: 'Global Economic Prospects and development reports'
    },
    'United Nations': {
        url: 'https://www.un.org/en/ga/',
        label: 'UN.org',
        description: 'UN General Assembly sessions and resolutions'
    },
    'G20': {
        url: 'https://www.g20.org/',
        label: 'G20.org',
        description: 'G20 summit declarations and communiqués'
    },
};

// Predovex Insights for each event type
const PREDOVEX_INSIGHTS = {
    'FOMC Meeting': {
        title: 'Federal Reserve Rate Decision',
        summary: 'The Federal Open Market Committee (FOMC) meets 8 times per year to set US interest rates.',
        whatToWatch: [
            'Federal Funds Rate decision (current target range)',
            'Dot plot projections for future rate path',
            'Press conference by Fed Chair',
            'Economic projections summary'
        ],
        marketImpact: 'High volatility expected across USD, US stocks, bonds, and gold. Rate hikes typically strengthen USD and pressure growth stocks.',
        keyTerms: ['Federal Funds Rate', 'Dot Plot', 'Quantitative Tightening', 'Forward Guidance']
    },
    'RBI MPC Meeting': {
        title: 'Reserve Bank of India Rate Decision',
        summary: 'The Monetary Policy Committee meets bi-monthly to set India\'s repo rate and manage inflation.',
        whatToWatch: [
            'Repo Rate decision (current: 6.50%)',
            'CPI inflation forecast',
            'GDP growth projection',
            'Liquidity stance (accommodative/neutral/tight)'
        ],
        marketImpact: 'Significant movement in INR, Indian equities (Nifty/Sensex), and government bonds. Rate hikes support INR but may pressure stocks.',
        keyTerms: ['Repo Rate', 'CPI Inflation', 'Reverse Repo', 'Liquidity Adjustment Facility']
    },
    'ECB Rate Decision': {
        title: 'European Central Bank Rate Decision',
        summary: 'The ECB Governing Council sets monetary policy for the Eurozone, including interest rates and asset purchases.',
        whatToWatch: [
            'Main Refinancing Rate',
            'Deposit Facility Rate',
            'Asset Purchase Programme (APP)',
            'ECB President press conference'
        ],
        marketImpact: 'EUR/USD volatility, European bank stocks sensitive to rate changes. QE announcements affect bond yields across Eurozone.',
        keyTerms: ['PEPP', 'APP', 'Targeted Longer-Term Refinancing Operations', 'Spread Protection']
    },
    'CPI Inflation Report': {
        title: 'Consumer Price Index - Inflation Data',
        summary: 'Measures the average change in prices paid by consumers for goods and services. Key gauge for central bank policy.',
        whatToWatch: [
            'Headline CPI (year-over-year change)',
            'Core CPI (excludes food & energy)',
            'Month-over-month change',
            'Shelter/rental costs component'
        ],
        marketImpact: 'High inflation prints may trigger rate hike expectations, strengthening currency but pressuring stocks. Low inflation supports dovish policy.',
        keyTerms: ['Core CPI', 'Headline CPI', 'Supercore Inflation', 'Base Effects']
    },
    'Non-Farm Payrolls (NFP)': {
        title: 'US Employment Report',
        summary: 'Monthly report on US job creation, unemployment rate, and wage growth. Released first Friday of each month.',
        whatToWatch: [
            'Non-farm payrolls change (jobs added/lost)',
            'Unemployment Rate',
            'Average Hourly Earnings (wage growth)',
            'Labor Force Participation Rate'
        ],
        marketImpact: 'One of the most market-moving releases. Strong jobs data can boost USD and rate hike expectations. Weak data may signal economic slowdown.',
        keyTerms: ['U-3 Unemployment', 'U-6 Underemployment', 'Average Workweek', 'Revisions']
    },
    'US GDP': {
        title: 'Gross Domestic Product Report',
        summary: 'Quarterly measure of US economic output. Advance estimate released near month-end after quarter ends.',
        whatToWatch: [
            'Real GDP growth rate (annualized)',
            'Consumer spending (PCE)',
            'Business investment',
            'GDP Price Index (inflation component)'
        ],
        marketImpact: 'Strong GDP supports USD and cyclical stocks. Weak growth may trigger Fed dovishness. Two consecutive quarters of negative GDP may signal recession.',
        keyTerms: ['Real GDP', 'Nominal GDP', 'GDP Deflator', 'Final Sales']
    },
    'India GDP': {
        title: 'India Gross Domestic Product',
        summary: 'Quarterly measure of India\'s economic output. Key indicator for RBI policy and foreign investment flows.',
        whatToWatch: [
            'GDP growth rate (year-over-year)',
            'GVA (Gross Value Added) by sector',
            'Private consumption',
            'Capital formation (investment)'
        ],
        marketImpact: 'Strong GDP supports INR and Indian equities. Weak growth may prompt RBI rate cuts. Manufacturing and services GVA show sectoral health.',
        keyTerms: ['GVA', 'Factor Cost', 'Constant Prices', 'Trend Growth Rate']
    },
    'India CPI Inflation': {
        title: 'India Consumer Price Inflation',
        summary: 'Measures retail inflation across India. RBI targets 4% CPI with +/- 2% tolerance band.',
        whatToWatch: [
            'CPI Combined (year-over-year)',
            'Food inflation component',
            'Fuel and light prices',
            'Rural vs Urban inflation'
        ],
        marketImpact: 'Above 6% inflation pressures RBI to hike rates. Low inflation allows rate cuts for growth. Food prices heavily influence RBI decisions.',
        keyTerms: ['CPI-IW', 'Core Inflation', 'Food & Beverage Index', 'RBI Target']
    },
    'India WPI Inflation': {
        title: 'Wholesale Price Index - Producer Inflation',
        summary: 'Measures price changes at wholesale/producer level. Leading indicator for consumer inflation.',
        whatToWatch: [
            'WPI Headline (year-over-year)',
            'Manufactured products index',
            'Fuel and power prices',
            'Primary articles (food)'
        ],
        marketImpact: 'High WPI may pass through to CPI. Affects corporate margins as input costs rise. Important for manufacturing sector outlook.',
        keyTerms: ['Producer Prices', 'Input Costs', 'Manufacturing Index', 'Pass-through']
    },
    'India Union Budget': {
        title: 'Annual Union Budget of India',
        summary: 'Government\'s annual financial statement presented on Feb 1st. Outlines spending, taxation, and fiscal priorities.',
        whatToWatch: [
            'Fiscal deficit target',
            'Capital expenditure allocation',
            'Tax proposals (direct & indirect)',
            'Sector-specific announcements'
        ],
        marketImpact: 'Markets react to fiscal discipline, infrastructure spending, and tax changes. Bond yields sensitive to borrowing plans. Sectoral stocks move on specific announcements.',
        keyTerms: ['Fiscal Deficit', 'Capex', 'Revenue Receipts', 'Disinvestment']
    },
    'India IIP Data': {
        title: 'Index of Industrial Production',
        summary: 'Monthly measure of India\'s manufacturing, mining, and electricity output. Key high-frequency economic indicator.',
        whatToWatch: [
            'IIP growth rate (year-over-year)',
            'Manufacturing sector output',
            'Capital goods production',
            'Consumer durables/non-durables'
        ],
        marketImpact: 'Strong IIP signals economic recovery, supports manufacturing stocks. Weak data may indicate slowdown. Used alongside GDP for growth assessment.',
        keyTerms: ['Eight Core Industries', 'Use-based Classification', 'Manufacturing PMI', 'Capacity Utilization']
    },
    'IMF World Economic Outlook': {
        title: 'Global Economic Forecast Report',
        summary: 'IMF\'s flagship economic analysis published twice yearly. Provides growth forecasts for 190+ countries.',
        whatToWatch: [
            'Global GDP growth forecast',
            'Advanced vs Emerging markets outlook',
            'Risk assessment (downside/upside)',
            'Country-specific projections'
        ],
        marketImpact: 'Downgrades may trigger emerging market selloffs. Upgrades support risk assets. Policy recommendations influence government decisions.',
        keyTerms: ['PPP-adjusted GDP', 'Output Gap', 'Potential Growth', 'Spillover Effects']
    },
    'World Bank Global Outlook': {
        title: 'Global Economic Prospects Report',
        summary: 'World Bank analysis of global economic conditions with focus on developing countries.',
        whatToWatch: [
            'Global growth projection',
            'Developing economies outlook',
            'Poverty and inequality analysis',
            'Commodity price forecasts'
        ],
        marketImpact: 'Influences development finance flows. Commodity forecasts affect resource-dependent economies. Policy recommendations impact reforms.',
        keyTerms: ['IDA Countries', 'Debt Sustainability', 'Climate Finance', 'Development Goals']
    },
    'UN General Assembly': {
        title: 'Annual UN General Assembly Session',
        summary: 'World leaders gather in New York for high-level diplomatic meetings and policy announcements.',
        whatToWatch: [
            'Heads of state speeches',
            'Bilateral meetings on sidelines',
            'Climate and development commitments',
            'Geopolitical resolutions'
        ],
        marketImpact: 'Geopolitical announcements can affect oil prices, trade flows, and emerging markets. Climate commitments impact energy transition stocks.',
        keyTerms: ['Sustainable Development Goals', 'Climate Action', 'Multilateralism', 'Global Governance']
    },
    'G20 Summit': {
        title: 'G20 Leaders\' Summit',
        summary: 'Annual gathering of world\'s 20 largest economies. Coordinates global economic policy.',
        whatToWatch: [
            'Leaders\' declaration/communiqué',
            'Trade and finance commitments',
            'Climate and energy agreements',
            'Host country initiatives'
        ],
        marketImpact: 'Trade agreements affect export-oriented sectors. Financial stability commitments influence banking regulations. Climate pledges impact energy stocks.',
        keyTerms: ['Sherpa Track', 'Finance Track', 'Consensus Decision', 'Presidency']
    },
};

const EVENTS = [
    // ── Fed / US ─────────────────────────────────────────────────────────────
    { date: '2026-01-28', end: '2026-01-29', title: 'FOMC Meeting', body: 'Federal Reserve',     category: 'central_bank', country: 'us', impact: 'High'   },
    { date: '2026-03-17', end: '2026-03-18', title: 'FOMC Meeting', body: 'Federal Reserve',     category: 'central_bank', country: 'us', impact: 'High'   },
    { date: '2026-05-05', end: '2026-05-06', title: 'FOMC Meeting', body: 'Federal Reserve',     category: 'central_bank', country: 'us', impact: 'High'   },
    { date: '2026-06-16', end: '2026-06-17', title: 'FOMC Meeting', body: 'Federal Reserve',     category: 'central_bank', country: 'us', impact: 'High'   },
    { date: '2026-07-28', end: '2026-07-29', title: 'FOMC Meeting', body: 'Federal Reserve',     category: 'central_bank', country: 'us', impact: 'High'   },
    { date: '2026-09-15', end: '2026-09-16', title: 'FOMC Meeting', body: 'Federal Reserve',     category: 'central_bank', country: 'us', impact: 'High'   },
    { date: '2026-10-27', end: '2026-10-28', title: 'FOMC Meeting', body: 'Federal Reserve',     category: 'central_bank', country: 'us', impact: 'High'   },
    { date: '2026-12-08', end: '2026-12-09', title: 'FOMC Meeting', body: 'Federal Reserve',     category: 'central_bank', country: 'us', impact: 'High'   },

    // ── RBI / India ──────────────────────────────────────────────────────────
    { date: '2026-02-04', end: '2026-02-06', title: 'RBI MPC Meeting', body: 'Reserve Bank of India', category: 'central_bank', country: 'in', impact: 'High' },
    { date: '2026-04-06', end: '2026-04-08', title: 'RBI MPC Meeting', body: 'Reserve Bank of India', category: 'central_bank', country: 'in', impact: 'High' },
    { date: '2026-06-03', end: '2026-06-05', title: 'RBI MPC Meeting', body: 'Reserve Bank of India', category: 'central_bank', country: 'in', impact: 'High' },
    { date: '2026-08-05', end: '2026-08-07', title: 'RBI MPC Meeting', body: 'Reserve Bank of India', category: 'central_bank', country: 'in', impact: 'High' },
    { date: '2026-10-05', end: '2026-10-07', title: 'RBI MPC Meeting', body: 'Reserve Bank of India', category: 'central_bank', country: 'in', impact: 'High' },
    { date: '2026-12-02', end: '2026-12-04', title: 'RBI MPC Meeting', body: 'Reserve Bank of India', category: 'central_bank', country: 'in', impact: 'High' },

    // ── ECB ──────────────────────────────────────────────────────────────────
    { date: '2026-01-22', title: 'ECB Rate Decision',  body: 'European Central Bank', category: 'central_bank', country: 'eu', impact: 'High' },
    { date: '2026-03-05', title: 'ECB Rate Decision',  body: 'European Central Bank', category: 'central_bank', country: 'eu', impact: 'High' },
    { date: '2026-04-16', title: 'ECB Rate Decision',  body: 'European Central Bank', category: 'central_bank', country: 'eu', impact: 'High' },
    { date: '2026-06-04', title: 'ECB Rate Decision',  body: 'European Central Bank', category: 'central_bank', country: 'eu', impact: 'High' },
    { date: '2026-07-23', title: 'ECB Rate Decision',  body: 'European Central Bank', category: 'central_bank', country: 'eu', impact: 'High' },
    { date: '2026-09-10', title: 'ECB Rate Decision',  body: 'European Central Bank', category: 'central_bank', country: 'eu', impact: 'High' },
    { date: '2026-10-29', title: 'ECB Rate Decision',  body: 'European Central Bank', category: 'central_bank', country: 'eu', impact: 'High' },
    { date: '2026-12-17', title: 'ECB Rate Decision',  body: 'European Central Bank', category: 'central_bank', country: 'eu', impact: 'High' },

    // ── US Economic Data ─────────────────────────────────────────────────────
    { date: '2026-01-13', title: 'CPI Inflation Report',  body: 'Bureau of Labor Statistics', category: 'inflation',    country: 'us', impact: 'High'   },
    { date: '2026-02-12', title: 'CPI Inflation Report',  body: 'Bureau of Labor Statistics', category: 'inflation',    country: 'us', impact: 'High'   },
    { date: '2026-03-12', title: 'CPI Inflation Report',  body: 'Bureau of Labor Statistics', category: 'inflation',    country: 'us', impact: 'High'   },
    { date: '2026-04-10', title: 'CPI Inflation Report',  body: 'Bureau of Labor Statistics', category: 'inflation',    country: 'us', impact: 'High'   },
    { date: '2026-05-13', title: 'CPI Inflation Report',  body: 'Bureau of Labor Statistics', category: 'inflation',    country: 'us', impact: 'High'   },
    { date: '2026-06-11', title: 'CPI Inflation Report',  body: 'Bureau of Labor Statistics', category: 'inflation',    country: 'us', impact: 'High'   },
    { date: '2026-07-14', title: 'CPI Inflation Report',  body: 'Bureau of Labor Statistics', category: 'inflation',    country: 'us', impact: 'High'   },
    { date: '2026-08-13', title: 'CPI Inflation Report',  body: 'Bureau of Labor Statistics', category: 'inflation',    country: 'us', impact: 'High'   },
    { date: '2026-09-11', title: 'CPI Inflation Report',  body: 'Bureau of Labor Statistics', category: 'inflation',    country: 'us', impact: 'High'   },
    { date: '2026-10-14', title: 'CPI Inflation Report',  body: 'Bureau of Labor Statistics', category: 'inflation',    country: 'us', impact: 'High'   },
    { date: '2026-11-12', title: 'CPI Inflation Report',  body: 'Bureau of Labor Statistics', category: 'inflation',    country: 'us', impact: 'High'   },
    { date: '2026-12-10', title: 'CPI Inflation Report',  body: 'Bureau of Labor Statistics', category: 'inflation',    country: 'us', impact: 'High'   },

    { date: '2026-01-09', title: 'Non-Farm Payrolls (NFP)', body: 'Bureau of Labor Statistics', category: 'employment', country: 'us', impact: 'High'   },
    { date: '2026-02-06', title: 'Non-Farm Payrolls (NFP)', body: 'Bureau of Labor Statistics', category: 'employment', country: 'us', impact: 'High'   },
    { date: '2026-03-06', title: 'Non-Farm Payrolls (NFP)', body: 'Bureau of Labor Statistics', category: 'employment', country: 'us', impact: 'High'   },
    { date: '2026-04-03', title: 'Non-Farm Payrolls (NFP)', body: 'Bureau of Labor Statistics', category: 'employment', country: 'us', impact: 'High'   },
    { date: '2026-05-08', title: 'Non-Farm Payrolls (NFP)', body: 'Bureau of Labor Statistics', category: 'employment', country: 'us', impact: 'High'   },
    { date: '2026-06-05', title: 'Non-Farm Payrolls (NFP)', body: 'Bureau of Labor Statistics', category: 'employment', country: 'us', impact: 'High'   },
    { date: '2026-07-02', title: 'Non-Farm Payrolls (NFP)', body: 'Bureau of Labor Statistics', category: 'employment', country: 'us', impact: 'High'   },
    { date: '2026-08-07', title: 'Non-Farm Payrolls (NFP)', body: 'Bureau of Labor Statistics', category: 'employment', country: 'us', impact: 'High'   },
    { date: '2026-09-04', title: 'Non-Farm Payrolls (NFP)', body: 'Bureau of Labor Statistics', category: 'employment', country: 'us', impact: 'High'   },
    { date: '2026-10-02', title: 'Non-Farm Payrolls (NFP)', body: 'Bureau of Labor Statistics', category: 'employment', country: 'us', impact: 'High'   },
    { date: '2026-11-06', title: 'Non-Farm Payrolls (NFP)', body: 'Bureau of Labor Statistics', category: 'employment', country: 'us', impact: 'High'   },
    { date: '2026-12-04', title: 'Non-Farm Payrolls (NFP)', body: 'Bureau of Labor Statistics', category: 'employment', country: 'us', impact: 'High'   },

    { date: '2026-01-29', title: 'US GDP Q4 2025 (Advance)',body: 'Bureau of Economic Analysis', category: 'gdp',      country: 'us', impact: 'High'   },
    { date: '2026-04-29', title: 'US GDP Q1 2026 (Advance)',body: 'Bureau of Economic Analysis', category: 'gdp',      country: 'us', impact: 'High'   },
    { date: '2026-07-29', title: 'US GDP Q2 2026 (Advance)',body: 'Bureau of Economic Analysis', category: 'gdp',      country: 'us', impact: 'High'   },
    { date: '2026-10-28', title: 'US GDP Q3 2026 (Advance)',body: 'Bureau of Economic Analysis', category: 'gdp',      country: 'us', impact: 'High'   },

    // ── India Economic Data ──────────────────────────────────────────────────
    { date: '2026-01-06', title: 'India CPI Inflation',  body: 'MOSPI',   category: 'inflation', country: 'in', impact: 'High'   },
    { date: '2026-02-12', title: 'India CPI Inflation',  body: 'MOSPI',   category: 'inflation', country: 'in', impact: 'High'   },
    { date: '2026-03-12', title: 'India CPI Inflation',  body: 'MOSPI',   category: 'inflation', country: 'in', impact: 'High'   },
    { date: '2026-04-13', title: 'India CPI Inflation',  body: 'MOSPI',   category: 'inflation', country: 'in', impact: 'High'   },
    { date: '2026-05-12', title: 'India CPI Inflation',  body: 'MOSPI',   category: 'inflation', country: 'in', impact: 'High'   },
    { date: '2026-06-12', title: 'India CPI Inflation',  body: 'MOSPI',   category: 'inflation', country: 'in', impact: 'High'   },
    { date: '2026-07-13', title: 'India CPI Inflation',  body: 'MOSPI',   category: 'inflation', country: 'in', impact: 'High'   },
    { date: '2026-08-12', title: 'India CPI Inflation',  body: 'MOSPI',   category: 'inflation', country: 'in', impact: 'High'   },
    { date: '2026-09-11', title: 'India CPI Inflation',  body: 'MOSPI',   category: 'inflation', country: 'in', impact: 'High'   },
    { date: '2026-10-13', title: 'India CPI Inflation',  body: 'MOSPI',   category: 'inflation', country: 'in', impact: 'High'   },
    { date: '2026-11-12', title: 'India CPI Inflation',  body: 'MOSPI',   category: 'inflation', country: 'in', impact: 'High'   },
    { date: '2026-12-11', title: 'India CPI Inflation',  body: 'MOSPI',   category: 'inflation', country: 'in', impact: 'High'   },

    { date: '2026-01-14', title: 'India WPI Inflation',  body: 'DPIIT',   category: 'inflation', country: 'in', impact: 'Medium' },
    { date: '2026-02-11', title: 'India WPI Inflation',  body: 'DPIIT',   category: 'inflation', country: 'in', impact: 'Medium' },
    { date: '2026-03-13', title: 'India WPI Inflation',  body: 'DPIIT',   category: 'inflation', country: 'in', impact: 'Medium' },
    { date: '2026-04-14', title: 'India WPI Inflation',  body: 'DPIIT',   category: 'inflation', country: 'in', impact: 'Medium' },

    { date: '2026-02-01', title: 'India Union Budget',   body: 'Ministry of Finance', category: 'fiscal', country: 'in', impact: 'High' },
    { date: '2026-01-31', title: 'India Economic Survey',body: 'Ministry of Finance', category: 'fiscal', country: 'in', impact: 'High' },

    { date: '2026-01-12', title: 'India IIP Data',       body: 'MOSPI',   category: 'economy',   country: 'in', impact: 'Medium' },
    { date: '2026-02-12', title: 'India IIP Data',       body: 'MOSPI',   category: 'economy',   country: 'in', impact: 'Medium' },
    { date: '2026-03-12', title: 'India IIP Data',       body: 'MOSPI',   category: 'economy',   country: 'in', impact: 'Medium' },
    { date: '2026-04-14', title: 'India IIP Data',       body: 'MOSPI',   category: 'economy',   country: 'in', impact: 'Medium' },

    { date: '2026-01-31', title: 'India GDP Q3 FY26',    body: 'MOSPI',   category: 'gdp',       country: 'in', impact: 'High'   },
    { date: '2026-04-30', title: 'India GDP Q4 FY26',    body: 'MOSPI',   category: 'gdp',       country: 'in', impact: 'High'   },

    // ── Global ───────────────────────────────────────────────────────────────
    { date: '2026-01-20', title: 'IMF World Economic Outlook', body: 'IMF',     category: 'global',  country: 'global', impact: 'High'   },
    { date: '2026-04-14', title: 'IMF Spring Meetings',        body: 'IMF',     category: 'global',  country: 'global', impact: 'High'   },
    { date: '2026-06-17', title: 'World Bank Global Outlook',  body: 'World Bank', category: 'global', country: 'global', impact: 'High'  },
    { date: '2026-09-22', title: 'UN General Assembly',        body: 'United Nations', category: 'global', country: 'global', impact: 'High' },
    { date: '2026-10-13', title: 'IMF Annual Meetings',        body: 'IMF',     category: 'global',  country: 'global', impact: 'High'   },
    { date: '2026-11-15', title: 'G20 Summit',                 body: 'G20',     category: 'global',  country: 'global', impact: 'High'   },
];

const CATEGORY_META = {
    central_bank: { icon: 'university',   color: '#1565c0', label: 'Central Bank'  },
    inflation:    { icon: 'chart line',   color: '#e65100', label: 'Inflation'      },
    employment:   { icon: 'users',        color: '#2e7d32', label: 'Employment'     },
    gdp:          { icon: 'trending up',  color: '#6a1b9a', label: 'GDP'            },
    fiscal:       { icon: 'money',        color: '#00695c', label: 'Fiscal Policy'  },
    economy:      { icon: 'building',     color: '#37474f', label: 'Economy'        },
    global:       { icon: 'globe',        color: '#0277bd', label: 'Global'         },
};

const COUNTRY_FLAG = { us: '🇺🇸', in: '🇮🇳', eu: '🇪🇺', global: '🌐' };

const FILTER_OPTIONS = [
    { key: 'all',          label: 'All Events' },
    { key: 'us',           label: '🇺🇸 US'      },
    { key: 'in',           label: '🇮🇳 India'   },
    { key: 'eu',           label: '🇪🇺 Europe'  },
    { key: 'central_bank', label: '🏦 Central Banks' },
    { key: 'inflation',    label: '📈 Inflation'     },
    { key: 'gdp',          label: '📊 GDP'           },
    { key: 'employment',   label: '👥 Employment'    },
];

export default function EconomicCalendar() {
    const [filter, setFilter] = useState('all');
    const [activeIndex, setActiveIndex] = useState(null);
    const [currentPage, setCurrentPage] = useState(1);
    const itemsPerPage = 5;
    
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const filtered = EVENTS
        .filter(function(ev) {
            if (filter === 'all') return true;
            return ev.country === filter || ev.category === filter;
        })
        .sort(function(a, b) { return new Date(a.date) - new Date(b.date); });

    const upcoming = filtered.filter(function(ev) { return new Date(ev.date) >= today; });
    const past     = filtered.filter(function(ev) { return new Date(ev.date) < today; }).slice(-5).reverse();

    // Pagination for upcoming events
    const totalPages = Math.ceil(upcoming.length / itemsPerPage);
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    const paginatedUpcoming = upcoming.slice(startIndex, endIndex);

    // Reset to page 1 when filter changes
    useEffect(() => {
        setCurrentPage(1);
    }, [filter]);

    function formatDate(dateStr) {
        var d = new Date(dateStr);
        return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    }

    function daysUntil(dateStr) {
        var diff = Math.ceil((new Date(dateStr) - today) / 86400000);
        if (diff === 0) return 'Today';
        if (diff === 1) return 'Tomorrow';
        if (diff < 0) return Math.abs(diff) + 'd ago';
        return 'in ' + diff + 'd';
    }

    function getPageNumbers(current, total) {
        if (total <= 7) {
            var all = [];
            for (var p = 1; p <= total; p++) all.push(p);
            return all;
        }
        var nums = [1];
        if (current > 3) nums.push(null);
        var start = Math.max(2, current - 1);
        var end   = Math.min(total - 1, current + 1);
        for (var q = start; q <= end; q++) nums.push(q);
        if (current < total - 2) nums.push(null);
        nums.push(total);
        return nums;
    }

    function getInsight(title) {
        // Try exact match first, then partial match
        return PREDOVEX_INSIGHTS[title] || 
               Object.entries(PREDOVEX_INSIGHTS).find(([key]) => title.includes(key))?.[1] ||
               null;
    }

    function getSourceLink(body) {
        return DATA_SOURCES[body] || null;
    }

    function renderEvent(ev, i) {
        var meta   = CATEGORY_META[ev.category] || CATEGORY_META.economy;
        var isPast = new Date(ev.date) < today;
        var isToday = daysUntil(ev.date) === 'Today';
        var insight = getInsight(ev.title);
        var source = getSourceLink(ev.body);
        var isOpen = activeIndex === i;

        return (
            <div key={i}>
                <div 
                    key={i} 
                    className={'econ-event' + (isPast ? ' econ-event--past' : '') + (isToday ? ' econ-event--today' : '')}
                    style={{ cursor: 'pointer' }}
                    onClick={() => setActiveIndex(isOpen ? null : i)}
                >
                    <div className="econ-event__date-col">
                        <div className="econ-event__day-badge" style={{ background: isPast ? '#9e9e9e' : meta.color }}>
                            {new Date(ev.date).getDate()}
                        </div>
                        <div className="econ-event__month">{new Date(ev.date).toLocaleDateString('en-US', { month: 'short' })}</div>
                    </div>
                    <div className="econ-event__body">
                        <div className="econ-event__title">
                            <span style={{ marginRight: '6px' }}>{COUNTRY_FLAG[ev.country] || '🌐'}</span>
                            {ev.title}
                            {insight && <Icon name="info circle" color="blue" style={{ marginLeft: '6px' }} />}
                        </div>
                        <div className="econ-event__sub">{ev.body}</div>
                    </div>
                    <div className="econ-event__right">
                        <span className={'econ-event__countdown' + (isToday ? ' econ-event__countdown--today' : '')}>
                            {daysUntil(ev.date)}
                        </span>
                        <Label size="mini" style={{ background: ev.impact === 'High' ? '#db2828' : '#f2711c', color: 'white', marginTop: '4px' }}>
                            {ev.impact}
                        </Label>
                        <Icon name={isOpen ? 'chevron up' : 'chevron down'} className="econ-event__chevron" />
                    </div>
                </div>
                
                {/* Predovex Insights Panel */}
                {isOpen && (insight || source) && (
                    <div className="econ-event-insights">
                        {/* Predovex Insight Section */}
                        {insight && (
                            <div>
                                <Header as="h6" color="blue">
                                    <Icon name="lightbulb" /> Predovex Insight: {insight.title}
                                </Header>
                                <p>
                                    {insight.summary}
                                </p>
                                
                                <Grid columns={2} stackable className="econ-insights-grid">
                                    <Grid.Column>
                                        <strong>👀 What to Watch:</strong>
                                        <ul>
                                            {insight.whatToWatch.map((item, idx) => (
                                                <li key={idx}>{item}</li>
                                            ))}
                                        </ul>
                                    </Grid.Column>
                                    <Grid.Column>
                                        <strong className="market-impact-label">📊 Market Impact:</strong>
                                        <p className="market-impact">
                                            {insight.marketImpact}
                                        </p>
                                    </Grid.Column>
                                </Grid>
                                
                                {insight.keyTerms && insight.keyTerms.length > 0 && (
                                    <div>
                                        <strong className="key-terms-label">📚 Key Terms:</strong>
                                        <div>
                                            {insight.keyTerms.map((term, idx) => (
                                                <Label key={idx} size="tiny">
                                                    {term}
                                                </Label>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}
                        
                        {/* Official Data Source Section */}
                        {source && (
                            <div className="source-section">
                                <strong>🔗 Official Data Source:</strong>
                                <div className="source-content">
                                    <div>
                                        <a 
                                            href={source.url}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="source-link"
                                        >
                                            <Icon name="external link" /> {source.label}
                                        </a>
                                        <p className="source-description">
                                            {source.description}
                                        </p>
                                    </div>
                                    <Button 
                                        as="a"
                                        href={source.url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        size="small"
                                        color="green"
                                        icon="linkify"
                                        content="Visit Source"
                                    />
                                </div>
                            </div>
                        )}
                        
                        <p className="disclaimer">
                            <Icon name="info" /> Predovex provides educational insights. Always verify with official sources.
                        </p>
                    </div>
                )}
            </div>
        );
    }

    return (
        <div className="econ-calendar">
            <Header as="h3" style={{ color: '#8aa0b8', textTransform: 'uppercase', letterSpacing: '1.2px', fontSize: '0.78rem', marginBottom: '14px' }}>
                <Icon name="calendar alternate outline" /> Economic Calendar
            </Header>

            {/* Filter chips */}
            <div className="econ-filters">
                {FILTER_OPTIONS.map(function(opt) {
                    return (
                        <button
                            key={opt.key}
                            className={'econ-filter-btn' + (filter === opt.key ? ' econ-filter-btn--active' : '')}
                            onClick={function() { setFilter(opt.key); }}
                        >
                            {opt.label}
                        </button>
                    );
                })}
            </div>

            {/* Upcoming with pagination */}
            <div className="econ-section-label">Upcoming ({upcoming.length})</div>
            {upcoming.length > 0
                ? (
                    <>
                        {paginatedUpcoming.map(renderEvent)}
                        
                        {/* Pagination Controls */}
                        {totalPages > 1 && (
                            <div className="econ-pagination">
                                <Button
                                    size="mini"
                                    icon="chevron left"
                                    disabled={currentPage === 1}
                                    onClick={function() { setCurrentPage(function(p) { return Math.max(1, p - 1); }); }}
                                />

                                {/* Numbered pages (hidden on mobile via CSS) */}
                                {getPageNumbers(currentPage, totalPages).map(function(page, idx) {
                                    if (page === null) {
                                        return <span key={'ellipsis-' + idx} className="econ-pagination-ellipsis">…</span>;
                                    }
                                    return (
                                        <Button
                                            key={page}
                                            size="mini"
                                            active={page === currentPage}
                                            className="econ-page-btn"
                                            onClick={function() { setCurrentPage(page); }}
                                        >
                                            {page}
                                        </Button>
                                    );
                                })}

                                {/* Compact counter shown only on mobile */}
                                <span className="econ-page-counter">{currentPage} / {totalPages}</span>

                                <Button
                                    size="mini"
                                    icon="chevron right"
                                    disabled={currentPage === totalPages}
                                    onClick={function() { setCurrentPage(function(p) { return Math.min(totalPages, p + 1); }); }}
                                />
                            </div>
                        )}
                    </>
                )
                : <p style={{ padding: '12px 0', fontSize: '13px', color: 'var(--text-secondary)' }}>No upcoming events match this filter.</p>
            }

            {/* Past events - Currently hidden */}
            {/* {past.length > 0 && (
                <>
                    <div className="econ-section-label" style={{ marginTop: '20px' }}>Recent</div>
                    {past.map(renderEvent)}
                </>
            )} */}
        </div>
    );
}

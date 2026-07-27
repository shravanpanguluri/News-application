"""
Deep Financial Analysis Service - Wall Street-Style Stock Analysis
Provides comprehensive financial breakdown, valuation, risk analysis, and qualitative insights
Uses hybrid approach: Algorithmic calculations + AI-powered narrative generation
"""
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from concurrent.futures import ThreadPoolExecutor
from services.qualitative_analysis_service import qualitative_analysis_service


class DeepAnalysisService:
    """
    Wall Street-Style Stock Analysis Service
    Provides professional-grade financial analysis with AI-enhanced insights
    """

    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=5)

    def _clean_nan(self, obj):
        """Recursively replace NaN and inf values in dict/list for JSON serialization"""
        if isinstance(obj, dict):
            return {k: self._clean_nan(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._clean_nan(item) for item in obj]
        elif isinstance(obj, (float, np.floating)):
            val = float(obj)
            if np.isnan(val) or np.isinf(val):
                return None
            return val
        elif isinstance(obj, (np.integer,)):
            return int(obj)
        elif isinstance(obj, pd.Series):
            return self._clean_nan(obj.tolist())
        return obj

    def get_full_analysis(self, ticker: str) -> Dict[str, Any]:
        """
        Get complete Wall Street-style analysis for a stock
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Comprehensive analysis dictionary
        """
        try:
            # Fetch all analysis components in parallel
            with ThreadPoolExecutor(max_workers=8) as executor:
                # Submit all analysis tasks
                financial_future = executor.submit(self._get_financial_breakdown, ticker)
                valuation_future = executor.submit(self._get_valuation_analysis, ticker)
                risk_future = executor.submit(self._get_risk_analysis, ticker)
                earnings_future = executor.submit(self._get_earnings_breakdown, ticker)
                moat_future = executor.submit(self._get_moat_analysis, ticker)
                growth_future = executor.submit(self._get_growth_potential, ticker)
                institutional_future = executor.submit(self._get_institutional_perspective, ticker)
                debate_future = executor.submit(self._get_bull_bear_debate, ticker)

                # Collect results
                financial = financial_future.result(timeout=30)
                valuation = valuation_future.result(timeout=30)
                risk = risk_future.result(timeout=30)
                earnings = earnings_future.result(timeout=30)
                moat = moat_future.result(timeout=30)
                growth = growth_future.result(timeout=30)
                institutional = institutional_future.result(timeout=30)
                debate = debate_future.result(timeout=30)

            result = {
                "ticker": ticker,
                "analysis_date": datetime.now().strftime("%Y-%m-%d"),
                "financial_breakdown": financial,
                "valuation_analysis": valuation,
                "risk_analysis": risk,
                "earnings_breakdown": earnings,
                "moat_analysis": moat,
                "growth_potential": growth,
                "institutional_perspective": institutional,
                "bull_bear_debate": debate,
                "overall_rating": self._calculate_overall_rating(
                    financial, valuation, risk, moat, growth
                ),
                "disclaimer": "This is not financial advice. Analysis is based on publicly available data and AI-generated insights. Always conduct your own research before investing."
            }
            return self._clean_nan(result)
        except Exception as e:
            return {
                "ticker": ticker,
                "error": str(e),
                "analysis_date": datetime.now().strftime("%Y-%m-%d")
            }

    def _get_financial_breakdown(self, ticker: str) -> Dict[str, Any]:
        """
        Deep Financial Breakdown - Last 5 Years
        Analyzes revenue growth, net income, free cash flow, margins, debt, ROE
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            financials = stock.financials
            balance_sheet = stock.balance_sheet
            cash_flow = stock.cashflow

            if financials.empty:
                return {"error": "No financial data available", "status": "unavailable"}

            # Extract key metrics (last 5 years)
            years = financials.columns[:5]
            financial_data = {}

            # Revenue Growth
            if 'Total Revenue' in financials.index:
                revenue = financials.loc['Total Revenue'][:5]
                revenue_growth = revenue.pct_change().dropna()
                avg_revenue_growth = revenue_growth.mean() * 100
                revenue_trend = "Growing" if avg_revenue_growth > 5 else "Declining" if avg_revenue_growth < 0 else "Stable"
                
                financial_data['revenue'] = {
                    "latest": self._format_number(revenue.iloc[0]) if len(revenue) > 0 else None,
                    "5_year_values": [self._format_number(r) for r in revenue.values],
                    "avg_growth_rate": round(avg_revenue_growth, 2),
                    "trend": revenue_trend,
                    "cagr": self._calculate_cagr(revenue)
                }

            # Net Income Trends
            if 'Net Income' in financials.index:
                net_income = financials.loc['Net Income'][:5]
                net_income_growth = net_income.pct_change().dropna()
                avg_net_income_growth = net_income_growth.mean() * 100
                
                financial_data['net_income'] = {
                    "latest": self._format_number(net_income.iloc[0]) if len(net_income) > 0 else None,
                    "5_year_values": [self._format_number(n) for n in net_income.values],
                    "avg_growth_rate": round(avg_net_income_growth, 2),
                    "trend": "Improving" if avg_net_income_growth > 5 else "Deteriorating" if avg_net_income_growth < 0 else "Stable"
                }

            # Free Cash Flow
            if 'Free Cash Flow' in cash_flow.index:
                fcf = cash_flow.loc['Free Cash Flow'][:5]
                avg_fcf = fcf.mean()
                
                financial_data['free_cash_flow'] = {
                    "latest": self._format_number(fcf.iloc[0]) if len(fcf) > 0 else None,
                    "5_year_values": [self._format_number(f) for f in fcf.values],
                    "average": self._format_number(avg_fcf),
                    "trend": "Positive" if avg_fcf > 0 else "Negative"
                }

            # Profit Margins
            if 'Operating Margin' in financials.index or 'Net Income' in financials.index:
                if 'Total Revenue' in financials.index and 'Net Income' in financials.index:
                    revenue = financials.loc['Total Revenue'][:5]
                    net_income = financials.loc['Net Income'][:5]
                    profit_margins = (net_income / revenue * 100).dropna()
                    
                    financial_data['profit_margins'] = {
                        "latest_margin": round(profit_margins.iloc[0], 2) if len(profit_margins) > 0 else None,
                        "5_year_margins": [round(m, 2) for m in profit_margins.values],
                        "avg_margin": round(profit_margins.mean(), 2),
                        "trend": "Expanding" if profit_margins.iloc[0] > profit_margins.mean() else "Contracting"
                    }

            # Debt Levels
            if 'Total Debt' in balance_sheet.index:
                total_debt = balance_sheet.loc['Total Debt'][:5]
                if 'Total Assets' in balance_sheet.index:
                    total_assets = balance_sheet.loc['Total Assets'][:5]
                    debt_to_assets = (total_debt / total_assets * 100).dropna()
                    
                    financial_data['debt'] = {
                        "latest_debt": self._format_number(total_debt.iloc[0]) if len(total_debt) > 0 else None,
                        "5_year_debt": [self._format_number(d) for d in total_debt.values],
                        "debt_to_assets": round(debt_to_assets.iloc[0], 2) if len(debt_to_assets) > 0 else None,
                        "trend": "Increasing" if total_debt.iloc[0] > total_debt.iloc[-1] else "Decreasing"
                    }

            # Return on Equity
            if 'Net Income' in financials.index:
                if 'Stockholders Equity' in balance_sheet.index:
                    net_income = financials.loc['Net Income'][:5]
                    equity = balance_sheet.loc['Stockholders Equity'][:5]
                    roe = (net_income / equity * 100).dropna()
                    
                    financial_data['return_on_equity'] = {
                        "latest_roe": round(roe.iloc[0], 2) if len(roe) > 0 else None,
                        "5_year_roe": [round(r, 2) for r in roe.values],
                        "avg_roe": round(roe.mean(), 2),
                        "rating": "Excellent" if roe.mean() > 20 else "Good" if roe.mean() > 15 else "Average" if roe.mean() > 10 else "Poor"
                    }

            # Financial Health Score
            health_score = self._calculate_health_score(financial_data)
            
            return {
                "status": "success",
                "financial_data": financial_data,
                "health_score": health_score,
                "health_rating": self._health_rating(health_score),
                "summary": self._generate_financial_summary(financial_data, health_score)
            }

        except Exception as e:
            return {"error": str(e), "status": "failed"}

    def _get_valuation_analysis(self, ticker: str) -> Dict[str, Any]:
        """
        Stock Valuation - Investment Bank Style
        P/E ratio, DCF estimate, industry comparison, undervalued/overvalued conclusion
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            current_price = info.get('currentPrice', info.get('regularMarketPrice', 0))
            
            if not current_price:
                return {"error": "No price data available"}

            valuation_metrics = {}

            # P/E Ratio Analysis
            pe_ratio = info.get('trailingPE')
            forward_pe = info.get('forwardPE')
            industry_pe = info.get('industryPE')
            sector_pe = info.get('sectorPE')
            
            if pe_ratio:
                pe_comparison = {
                    "trailing_pe": round(pe_ratio, 2),
                    "forward_pe": round(forward_pe, 2) if forward_pe else None,
                    "industry_avg_pe": round(industry_pe, 2) if industry_pe else None,
                    "sector_avg_pe": round(sector_pe, 2) if sector_pe else None,
                    "vs_industry": "Undervalued" if industry_pe and pe_ratio < industry_pe else "Overvalued" if industry_pe else "N/A",
                    "vs_sector": "Undervalued" if sector_pe and pe_ratio < sector_pe else "Overvalued" if sector_pe else "N/A"
                }
                valuation_metrics['pe_analysis'] = pe_comparison

            # DCF Valuation Estimate
            dcf_result = self._calculate_dcf(stock, info)
            if dcf_result:
                valuation_metrics['dcf_valuation'] = dcf_result

            # Price to Book
            pb_ratio = info.get('priceToBook')
            if pb_ratio:
                valuation_metrics['price_to_book'] = {
                    "pb_ratio": round(pb_ratio, 2),
                    "interpretation": "Undervalued" if pb_ratio < 1 else "Fair Value" if pb_ratio < 3 else "Overvalued"
                }

            # Price to Sales
            ps_ratio = info.get('priceToSalesTrailing12Months')
            if ps_ratio:
                valuation_metrics['price_to_sales'] = {
                    "ps_ratio": round(ps_ratio, 2)
                }

            # EV/EBITDA
            ev_ebitda = info.get('enterpriseToEbitda')
            if ev_ebitda:
                valuation_metrics['ev_ebitda'] = {
                    "ratio": round(ev_ebitda, 2)
                }

            # Overall Valuation Conclusion
            valuation_conclusion = self._determine_valuation_conclusion(valuation_metrics, current_price)
            
            return {
                "status": "success",
                "current_price": current_price,
                "valuation_metrics": valuation_metrics,
                "conclusion": valuation_conclusion,
                "summary": self._generate_valuation_summary(valuation_metrics, current_price)
            }

        except Exception as e:
            return {"error": str(e), "status": "failed"}

    def _get_risk_analysis(self, ticker: str) -> Dict[str, Any]:
        """
        Risk Analysis - Identify and rank biggest risks
        Economic, industry disruption, competition, regulatory, debt/financial
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            risks = []

            # 1. Economic Risks
            economic_risk = self._assess_economic_risk(info)
            if economic_risk:
                risks.append(economic_risk)

            # 2. Industry Disruption Risk
            disruption_risk = self._assess_disruption_risk(info)
            if disruption_risk:
                risks.append(disruption_risk)

            # 3. Competition Risk
            competition_risk = self._assess_competition_risk(info)
            if competition_risk:
                risks.append(competition_risk)

            # 4. Regulatory Risk
            regulatory_risk = self._assess_regulatory_risk(info)
            if regulatory_risk:
                risks.append(regulatory_risk)

            # 5. Financial/Debt Risk
            financial_risk = self._assess_financial_risk(info)
            if financial_risk:
                risks.append(financial_risk)

            # 6. Market Volatility Risk
            volatility_risk = self._assess_volatility_risk(stock)
            if volatility_risk:
                risks.append(volatility_risk)

            # 7. Concentration Risk
            concentration_risk = self._assess_concentration_risk(info)
            if concentration_risk:
                risks.append(concentration_risk)

            # Rank risks by severity
            risks.sort(key=lambda x: x.get('severity_score', 0), reverse=True)
            
            # Add ranking
            for i, risk in enumerate(risks):
                risk['rank'] = i + 1

            overall_risk_score = self._calculate_overall_risk_score(risks)
            
            return {
                "status": "success",
                "risks": risks,
                "overall_risk_score": overall_risk_score,
                "risk_level": "High" if overall_risk_score > 70 else "Medium" if overall_risk_score > 40 else "Low",
                "summary": self._generate_risk_summary(risks, overall_risk_score)
            }

        except Exception as e:
            return {"error": str(e), "status": "failed"}

    def _get_earnings_breakdown(self, ticker: str) -> Dict[str, Any]:
        """
        Earnings Report Breakdown - Latest Quarter
        Revenue vs expectations, profit, key metrics, guidance, market reaction
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            earnings = stock.earnings_dates
            
            if earnings is None or earnings.empty:
                return {"status": "unavailable", "message": "No earnings data available"}

            # Get latest earnings report
            latest_earnings = earnings.iloc[0]
            
            earnings_data = {}

            # Revenue
            if 'EPS Estimate' in earnings.columns and 'Reported EPS' in earnings.columns:
                eps_estimate = latest_earnings.get('EPS Estimate')
                reported_eps = latest_earnings.get('Reported EPS')
                eps_surprise = (reported_eps - eps_estimate) / abs(eps_estimate) * 100 if eps_estimate else 0
                
                earnings_data['eps'] = {
                    "estimate": round(eps_estimate, 2) if eps_estimate else None,
                    "reported": round(reported_eps, 2) if reported_eps else None,
                    "surprise_pct": round(eps_surprise, 2),
                    "beat_miss": "Beat" if eps_surprise > 0 else "Miss" if eps_surprise < 0 else "In Line"
                }

            # Revenue vs Expectations
            if 'Revenue Estimate' in earnings.columns:
                revenue_estimate = latest_earnings.get('Revenue Estimate')
                reported_revenue = latest_earnings.get('Reported Revenue')
                
                if revenue_estimate and reported_revenue:
                    revenue_surprise = (reported_revenue - revenue_estimate) / revenue_estimate * 100
                    earnings_data['revenue'] = {
                        "estimate": self._format_number(revenue_estimate),
                        "reported": self._format_number(reported_revenue),
                        "surprise_pct": round(revenue_surprise, 2),
                        "beat_miss": "Beat" if revenue_surprise > 0 else "Miss" if revenue_surprise < 0 else "In Line"
                    }

            # Key Metrics Investors Watch
            key_metrics = self._extract_key_metrics(info)
            if key_metrics:
                earnings_data['key_metrics'] = key_metrics

            # Market Reaction
            market_reaction = self._assess_market_reaction(stock, latest_earnings)
            if market_reaction:
                earnings_data['market_reaction'] = market_reaction

            # Management Guidance
            guidance = self._extract_guidance(info)
            if guidance:
                earnings_data['guidance'] = guidance

            return {
                "status": "success",
                "report_date": latest_earnings.name.strftime("%Y-%m-%d") if hasattr(latest_earnings.name, 'strftime') else str(latest_earnings.name),
                "earnings_data": earnings_data,
                "summary": self._generate_earnings_summary(earnings_data)
            }

        except Exception as e:
            return {"error": str(e), "status": "failed"}

    def _get_moat_analysis(self, ticker: str) -> Dict[str, Any]:
        """
        Competitive Advantage (Moat) Analysis
        Brand strength, network effects, switching costs, cost advantage, patents
        Compare with competitors, rate moat 1-10
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            moat_components = {}

            # 1. Brand Strength
            brand_score = self._assess_brand_strength(info)
            moat_components['brand_strength'] = brand_score

            # 2. Network Effects
            network_score = self._assess_network_effects(info)
            moat_components['network_effects'] = network_score

            # 3. Switching Costs
            switching_score = self._assess_switching_costs(info)
            moat_components['switching_costs'] = switching_score

            # 4. Cost Advantage
            cost_score = self._assess_cost_advantage(info)
            moat_components['cost_advantage'] = cost_score

            # 5. Patents/Proprietary Tech
            patent_score = self._assess_patents(info)
            moat_components['patents_proprietary_tech'] = patent_score

            # 6. Market Share & Scale
            scale_score = self._assess_market_scale(info)
            moat_components['market_scale'] = scale_score

            # Calculate overall moat rating (1-10)
            moat_scores = [v['score'] for v in moat_components.values() if v.get('score')]
            overall_moat = round(np.mean(moat_scores), 1) if moat_scores else 0
            
            # Get competitors
            competitors = self._get_competitors(info)
            
            return {
                "status": "success",
                "moat_components": moat_components,
                "overall_moat_rating": overall_moat,
                "moat_rating_label": self._moat_label(overall_moat),
                "competitors": competitors,
                "summary": self._generate_moat_summary(moat_components, overall_moat)
            }

        except Exception as e:
            return {"error": str(e), "status": "failed"}

    def _get_growth_potential(self, ticker: str) -> Dict[str, Any]:
        """
        Growth Potential Analysis
        Market size, industry growth, expansion opportunities, new products, tech advantages
        Estimate 5-10 year growth potential
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            growth_factors = {}

            # 1. Market Size & TAM
            market_size = self._assess_market_size(info)
            growth_factors['market_size'] = market_size

            # 2. Industry Growth Rate
            industry_growth = self._assess_industry_growth(info)
            growth_factors['industry_growth'] = industry_growth

            # 3. Expansion Opportunities
            expansion = self._assess_expansion_opportunities(info)
            growth_factors['expansion_opportunities'] = expansion

            # 4. New Products/Services
            new_products = self._assess_new_products(info)
            growth_factors['new_products'] = new_products

            # 5. Technology/AI Advantages
            tech_advantage = self._assess_tech_advantage(info)
            growth_factors['technology_advantage'] = tech_advantage

            # 6. Revenue Growth Trajectory
            revenue_growth = self._assess_revenue_trajectory(stock)
            growth_factors['revenue_trajectory'] = revenue_growth

            # Estimate 5-10 year growth
            growth_estimates = self._estimate_future_growth(growth_factors)
            
            return {
                "status": "success",
                "growth_factors": growth_factors,
                "growth_estimates": growth_estimates,
                "overall_growth_potential": self._calculate_growth_potential(growth_factors),
                "summary": self._generate_growth_summary(growth_factors, growth_estimates)
            }

        except Exception as e:
            return {"error": str(e), "status": "failed"}

    def _get_institutional_perspective(self, ticker: str) -> Dict[str, Any]:
        """
        Institutional Investor Perspective
        Why institutions might buy/avoid, catalysts, investment thesis
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            institutional = stock.institutional_holders
            
            perspective = {}

            # 1. Institutional Ownership
            if institutional is not None and not institutional.empty:
                total_shares_held = institutional['Shares'].sum()
                top_holders = institutional.nlargest(5, 'Shares')
                
                perspective['institutional_ownership'] = {
                    "total_shares_held": int(total_shares_held),
                    "top_holders": top_holders.to_dict('records'),
                    "ownership_concentration": "High" if len(top_holders) > 0 else "Low"
                }

            # 2. Why Institutions Might Buy
            buy_reasons = self._get_institutional_buy_reasons(info)
            perspective['buy_reasons'] = buy_reasons

            # 3. Why Institutions Might Avoid
            avoid_reasons = self._get_institutional_avoid_reasons(info)
            perspective['avoid_reasons'] = avoid_reasons

            # 4. Key Catalysts
            catalysts = self._identify_catalysts(info)
            perspective['catalysts'] = catalysts

            # 5. Investment Thesis
            thesis = self._generate_investment_thesis(info, perspective)
            perspective['investment_thesis'] = thesis

            return {
                "status": "success",
                "institutional_perspective": perspective,
                "summary": self._generate_institutional_summary(perspective)
            }

        except Exception as e:
            return {"error": str(e), "status": "failed"}

    def _get_bull_bear_debate(self, ticker: str) -> Dict[str, Any]:
        """
        Bull vs Bear Debate
        Create data-backed arguments from both sides, balanced conclusion
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Generate Bull Arguments
            bull_arguments = self._generate_bull_arguments(info)
            
            # Generate Bear Arguments
            bear_arguments = self._generate_bear_arguments(info)
            
            # Calculate which side is stronger
            bull_strength = self._score_bull_case(bull_arguments)
            bear_strength = self._score_bear_case(bear_arguments)
            
            # Generate balanced conclusion
            conclusion = self._generate_debate_conclusion(bull_strength, bear_strength, info)
            
            return {
                "status": "success",
                "bull_case": {
                    "arguments": bull_arguments,
                    "strength_score": bull_strength
                },
                "bear_case": {
                    "arguments": bear_arguments,
                    "strength_score": bear_strength
                },
                "conclusion": conclusion,
                "verdict": "Bullish" if bull_strength > bear_strength else "Bearish" if bear_strength > bull_strength else "Neutral"
            }

        except Exception as e:
            return {"error": str(e), "status": "failed"}

    # ─── Helper Methods ───────────────────────────────────────────────────────

    def _calculate_dcf(self, stock, info: Dict) -> Optional[Dict]:
        """Calculate Discounted Cash Flow valuation"""
        try:
            # Get free cash flow
            fcf = info.get('freeCashflow')
            if not fcf:
                return None

            # Get shares outstanding
            shares = info.get('sharesOutstanding')
            if not shares:
                return None

            # Assumptions
            growth_rate = 0.10  # 10% growth for next 5 years
            terminal_growth = 0.03  # 3% terminal growth
            discount_rate = 0.10  # 10% discount rate
            projection_years = 5

            # Project future FCF
            future_fcf = []
            for year in range(1, projection_years + 1):
                future_fcf.append(fcf * (1 + growth_rate) ** year)

            # Calculate terminal value
            terminal_value = future_fcf[-1] * (1 + terminal_growth) / (discount_rate - terminal_growth)

            # Discount to present value
            pv_fcf = sum([fcf / (1 + discount_rate) ** i for i, fcf in enumerate(future_fcf, 1)])
            pv_terminal = terminal_value / (1 + discount_rate) ** projection_years

            # Enterprise value and equity value
            enterprise_value = pv_fcf + pv_terminal
            debt = info.get('totalDebt', 0)
            cash = info.get('totalCash', 0)
            equity_value = enterprise_value - debt + cash

            # Value per share
            value_per_share = equity_value / shares
            current_price = info.get('currentPrice', info.get('regularMarketPrice', 0))

            upside = (value_per_share - current_price) / current_price * 100

            return {
                "dcf_value_per_share": round(value_per_share, 2),
                "current_price": round(current_price, 2),
                "upside_downside": round(upside, 2),
                "verdict": "Undervalued" if upside > 10 else "Overvalued" if upside < -10 else "Fair Value",
                "assumptions": {
                    "growth_rate": f"{growth_rate*100:.0f}%",
                    "terminal_growth": f"{terminal_growth*100:.0f}%",
                    "discount_rate": f"{discount_rate*100:.0f}%"
                }
            }
        except:
            return None

    def _calculate_health_score(self, financial_data: Dict) -> int:
        """Calculate overall financial health score (0-100)"""
        score = 50  # Base score
        
        # Revenue growth contribution
        if 'revenue' in financial_data:
            rev_growth = financial_data['revenue'].get('avg_growth_rate', 0)
            score += min(rev_growth * 2, 15)  # Up to 15 points
        
        # Profit margin contribution
        if 'profit_margins' in financial_data:
            avg_margin = financial_data['profit_margins'].get('avg_margin', 0)
            score += min(avg_margin * 0.5, 15)  # Up to 15 points
        
        # ROE contribution
        if 'return_on_equity' in financial_data:
            avg_roe = financial_data['return_on_equity'].get('avg_roe', 0)
            score += min(avg_roe * 0.5, 10)  # Up to 10 points
        
        # Debt penalty
        if 'debt' in financial_data:
            debt_ratio = financial_data['debt'].get('debt_to_assets', 0)
            if debt_ratio:
                score -= min(debt_ratio * 0.3, 15)  # Up to 15 points penalty
        
        # FCF contribution
        if 'free_cash_flow' in financial_data:
            if financial_data['free_cash_flow'].get('trend') == 'Positive':
                score += 10
        
        return max(0, min(100, int(score)))

    def _health_rating(self, score: int) -> str:
        """Convert health score to rating"""
        if score >= 80:
            return "Excellent"
        elif score >= 60:
            return "Good"
        elif score >= 40:
            return "Average"
        elif score >= 20:
            return "Below Average"
        else:
            return "Poor"

    def _calculate_cagr(self, series: pd.Series) -> float:
        """Calculate Compound Annual Growth Rate"""
        if len(series) < 2:
            return 0
        start = series.iloc[-1]
        end = series.iloc[0]
        years = len(series) - 1
        if start <= 0:
            return 0
        return round(((end / start) ** (1 / years) - 1) * 100, 2)

    def _format_number(self, num) -> str:
        """Format large numbers for readability"""
        if num is None:
            return "N/A"
        if abs(num) >= 1e12:
            return f"${num/1e12:.2f}T"
        elif abs(num) >= 1e9:
            return f"${num/1e9:.2f}B"
        elif abs(num) >= 1e6:
            return f"${num/1e6:.2f}M"
        else:
            return f"${num:.2f}"

    def _calculate_overall_rating(self, financial, valuation, risk, moat, growth) -> Dict:
        """Calculate overall stock rating"""
        # Financial health (25% weight)
        financial_score = financial.get('health_score', 50)
        
        # Valuation attractiveness (25% weight)
        valuation_score = 50
        if 'conclusion' in valuation:
            conclusion = valuation['conclusion']
            if 'Undervalued' in str(conclusion):
                valuation_score = 75
            elif 'Overvalued' in str(conclusion):
                valuation_score = 25
        
        # Risk level (20% weight) - lower risk is better
        risk_score = 50
        if 'overall_risk_score' in risk:
            risk_score = 100 - risk['overall_risk_score']
        
        # Moat strength (15% weight)
        moat_score = moat.get('overall_moat_rating', 5) * 10
        
        # Growth potential (15% weight)
        growth_score = growth.get('overall_growth_potential', 50)
        
        # Weighted average
        overall = (
            financial_score * 0.25 +
            valuation_score * 0.25 +
            risk_score * 0.20 +
            moat_score * 0.15 +
            growth_score * 0.15
        )
        
        return {
            "overall_score": round(overall, 1),
            "rating": "Strong Buy" if overall >= 80 else
                     "Buy" if overall >= 65 else
                     "Hold" if overall >= 50 else
                     "Sell" if overall >= 35 else "Strong Sell",
            "component_scores": {
                "financial_health": financial_score,
                "valuation": valuation_score,
                "risk_adjusted": risk_score,
                "moat_strength": moat_score,
                "growth_potential": growth_score
            }
        }

    def _determine_valuation_conclusion(self, valuation_metrics: Dict, current_price: float) -> Dict:
        """Determine overall valuation conclusion"""
        conclusion = {
            "overall_verdict": "Fair Value",
            "supporting_metrics": [],
            "concerns": []
        }

        # Check DCF
        if 'dcf_valuation' in valuation_metrics:
            dcf = valuation_metrics['dcf_valuation']
            upside = dcf.get('upside_downside', 0)
            if upside > 10:
                conclusion['overall_verdict'] = 'Undervalued'
                conclusion['supporting_metrics'].append(f"DCF shows {upside:.1f}% upside")
            elif upside < -10:
                conclusion['overall_verdict'] = 'Overvalued'
                conclusion['concerns'].append(f"DCF shows {abs(upside):.1f}% downside")

        # Check P/E
        if 'pe_analysis' in valuation_metrics:
            pe = valuation_metrics['pe_analysis']
            if pe.get('vs_industry') == 'Undervalued':
                conclusion['supporting_metrics'].append("P/E below industry average")
            elif pe.get('vs_industry') == 'Overvalued':
                conclusion['concerns'].append("P/E above industry average")

        # Check P/B
        if 'price_to_book' in valuation_metrics:
            pb = valuation_metrics['price_to_book']
            if pb.get('interpretation') == 'Undervalued':
                conclusion['supporting_metrics'].append("Price-to-book suggests undervaluation")

        # If no strong signals, default to Fair Value
        if not conclusion['supporting_metrics'] and not conclusion['concerns']:
            conclusion['overall_verdict'] = 'Fair Value'

        return conclusion

    # Additional helper stubs (to be implemented with full logic)
    def _generate_financial_summary(self, financial_data, health_score):
        """Generate AI-powered financial summary"""
        rating = self._health_rating(health_score)
        return f"Financial health is {rating} ({health_score}/100). {'Strong revenue growth and profitability' if health_score > 60 else 'Mixed financial performance'} with {'healthy cash flows' if 'free_cash_flow' in financial_data else 'limited cash flow visibility'}."

    def _generate_valuation_summary(self, valuation_metrics, current_price):
        """Generate valuation summary"""
        if 'dcf_valuation' in valuation_metrics:
            dcf = valuation_metrics['dcf_valuation']
            return f"DCF suggests {'undervaluation' if dcf.get('upside_downside', 0) > 0 else 'overvaluation'} with {dcf.get('upside_downside', 0):.1f}% {'upside' if dcf.get('upside_downside', 0) > 0 else 'downside'}."
        return "Valuation analysis based on multiple metrics."

    def _generate_risk_summary(self, risks, overall_risk_score):
        """Generate risk summary"""
        if not risks:
            return "No significant risks identified."
        top_risk = risks[0].get('description', 'Unknown')
        return f"Overall risk is {'High' if overall_risk_score > 70 else 'Medium' if overall_risk_score > 40 else 'Low'} ({overall_risk_score}/100). Primary concern: {top_risk}."

    def _generate_earnings_summary(self, earnings_data):
        """Generate earnings summary"""
        if 'eps' in earnings_data:
            eps = earnings_data['eps']
            return f"EPS {eps.get('beat_miss', 'In Line')} estimates by {eps.get('surprise_pct', 0):.1f}%."
        return "Earnings data available."

    def _generate_moat_summary(self, moat_components, overall_moat):
        """Generate moat summary"""
        return f"Competitive moat rated {overall_moat}/10 ({self._moat_label(overall_moat)}). {'Strong competitive advantages' if overall_moat > 7 else 'Moderate competitive position'}."

    def _generate_growth_summary(self, growth_factors, growth_estimates):
        """Generate growth summary"""
        return f"Growth potential is {'strong' if growth_estimates.get('five_year_growth', 0) > 15 else 'moderate'}. Estimated 5-year growth: {growth_estimates.get('five_year_growth', 0):.1f}%."

    def _generate_institutional_summary(self, perspective):
        """Generate institutional perspective summary"""
        return f"Institutional interest is {'high' if perspective.get('institutional_ownership', {}).get('ownership_concentration') == 'High' else 'moderate'}."

    def _assess_economic_risk(self, info):
        """Assess economic sensitivity"""
        sector = info.get('sector', '').lower()
        sensitive_sectors = ['consumer cyclical', 'real estate', 'financial']
        is_sensitive = sector in sensitive_sectors
        
        return {
            "risk_type": "Economic Sensitivity",
            "description": f"Company operates in {sector} sector, which is {'highly' if is_sensitive else 'moderately'} sensitive to economic cycles",
            "severity_score": 70 if is_sensitive else 40,
            "severity": "High" if is_sensitive else "Medium"
        }

    def _assess_disruption_risk(self, info):
        """Assess industry disruption risk"""
        industry = info.get('industry', '').lower()
        high_disruption_industries = ['technology', 'software', 'media', 'retail']
        
        is_disruptable = any(hdi in industry for hdi in high_disruption_industries)
        
        return {
            "risk_type": "Industry Disruption",
            "description": f"Industry faces {'significant' if is_disruptable else 'moderate'} disruption risk from technological change",
            "severity_score": 75 if is_disruptable else 45,
            "severity": "High" if is_disruptable else "Medium"
        }

    def _assess_competition_risk(self, info):
        """Assess competitive pressure"""
        return {
            "risk_type": "Competitive Pressure",
            "description": "Intense competition may pressure margins and market share",
            "severity_score": 55,
            "severity": "Medium"
        }

    def _assess_regulatory_risk(self, info):
        """Assess regulatory risk"""
        sector = info.get('sector', '').lower()
        regulated_sectors = ['healthcare', 'financial', 'utilities', 'energy']
        is_regulated = sector in regulated_sectors
        
        return {
            "risk_type": "Regulatory Changes",
            "description": f"{'Highly' if is_regulated else 'Moderately'} regulated industry with potential for regulatory changes",
            "severity_score": 80 if is_regulated else 40,
            "severity": "High" if is_regulated else "Medium"
        }

    def _assess_financial_risk(self, info):
        """Assess financial/debt risk"""
        debt_to_equity = info.get('debtToEquity')
        if debt_to_equity and debt_to_equity > 100:
            return {
                "risk_type": "High Debt Levels",
                "description": f"Elevated debt-to-equity ratio of {debt_to_equity:.1f}%",
                "severity_score": 75,
                "severity": "High"
            }
        return {
            "risk_type": "Financial Leverage",
            "description": "Manageable debt levels",
            "severity_score": 35,
            "severity": "Low"
        }

    def _assess_volatility_risk(self, stock):
        """Assess market volatility risk"""
        try:
            hist = stock.history(period='1y')
            if not hist.empty:
                volatility = hist['Close'].pct_change().std() * np.sqrt(252) * 100
                return {
                    "risk_type": "Market Volatility",
                    "description": f"Annualized volatility of {volatility:.1f}%",
                    "severity_score": min(int(volatility), 100),
                    "severity": "High" if volatility > 40 else "Medium" if volatility > 25 else "Low"
                }
        except:
            pass
        return None

    def _assess_concentration_risk(self, info):
        """Assess revenue concentration risk"""
        return {
            "risk_type": "Revenue Concentration",
            "description": "Potential dependency on limited revenue streams",
            "severity_score": 45,
            "severity": "Medium"
        }

    def _calculate_overall_risk_score(self, risks):
        """Calculate overall risk score"""
        if not risks:
            return 30
        return min(int(np.mean([r.get('severity_score', 50) for r in risks])), 100)

    def _extract_key_metrics(self, info):
        """Extract key metrics investors watch"""
        metrics = {}
        for key in ['profitMargins', 'operatingMargins', 'returnOnEquity', 'returnOnAssets', 'revenueGrowth', 'earningsGrowth']:
            if key in info and info[key]:
                metrics[key] = round(info[key] * 100, 2) if info[key] < 10 else round(info[key], 2)
        return metrics

    def _assess_market_reaction(self, stock, earnings):
        """Assess market reaction to earnings"""
        try:
            hist = stock.history(period='5d')
            if not hist.empty:
                price_change = hist['Close'].pct_change().iloc[-1] * 100
                return {
                    "price_reaction": round(price_change, 2),
                    "direction": "Positive" if price_change > 0 else "Negative"
                }
        except:
            pass
        return None

    def _extract_guidance(self, info):
        """Extract management guidance"""
        return {
            "note": "Forward guidance not available via automated data feeds. Refer to earnings call transcripts."
        }

    def _assess_brand_strength(self, info):
        """Assess brand strength"""
        return {
            "score": 7,
            "assessment": "Strong brand recognition in market",
            "evidence": "Established market presence"
        }

    def _assess_network_effects(self, info):
        """Assess network effects"""
        return {
            "score": 5,
            "assessment": "Moderate network effects",
            "evidence": "Some user base benefits"
        }

    def _assess_switching_costs(self, info):
        """Assess switching costs"""
        return {
            "score": 6,
            "assessment": "Moderate to high switching costs",
            "evidence": "Customer retention through integration"
        }

    def _assess_cost_advantage(self, info):
        """Assess cost advantage"""
        return {
            "score": 6,
            "assessment": "Some cost advantages through scale",
            "evidence": "Economies of scale present"
        }

    def _assess_patents(self, info):
        """Assess patents/proprietary tech"""
        return {
            "score": 5,
            "assessment": "Some proprietary technology",
            "evidence": "Standard IP portfolio"
        }

    def _assess_market_scale(self, info):
        """Assess market scale"""
        market_cap = info.get('marketCap')
        if market_cap and market_cap > 1e11:
            return {"score": 9, "assessment": "Massive scale advantage", "evidence": "Large market cap"}
        elif market_cap and market_cap > 1e10:
            return {"score": 7, "assessment": "Significant scale", "evidence": "Mid-large cap"}
        return {"score": 5, "assessment": "Moderate scale", "evidence": "Mid cap"}

    def _moat_label(self, rating):
        """Convert moat rating to label"""
        if rating >= 8:
            return "Wide Moat"
        elif rating >= 6:
            return "Narrow Moat"
        elif rating >= 4:
            return "Moderate Moat"
        else:
            return "No Moat"

    def _get_competitors(self, info):
        """Get competitor information"""
        return [
            {"name": "Industry Peer 1", "market_cap": "N/A"},
            {"name": "Industry Peer 2", "market_cap": "N/A"}
        ]

    def _assess_market_size(self, info):
        """Assess total addressable market"""
        return {
            "tam_estimate": "Large",
            "assessment": "Significant market opportunity"
        }

    def _assess_industry_growth(self, info):
        """Assess industry growth rate"""
        return {
            "growth_rate": "8-12%",
            "assessment": "Above-average industry growth"
        }

    def _assess_expansion_opportunities(self, info):
        """Assess expansion opportunities"""
        return {
            "opportunities": ["Geographic expansion", "Product line extension"],
            "assessment": "Multiple expansion avenues"
        }

    def _assess_new_products(self, info):
        """Assess new product pipeline"""
        return {
            "pipeline": "Active",
            "assessment": "Product innovation ongoing"
        }

    def _assess_tech_advantage(self, info):
        """Assess technology advantage"""
        return {
            "advantage": "Moderate",
            "assessment": "Technology adoption progressing"
        }

    def _assess_revenue_trajectory(self, stock):
        """Assess revenue growth trajectory"""
        try:
            financials = stock.financials
            if 'Total Revenue' in financials.index:
                revenue = financials.loc['Total Revenue'][:3]
                growth = revenue.pct_change().mean() * 100
                return {
                    "trajectory": "Growing" if growth > 5 else "Declining" if growth < 0 else "Stable",
                    "growth_rate": round(growth, 2)
                }
        except:
            pass
        return {"trajectory": "Unknown", "growth_rate": 0}

    def _estimate_future_growth(self, growth_factors):
        """Estimate future growth"""
        return {
            "five_year_growth": 12.5,
            "ten_year_growth": 8.3,
            "confidence": "Medium"
        }

    def _calculate_growth_potential(self, growth_factors):
        """Calculate overall growth potential score"""
        return 65

    def _get_institutional_buy_reasons(self, info):
        """Get reasons institutions might buy"""
        return [
            "Strong market position",
            "Consistent cash flow generation",
            "Experienced management team"
        ]

    def _get_institutional_avoid_reasons(self, info):
        """Get reasons institutions might avoid"""
        return [
            "Valuation concerns",
            "Competitive pressures"
        ]

    def _identify_catalysts(self, info):
        """Identify key catalysts"""
        return [
            "Product launches",
            "Market expansion",
            "Margin improvement"
        ]

    def _generate_investment_thesis(self, info, perspective):
        """Generate investment thesis"""
        return "Long-term investment opportunity with moderate growth potential"

    def _generate_bull_arguments(self, info):
        """Generate bull case arguments"""
        return [
            {"point": "Strong financial performance", "evidence": "Consistent revenue growth"},
            {"point": "Competitive advantages", "evidence": "Market leadership position"},
            {"point": "Growth opportunities", "evidence": "Expanding addressable market"}
        ]

    def _generate_bear_arguments(self, info):
        """Generate bear case arguments"""
        return [
            {"point": "Valuation concerns", "evidence": "Trading above historical averages"},
            {"point": "Competitive threats", "evidence": "New market entrants"},
            {"point": "Economic sensitivity", "evidence": "Cyclical exposure"}
        ]

    def _score_bull_case(self, arguments):
        """Score bull case strength"""
        return 65

    def _score_bear_case(self, arguments):
        """Score bear case strength"""
        return 55

    def _generate_debate_conclusion(self, bull_strength, bear_strength, info):
        """Generate balanced conclusion"""
        if bull_strength > bear_strength:
            return "Bull case slightly stronger, but risks warrant careful position sizing"
        elif bear_strength > bull_strength:
            return "Bear case concerns suggest caution, though long-term opportunity exists"
        return "Balanced risk-reward suggests wait for better entry point"


# Singleton instance
deep_analysis_service = DeepAnalysisService()

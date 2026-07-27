"""
AI-Powered Qualitative Analysis Service
Uses HuggingFace transformers for professional-grade narrative generation
Wall Street-style research report generation
"""
from typing import Dict, List, Optional, Any
import json
import os

try:
    from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class QualitativeAnalysisService:
    """
    AI-Powered Qualitative Analysis Service
    Generates professional Wall Street-style narratives using AI
    """

    def __init__(self, use_openai: bool = False, openai_api_key: Optional[str] = None):
        self.use_openai = use_openai and OPENAI_AVAILABLE
        self.openai_api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
        
        # Initialize HuggingFace model if OpenAI not available
        self.hf_model = None
        self.hf_tokenizer = None
        self._load_hf_model()

    def _load_hf_model(self):
        """Load HuggingFace model for text generation"""
        if self.use_openai or not AI_AVAILABLE:
            return
        
        try:
            # Use a lightweight model for text generation
            model_name = "facebook/bart-large-cnn"  # Good for summarization
            print(f"📥 Loading HuggingFace model: {model_name}")
            self.hf_tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.hf_model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
            print("✅ HuggingFace model loaded successfully")
        except Exception as e:
            print(f"⚠️ Failed to load HuggingFace model: {e}")
            self.hf_model = None
            self.hf_tokenizer = None

    def generate_financial_summary(self, financial_data: Dict, health_score: int) -> str:
        """
        Generate AI-powered financial summary
        
        Args:
            financial_data: Dictionary with financial metrics
            health_score: Overall health score (0-100)
            
        Returns:
            Professional narrative summary
        """
        rating = "Excellent" if health_score >= 80 else "Good" if health_score >= 60 else "Average" if health_score >= 40 else "Poor"
        
        revenue_info = financial_data.get('revenue', {})
        profit_info = financial_data.get('profit_margins', {})
        fcf_info = financial_data.get('free_cash_flow', {})
        
        prompt = f"""
        Write a professional Wall Street-style financial summary for a company with the following metrics:
        
        - Financial Health Rating: {rating} ({health_score}/100)
        - Revenue Trend: {revenue_info.get('trend', 'N/A')}
        - Average Revenue Growth: {revenue_info.get('avg_growth_rate', 'N/A')}%
        - Latest Revenue: {revenue_info.get('latest', 'N/A')}
        - Profit Margin Trend: {profit_info.get('trend', 'N/A')}
        - Average Profit Margin: {profit_info.get('avg_margin', 'N/A')}%
        - Free Cash Flow Trend: {fcf_info.get('trend', 'N/A')}
        
        Write 2-3 sentences in professional financial analyst tone.
        """
        
        return self._generate_text(prompt, max_length=150)

    def generate_valuation_narrative(self, valuation_metrics: Dict, current_price: float) -> str:
        """
        Generate AI-powered valuation narrative
        
        Args:
            valuation_metrics: Dictionary with valuation data
            current_price: Current stock price
            
        Returns:
            Professional valuation narrative
        """
        dcf_info = valuation_metrics.get('dcf_valuation', {})
        pe_info = valuation_metrics.get('pe_analysis', {})
        
        prompt = f"""
        Write a professional Wall Street-style valuation analysis:
        
        Current Stock Price: ${current_price}
        DCF Fair Value Estimate: ${dcf_info.get('dcf_value_per_share', 'N/A')}
        DCF Upside/Downside: {dcf_info.get('upside_downside', 'N/A')}%
        DCF Verdict: {dcf_info.get('verdict', 'N/A')}
        Trailing P/E: {pe_info.get('trailing_pe', 'N/A')}
        Forward P/E: {pe_info.get('forward_pe', 'N/A')}
        vs Industry: {pe_info.get('vs_industry', 'N/A')}
        
        Write 2-3 sentences explaining whether the stock is attractively valued.
        """
        
        return self._generate_text(prompt, max_length=150)

    def generate_risk_narrative(self, risks: List[Dict], overall_risk_score: int) -> str:
        """
        Generate AI-powered risk narrative
        
        Args:
            risks: List of risk dictionaries
            overall_risk_score: Overall risk score (0-100)
            
        Returns:
            Professional risk assessment narrative
        """
        risk_level = "High" if overall_risk_score > 70 else "Medium" if overall_risk_score > 40 else "Low"
        top_risks = risks[:3] if len(risks) >= 3 else risks
        
        prompt = f"""
        Write a professional Wall Street-style risk assessment:
        
        Overall Risk Level: {risk_level} ({overall_risk_score}/100)
        Top Risks:
        {chr(10).join([f"- {r.get('risk_type', 'Unknown')}: {r.get('description', 'N/A')}" for r in top_risks])}
        
        Write 2-3 sentences summarizing the key risk factors.
        """
        
        return self._generate_text(prompt, max_length=150)

    def generate_moat_narrative(self, moat_components: Dict, overall_moat: float) -> str:
        """
        Generate AI-powered moat analysis narrative
        
        Args:
            moat_components: Dictionary with moat component scores
            overall_moat: Overall moat rating (1-10)
            
        Returns:
            Professional moat assessment narrative
        """
        moat_label = "Wide" if overall_moat >= 8 else "Narrow" if overall_moat >= 6 else "Moderate" if overall_moat >= 4 else "No"
        
        prompt = f"""
        Write a professional Wall Street-style competitive moat analysis:
        
        Overall Moat Rating: {overall_moat}/10 ({moat_label} Moat)
        Moat Components:
        {chr(10).join([f"- {k.replace('_', ' ').title()}: {v.get('score', 'N/A')}/10 - {v.get('assessment', 'N/A')}" for k, v in moat_components.items()])}
        
        Write 2-3 sentences evaluating the company's competitive advantages.
        """
        
        return self._generate_text(prompt, max_length=150)

    def generate_growth_narrative(self, growth_factors: Dict, growth_estimates: Dict) -> str:
        """
        Generate AI-powered growth potential narrative
        
        Args:
            growth_factors: Dictionary with growth factor data
            growth_estimates: Dictionary with growth estimates
            
        Returns:
            Professional growth assessment narrative
        """
        prompt = f"""
        Write a professional Wall Street-style growth potential analysis:
        
        Estimated 5-Year Growth: {growth_estimates.get('five_year_growth', 'N/A')}%
        Estimated 10-Year Growth: {growth_estimates.get('ten_year_growth', 'N/A')}%
        Confidence Level: {growth_estimates.get('confidence', 'N/A')}
        
        Growth Drivers:
        {chr(10).join([f"- {k.replace('_', ' ').title()}: {v.get('assessment', 'N/A')}" for k, v in growth_factors.items()])}
        
        Write 2-3 sentences on the company's growth prospects.
        """
        
        return self._generate_text(prompt, max_length=150)

    def generate_institutional_thesis(self, perspective: Dict) -> str:
        """
        Generate AI-powered investment thesis from institutional perspective
        
        Args:
            perspective: Dictionary with institutional perspective data
            
        Returns:
            Professional investment thesis
        """
        buy_reasons = perspective.get('buy_reasons', [])
        avoid_reasons = perspective.get('avoid_reasons', [])
        catalysts = perspective.get('catalysts', [])
        
        prompt = f"""
        Write a professional Wall Street-style investment thesis from an institutional investor perspective:
        
        Reasons to Buy:
        {chr(10).join([f"- {reason}" for reason in buy_reasons])}
        
        Reasons to Avoid:
        {chr(10).join([f"- {reason}" for reason in avoid_reasons])}
        
        Key Catalysts:
        {chr(10).join([f"- {catalyst}" for catalyst in catalysts])}
        
        Write a balanced 3-4 sentence investment thesis.
        """
        
        return self._generate_text(prompt, max_length=200)

    def generate_bull_bear_debate(self, bull_args: List[Dict], bear_args: List[Dict]) -> Dict[str, str]:
        """
        Generate AI-powered bull/bear debate narratives
        
        Args:
            bull_args: List of bull case arguments
            bear_args: List of bear case arguments
            
        Returns:
            Dictionary with bull narrative, bear narrative, and conclusion
        """
        bull_prompt = f"""
        Write a compelling bull case narrative for this stock:
        
        Bull Arguments:
        {chr(10).join([f"- {arg.get('point', 'N/A')}: {arg.get('evidence', 'N/A')}" for arg in bull_args])}
        
        Write 2-3 sentences making the bull case.
        """
        
        bear_prompt = f"""
        Write a compelling bear case narrative for this stock:
        
        Bear Arguments:
        {chr(10).join([f"- {arg.get('point', 'N/A')}: {arg.get('evidence', 'N/A')}" for arg in bear_args])}
        
        Write 2-3 sentences making the bear case.
        """
        
        bull_narrative = self._generate_text(bull_prompt, max_length=150)
        bear_narrative = self._generate_text(bear_prompt, max_length=150)
        
        conclusion_prompt = f"""
        Based on these competing arguments, write a balanced conclusion:
        
        Bull Case: {bull_narrative}
        Bear Case: {bear_narrative}
        
        Write 2-3 sentences with a balanced investment conclusion.
        """
        
        conclusion = self._generate_text(conclusion_prompt, max_length=150)
        
        return {
            "bull_narrative": bull_narrative,
            "bear_narrative": bear_narrative,
            "conclusion": conclusion
        }

    def _generate_text(self, prompt: str, max_length: int = 150) -> str:
        """
        Generate text using AI (OpenAI or HuggingFace)
        
        Args:
            prompt: Input prompt
            max_length: Maximum output length
            
        Returns:
            Generated text
        """
        if self.use_openai and self.openai_api_key:
            return self._generate_with_openai(prompt, max_length)
        else:
            return self._generate_with_huggingface(prompt, max_length)

    def _generate_with_openai(self, prompt: str, max_length: int) -> str:
        """Generate text using OpenAI API"""
        try:
            openai.api_key = self.openai_api_key
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a professional Wall Street equity research analyst."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_length,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"⚠️ OpenAI generation failed: {e}")
            return self._generate_fallback(prompt)

    def _generate_with_huggingface(self, prompt: str, max_length: int) -> str:
        """Generate text using HuggingFace model"""
        if not self.hf_model or not self.hf_tokenizer:
            return self._generate_fallback(prompt)
        
        try:
            # Tokenize input
            inputs = self.hf_tokenizer(prompt, return_tensors="pt", max_length=512, truncation=True)
            
            # Generate summary
            summary_ids = self.hf_model.generate(
                inputs['input_ids'],
                max_length=max_length,
                min_length=50,
                length_penalty=1.0,
                num_beams=4,
                early_stopping=True
            )
            
            # Decode output
            summary = self.hf_tokenizer.decode(summary_ids[0], skip_special_tokens=True)
            return summary.strip()
        except Exception as e:
            print(f"⚠️ HuggingFace generation failed: {e}")
            return self._generate_fallback(prompt)

    def _generate_fallback(self, prompt: str) -> str:
        """
        Fallback text generation using rule-based approach
        
        Args:
            prompt: Input prompt
            
        Returns:
            Generated text based on extracted key points
        """
        # Extract key information from prompt and create simple summary
        lines = prompt.strip().split('\n')
        key_points = [line.strip().lstrip('- ') for line in lines if line.strip().startswith('-')]
        
        if not key_points:
            return "Analysis based on available financial data and market metrics."
        
        # Create simple narrative from key points
        if len(key_points) >= 3:
            return f"Based on our analysis: {key_points[0]}. Additionally, {key_points[1]}. Furthermore, {key_points[2]}."
        elif len(key_points) >= 2:
            return f"Analysis indicates: {key_points[0]}. Moreover, {key_points[1]}."
        else:
            return f"Key finding: {key_points[0]}."


# Singleton instance
qualitative_analysis_service = QualitativeAnalysisService()

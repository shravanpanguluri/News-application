from sqlalchemy.orm import Session
from models.models import Article
import pandas as pd
from datetime import datetime, timedelta

class AnalyticsService:
    def get_impact_trends(self, db: Session, days: int = 30):
        # Calculate start date
        start_date = datetime.now() - timedelta(days=days)
        
        # Query articles within the time range
        articles = db.query(Article).filter(Article.published_at >= start_date).all()
        
        if not articles:
            return []
            
        # Convert to DataFrame for easy manipulation
        data = []
        for a in articles:
            data.append({
                "id": a.id,
                "date": a.published_at.date(),
                "country": a.country or "Global",
                "category": a.category or "General",
                "impact_score": a.impact_score or 0,
                "sentiment": a.sentiment or "Neutral"
            })
            
        df = pd.DataFrame(data)
        
        # Group by date and country
        trends = df.groupby(["date", "country"]).agg({
            "id": "count",
            "impact_score": "mean"
        }).reset_index()
        
        # Rename columns for clarity
        trends.columns = ["date", "country", "article_count", "avg_impact"]
        
        # Sort by date
        trends = trends.sort_values("date")
        
        # Convert date to string for JSON serialization
        trends["date"] = trends["date"].astype(str)
        
        # Pivot the data so each country is a column for the chart
        pivot_count = trends.pivot(index="date", columns="country", values="article_count").fillna(0).reset_index()
        pivot_impact = trends.pivot(index="date", columns="country", values="avg_impact").fillna(0).reset_index()
        
        return {
            "time_series": trends.to_dict(orient="records"),
            "chart_data": pivot_count.to_dict(orient="records"),
            "impact_chart_data": pivot_impact.to_dict(orient="records"),
            "summary": {
                "total_articles": len(articles),
                "avg_impact": float(df["impact_score"].mean()),
                "countries": df["country"].unique().tolist()
            }
        }

analytics_service = AnalyticsService()

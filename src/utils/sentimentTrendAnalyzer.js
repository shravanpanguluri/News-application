/**
 * Sentiment Trend Analyzer - Track sentiment changes over time
 * Uses embeddings to find relevant articles and analyze sentiment trends
 */

import { narrativeDNA } from './narrativeDNA';

class SentimentTrendAnalyzer {
    constructor() {
        this.initialized = false;
    }

    async initialize() {
        if (this.initialized) return true;
        await narrativeDNA.initialize();
        this.initialized = true;
        return true;
    }

    /**
     * Analyze sentiment trend for a topic
     */
    async analyzeTrend(articles, topic, days = 7) {
        await this.initialize();

        // Get topic embedding
        const topicEmbedding = await narrativeDNA.getEmbedding(topic);

        // Filter relevant articles
        const relevantArticles = [];

        for (const article of articles) {
            const text = `${article.title}. ${article.description || ''}`;
            const articleEmbedding = await narrativeDNA.getEmbedding(text);

            const similarity = narrativeDNA.cosineSimilarity(
                topicEmbedding,
                articleEmbedding
            );

            // Only include if sufficiently relevant
            if (similarity > 0.5) {
                relevantArticles.push({
                    ...article,
                    relevanceScore: similarity
                });
            }
        }

        // Group by date
        const byDate = {};
        const now = Date.now();
        const dayMs = 24 * 60 * 60 * 1000;

        relevantArticles.forEach(article => {
            const date = new Date(article.published_at || article.createdAt);
            const daysAgo = Math.floor((now - date.getTime()) / dayMs);

            // Only include articles from last N days
            if (daysAgo <= days) {
                const dateStr = date.toISOString().split('T')[0];

                if (!byDate[dateStr]) {
                    byDate[dateStr] = {
                        date: dateStr,
                        sentiments: [],
                        articles: []
                    };
                }

                // Convert sentiment to numeric
                let sentimentValue = 0;
                if (article.sentiment === 'Positive') sentimentValue = 1;
                else if (article.sentiment === 'Negative') sentimentValue = -1;

                byDate[dateStr].sentiments.push({
                    value: sentimentValue,
                    sentiment: article.sentiment,
                    relevance: article.relevanceScore
                });
                byDate[dateStr].articles.push(article);
            }
        });

        // Calculate daily averages
        const trend = Object.values(byDate)
            .map(day => {
                const avgSentiment = day.sentiments.reduce((sum, s) => sum + s.value, 0) / day.sentiments.length;
                const weightedAvg = day.sentiments.reduce((sum, s) => sum + (s.value * s.relevance), 0) / 
                                   day.sentiments.reduce((sum, s) => sum + s.relevance, 0);

                return {
                    date: day.date,
                    avgSentiment: Math.round(avgSentiment * 100) / 100,
                    weightedSentiment: Math.round(weightedAvg * 100) / 100,
                    articleCount: day.articles.length,
                    label: this.getSentimentLabel(avgSentiment),
                    trend: this.getTrendLabel(day.sentiments)
                };
            })
            .sort((a, b) => new Date(a.date) - new Date(b.date));

        // Calculate overall trend direction
        const trendDirection = this.calculateTrendDirection(trend);

        return {
            topic,
            days,
            trend,
            totalArticles: relevantArticles.length,
            trendDirection,
            summary: this.generateSummary(trend, topic)
        };
    }

    /**
     * Get sentiment label
     */
    getSentimentLabel(score) {
        if (score > 0.3) return { label: 'Positive', emoji: '😊', color: 'green' };
        if (score < -0.3) return { label: 'Negative', emoji: '😟', color: 'red' };
        return { label: 'Neutral', emoji: '😐', color: 'gray' };
    }

    /**
     * Get trend label for the day
     */
    getTrendLabel(sentiments) {
        const positive = sentiments.filter(s => s.value > 0).length;
        const negative = sentiments.filter(s => s.value < 0).length;

        if (positive > negative * 2) return 'Mostly Positive';
        if (negative > positive * 2) return 'Mostly Negative';
        return 'Mixed';
    }

    /**
     * Calculate overall trend direction
     */
    calculateTrendDirection(trend) {
        if (trend.length < 2) return 'stable';

        const recent = trend.slice(-3);
        const older = trend.slice(0, 3);

        const recentAvg = recent.reduce((sum, d) => sum + d.weightedSentiment, 0) / recent.length;
        const olderAvg = older.reduce((sum, d) => sum + d.weightedSentiment, 0) / older.length;

        const change = recentAvg - olderAvg;

        if (change > 0.2) return { direction: 'improving', change: Math.round(change * 100) };
        if (change < -0.2) return { direction: 'worsening', change: Math.round(change * 100) };
        return { direction: 'stable', change: Math.round(change * 100) };
    }

    /**
     * Generate summary text
     */
    generateSummary(trend, topic) {
        if (trend.length === 0) return `No data available for "${topic}"`;

        const latest = trend[trend.length - 1];
        const trendDirection = this.calculateTrendDirection(trend);

        let summary = `Over the past ${trend.length} days, `;
        summary += `${latest.articleCount} articles about "${topic}" `;
        summary += `have been ${latest.label.toLowerCase()}`;

        if (trendDirection.direction === 'improving') {
            summary += `, with sentiment improving by ${Math.abs(trendDirection.change)}%.`;
        } else if (trendDirection.direction === 'worsening') {
            summary += `, with sentiment worsening by ${Math.abs(trendDirection.change)}%.`;
        } else {
            summary += ', with relatively stable sentiment.';
        }

        return summary;
    }

    /**
     * Compare sentiment between two topics
     */
    async compareTopics(articles, topic1, topic2) {
        const trend1 = await this.analyzeTrend(articles, topic1, 7);
        const trend2 = await this.analyzeTrend(articles, topic2, 7);

        return {
            topic1: {
                name: topic1,
                avgSentiment: trend1.trend.reduce((sum, d) => sum + d.weightedSentiment, 0) / trend1.trend.length,
                articleCount: trend1.totalArticles,
                trend: trend1.trendDirection.direction
            },
            topic2: {
                name: topic2,
                avgSentiment: trend2.trend.reduce((sum, d) => sum + d.weightedSentiment, 0) / trend2.trend.length,
                articleCount: trend2.totalArticles,
                trend: trend2.trendDirection.direction
            },
            comparison: {
                morePositive: trend1.totalArticles > 0 && trend2.totalArticles > 0 ?
                    (trend1.trend.reduce((sum, d) => sum + d.weightedSentiment, 0) / trend1.trend.length) >
                    (trend2.trend.reduce((sum, d) => sum + d.weightedSentiment, 0) / trend2.trend.length) ?
                    topic1 : topic2 : 'N/A',
                moreArticles: trend1.totalArticles > trend2.totalArticles ? topic1 : topic2
            }
        };
    }
}

export const sentimentTrendAnalyzer = new SentimentTrendAnalyzer();

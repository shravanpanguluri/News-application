/**
 * User Preference Learner - Personalized news recommendations
 * Learns from reading behavior to recommend relevant articles
 */

import { narrativeDNA } from './narrativeDNA';

class UserPreferenceLearner {
    constructor() {
        this.userEmbeddings = [];
        this.userCategories = {};
        this.userSources = {};
        this.userTopics = {};
        this.maxHistory = 100;  // Keep last 100 articles
        this.initialized = false;
        
        // Load from localStorage
        this.loadFromStorage();
    }

    async initialize() {
        if (this.initialized) return true;
        await narrativeDNA.initialize();
        this.initialized = true;
        return true;
    }

    /**
     * Record that user read an article
     */
    async articleRead(article, readDuration = 30) {
        await this.initialize();

        const text = `${article.title}. ${article.description || ''}`;
        const embedding = await narrativeDNA.getEmbedding(text);

        // Store embedding with metadata
        this.userEmbeddings.push({
            embedding,
            category: article.category || 'general',
            source: article.source || 'Unknown',
            timestamp: Date.now(),
            readDuration,  // seconds
            impact: article.impact_level || 'Low'
        });

        // Update category preferences
        this.userCategories[article.category || 'general'] = 
            (this.userCategories[article.category || 'general'] || 0) + 1;

        // Update source preferences
        this.userSources[article.source || 'Unknown'] = 
            (this.userSources[article.source || 'Unknown'] || 0) + 1;

        // Extract and store topics from title
        const topics = this.extractTopics(article.title);
        topics.forEach(topic => {
            this.userTopics[topic] = (this.userTopics[topic] || 0) + 1;
        });

        // Limit history size
        if (this.userEmbeddings.length > this.maxHistory) {
            this.userEmbeddings.shift();
        }

        // Save to localStorage
        this.saveToStorage();
    }

    /**
     * Get personalized recommendations
     */
    async getRecommendations(allArticles, limit = 10) {
        await this.initialize();

        if (this.userEmbeddings.length === 0) {
            // No history, return trending/high impact
            return allArticles
                .filter(a => a.impact_level === 'High')
                .slice(0, limit);
        }

        // Calculate average user preference embedding
        const avgEmbedding = this.calculateAverageEmbedding();

        // Get top categories
        const topCategories = this.getTopCategories(3);

        // Score all articles
        const scored = await Promise.all(allArticles.map(async article => {
            const text = `${article.title}. ${article.description || ''}`;
            const articleEmbedding = await narrativeDNA.getEmbedding(text);

            // Similarity to user preferences
            const similarity = narrativeDNA.cosineSimilarity(
                avgEmbedding,
                articleEmbedding
            );

            // Category preference boost
            const categoryBoost = this.userCategories[article.category] || 0;

            // Source preference boost
            const sourceBoost = this.userSources[article.source] || 0;

            // Recency boost (newer articles)
            const recencyBoost = this.calculateRecencyBoost(article.published_at);

            // Impact boost
            const impactBoost = article.impact_level === 'High' ? 0.1 : 0;

            // Calculate final score
            const recommendationScore = 
                similarity + 
                (categoryBoost * 0.15) + 
                (sourceBoost * 0.05) + 
                recencyBoost + 
                impactBoost;

            return {
                ...article,
                recommendationScore,
                matchPercent: Math.round(similarity * 100),
                reason: this.generateReason(article, topCategories)
            };
        }));

        // Sort by recommendation score and return top N
        return scored
            .sort((a, b) => b.recommendationScore - a.recommendationScore)
            .filter(a => a.recommendationScore > 0.3)  // Minimum threshold
            .slice(0, limit);
    }

    /**
     * Calculate average embedding from user history
     */
    calculateAverageEmbedding() {
        if (this.userEmbeddings.length === 0) return new Array(512).fill(0);

        const sum = new Array(512).fill(0);
        this.userEmbeddings.forEach(item => {
            item.embedding.forEach((val, i) => {
                sum[i] += val;
            });
        });

        return sum.map(val => val / this.userEmbeddings.length);
    }

    /**
     * Get user's top categories
     */
    getTopCategories(limit = 5) {
        return Object.entries(this.userCategories)
            .sort((a, b) => b[1] - a[1])
            .slice(0, limit)
            .map(([cat, count]) => ({ category: cat, count }));
    }

    /**
     * Calculate recency boost (newer = higher boost)
     */
    calculateRecencyBoost(publishedAt) {
        if (!publishedAt) return 0;

        const age = Date.now() - new Date(publishedAt).getTime();
        const hoursOld = age / (1000 * 60 * 60);

        if (hoursOld < 1) return 0.2;      // < 1 hour
        if (hoursOld < 6) return 0.15;     // < 6 hours
        if (hoursOld < 24) return 0.1;     // < 1 day
        if (hoursOld < 72) return 0.05;    // < 3 days
        return 0;
    }

    /**
     * Extract topics from title
     */
    extractTopics(title) {
        // Simple keyword extraction
        const stopWords = ['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'];
        const words = title.toLowerCase().split(' ')
            .filter(w => w.length > 4 && !stopWords.includes(w))
            .map(w => w.replace(/[^a-z0-9]/gi, ''));

        return [...new Set(words)].slice(0, 5);
    }

    /**
     * Generate recommendation reason
     */
    generateReason(article, topCategories) {
        const reasons = [];

        if (this.userCategories[article.category] > 2) {
            reasons.push(`You read ${article.category} news often`);
        }

        if (this.userSources[article.source] > 1) {
            reasons.push(`From ${article.source}`);
        }

        if (article.impact_level === 'High') {
            reasons.push('High impact story');
        }

        return reasons.join(' • ') || 'Recommended for you';
    }

    /**
     * Save preferences to localStorage
     */
    saveToStorage() {
        try {
            localStorage.setItem('predovex_preferences', JSON.stringify({
                categories: this.userCategories,
                sources: this.userSources,
                topics: this.userTopics,
                embeddingCount: this.userEmbeddings.length,
                lastUpdated: Date.now()
            }));
        } catch (e) {
            console.error('Failed to save preferences:', e);
        }
    }

    /**
     * Load preferences from localStorage
     */
    loadFromStorage() {
        try {
            const saved = localStorage.getItem('predovex_preferences');
            if (saved) {
                const data = JSON.parse(saved);
                this.userCategories = data.categories || {};
                this.userSources = data.sources || {};
                this.userTopics = data.topics || {};
            }
        } catch (e) {
            console.error('Failed to load preferences:', e);
        }
    }

    /**
     * Clear user history
     */
    clearHistory() {
        this.userEmbeddings = [];
        this.userCategories = {};
        this.userSources = {};
        this.userTopics = {};
        localStorage.removeItem('predovex_preferences');
    }

    /**
     * Get user profile summary
     */
    getUserProfile() {
        const topCategories = this.getTopCategories(3);
        const topSources = Object.entries(this.userSources)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 3)
            .map(([source, count]) => ({ source, count }));

        return {
            articlesRead: this.userEmbeddings.length,
            topCategories,
            topSources,
            favoriteTopic: Object.entries(this.userTopics)
                .sort((a, b) => b[1] - a[1])[0]?.[0] || 'N/A',
            lastUpdated: new Date(Math.max(...this.userEmbeddings.map(e => e.timestamp))).toLocaleDateString()
        };
    }
}

export const userPreferenceLearner = new UserPreferenceLearner();

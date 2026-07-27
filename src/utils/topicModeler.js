/**
 * Topic Modeler - Auto-categorize articles using embeddings
 * Pre-compute category embeddings and match articles to them
 */

import { narrativeDNA } from './narrativeDNA';

class TopicModeler {
    constructor() {
        this.categoryEmbeddings = {};
        this.initialized = false;
        
        // Category definitions with representative keywords
        this.categoryDefinitions = {
            politics: 'government policy election parliament congress legislation voting politics politician law bill senate representative',
            economy: 'market stocks economy inflation GDP trade finance business investment money banking currency',
            technology: 'technology AI artificial intelligence software hardware tech startup innovation digital computer internet',
            health: 'health medical doctor hospital disease treatment medicine healthcare patient wellness fitness',
            sports: 'sports team player game match score championship league tournament athlete coach',
            entertainment: 'entertainment movie music celebrity actor singer film TV show award concert',
            science: 'science research discovery space NASA physics chemistry biology environment climate',
            world: 'international world global country nation foreign diplomacy war conflict peace treaty',
            business: 'business company corporate CEO earnings profit revenue merger acquisition industry',
            crypto: 'cryptocurrency bitcoin blockchain crypto ethereum digital currency trading NFT DeFi'
        };
    }

    /**
     * Initialize category embeddings
     */
    async initialize() {
        if (this.initialized) return true;

        await narrativeDNA.initialize();

        // Pre-compute embeddings for all categories
        for (const [category, definition] of Object.entries(this.categoryDefinitions)) {
            this.categoryEmbeddings[category] = await narrativeDNA.getEmbedding(definition);
        }

        this.initialized = true;
        return true;
    }

    /**
     * Categorize a single article
     */
    async categorizeArticle(article) {
        await this.initialize();

        const text = `${article.title}. ${article.description || ''}`;
        const articleEmbedding = await narrativeDNA.getEmbedding(text);

        let bestCategory = 'general';
        let bestScore = 0;
        const allScores = {};

        // Compare with each category
        for (const [category, embedding] of Object.entries(this.categoryEmbeddings)) {
            const similarity = narrativeDNA.cosineSimilarity(
                articleEmbedding,
                embedding
            );

            allScores[category] = similarity;

            if (similarity > bestScore) {
                bestScore = similarity;
                bestCategory = category;
            }
        }

        return {
            category: bestCategory,
            confidence: Math.round(bestScore * 100),
            allScores: Object.entries(allScores)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 3)
                .map(([cat, score]) => ({
                    category: cat,
                    score: Math.round(score * 100)
                })),
            isConfident: bestScore > 0.6
        };
    }

    /**
     * Batch categorize multiple articles
     */
    async categorizeBatch(articles) {
        const results = [];

        for (const article of articles) {
            const categorization = await this.categorizeArticle(article);
            results.push({
                ...article,
                predictedCategory: categorization.category,
                categoryConfidence: categorization.confidence,
                categoryScores: categorization.allScores,
                isConfident: categorization.isConfident
            });
        }

        return results;
    }

    /**
     * Get category distribution
     */
    getCategoryDistribution(articles) {
        const distribution = {};

        articles.forEach(article => {
            const cat = article.predictedCategory || article.category || 'general';
            distribution[cat] = (distribution[cat] || 0) + 1;
        });

        return Object.entries(distribution)
            .sort((a, b) => b[1] - a[1])
            .map(([category, count]) => ({
                category,
                count,
                percentage: Math.round((count / articles.length) * 100)
            }));
    }

    /**
     * Find articles by category
     */
    filterByCategory(articles, category, minConfidence = 50) {
        return articles.filter(article => {
            if (article.predictedCategory === category && 
                article.categoryConfidence >= minConfidence) {
                return true;
            }
            // Fallback to existing category field
            if (article.category === category && !article.predictedCategory) {
                return true;
            }
            return false;
        });
    }
}

export const topicModeler = new TopicModeler();

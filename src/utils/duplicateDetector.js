/**
 * Duplicate Article Detector - Find and merge duplicate stories
 * Uses TensorFlow.js embeddings to detect same story from different sources
 */

import { narrativeDNA } from './narrativeDNA';

class DuplicateDetector {
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
     * Detect and merge duplicate articles
     * @param {Array} articles - Array of article objects
     * @param {number} threshold - Similarity threshold (0.92 = 92% similar)
     * @returns {Array} Deduplicated articles with source lists
     */
    async detectDuplicates(articles, threshold = 0.92) {
        await this.initialize();

        const duplicates = new Map();  // article -> embedding
        const uniqueArticles = [];

        for (const article of articles) {
            const text = `${article.title}. ${article.description || ''}`;
            const embedding = await narrativeDNA.getEmbedding(text);

            let isDuplicate = false;

            for (const [uniqueArticle, uniqueEmbedding] of duplicates) {
                const similarity = narrativeDNA.cosineSimilarity(
                    embedding,
                    uniqueEmbedding
                );

                if (similarity > threshold) {
                    // Found duplicate!
                    if (!uniqueArticle.sources) {
                        uniqueArticle.sources = [uniqueArticle.source];
                    }
                    uniqueArticle.sources.push(article.source);
                    uniqueArticle.sourceCount = uniqueArticle.sources.length;
                    
                    // Merge metadata
                    if (article.impact_level === 'High' && uniqueArticle.impact_level !== 'High') {
                        uniqueArticle.impact_level = 'High';
                    }
                    if (article.urlToImage && !uniqueArticle.urlToImage) {
                        uniqueArticle.urlToImage = article.urlToImage;
                    }

                    isDuplicate = true;
                    break;
                }
            }

            if (!isDuplicate) {
                article.sources = [article.source];
                article.sourceCount = 1;
                uniqueArticles.push(article);
                duplicates.set(article, embedding);
            }
        }

        return uniqueArticles;
    }

    /**
     * Get duplicate statistics
     */
    getDuplicateStats(originalCount, uniqueCount) {
        const duplicatesRemoved = originalCount - uniqueCount;
        const reductionPercent = ((duplicatesRemoved / originalCount) * 100).toFixed(1);

        return {
            originalCount,
            uniqueCount,
            duplicatesRemoved,
            reductionPercent: reductionPercent + '%',
            efficiency: ((uniqueCount / originalCount) * 100).toFixed(1) + '% unique'
        };
    }
}

export const duplicateDetector = new DuplicateDetector();

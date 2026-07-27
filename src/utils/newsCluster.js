/**
 * News Clustering - Group similar articles using TensorFlow.js embeddings
 * Reduces clutter by showing "X related articles" instead of duplicates
 */

import { narrativeDNA } from './narrativeDNA';

class NewsClusterer {
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
     * Cluster articles by similarity
     * @param {Array} articles - Array of article objects
     * @param {number} threshold - Similarity threshold (0.85 = 85% similar)
     * @returns {Array} Clustered articles
     */
    async clusterArticles(articles, threshold = 0.85) {
        await this.initialize();

        const clusters = [];
        const processedArticles = [];

        for (const article of articles) {
            const text = `${article.title}. ${article.description || ''}`;
            const embedding = await narrativeDNA.getEmbedding(text);

            let foundCluster = false;

            for (const cluster of clusters) {
                const similarity = narrativeDNA.cosineSimilarity(
                    embedding,
                    cluster.centroid
                );

                if (similarity > threshold) {
                    // Add to existing cluster
                    cluster.articles.push(article);
                    cluster.count++;
                    
                    // Update centroid (average embedding)
                    cluster.centroid = this.updateCentroid(
                        cluster.centroid,
                        embedding,
                        cluster.count
                    );

                    // Keep best title (usually first article)
                    if (article.impact_level === 'High' && cluster.articles[0].impact_level !== 'High') {
                        cluster.articles.swap(0, cluster.articles.length - 1);
                    }

                    foundCluster = true;
                    break;
                }
            }

            if (!foundCluster) {
                // Create new cluster
                clusters.push({
                    centroid: embedding,
                    articles: [article],
                    count: 1,
                    topic: this.extractTopic(article.title),
                    isCluster: true
                });
            }

            processedArticles.push(article);
        }

        // Return clustered articles
        return clusters.map(cluster => ({
            ...cluster.articles[0],  // Use first article as main
            relatedArticles: cluster.articles.slice(1),
            relatedCount: cluster.count - 1,
            isCluster: cluster.count > 1,
            clusterTopic: cluster.topic
        }));
    }

    /**
     * Update cluster centroid with new embedding
     */
    updateCentroid(oldCentroid, newEmbedding, count) {
        return oldCentroid.map((val, i) => {
            return (val * (count - 1) + newEmbedding[i]) / count;
        });
    }

    /**
     * Extract topic from title (first 5-7 words)
     */
    extractTopic(title) {
        const words = title.split(' ');
        return words.slice(0, Math.min(7, words.length)).join(' ') + '...';
    }

    /**
     * Get cluster statistics
     */
    getClusterStats(clusters) {
        const totalArticles = clusters.reduce((sum, c) => sum + c.count, 0);
        const totalClusters = clusters.length;
        const avgClusterSize = totalArticles / totalClusters;
        const maxCluster = Math.max(...clusters.map(c => c.count));

        return {
            totalArticles,
            totalClusters,
            avgClusterSize: avgClusterSize.toFixed(1),
            maxCluster,
            reduction: ((1 - (totalClusters / totalArticles)) * 100).toFixed(1) + '%'
        };
    }
}

export const newsClusterer = new NewsClusterer();

/**
 * Predovex AI Utilities - Master Index
 * All TensorFlow.js powered features
 */

// Core NLP
export { narrativeDNA } from './narrativeDNA';

// Article Enhancement
export { newsClusterer } from './newsCluster';
export { duplicateDetector } from './duplicateDetector';
export { readingLevelAnalyzer } from './readingLevelAnalyzer';
export { clickbaitDetector } from './clickbaitDetector';

// Personalization
export { userPreferenceLearner } from './userPreferenceLearner';

// Analysis
export { topicModeler } from './topicModeler';
export { sentimentTrendAnalyzer } from './sentimentTrendAnalyzer';
export { fakeNewsDetector } from './fakeNewsDetector';

// Convenience function to initialize all AI features
export async function initializeAllAIFeatures() {
    const results = {};
    
    try {
        const { narrativeDNA } = await import('./narrativeDNA');
        const { newsClusterer } = await import('./newsCluster');
        const { duplicateDetector } = await import('./duplicateDetector');
        const { userPreferenceLearner } = await import('./userPreferenceLearner');
        const { topicModeler } = await import('./topicModeler');
        const { sentimentTrendAnalyzer } = await import('./sentimentTrendAnalyzer');
        const { fakeNewsDetector } = await import('./fakeNewsDetector');
        
        results.narrativeDNA = await narrativeDNA.initialize();
        results.newsClusterer = await newsClusterer.initialize();
        results.duplicateDetector = await duplicateDetector.initialize();
        results.userPreferenceLearner = await userPreferenceLearner.initialize();
        results.topicModeler = await topicModeler.initialize();
        results.sentimentTrendAnalyzer = await sentimentTrendAnalyzer.initialize();
        results.fakeNewsDetector = await fakeNewsDetector.initialize();
        
        console.log('✅ All AI features initialized:', results);
        return results;
    } catch (error) {
        console.error('❌ AI initialization failed:', error);
        return results;
    }
}

// Get AI features status
export function getAIFeaturesStatus() {
    try {
        const { narrativeDNA } = require('./narrativeDNA');
        const { newsClusterer } = require('./newsCluster');
        const { duplicateDetector } = require('./duplicateDetector');
        const { userPreferenceLearner } = require('./userPreferenceLearner');
        const { topicModeler } = require('./topicModeler');
        const { sentimentTrendAnalyzer } = require('./sentimentTrendAnalyzer');
        const { fakeNewsDetector } = require('./fakeNewsDetector');
        
        return {
            narrativeDNA: narrativeDNA.initialized,
            newsClusterer: newsClusterer.initialized,
            duplicateDetector: duplicateDetector.initialized,
            userPreferenceLearner: userPreferenceLearner.initialized,
            topicModeler: topicModeler.initialized,
            sentimentTrendAnalyzer: sentimentTrendAnalyzer.initialized,
            fakeNewsDetector: fakeNewsDetector.initialized
        };
    } catch (e) {
        console.error('Error getting AI status:', e);
        return {};
    }
}

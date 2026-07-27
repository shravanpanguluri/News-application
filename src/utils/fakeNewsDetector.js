/**
 * Fake News Detector - Identify potentially unreliable articles
 * Uses multiple signals to assess credibility
 */

import { narrativeDNA } from './narrativeDNA';

class FakeNewsDetector {
    constructor() {
        this.initialized = false;
        
        // Trusted sources (manually curated)
        this.trustedSources = [
            'bbc', 'reuters', 'associated press', 'ap news', 'npr',
            'the new york times', 'washington post', 'wall street journal',
            'the guardian', 'al jazeera', 'dw news', 'france 24',
            'bloomberg', 'financial times', 'economist'
        ];

        // Suspicious patterns
        this.suspiciousPatterns = [
            /\.co$/,      // .co domains (often fake)
            /\.lo$/,      // .lo domains
            /\.com\.co$/, // Fake .co.co domains
            /wordpress\.com$/,
            /blogspot\.com$/,
            /naturalnews/i,
            /infowars/i,
            /beforeitsnews/i
        ];
    }

    async initialize() {
        if (this.initialized) return true;
        await narrativeDNA.initialize();
        this.initialized = true;
        return true;
    }

    /**
     * Detect potential fake news
     */
    async detect(article) {
        await this.initialize();

        const redFlags = [];
        const greenFlags = [];
        let credibilityScore = 50;  // Start neutral

        // 1. Check source credibility
        const sourceCheck = this.checkSource(article.source, article.url);
        credibilityScore += sourceCheck.score;
        if (sourceCheck.isTrusted) {
            greenFlags.push('Trusted source');
        } else if (sourceCheck.isSuspicious) {
            redFlags.push('Suspicious source');
        }

        // 2. Check title quality
        const titleCheck = this.checkTitle(article.title);
        credibilityScore += titleCheck.score;
        redFlags.push(...titleCheck.redFlags);
        greenFlags.push(...titleCheck.greenFlags);

        // 3. Check content quality
        const contentCheck = this.checkContent(article.description);
        credibilityScore += contentCheck.score;
        redFlags.push(...contentCheck.redFlags);
        greenFlags.push(...contentCheck.greenFlags);

        // 4. Check date freshness
        const dateCheck = this.checkDate(article.published_at);
        credibilityScore += dateCheck.score;
        if (dateCheck.isFresh) greenFlags.push('Recent article');
        else redFlags.push('Old article');

        // 5. Check for author attribution
        if (article.author) {
            greenFlags.push('Author identified');
            credibilityScore += 5;
        } else {
            redFlags.push('No author listed');
            credibilityScore -= 5;
        }

        // 6. Check for images
        if (article.urlToImage) {
            greenFlags.push('Has image');
            credibilityScore += 3;
        }

        // Normalize score to 0-100
        credibilityScore = Math.max(0, Math.min(100, credibilityScore));

        // Determine classification
        let classification, label, color;
        if (credibilityScore >= 70) {
            classification = 'credible';
            label = 'High Credibility';
            color = 'green';
        } else if (credibilityScore >= 50) {
            classification = 'mixed';
            label = 'Mixed Credibility';
            color = 'yellow';
        } else if (credibilityScore >= 30) {
            classification = 'questionable';
            label = 'Low Credibility';
            color = 'orange';
        } else {
            classification = 'fake';
            label = 'Very Low Credibility';
            color = 'red';
        }

        return {
            credibilityScore,
            classification,
            label,
            color,
            redFlags,
            greenFlags,
            isTrusted: credibilityScore >= 70,
            isSuspicious: credibilityScore < 50,
            recommendation: this.getRecommendation(classification)
        };
    }

    /**
     * Check source credibility
     */
    checkSource(source, url) {
        const sourceLower = (source || '').toLowerCase();
        const urlLower = (url || '').toLowerCase();

        // Check trusted sources
        if (this.trustedSources.some(ts => sourceLower.includes(ts) || urlLower.includes(ts))) {
            return { score: 30, isTrusted: true, isSuspicious: false };
        }

        // Check suspicious patterns
        if (this.suspiciousPatterns.some(pattern => pattern.test(urlLower))) {
            return { score: -30, isTrusted: false, isSuspicious: true };
        }

        // Unknown source
        if (!source || source === 'Unknown' || source === 'RSS Feed') {
            return { score: -10, isTrusted: false, isSuspicious: false };
        }

        return { score: 0, isTrusted: false, isSuspicious: false };
    }

    /**
     * Check title quality
     */
    checkTitle(title) {
        const redFlags = [];
        const greenFlags = [];
        let score = 0;

        // Check for excessive punctuation
        if (title.includes('!!!') || title.includes('???')) {
            redFlags.push('Excessive punctuation in title');
            score -= 10;
        }

        // Check for ALL CAPS
        if (title === title.toUpperCase() && title.length > 10) {
            redFlags.push('ALL CAPS title');
            score -= 15;
        }

        // Check for clickbait patterns
        const clickbaitPatterns = [
            /you won't believe/i,
            /shocking/i,
            /amazing/i,
            /doctors hate/i,
            /one weird trick/i
        ];

        if (clickbaitPatterns.some(p => p.test(title))) {
            redFlags.push('Clickbait language');
            score -= 15;
        }

        // Check for reasonable length
        if (title.length < 20) {
            redFlags.push('Very short title');
            score -= 5;
        } else if (title.length > 150) {
            redFlags.push('Very long title');
            score -= 5;
        } else {
            greenFlags.push('Reasonable title length');
            score += 5;
        }

        return { score, redFlags, greenFlags };
    }

    /**
     * Check content quality
     */
    checkContent(description) {
        const redFlags = [];
        const greenFlags = [];
        let score = 0;

        if (!description || description.length < 50) {
            redFlags.push('Very short or missing description');
            score -= 15;
        } else if (description.length > 500) {
            greenFlags.push('Detailed description');
            score += 5;
        }

        // Check for grammar issues (simplified)
        if (description && description.match(/\b(the|a|is|are)\s{2,}/)) {
            redFlags.push('Possible grammar issues');
            score -= 5;
        }

        return { score, redFlags, greenFlags };
    }

    /**
     * Check date freshness
     */
    checkDate(publishedAt) {
        if (!publishedAt) return { score: -5, isFresh: false };

        const age = Date.now() - new Date(publishedAt).getTime();
        const daysOld = age / (1000 * 60 * 60 * 24);

        if (daysOld < 1) return { score: 10, isFresh: true };
        if (daysOld < 7) return { score: 5, isFresh: true };
        if (daysOld < 30) return { score: 0, isFresh: false };
        return { score: -10, isFresh: false };
    }

    /**
     * Get recommendation based on classification
     */
    getRecommendation(classification) {
        switch (classification) {
            case 'credible':
                return '✅ This article appears reliable';
            case 'mixed':
                return '⚠️ Verify with additional sources';
            case 'questionable':
                return '⚠️ Approach with caution, verify claims';
            case 'fake':
                return '❌ High risk of misinformation';
            default:
                return 'Unable to assess credibility';
        }
    }

    /**
     * Batch detect for multiple articles
     */
    async detectBatch(articles) {
        const results = [];

        for (const article of articles) {
            const analysis = await this.detect(article);
            results.push({
                ...article,
                credibilityAnalysis: analysis
            });
        }

        return results;
    }

    /**
     * Filter by credibility
     */
    async filterByCredibility(articles, minScore = 50) {
        const analyzed = await this.detectBatch(articles);
        return analyzed.filter(a => a.credibilityAnalysis.credibilityScore >= minScore);
    }
}

export const fakeNewsDetector = new FakeNewsDetector();

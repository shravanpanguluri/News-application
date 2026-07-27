/**
 * Clickbait Detector - Identify sensational headlines
 * Warns users about clickbait and suggests better titles
 */

import { narrativeDNA } from './narrativeDNA';

class ClickbaitDetector {
    constructor() {
        this.clickbaitPatterns = [
            /you won't believe/i,
            /shocking/i,
            /amazing/i,
            /incredible/i,
            /unbelievable/i,
            /doctors hate/i,
            /one weird trick/i,
            /this will change/i,
            /number \d+ will/i,
            /they don't want you to know/i,
            /secret/i,
            /exposed/i,
            /revealed/i,
            /\!{2,}/,  // Multiple exclamation marks
            /[A-Z]{5,}/,  // ALL CAPS words (5+ letters)
            /\?\?\?/,  // Multiple question marks
            /click here/i,
            /see more/i
        ];

        this.betterAlternatives = {
            'you won\'t believe': 'Surprisingly',
            'shocking': 'Significant',
            'amazing': 'Notable',
            'incredible': 'Remarkable',
            'unbelievable': 'Unexpected',
            'secret': 'Internal',
            'exposed': 'Revealed',
            'revealed': 'Reported'
        };
    }

    /**
     * Detect clickbait in headline
     */
    async detect(headline) {
        // Count patterns
        let patternCount = 0;
        const matchedPatterns = [];

        this.clickbaitPatterns.forEach(pattern => {
            if (pattern.test(headline)) {
                patternCount++;
                matchedPatterns.push(pattern.toString());
            }
        });

        // Calculate clickbait score
        const clickbaitScore = Math.min(patternCount / 5, 1.0);  // Cap at 1.0

        // Get embedding-based analysis
        const isEmotional = await this.analyzeEmotionalLanguage(headline);

        // Determine if clickbait
        const isClickbait = clickbaitScore > 0.3 || isEmotional.score > 0.7;

        return {
            isClickbait,
            score: Math.round(clickbaitScore * 100),
            confidence: Math.round((1 - clickbaitScore) * 100),
            patterns: matchedPatterns,
            patternCount,
            isEmotional: isEmotional.score > 0.5,
            emotionalScore: isEmotional.score,
            betterTitle: this.suggestBetterTitle(headline),
            redFlags: this.getRedFlags(headline, matchedPatterns)
        };
    }

    /**
     * Analyze emotional language using embeddings
     */
    async analyzeEmotionalLanguage(headline) {
        const emotionalEmbedding = await narrativeDNA.getEmbedding(
            'shocking amazing incredible unbelievable wow omg must see'
        );

        const headlineEmbedding = await narrativeDNA.getEmbedding(headline);

        const similarity = narrativeDNA.cosineSimilarity(
            emotionalEmbedding,
            headlineEmbedding
        );

        return {
            score: Math.max(0, similarity),  // 0 to 1
            isEmotional: similarity > 0.5
        };
    }

    /**
     * Suggest better title
     */
    suggestBetterTitle(headline) {
        let better = headline;

        // Replace clickbait words
        Object.entries(this.betterAlternatives).forEach(([bad, good]) => {
            const regex = new RegExp(bad, 'gi');
            better = better.replace(regex, good);
        });

        // Remove excessive punctuation
        better = better.replace(/!{2,}/g, '.');
        better = better.replace(/\?{2,}/g, '?');

        // Remove ALL CAPS (keep first letter)
        better = better.replace(/\b([A-Z]{5,})\b/g, (match) => {
            return match.charAt(0) + match.slice(1).toLowerCase();
        });

        // If significantly different, return suggestion
        return better !== headline ? better : null;
    }

    /**
     * Get red flags list
     */
    getRedFlags(headline, matchedPatterns) {
        const flags = [];

        if (headline.includes('!!!') || headline.includes('??')) {
            flags.push('Excessive punctuation');
        }

        if (/[A-Z]{5,}/.test(headline)) {
            flags.push('ALL CAPS words');
        }

        if (matchedPatterns.some(p => p.includes('won\'t believe') || p.includes('shocking'))) {
            flags.push('Sensational language');
        }

        if (headline.length < 20) {
            flags.push('Too short (vague)');
        }

        if (headline.length > 120) {
            flags.push('Too long');
        }

        return flags;
    }

    /**
     * Batch detect for multiple articles
     */
    async detectBatch(articles) {
        const results = [];

        for (const article of articles) {
            const result = await this.detect(article.title);
            results.push({
                ...article,
                clickbaitAnalysis: result,
                isClickbait: result.isClickbait
            });
        }

        return results;
    }

    /**
     * Filter out clickbait articles
     */
    async filterClickbait(articles, threshold = 0.5) {
        const analyzed = await this.detectBatch(articles);
        return analyzed.filter(a => !a.isClickbait || a.clickbaitAnalysis.score < threshold * 100);
    }
}

export const clickbaitDetector = new ClickbaitDetector();

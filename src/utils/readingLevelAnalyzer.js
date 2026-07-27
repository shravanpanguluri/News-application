/**
 * Reading Level Analyzer - Analyze article readability
 * Helps users choose articles matching their reading preference
 */

class ReadingLevelAnalyzer {
    /**
     * Analyze article reading level
     */
    analyze(article) {
        const text = article.title + '. ' + (article.description || '');
        
        return {
            level: this.getReadingLevel(text),
            grade: this.getGradeLevel(text),
            fleschScore: this.calculateFlesch(text),
            avgSentenceLength: this.getAvgSentenceLength(text),
            complexWordRatio: this.getComplexWordRatio(text),
            readTime: this.calculateReadTime(text),
            wordCount: text.split(' ').length
        };
    }

    /**
     * Calculate Flesch Reading Ease Score
     * Higher = easier to read
     */
    calculateFlesch(text) {
        const sentences = text.split(/[.!?]+/).filter(s => s.trim().length > 0).length;
        const words = text.split(' ').length;
        const syllables = this.countSyllables(text);

        if (sentences === 0 || words === 0) return 0;

        // Flesch formula
        const score = 206.835 - (1.015 * (words / sentences)) - (84.6 * (syllables / words));
        return Math.round(score);
    }

    /**
     * Get reading level label
     */
    getReadingLevel(text) {
        const score = this.calculateFlesch(text);

        if (score >= 90) return { label: 'Very Easy', emoji: '😊', color: 'green' };
        if (score >= 80) return { label: 'Easy', emoji: '🙂', color: 'lightgreen' };
        if (score >= 70) return { label: 'Fairly Easy', emoji: '😐', color: 'yellow' };
        if (score >= 60) return { label: 'Standard', emoji: '😐', color: 'orange' };
        if (score >= 50) return { label: 'Fairly Difficult', emoji: '😕', color: 'orangered' };
        if (score >= 30) return { label: 'Difficult', emoji: '😟', color: 'red' };
        return { label: 'Very Difficult', emoji: '😫', color: 'darkred' };
    }

    /**
     * Get US grade level
     */
    getGradeLevel(text) {
        const sentences = text.split(/[.!?]+/).filter(s => s.trim().length > 0).length;
        const words = text.split(' ').length;
        const syllables = this.countSyllables(text);

        if (sentences === 0 || words === 0) return 'N/A';

        // Flesch-Kincaid Grade Level
        const grade = (0.39 * (words / sentences)) + (11.8 * (syllables / words)) - 15.59;
        
        if (grade < 1) return 'Elementary';
        if (grade < 6) return `Grade ${Math.round(grade)}`;
        if (grade < 9) return `Middle School`;
        if (grade < 13) return `High School`;
        return 'College+';
    }

    /**
     * Count syllables in text (simplified)
     */
    countSyllables(text) {
        const words = text.toLowerCase().split(' ');
        let total = 0;

        words.forEach(word => {
            // Remove non-alpha characters
            word = word.replace(/[^a-z]/g, '');
            if (word.length === 0) return;

            // Count vowel groups
            const vowelGroups = word.match(/[aeiouy]+/g);
            if (vowelGroups) {
                total += vowelGroups.length;
            } else {
                total += 1;
            }

            // Adjust for silent e
            if (word.endsWith('e') && !word.endsWith('le')) {
                total -= 1;
            }

            // Minimum 1 syllable per word
            if (total < 1) total = 1;
        });

        return total;
    }

    /**
     * Get average sentence length
     */
    getAvgSentenceLength(text) {
        const sentences = text.split(/[.!?]+/).filter(s => s.trim().length > 0);
        const words = text.split(' ').length;

        return sentences.length > 0 ? Math.round(words / sentences.length) : 0;
    }

    /**
     * Get ratio of complex words
     */
    getComplexWordRatio(text) {
        const words = text.split(' ');
        const complexWords = words.filter(word => {
            return this.countSyllables(word) > 2;
        }).length;

        return words.length > 0 ? Math.round((complexWords / words.length) * 100) : 0;
    }

    /**
     * Calculate read time in minutes
     */
    calculateReadTime(text) {
        const words = text.split(' ').length;
        const wordsPerMinute = 200;  // Average reading speed

        return Math.ceil(words / wordsPerMinute);
    }
}

export const readingLevelAnalyzer = new ReadingLevelAnalyzer();

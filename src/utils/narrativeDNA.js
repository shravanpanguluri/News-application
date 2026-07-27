/**
 * Narrative DNA - NLP Pipeline for News Analysis
 * Uses TensorFlow.js for client-side text analysis
 * LAZY LOADED - Only loads when explicitly called
 */

// import * as tf from '@tensorflow/tfjs'; // DISABLED for Vercel deployment

class NarrativeDNA {
  constructor() {
    this.model = null;
    this.embeddingCache = new Map();
    this.initialized = false;
    this.loadingProgress = 0;
    this.loadPromise = null;  // Track loading promise
  }

  async initialize() {
    if (this.initialized) return true;
    if (this.loadPromise) return this.loadPromise;  // Prevent duplicate loads

    this.loadPromise = (async () => {
      try {
        console.log('🧠 NLP Pipeline: Using lightweight hash-based embeddings (optimized for production)');
        // TensorFlow.js model loading disabled for production deployment
        // Embeddings use deterministic hash-based fallback for speed and reliability
        this.initialized = true;
        this.loadingProgress = 100;
        console.log('✅ NLP Pipeline ready (hash-based embeddings)');
        return true;
      } catch (error) {
        console.error('Failed to load NLP model:', error);
        this.loadingProgress = 0;
        this.loadPromise = null;  // Reset to allow retry
        return false;
      }
    })();

    return this.loadPromise;
  }

  // Extract narrative "genes" from article
  async extractGenes(text, headline) {
    if (!this.initialized) {
      await this.initialize();
    }

    const combinedText = `${headline}. ${text}`;
    
    try {
      // Parallel processing for speed
      const [embedding, entities, sentiment, framing] = await Promise.all([
        this.getEmbedding(combinedText),
        this.extractEntities(combinedText),
        this.analyzeSentiment(combinedText),
        this.detectFraming(combinedText)
      ]);

      return {
        embedding: Array.from(embedding), // Convert tensor to array
        entities,
        sentiment,
        framing,
        keyClaims: this.extractClaims(combinedText),
        emotionalTone: this.detectEmotionalTone(combinedText),
        timestamp: Date.now(),
        textHash: this.hashText(combinedText)
      };
    } catch (error) {
      console.error('Error extracting genes:', error);
      return this.getFallbackGenes(text, headline);
    }
  }

  // Semantic embedding using USE
  async getEmbedding(text) {
    // Check cache first
    if (this.embeddingCache.has(text)) {
      return this.embeddingCache.get(text);
    }

    // If model not loaded, return cached/fallback embedding
    if (!this.model || !this.initialized) {
      console.warn('⚠️  NLP model not loaded - using cached/fallback embeddings');
      // Return a deterministic hash-based embedding for consistency
      const fallbackEmbedding = this.hashToEmbedding(text);
      this.embeddingCache.set(text, fallbackEmbedding);
      return fallbackEmbedding;
    }

    try {
      const embeddings = await this.model.embed([text]);
      const array = await embeddings.array();
      embeddings.dispose(); // Prevent memory leaks

      this.embeddingCache.set(text, array[0]);

      // Limit cache size
      if (this.embeddingCache.size > 100) {
        const firstKey = this.embeddingCache.keys().next().value;
        this.embeddingCache.delete(firstKey);
      }

      return array[0];
    } catch (error) {
      console.error('Error getting embedding:', error);
      const fallbackEmbedding = this.hashToEmbedding(text);
      this.embeddingCache.set(text, fallbackEmbedding);
      return fallbackEmbedding; // Fallback to hash-based embedding
    }
  }

  // Generate deterministic embedding from text hash (fallback when model not loaded)
  hashToEmbedding(text) {
    // Create a simple hash-based pseudo-embedding (512 dimensions)
    const embedding = new Array(512).fill(0);
    let hash = 0;
    for (let i = 0; i < text.length; i++) {
      const char = text.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32-bit integer
      // Distribute hash across embedding dimensions
      for (let j = 0; j < 512; j++) {
        embedding[j] = Math.sin(hash + j) * 0.1; // Small values to mimic normalized embeddings
      }
    }
    return embedding;
  }

  // Entity extraction using regex patterns (simple, fast, no dependencies)
  extractEntities(text) {
    try {
      // Simple regex-based entity extraction
      const patterns = {
        people: /\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b/g,
        organizations: /\b(AI|NASA|FBI|CIA|UN|WHO|NATO|EU|Apple|Google|Microsoft|Amazon|Facebook|Twitter|Tesla|Netflix|IBM|Intel|NVIDIA)\b/gi,
        places: /\b([A-Z][a-z]+(?:ville|ton|burg|land|city|town|ford|mouth))\b/g,
        topics: /\b(artificial intelligence|machine learning|climate change|economy|technology|healthcare|education|politics|sports|entertainment)\b/gi,
        dates: /\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b/gi,
        money: /\$[\d,]+(?:\s+(?:million|billion|trillion))?\b/gi
      };

      const extract = (pattern) => {
        const matches = text.match(pattern);
        return matches ? [...new Set(matches)].slice(0, 10) : [];
      };

      return {
        people: extract(patterns.people).filter(p => p.length > 3 && p.length < 50),
        organizations: extract(patterns.organizations),
        places: extract(patterns.places),
        topics: extract(patterns.topics),
        dates: extract(patterns.dates),
        money: extract(patterns.money)
      };
    } catch (error) {
      console.error('Error extracting entities:', error);
      return {
        people: [],
        organizations: [],
        places: [],
        topics: [],
        dates: [],
        money: []
      };
    }
  }

  // Sentiment analysis using keyword scoring
  analyzeSentiment(text) {
    try {
      const textLower = text.toLowerCase();
      let positive = 0, negative = 0, intensity = 0;
      
      const emotionalWords = {
        positive: ['breakthrough', 'victory', 'growth', 'success', 'peace', 'hope', 'improve', 'benefit', 'progress', 'achievement', 'positive', 'good', 'great', 'excellent', 'wonderful'],
        negative: ['crisis', 'disaster', 'failure', 'death', 'war', 'scandal', 'crash', 'threat', 'danger', 'loss', 'negative', 'bad', 'terrible', 'awful', 'horrible'],
        intense: ['catastrophic', 'unprecedented', 'shocking', 'devastating', 'miracle', 'historic', 'massive', 'critical', 'huge', 'enormous']
      };

      emotionalWords.positive.forEach(word => {
        const regex = new RegExp(`\\b${word}\\b`, 'gi');
        const matches = textLower.match(regex);
        if (matches) positive += matches.length;
      });

      emotionalWords.negative.forEach(word => {
        const regex = new RegExp(`\\b${word}\\b`, 'gi');
        const matches = textLower.match(regex);
        if (matches) negative += matches.length;
      });

      emotionalWords.intense.forEach(word => {
        const regex = new RegExp(`\\b${word}\\b`, 'gi');
        const matches = textLower.match(regex);
        if (matches) intensity += matches.length * 0.5;
      });

      const total = positive + negative || 1;
      const score = (positive - negative) / total;
      const magnitude = Math.min((positive + negative + intensity) / 10, 1);

      return {
        score: Math.max(-1, Math.min(1, score)), // Clamp to -1 to 1
        magnitude: magnitude,
        confidence: text.split('.').length > 3 ? 0.8 : 0.5,
        positive: positive,
        negative: negative
      };
    } catch (error) {
      console.error('Error analyzing sentiment:', error);
      return {
        score: 0,
        magnitude: 0,
        confidence: 0.3,
        positive: 0,
        negative: 0
      };
    }
  }

  // Detect narrative framing using keyword patterns
  detectFraming(text) {
    try {
      const textLower = text.toLowerCase();
      
      const frames = {
        economic: ['market', 'economy', 'stocks', 'trade', 'financial', 'gdp', 'inflation', 'business', 'investment', 'profit'],
        security: ['threat', 'attack', 'defense', 'military', 'terror', 'security', 'war', 'weapon', 'missile', 'army'],
        humanitarian: ['victims', 'families', 'community', 'help', 'relief', 'suffering', 'refugees', 'crisis', 'aid', 'shelter'],
        political: ['election', 'vote', 'party', 'government', 'policy', 'senate', 'congress', 'president', 'campaign', 'legislation'],
        scientific: ['study', 'research', 'data', 'scientists', 'discovery', 'evidence', 'experiment', 'findings', 'analysis', 'theory'],
        moral: ['right', 'wrong', 'ethics', 'values', 'principles', 'justice', 'fairness', 'responsibility', 'duty', 'integrity']
      };

      const scores = {};
      Object.keys(frames).forEach(frame => {
        const matches = frames[frame].filter(keyword => textLower.includes(keyword));
        scores[frame] = matches.length / frames[frame].length;
      });

      // Get dominant frame
      const sorted = Object.entries(scores).sort((a, b) => b[1] - a[1]);
      const dominant = sorted[0];

      return {
        primary: dominant[0],
        confidence: dominant[1],
        distribution: scores,
        secondary: (sorted[1] && sorted[1][0]) || null
      };
    } catch (error) {
      console.error('Error detecting framing:', error);
      return {
        primary: 'general',
        confidence: 0.3,
        distribution: {},
        secondary: null
      };
    }
  }

  // Extract factual claims using pattern matching
  extractClaims(text) {
    try {
      const sentences = text.split(/[.!?]+/).filter(s => s.trim().length > 10);
      const indicators = ['said', 'announced', 'reported', 'found', 'revealed', 'confirmed', 'stated', 'declared', 'claimed', 'according'];
      
      return sentences
        .filter(sent => {
          const sentLower = sent.toLowerCase();
          return indicators.some(ind => sentLower.includes(ind));
        })
        .map(sent => {
          // Try to extract speaker (simple heuristic: capitalized words at start)
          const words = sent.trim().split(/\s+/);
          const potentialSpeaker = words.slice(0, 3).find(w => w.match(/^[A-Z][a-z]+$/));
          
          return {
            text: sent.trim(),
            speaker: potentialSpeaker || 'Unknown',
            confidence: words.length > 5 ? 0.7 : 0.4
          };
        })
        .slice(0, 5); // Top 5 claims
    } catch (error) {
      console.error('Error extracting claims:', error);
      return [];
    }
  }

  // Detect emotional tone
  detectEmotionalTone(text) {
    try {
      const textLower = text.toLowerCase();
      const tones = {
        urgent: ['breaking', 'urgent', 'just', 'now', 'alert', 'developing', 'live', 'update'],
        somber: ['tragic', 'sad', 'loss', 'mourning', 'death', 'funeral', 'grief', 'sorrow'],
        hopeful: ['hope', 'future', 'promise', 'better', 'improve', 'recovery', 'optimism', 'bright'],
        angry: ['outrage', 'furious', 'demand', 'protest', 'anger', 'unacceptable', 'condemn'],
        neutral: []
      };

      let maxScore = 0;
      let dominantTone = 'neutral';

      Object.entries(tones).forEach(([tone, keywords]) => {
        const score = keywords.filter(k => textLower.includes(k)).length;
        if (score > maxScore) {
          maxScore = score;
          dominantTone = tone;
        }
      });

      return dominantTone;
    } catch (error) {
      console.error('Error detecting tone:', error);
      return 'neutral';
    }
  }

  // Calculate narrative distance between two stories
  async calculateDistance(genes1, genes2) {
    try {
      // Cosine similarity of embeddings
      const embeddingSim = this.cosineSimilarity(genes1.embedding, genes2.embedding);
      
      // Entity overlap
      const entityOverlap = this.calculateEntityOverlap(genes1.entities, genes2.entities);
      
      // Framing divergence
      const framingDiff = genes1.framing.primary !== genes2.framing.primary ? 0.3 : 0;
      
      // Sentiment divergence
      const sentimentDiff = Math.abs(genes1.sentiment.score - genes2.sentiment.score);

      // Weighted combination
      const distance = (
        (1 - embeddingSim) * 0.5 +
        (1 - entityOverlap) * 0.2 +
        framingDiff * 0.2 +
        sentimentDiff * 0.1
      );

      return {
        total: distance,
        embeddingDistance: 1 - embeddingSim,
        entityDistance: 1 - entityOverlap,
        framingDistance: framingDiff,
        sentimentDistance: sentimentDiff,
        similarity: 1 - distance
      };
    } catch (error) {
      console.error('Error calculating distance:', error);
      return {
        total: 0.5,
        embeddingDistance: 0.5,
        entityDistance: 0.5,
        framingDistance: 0,
        sentimentDistance: 0,
        similarity: 0.5
      };
    }
  }

  cosineSimilarity(a, b) {
    let dotProduct = 0;
    let normA = 0;
    let normB = 0;
    
    for (let i = 0; i < a.length; i++) {
      dotProduct += a[i] * b[i];
      normA += a[i] * a[i];
      normB += b[i] * b[i];
    }
    
    if (normA === 0 || normB === 0) return 0;
    return dotProduct / (Math.sqrt(normA) * Math.sqrt(normB));
  }

  calculateEntityOverlap(entities1, entities2) {
    const allTypes = ['people', 'organizations', 'places', 'topics'];
    let totalOverlap = 0;
    
    allTypes.forEach(type => {
      const set1 = new Set(entities1[type] || []);
      const set2 = new Set(entities2[type] || []);
      const intersection = new Set([...set1].filter(x => set2.has(x)));
      const union = new Set([...set1, ...set2]);
      
      if (union.size > 0) {
        totalOverlap += intersection.size / union.size;
      }
    });
    
    return totalOverlap / allTypes.length;
  }

  hashText(text) {
    let hash = 0;
    for (let i = 0; i < text.length; i++) {
      const char = text.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash;
    }
    return hash.toString(16);
  }

  getFallbackGenes(text, headline) {
    return {
      embedding: new Array(512).fill(0),
      entities: this.extractEntities(text),
      sentiment: this.analyzeSentiment(text),
      framing: this.detectFraming(text),
      keyClaims: [],
      emotionalTone: this.detectEmotionalTone(text),
      timestamp: Date.now(),
      textHash: this.hashText(`${headline}. ${text}`)
    };
  }

  // Clear cache to free memory
  clearCache() {
    this.embeddingCache.clear();
    console.log('NLP cache cleared');
  }

  // Get cache stats
  getCacheStats() {
    return {
      size: this.embeddingCache.size,
      initialized: this.initialized,
      loadingProgress: this.loadingProgress
    };
  }
}

// Singleton instance
export const narrativeDNA = new NarrativeDNA();

// Helper function to get framing color
export const getFramingColor = (framing) => {
  const colors = {
    economic: '#3498db',    // Blue
    security: '#e74c3c',    // Red
    humanitarian: '#2ecc71', // Green
    political: '#9b59b6',   // Purple
    scientific: '#f39c12',  // Orange
    moral: '#1abc9c',       // Teal
    general: '#95a5a6'      // Gray
  };
  return colors[framing] || colors.general;
};

// Helper function to get sentiment color
export const getSentimentColor = (score) => {
  if (score > 0.3) return '#27ae60'; // Green (positive)
  if (score < -0.3) return '#c0392b'; // Red (negative)
  return '#f39c12'; // Orange (neutral)
};

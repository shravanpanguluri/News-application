import { useState, useEffect, useCallback } from 'react';
import { narrativeDNA } from '../utils/narrativeDNA';

/**
 * React Hook for NLP Processing
 * Provides easy access to narrative analysis in components
 */
export const useNLP = () => {
  const [ready, setReady] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState(null);
  const [loadingProgress, setLoadingProgress] = useState(0);
  const [cacheStats, setCacheStats] = useState({ size: 0, initialized: false });

  // Initialize NLP pipeline on mount
  useEffect(() => {
    let isMounted = true;

    const init = async () => {
      try {
        setLoadingProgress(0);
        const success = await narrativeDNA.initialize();
        
        if (isMounted) {
          setReady(success);
          setLoadingProgress(success ? 100 : 0);
          if (!success) {
            setError('Failed to initialize NLP model. Using fallback analysis.');
          }
          setCacheStats(narrativeDNA.getCacheStats());
        }
      } catch (err) {
        if (isMounted) {
          setError(err.message);
          setReady(false);
        }
      }
    };

    init();

    return () => {
      isMounted = false;
    };
  }, []);

  // Analyze single article
  const analyzeArticle = useCallback(async (article) => {
    if (!article) return null;
    if (!ready && !narrativeDNA.initialized) {
      console.warn('NLP not ready, attempting to initialize...');
      await narrativeDNA.initialize();
    }
    
    setProcessing(true);
    setError(null);
    
    try {
      const genes = await narrativeDNA.extractGenes(
        article.content || article.description || '',
        article.title || ''
      );
      
      setProcessing(false);
      setCacheStats(narrativeDNA.getCacheStats());
      return genes;
    } catch (err) {
      console.error('Error analyzing article:', err);
      setError(err.message);
      setProcessing(false);
      return narrativeDNA.getFallbackGenes(
        article.content || article.description || '',
        article.title || ''
      );
    }
  }, [ready]);

  // Analyze multiple articles in batches
  const analyzeArticles = useCallback(async (articles, batchSize = 3) => {
    if (!articles || articles.length === 0) return [];
    
    const enriched = [];
    setProcessing(true);
    
    // Process in batches to avoid blocking UI
    for (let i = 0; i < articles.length; i += batchSize) {
      const batch = articles.slice(i, i + batchSize);
      
      const batchResults = await Promise.all(
        batch.map(async (article) => {
          const genes = await analyzeArticle(article);
          return { ...article, genes };
        })
      );
      
      enriched.push(...batchResults);
      
      // Small delay to allow UI to update
      await new Promise(resolve => setTimeout(resolve, 50));
    }
    
    setProcessing(false);
    return enriched;
  }, [analyzeArticle]);

  // Compare two articles
  const compareArticles = useCallback(async (article1, article2) => {
    if (!article1 || !article2) return null;
    
    try {
      const [genes1, genes2] = await Promise.all([
        analyzeArticle(article1),
        analyzeArticle(article2)
      ]);
      
      if (!genes1 || !genes2) return null;
      
      const distance = await narrativeDNA.calculateDistance(genes1, genes2);
      
      return {
        genes1,
        genes2,
        distance,
        similarity: distance.similarity
      };
    } catch (err) {
      console.error('Error comparing articles:', err);
      return null;
    }
  }, [analyzeArticle]);

  // Find similar articles from a list
  const findSimilarArticles = useCallback(async (sourceArticle, articles, threshold = 0.6) => {
    if (!sourceArticle || !articles || articles.length === 0) return [];
    
    const sourceGenes = await analyzeArticle(sourceArticle);
    
    const similarities = await Promise.all(
      articles.map(async (article) => {
        if (article.id === sourceArticle.id) return null;
        
        const genes = await analyzeArticle(article);
        const distance = await narrativeDNA.calculateDistance(sourceGenes, genes);
        
        return {
          article,
          similarity: distance.similarity,
          distance: distance.total
        };
      })
    );
    
    return similarities
      .filter(result => result !== null && result.similarity >= threshold)
      .sort((a, b) => b.similarity - a.similarity);
  }, [analyzeArticle]);

  // Clear embedding cache
  const clearCache = useCallback(() => {
    narrativeDNA.clearCache();
    setCacheStats(narrativeDNA.getCacheStats());
  }, []);

  return {
    ready,
    processing,
    error,
    loadingProgress,
    cacheStats,
    analyzeArticle,
    analyzeArticles,
    compareArticles,
    findSimilarArticles,
    clearCache
  };
};

// Helper hook for real-time analysis of changing content
export const useRealTimeNLP = (content, headline) => {
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const { ready } = useNLP();

  useEffect(() => {
    if (!content || !ready) return;

    let cancelled = false;

    const analyze = async () => {
      setLoading(true);
      try {
        const genes = await narrativeDNA.extractGenes(content, headline || '');
        if (!cancelled) {
          setAnalysis(genes);
        }
      } catch (error) {
        console.error('Real-time analysis error:', error);
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    // Debounce analysis (wait 500ms after content stops changing)
    const timeoutId = setTimeout(analyze, 500);

    return () => {
      cancelled = true;
      clearTimeout(timeoutId);
    };
  }, [content, headline, ready]);

  return { analysis, loading };
};

export default useNLP;

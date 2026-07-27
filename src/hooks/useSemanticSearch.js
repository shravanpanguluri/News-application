import { useState, useEffect, useCallback } from 'react';
import { narrativeDNA } from '../utils/narrativeDNA';

export const useSemanticSearch = (articles) => {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [isModelLoaded, setIsModelLoaded] = useState(false);

    // Initialize the model
    useEffect(() => {
        const init = async () => {
            const loaded = await narrativeDNA.initialize();
            setIsModelLoaded(loaded);
        };
        init();
    }, []);

    const performSearch = useCallback(async (searchQuery) => {
        if (!searchQuery || searchQuery.length < 3 || !articles || articles.length === 0) {
            setResults(articles);
            return;
        }

        setIsLoading(true);
        try {
            // Get embedding for the search query
            const queryEmbedding = await narrativeDNA.getEmbedding(searchQuery);
            
            // Map articles to their similarity scores
            const scoredArticles = await Promise.all(articles.map(async (article) => {
                const text = `${article.title}. ${article.description || ''}`;
                const articleEmbedding = await narrativeDNA.getEmbedding(text);
                
                // Use cosine similarity
                const similarity = narrativeDNA.cosineSimilarity(queryEmbedding, articleEmbedding);
                
                return {
                    ...article,
                    semanticScore: similarity
                };
            }));

            // Sort by similarity score
            const sorted = scoredArticles
                .filter(a => a.semanticScore > 0.1) // Minimum threshold
                .sort((a, b) => b.semanticScore - a.semanticScore);

            setResults(sorted);
        } catch (error) {
            console.error('Semantic search failed:', error);
            // Fallback to keyword search
            const fallback = articles.filter(a => 
                a.title.toLowerCase().includes(searchQuery.toLowerCase()) || 
                (a.description && a.description.toLowerCase().includes(searchQuery.toLowerCase()))
            );
            setResults(fallback);
        } finally {
            setIsLoading(false);
        }
    }, [articles]);

    useEffect(() => {
        const timer = setTimeout(() => {
            if (query) {
                performSearch(query);
            } else {
                setResults(articles);
            }
        }, 500); // Debounce search

        return () => clearTimeout(timer);
    }, [query, performSearch, articles]);

    return {
        query,
        setQuery,
        results,
        isLoading,
        isModelLoaded
    };
};

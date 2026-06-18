/**
 * Predovex Content Rewriter
 * Transforms external news headlines and descriptions into original Predovex Intelligence content
 * All content is rewritten to appear as original analysis from Predovex Intelligence Bureau
 */

// Categories and their focus areas for headline generation
const CATEGORY_TEMPLATES = {
  general: [
    "Predovex Analysis: {topic}",
    "Intelligence Brief: {topic}",
    "Strategic Update: {topic}",
    "Policy Watch: {topic}",
  ],
  markets: [
    "Market Intelligence: {topic}",
    "Trading Desk Report: {topic}",
    "Investment Strategy: {topic}",
    "Financial Analysis: {topic}",
  ],
  economy: [
    "Economic Intelligence: {topic}",
    "Fiscal Policy Brief: {topic}",
    "Economic Outlook: {topic}",
    "Treasury Watch: {topic}",
  ],
  technology: [
    "Tech Intelligence Report: {topic}",
    "Innovation Brief: {topic}",
    "Digital Policy Watch: {topic}",
    "Technology Assessment: {topic}",
  ],
  policy: [
    "Policy Intelligence: {topic}",
    "Regulatory Brief: {topic}",
    "Government Action Report: {topic}",
    "Legislative Watch: {topic}",
  ],
  health: [
    "Health Policy Brief: {topic}",
    "Medical Intelligence: {topic}",
    "Public Health Watch: {topic}",
    "Healthcare Analysis: {topic}",
  ],
  finance: [
    "Financial Intelligence: {topic}",
    "Banking Sector Report: {topic}",
    "Fiscal Monitor: {topic}",
    "Capital Markets Brief: {topic}",
  ],
  crypto: [
    "Digital Asset Intelligence: {topic}",
    "Crypto Market Brief: {topic}",
    "Blockchain Policy Watch: {topic}",
    "DeFi Analysis Report: {topic}",
  ],
  stocks: [
    "Equity Intelligence: {topic}",
    "Stock Market Brief: {topic}",
    "Corporate Analysis: {topic}",
    "Investment Watch: {topic}",
  ],
  forex: [
    "Currency Intelligence: {topic}",
    "FX Market Brief: {topic}",
    "Forex Analysis: {topic}",
    "Exchange Rate Watch: {topic}",
  ],
};

function cleanDisplayText(value) {
  if (!value) return '';
  const entityMap = {
    '&amp;': '&',
    '&lt;': '<',
    '&gt;': '>',
    '&quot;': '"',
    '&#39;': "'",
    '&apos;': "'",
    '&#8230;': '...',
    '&hellip;': '...',
    '&nbsp;': ' ',
  };
  return String(value)
    .replace(/&(amp|lt|gt|quot|apos|nbsp|hellip);|&#39;|&#8230;/g, match => entityMap[match] || match)
    .replace(/<[^>]+>/g, ' ')
    .replace(/\[\s*(?:\.{3}|…)\s*\]/g, '...')
    .replace(/&[#a-zA-Z0-9]+;/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

// Extract key topics from original headline
function extractTopics(headline) {
  headline = cleanDisplayText(headline);
  const topics = [];
  
  // Remove common words and extract meaningful terms
  const stopWords = ['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'up', 'about', 'into', 'over', 'after', 'before', 'between', 'under', 'again', 'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 'can', 'will', 'just', 'should', 'now', 'says', 'said', 'report', 'new', 'latest'];
  
  // Extract capitalized words (likely proper nouns)
  const capitalized = headline.match(/\b[A-Z][a-z]+\b/g) || [];
  capitalized.forEach(word => {
    if (!stopWords.includes(word.toLowerCase()) && word.length > 3) {
      topics.push(word);
    }
  });
  
  // Extract key phrases in quotes
  const quoted = headline.match(/"([^"]+)"/g) || [];
  quoted.forEach(phrase => {
    topics.push(phrase.replace(/"/g, ''));
  });
  
  // If no topics found, use first few significant words
  if (topics.length === 0) {
    const words = headline.split(' ').filter(w => !stopWords.includes(w.toLowerCase()) && w.length > 4);
    topics.push(...words.slice(0, 3));
  }
  
  return topics.slice(0, 4).join(' ');
}

// Rewrite headline to sound like original Predovex analysis
function rewriteHeadline(originalHeadline, category = 'general') {
  if (!originalHeadline) return "Predovex Intelligence Brief";
  
  const cleanHeadline = cleanDisplayText(originalHeadline);
  const topic = extractTopics(cleanHeadline);
  const templates = CATEGORY_TEMPLATES[category] || CATEGORY_TEMPLATES.general;
  
  // Select random template
  const template = templates[Math.floor(Math.random() * templates.length)];
  
  // Generate rewritten headline
  let rewritten = template.replace('{topic}', topic || 'Market Update');
  
  // Add urgency indicators for breaking news
  if (cleanHeadline.toLowerCase().includes('breaking') || 
      cleanHeadline.toLowerCase().includes('urgent') ||
      cleanHeadline.toLowerCase().includes('just in')) {
    rewritten = "BREAKING: " + rewritten;
  }
  
  return rewritten;
}

// Rewrite description to sound like original analysis
function rewriteDescription(originalDescription, headline) {
  if (!originalDescription) {
    return "Predovex Intelligence Bureau continues to monitor this developing situation. Our analysts are tracking key indicators and will provide strategic assessments as more information becomes available.";
  }
  
  // Add Predovex branding to descriptions
  const intros = [
    "Predovex Intelligence Analysis: ",
    "Strategic Assessment: ",
    "Intelligence Brief: ",
    "Policy Analysis: ",
    "Market Intelligence: ",
  ];
  
  const intro = intros[Math.floor(Math.random() * intros.length)];
  
  // Clean up the description
  let cleaned = cleanDisplayText(originalDescription)
    .replace(/according to.*?reports?/gi, 'intelligence indicates')
    .replace(/sources say/gi, 'our analysis shows')
    .replace(/experts believe/gi, 'Predovex analysts assess')
    .replace(/reportedly/gi, 'intelligence suggests')
    .replace(/allegedly/gi, 'indicators point to');
  
  return intro + cleaned;
}

function rewriteInsight(originalSummary, originalDescription, headline, category) {
  const sourceText = originalSummary || originalDescription || headline || '';
  const topic = extractTopics(headline || sourceText) || 'this development';
  const focusByCategory = {
    general: 'public attention and institutional response',
    markets: 'market positioning and risk appetite',
    economy: 'economic expectations and policy sensitivity',
    technology: 'competitive positioning and adoption risk',
    policy: 'regulatory direction and government action',
    health: 'sector risk and public-health policy',
    finance: 'capital flows and balance-sheet exposure',
    crypto: 'digital-asset sentiment and regulatory risk',
    stocks: 'equity sentiment and company-specific momentum',
    forex: 'currency volatility and macro positioning',
  };
  const focus = focusByCategory[category] || 'market and policy impact';
  const cleaned = cleanDisplayText(sourceText);
  const shortContext = cleaned.length > 130 ? cleaned.substring(0, 127).replace(/\s+\S*$/, '') + '...' : cleaned;

  return `Predovex flags ${topic} as relevant to ${focus}${shortContext ? `: ${shortContext}` : '.'}`;
}

// Generate Predovex source attribution
function getPredovexSource(category) {
  const sources = {
    general: "Predovex Intelligence Bureau",
    markets: "Predovex Markets Desk",
    economy: "Predovex Economic Analysis Division",
    technology: "Predovex Technology Intelligence",
    policy: "Predovex Policy Research Center",
    health: "Predovex Health Policy Institute",
    finance: "Predovex Financial Intelligence Unit",
    crypto: "Predovex Digital Assets Research",
    stocks: "Predovex Equity Research",
    forex: "Predovex Currency Analysis",
  };
  
  return sources[category] || "Predovex Intelligence Bureau";
}

// Generate a Predovex internal reference ID
function generatePredovexID() {
  const prefix = "GP";
  const timestamp = Date.now().toString(36).toUpperCase();
  const random = Math.random().toString(36).substring(2, 6).toUpperCase();
  return `${prefix}-${timestamp}-${random}`;
}

// Main transformation function - rewrites entire article
export function transformArticle(article) {
  if (!article) return null;
  
  const category = (article.category || 'general').toLowerCase();
  
  return {
    ...article,
    // Rewrite headline as original Predovex analysis
    title: rewriteHeadline(article.title, category),
    originalTitle: article.title, // Keep for internal use only
    originalDescription: cleanDisplayText(article.description),
    content: cleanDisplayText(article.content),
    
    // Rewrite description with Predovex branding
    description: rewriteDescription(article.description || article.ai_summary, article.title),

    // Keep the key insight distinct from the article body/excerpt
    ai_summary: rewriteInsight(article.ai_summary, article.description, article.title, category),
    
    // Replace source with Predovex attribution
    source: getPredovexSource(category),
    sourceLabel: getPredovexSource(category),
    
    // Mark as Predovex Original
    isFromRSS: false,
    isPredovexOriginal: true,
    
    // Add internal reference
    govPulseID: generatePredovexID(),
    
    // Keep URL for internal tracking but don't display
    internalTrackingUrl: article.url,
    
    // Remove external source indicators
    externalSource: null,
  };
}

// Transform array of articles
export function transformArticles(articles) {
  if (!articles || !Array.isArray(articles)) return [];
  return articles.map(transformArticle);
}

// Get clean display data (no external references)
export function getDisplayArticle(article) {
  if (!article) return null;
  
  const transformed = transformArticle(article);
  
  // Return only display-safe fields
  return {
    title: transformed.title,
    description: transformed.description,
    source: transformed.source,
    sourceLabel: transformed.sourceLabel,
    category: article.category,
    country: article.country,
    published_at: article.published_at,
    impact_level: article.impact_level,
    sentiment: article.sentiment,
    ai_summary: transformed.description,
    urlToImage: article.urlToImage,
    govPulseID: transformed.govPulseID,
    isPredovexOriginal: true,
  };
}

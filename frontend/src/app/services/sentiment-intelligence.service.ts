import { Injectable } from '@angular/core';

/**
 * Client-side sentiment intelligence preprocessing
 * Improves sentiment classification accuracy, especially for multilingual content
 */
@Injectable({
  providedIn: 'root'
})
export class SentimentIntelligenceService {

  // Common patterns for sentiment correction
  private readonly positivePhrases = [
    'love', 'amazing', 'excellent', 'great', 'awesome', 'perfect', 'best',
    'fantastic', 'wonderful', 'good', 'nice', 'happy', 'satisfied', 'recommend',
    'thumbs up', 'great app', 'love it', 'highly', 'buen', 'excelente', 'muy bien',
    'genial', 'maravilloso', 'fantástico', 'super', 'increíble'
  ];

  private readonly negativePhrases = [
    'hate', 'terrible', 'awful', 'bad', 'horrible', 'poor', 'worse',
    'crash', 'bug', 'error', 'issue', 'problem', 'don\'t like', 'waste',
    'disappoint', 'useless', 'broken', 'refuse', 'delete', 'uninstall',
    'malo', 'horrible', 'peor', 'problema', 'error', 'no me gusta'
  ];

  /**
   * Detect language of a text (basic heuristic)
   */
  detectLanguage(text: string): 'en' | 'es' | 'other' {
    if (!text) return 'en';
    
    // Simple language detection via character patterns
    const spanishPatterns = /[áéíóúñü]/gi;
    const spanishWords = /\b(el|la|de|que|es|un|una|por|para|en|con|se)\b/gi;
    
    const spanishMatches = (text.match(spanishPatterns) || []).length +
                          (text.match(spanishWords) || []).length * 2;
    
    return spanishMatches > text.length / 20 ? 'es' : 'en';
  }

  /**
   * Normalize text: lowercase, remove extra spaces, trim
   */
  normalizeText(text: string): string {
    return (text || '').toLowerCase().trim().replace(/\s+/g, ' ');
  }

  /**
   * Apply keyword-based sentiment correction for misclassified reviews
   */
  correctSentiment(text: string, originalSentiment: string, score: number): { sentiment: string; score: number; corrected: boolean } {
    const normalized = this.normalizeText(text);
    
    // Strong positive indicators
    const positiveCount = this.positivePhrases.filter(p => normalized.includes(p)).length;
    
    // Strong negative indicators
    const negativeCount = this.negativePhrases.filter(p => normalized.includes(p)).length;
    
    let corrected = false;
    let sentiment = originalSentiment;
    let newScore = score;
    
    // If strong positive signals override negative classification
    if (positiveCount > 0 && originalSentiment === 'negative' && score < 0.5) {
      sentiment = 'positive';
      newScore = 0.7;
      corrected = true;
    }
    
    // If strong negative signals override positive classification
    if (negativeCount > 0 && originalSentiment === 'positive' && score > 0.5) {
      sentiment = 'negative';
      newScore = 0.3;
      corrected = true;
    }
    
    // If uncertain and mixed signals, mark as neutral
    if (positiveCount > 0 && negativeCount > 0 && Math.abs(positiveCount - negativeCount) <= 1) {
      sentiment = 'neutral';
      newScore = 0.5;
      corrected = true;
    }
    
    return { sentiment, score: newScore, corrected };
  }

  /**
   * Enhance sentiment data with intelligence
   */
  enrichSentimentData(reviews: any[]) {
    return reviews.map(review => {
      const { sentiment, score, corrected } = this.correctSentiment(
        review.text,
        review.sentiment || 'neutral',
        review.sentiment_score || 0.5
      );
      
      return {
        ...review,
        sentiment,
        sentiment_score: score,
        sentiment_corrected: corrected,
        detected_language: this.detectLanguage(review.text)
      };
    });
  }

  /**
   * Get sentiment summary with confidence metrics
   */
  getSentimentSummary(reviews: any[]) {
    if (!reviews?.length) {
      return {
        positive: 0,
        negative: 0,
        neutral: 0,
        average_score: 0,
        confidence: 0,
        trend: 'stable'
      };
    }

    const enriched = this.enrichSentimentData(reviews);
    const total = enriched.length;
    
    const positive = enriched.filter(r => r.sentiment === 'positive').length;
    const negative = enriched.filter(r => r.sentiment === 'negative').length;
    const neutral = enriched.filter(r => r.sentiment === 'neutral').length;
    
    const avgScore = enriched.reduce((sum, r) => sum + (r.sentiment_score || 0.5), 0) / total;
    
    // Confidence: lower if many were corrected
    const corrected = enriched.filter(r => r.sentiment_corrected).length;
    const confidence = 1 - (corrected / total);
    
    return {
      positive,
      negative,
      neutral,
      average_score: parseFloat(avgScore.toFixed(2)),
      confidence: parseFloat(confidence.toFixed(2)),
      trend: avgScore > 0.6 ? 'improving' : avgScore < 0.4 ? 'declining' : 'stable',
      corrected_count: corrected
    };
  }
}

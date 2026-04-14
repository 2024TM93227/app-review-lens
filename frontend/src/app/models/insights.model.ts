/**
 * V2 Data models for App Review Lens
 */

export interface TopIssue {
  name: string;
  impact: number;
  impact_breakdown?: ImpactBreakdown;
  trend: 'up' | 'down' | 'stable';
  affected_users: number;
  frequency: number;
  avg_severity: number;
  avg_sentiment: number;
  avg_rating: number;
  rank: number;
  example_reviews: ExampleReview[];
  recommendation: string;
  recommendation_detail: string;
  recommendation_owner: string;
  top_complaints: string[];
}

export interface ImpactBreakdown {
  frequency: number;
  severity: number;
  negativity: number;
}

export interface ExampleReview {
  text: string;
  rating: number;
  sentiment: string;
}

export interface Alert {
  type: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  message: string;
  category?: string;
  previous_count: number;
  current_count: number;
  change_percentage: number;
  detected_at: string;
}

export interface RatingTrendPoint {
  date: string;
  avg_rating: number;
  count: number;
}

export interface InsightsV2Response {
  app_id: string;
  total_reviews: number;
  playstore_rating: number | null;
  top_issues: TopIssue[];
  alerts: Alert[];
  rating_trend: RatingTrendPoint[];
}

export interface SentimentTrendPoint {
  date: string;
  avg_sentiment_score: number;
  positive_count: number;
  negative_count: number;
  neutral_count: number;
  total_count: number;
}

export interface SentimentBreakdown {
  positive: number;
  negative: number;
  neutral: number;
}

export interface IssueDetailReview {
  text: string;
  rating: number;
  sentiment: string;
  sentiment_score: number;
  timestamp: string;
  app_version?: string;
  severity: number;
}

export interface IssueDetailResponse {
  issue_name: string;
  app_id: string;
  frequency: number;
  affected_users_pct: number;
  avg_rating: number;
  avg_sentiment: number;
  avg_severity: number;
  sentiment_breakdown: SentimentBreakdown;
  trend_data: SentimentTrendPoint[];
  ai_insight: string;
  recommendation: string;
  recommendation_detail: string;
  recommendation_owner: string;
  top_complaints: string[];
  reviews: IssueDetailReview[];
}

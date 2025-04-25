"""
Peer feedback plugin for Task Manager.
Handles the collection and analysis of peer feedback.
"""
from typing import Dict, List, Any, Optional
import pandas as pd
from datetime import datetime, timedelta

from core.adapters.plugin_base import PluginBase
from core.adapters.notion_adapter import NotionAdapter

class PeerFeedbackPlugin(PluginBase):
    """Plugin for collecting and analyzing peer feedback."""
    
    def __init__(self, config=None):
        """
        Initialize the plugin.
        
        Args:
            config: Configuration dictionary.
        """
        super().__init__(config)
        self.notion = NotionAdapter()
        self.feedback_db_id = self.config.get('feedback_database_id')
        
        # Cache feedback data
        self._feedback_cache = {}
        self._cache_timestamp = None
        self._cache_valid_duration = timedelta(minutes=30)  # Cache valid for 30 minutes
    
    def initialize(self):
        """
        Initialize the plugin.
        
        Returns:
            bool: True if initialization was successful, False otherwise.
        """
        # Test connection to the feedback database
        if not self.feedback_db_id:
            print("No feedback database ID configured")
            return False
            
        # Check if we can fetch sample feedback
        try:
            test_feedback = self.notion.fetch_peer_feedback("test", self.feedback_db_id, days_back=1)
            return True
        except Exception as e:
            print(f"Error connecting to feedback database: {e}")
            return False
    
    def get_recent_feedback(self, person_name: str, days_back: int = 14, use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        Get recent feedback for a specific person.
        
        Args:
            person_name: Name of the person to get feedback for.
            days_back: Number of days back to search for feedback.
            use_cache: Whether to use cached data if available.
            
        Returns:
            List[Dict[str, Any]]: List of feedback entries.
        """
        # Check if we have cached data that's still valid
        cache_key = f"{person_name}_{days_back}"
        if use_cache and self._is_cache_valid() and cache_key in self._feedback_cache:
            return self._feedback_cache[cache_key]
            
        # Fetch fresh data
        feedback = self.notion.fetch_peer_feedback(person_name, self.feedback_db_id, days_back)
        
        # Update cache
        self._feedback_cache[cache_key] = feedback
        self._cache_timestamp = datetime.now()
        
        return feedback
    
    def _is_cache_valid(self) -> bool:
        """
        Check if the cache is still valid.
        
        Returns:
            bool: True if the cache is valid, False otherwise.
        """
        if not self._cache_timestamp:
            return False
            
        age = datetime.now() - self._cache_timestamp
        return age < self._cache_valid_duration
    
    def clear_cache(self):
        """Clear the feedback cache."""
        self._feedback_cache = {}
        self._cache_timestamp = None
    
    def analyze_feedback_trends(self, person_name: str, days_back: int = 30) -> Dict[str, Any]:
        """
        Analyze feedback trends for a person.
        
        Args:
            person_name: Name of the person to analyze feedback for.
            days_back: Number of days back to analyze.
            
        Returns:
            Dict[str, Any]: Analysis results.
        """
        feedback = self.get_recent_feedback(person_name, days_back)
        
        if not feedback:
            return {
                "person": person_name,
                "data_points": 0,
                "message": f"No feedback found for {person_name} in the last {days_back} days."
            }
            
        # Simple analysis - this would be enhanced with AI in a real implementation
        feedback_df = pd.DataFrame(feedback)
        
        # Count feedback entries by day
        if 'date' in feedback_df:
            feedback_df['date'] = pd.to_datetime(feedback_df['date'])
            date_counts = feedback_df.groupby(feedback_df['date'].dt.date).size()
            
            # Find most frequent words
            all_feedback = ' '.join(feedback_df['feedback'].tolist())
            words = all_feedback.lower().split()
            word_counts = pd.Series(words).value_counts().head(20)
            
            # Basic sentiment analysis
            positive_words = ['good', 'great', 'excellent', 'helpful', 'positive', 'thank', 'thanks']
            negative_words = ['issue', 'problem', 'difficult', 'challenging', 'unclear', 'confused']
            
            sentiment_score = 0
            for word in words:
                if word in positive_words:
                    sentiment_score += 1
                elif word in negative_words:
                    sentiment_score -= 1
            
            sentiment = "neutral"
            if sentiment_score > 0:
                sentiment = "positive"
            elif sentiment_score < 0:
                sentiment = "negative"
            
            return {
                "person": person_name,
                "data_points": len(feedback),
                "date_range": f"{feedback_df['date'].min().date()} to {feedback_df['date'].max().date()}",
                "frequency": date_counts.to_dict(),
                "common_themes": word_counts.to_dict(),
                "sentiment": sentiment,
                "sentiment_score": sentiment_score
            }
        
        # Fallback if no date column
        return {
            "person": person_name,
            "data_points": len(feedback),
            "feedback": feedback
        }
    
    def get_feedback_summary(self, person_name: str) -> str:
        """
        Get a human-readable summary of feedback.
        
        Args:
            person_name: Name of the person to get summary for.
            
        Returns:
            str: Feedback summary.
        """
        analysis = self.analyze_feedback_trends(person_name)
        
        if analysis.get('data_points', 0) == 0:
            return f"No feedback found for {person_name} in the recent period."
            
        sentiment = analysis.get('sentiment', 'neutral')
        data_points = analysis.get('data_points', 0)
        
        summary = f"Based on {data_points} feedback entries, the overall feedback for {person_name} has been {sentiment}. "
        
        if sentiment == 'positive':
            summary += "Their colleagues have noted their contributions positively. "
        elif sentiment == 'negative':
            summary += "There may be some areas where improvement could be beneficial. "
        else:
            summary += "The feedback has been balanced. "
            
        return summary
    
    def submit_new_feedback(self, feedback_data: Dict[str, Any]) -> bool:
        """
        Submit new feedback to the database.
        
        Args:
            feedback_data: Feedback data to submit.
            
        Returns:
            bool: True if submission was successful, False otherwise.
        """
        # This would require implementing a method in NotionAdapter
        # to create new feedback entries
        print("Feedback submission not implemented yet")
        return False
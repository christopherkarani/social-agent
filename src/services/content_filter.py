# src/services/content_filter.py
"""
Content filtering and quality control for the Bluesky crypto agent
"""
from typing import List, Dict, Set, Optional, Tuple
from collections import deque
import logging
import re
import hashlib
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from dataclasses import dataclass

from ..models.data_models import GeneratedContent

logger = logging.getLogger(__name__)


@dataclass
class ContentHistoryItem:
    """Item stored in content history with metadata"""
    content: str
    timestamp: datetime
    content_hash: str
    engagement_score: float
    topics: List[str]


class ContentFilter:
    """
    Advanced content filtering, duplicate detection, and quality control system
    """
    
    # Inappropriate content patterns
    INAPPROPRIATE_PATTERNS = [
        r'\b(scam|fraud|ponzi|rug\s*pull)\b',
        r'\b(pump\s*and\s*dump|market\s*manipulation)\b',
        r'\b(guaranteed\s*profit|risk\s*free)\b',
        r'\b(financial\s*advice|investment\s*advice)\b',
        r'\b(hate|racist|sexist|offensive)\b'
    ]
    
    # Quality indicators
    QUALITY_INDICATORS = {
        'positive': [
            r'\b(analysis|insight|research|data|trend)\b',
            r'\b(development|innovation|technology|adoption)\b',
            r'\b(community|ecosystem|partnership|collaboration)\b'
        ],
        'negative': [
            r'\b(moon|lambo|diamond\s*hands|hodl)\b',
            r'\b(to\s*the\s*moon|when\s*moon)\b',
            r'[!]{3,}',  # Excessive exclamation marks
            r'[🚀]{2,}',  # Excessive rocket emojis
        ]
    }
    
    def __init__(self, 
                 history_size: int = 100, 
                 duplicate_threshold: float = 0.75,
                 quality_threshold: float = 0.6,
                 retention_hours: int = 168):  # 7 days default
        """
        Initialize ContentFilter with configurable parameters
        
        Args:
            history_size: Maximum number of items to keep in history
            duplicate_threshold: Similarity threshold for duplicate detection (0.0-1.0)
            quality_threshold: Minimum quality score for content approval (0.0-1.0)
            retention_hours: Hours to retain content in history
        """
        self.recent_posts = deque(maxlen=history_size)
        self.duplicate_threshold = duplicate_threshold
        self.quality_threshold = quality_threshold
        self.retention_hours = retention_hours
        self.content_hashes: Set[str] = set()
        
        # Compile regex patterns for performance
        self._inappropriate_patterns = [re.compile(pattern, re.IGNORECASE) 
                                      for pattern in self.INAPPROPRIATE_PATTERNS]
        self._positive_patterns = [re.compile(pattern, re.IGNORECASE) 
                                 for pattern in self.QUALITY_INDICATORS['positive']]
        self._negative_patterns = [re.compile(pattern, re.IGNORECASE) 
                                 for pattern in self.QUALITY_INDICATORS['negative']]
        
        logger.info(f"ContentFilter initialized with history_size={history_size}, "
                   f"duplicate_threshold={duplicate_threshold}, "
                   f"quality_threshold={quality_threshold}")
    
    def filter_content(self, content: GeneratedContent) -> Tuple[bool, Dict[str, any]]:
        """
        Comprehensive content filtering with detailed results
        
        Args:
            content: GeneratedContent object to filter
            
        Returns:
            Tuple of (approved: bool, details: dict)
        """
        details = {
            'timestamp': datetime.now(),
            'content_length': len(content.text),
            'checks_performed': [],
            'scores': {},
            'reasons': []
        }
        
        # Clean up old content first
        self._cleanup_old_content()
        
        # 1. Duplicate detection
        is_duplicate, similarity_score = self._check_duplicates(content.text)
        details['checks_performed'].append('duplicate_detection')
        details['scores']['similarity'] = similarity_score
        
        if is_duplicate:
            details['reasons'].append(f'Duplicate content detected (similarity: {similarity_score:.2f})')
            logger.info(f"Content rejected: {details['reasons'][-1]}")
            return False, details
        
        # 2. Quality scoring
        quality_score = self._calculate_quality_score(content.text)
        details['checks_performed'].append('quality_scoring')
        details['scores']['quality'] = quality_score
        
        if quality_score < self.quality_threshold:
            details['reasons'].append(f'Quality score too low: {quality_score:.2f} < {self.quality_threshold}')
            logger.info(f"Content rejected: {details['reasons'][-1]}")
            return False, details
        
        # 3. Content moderation
        is_appropriate, moderation_details = self._moderate_content(content.text)
        details['checks_performed'].append('content_moderation')
        details['moderation'] = moderation_details
        
        if not is_appropriate:
            details['reasons'].append('Content failed moderation checks')
            logger.warning(f"Content rejected: {details['reasons'][-1]}")
            return False, details
        
        # 4. Length and format validation
        format_valid, format_issues = self._validate_format(content)
        details['checks_performed'].append('format_validation')
        details['format_issues'] = format_issues
        
        if not format_valid:
            details['reasons'].extend(format_issues)
            logger.info(f"Content rejected: Format issues - {format_issues}")
            return False, details
        
        # All checks passed
        details['reasons'].append('All quality checks passed')
        logger.info(f"Content approved with quality score: {quality_score:.2f}")
        return True, details
    
    def add_to_history(self, content: GeneratedContent):
        """
        Add content to history with metadata
        
        Args:
            content: GeneratedContent object to add to history
        """
        content_hash = self._generate_content_hash(content.text)
        
        history_item = ContentHistoryItem(
            content=content.text,
            timestamp=datetime.now(),
            content_hash=content_hash,
            engagement_score=content.engagement_score,
            topics=content.source_news.topics
        )
        
        self.recent_posts.append(history_item)
        self.content_hashes.add(content_hash)
        
        logger.debug(f"Added content to history. Total items: {len(self.recent_posts)}")
    
    def get_history_stats(self) -> Dict[str, any]:
        """Get statistics about content history"""
        if not self.recent_posts:
            return {'total_items': 0, 'avg_quality': 0.0, 'topics': []}
        
        total_items = len(self.recent_posts)
        avg_engagement = sum(item.engagement_score for item in self.recent_posts) / total_items
        
        # Count topics
        topic_counts = {}
        for item in self.recent_posts:
            for topic in item.topics:
                topic_counts[topic] = topic_counts.get(topic, 0) + 1
        
        return {
            'total_items': total_items,
            'avg_engagement_score': round(avg_engagement, 2),
            'top_topics': sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:5],
            'oldest_item_age_hours': (datetime.now() - self.recent_posts[0].timestamp).total_seconds() / 3600
        }
    
    def _check_duplicates(self, content: str) -> Tuple[bool, float]:
        """
        Advanced duplicate detection using multiple similarity algorithms
        
        Returns:
            Tuple of (is_duplicate: bool, max_similarity: float)
        """
        if not self.recent_posts:
            return False, 0.0
        
        content_hash = self._generate_content_hash(content)
        
        # Fast hash-based exact duplicate check
        if content_hash in self.content_hashes:
            return True, 1.0
        
        max_similarity = 0.0
        
        for item in self.recent_posts:
            # Sequence-based similarity
            seq_similarity = SequenceMatcher(None, content.lower(), item.content.lower()).ratio()
            
            # Word-based similarity (Jaccard similarity)
            word_similarity = self._calculate_word_similarity(content, item.content)
            
            # Combined similarity score (weighted average)
            combined_similarity = (seq_similarity * 0.7) + (word_similarity * 0.3)
            
            max_similarity = max(max_similarity, combined_similarity)
            
            if combined_similarity > self.duplicate_threshold:
                return True, combined_similarity
        
        return False, max_similarity
    
    def _calculate_quality_score(self, content: str) -> float:
        """
        Calculate content quality score based on multiple factors
        
        Returns:
            Quality score between 0.0 and 1.0
        """
        score = 0.5  # Base score
        
        # Length factor (optimal length around 100-200 chars)
        length = len(content)
        if 80 <= length <= 250:
            score += 0.1
        elif length < 50 or length > 280:
            score -= 0.1
        
        # Positive quality indicators
        positive_matches = sum(1 for pattern in self._positive_patterns 
                             if pattern.search(content))
        score += min(positive_matches * 0.1, 0.3)
        
        # Negative quality indicators
        negative_matches = sum(1 for pattern in self._negative_patterns 
                             if pattern.search(content))
        score -= min(negative_matches * 0.15, 0.4)
        
        # Hashtag balance (2-4 hashtags is optimal)
        hashtag_count = content.count('#')
        if 2 <= hashtag_count <= 4:
            score += 0.1
        elif hashtag_count > 6:
            score -= 0.2
        
        # Emoji balance (1-3 emojis is good)
        emoji_count = len(re.findall(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]', content))
        if 1 <= emoji_count <= 3:
            score += 0.05
        elif emoji_count > 5:
            score -= 0.1
        
        # Readability (avoid excessive caps)
        caps_ratio = sum(1 for c in content if c.isupper()) / len(content) if content else 0
        if caps_ratio > 0.3:
            score -= 0.2
        
        return max(0.0, min(1.0, score))
    
    def _moderate_content(self, content: str) -> Tuple[bool, Dict[str, any]]:
        """
        Content moderation to check for inappropriate content
        
        Returns:
            Tuple of (is_appropriate: bool, details: dict)
        """
        details = {
            'inappropriate_patterns_found': [],
            'severity': 'none'
        }
        
        for i, pattern in enumerate(self._inappropriate_patterns):
            matches = pattern.findall(content)
            if matches:
                details['inappropriate_patterns_found'].append({
                    'pattern_index': i,
                    'matches': matches,
                    'pattern_description': self.INAPPROPRIATE_PATTERNS[i]
                })
        
        if details['inappropriate_patterns_found']:
            details['severity'] = 'high' if len(details['inappropriate_patterns_found']) > 2 else 'medium'
            return False, details
        
        return True, details
    
    def _validate_format(self, content: GeneratedContent) -> Tuple[bool, List[str]]:
        """
        Validate content format and structure
        
        Returns:
            Tuple of (is_valid: bool, issues: List[str])
        """
        issues = []
        
        # Character limit check
        if len(content.text) > 300:
            issues.append(f"Content exceeds 300 character limit: {len(content.text)} chars")
        
        # Minimum length check
        if len(content.text.strip()) < 30:
            issues.append(f"Content too short: {len(content.text.strip())} chars")
        
        # Hashtag validation
        if len(content.hashtags) > 6:
            issues.append(f"Too many hashtags: {len(content.hashtags)}")
        
        # Check for malformed hashtags
        for hashtag in content.hashtags:
            if not hashtag.startswith('#') or len(hashtag) < 2:
                issues.append(f"Malformed hashtag: {hashtag}")
        
        # Engagement score validation
        if not (0.0 <= content.engagement_score <= 1.0):
            issues.append(f"Invalid engagement score: {content.engagement_score}")
        
        return len(issues) == 0, issues
    
    def _cleanup_old_content(self):
        """Remove content older than retention period"""
        cutoff_time = datetime.now() - timedelta(hours=self.retention_hours)
        
        # Remove old items from the front of the deque
        while self.recent_posts and self.recent_posts[0].timestamp < cutoff_time:
            old_item = self.recent_posts.popleft()
            self.content_hashes.discard(old_item.content_hash)
            logger.debug(f"Removed old content from history: {old_item.timestamp}")
    
    def _generate_content_hash(self, content: str) -> str:
        """Generate hash for content deduplication"""
        # Normalize content for hashing (remove extra spaces, convert to lowercase)
        normalized = re.sub(r'\s+', ' ', content.lower().strip())
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def _calculate_word_similarity(self, text1: str, text2: str) -> float:
        """Calculate Jaccard similarity between word sets"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
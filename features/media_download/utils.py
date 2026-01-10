
class MediaUrlValidator:
    """Helper class for validating media URLs."""
    
    @staticmethod
    def is_valid_url(text: str) -> bool:
        """
        Check if the text is a valid URL for media download.
        
        Args:
            text: The text to check.
            
        Returns:
            True if text appears to be a valid URL, False otherwise.
        """
        if not text:
            return False
            
        text = text.strip()
        
        # Basic URL check
        if not (text.startswith("http://") or text.startswith("https://")):
            return False
            
        # Optional: Add specific domain checks if needed in future
        # for domain in ["youtube.com", "youtu.be", "bilibili.com", ...]:
        #     if domain in text: return True
            
        return True

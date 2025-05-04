class UIElement:
    """
    Class representing a UI element on screen.
    
    Attributes:
        name: Element name
        reference_paths: List of paths to reference images
        region: Screen region (x, y, width, height)
        confidence: Confidence threshold for recognition
    """
    
    def __init__(self, name, reference_paths=None, region=None, confidence=0.7):
        """
        Initialize a UI element.
        
        Args:
            name: Element name
            reference_paths: List of paths to reference images
            region: Screen region (x, y, width, height) or None for full screen
            confidence: Confidence threshold for recognition
        """
        self.name = name
        self.reference_paths = reference_paths or []
        self.region = region
        self.confidence = confidence
    
    def __str__(self):
        """String representation of the UI element."""
        return f"UIElement(name={self.name}, region={self.region}, confidence={self.confidence})"
    
    def __repr__(self):
        """Detailed representation of the UI element."""
        return f"UIElement(name='{self.name}', reference_paths={self.reference_paths}, region={self.region}, confidence={self.confidence})"
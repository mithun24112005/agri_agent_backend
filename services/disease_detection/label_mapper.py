class LabelMapper:
    """
    Normalizes the human-readable labels returned by the Hugging Face model
    into structured Crop and Disease components.
    
    Expected crops: Apple, Maize/Corn, Grape, Orange, Cherry, Blueberry, Peach, Bell Pepper, Potato, Raspberry, Soybean, Squash, Strawberry, Tomato.
    Supported by existing agent logic natively (ideal crops): Apple, Maize/Corn, Grape, Orange.
    """
    
    SUPPORTED_CROPS = {"Apple", "Maize/Corn", "Grape", "Orange"}
    
    @classmethod
    def parse_label(cls, label: str) -> dict:
        """
        Parses a HF label like 'Apple Scab', 'Apple with Black Rot', 'Healthy Apple', 'Tomato with Spider Mites or Two-spotted Spider Mite'
        into a dict containing `crop`, `disease`, `is_healthy`.
        """
        is_healthy = "Healthy" in label
        
        # 1. Determine Crop
        crop = "Unknown"
        if "Apple" in label:
            crop = "Apple"
        elif "Corn" in label or "Maize" in label:
            crop = "Maize/Corn"
        elif "Grape" in label:
            crop = "Grape"
        elif "Orange" in label or "Citrus" in label:
            crop = "Orange"
        elif "Cherry" in label:
            crop = "Cherry"
        elif "Blueberry" in label:
            crop = "Blueberry"
        elif "Peach" in label:
            crop = "Peach"
        elif "Bell Pepper" in label:
            crop = "Bell Pepper"
        elif "Potato" in label:
            crop = "Potato"
        elif "Raspberry" in label:
            crop = "Raspberry"
        elif "Soybean" in label:
            crop = "Soybean"
        elif "Squash" in label:
            crop = "Squash"
        elif "Strawberry" in label:
            crop = "Strawberry"
        elif "Tomato" in label:
            crop = "Tomato"
            
        # 2. Determine Disease string (normalized for the RAG matcher)
        if is_healthy:
            disease = "healthy"
        else:
            # E.g. 'Apple with Black Rot' -> 'Black Rot'
            # 'Apple Scab' -> 'Scab' or 'Apple Scab' (we can just keep the whole label or remove crop prefix)
            if " with " in label:
                disease = label.split(" with ", 1)[1]
            else:
                disease = label # Fallback, e.g. 'Apple Scab' -> 'Apple Scab', 'Tomato Yellow Leaf Curl Virus'
                
        is_supported = crop in cls.SUPPORTED_CROPS
        
        return {
            "crop": crop,
            "disease": disease,
            "is_healthy": is_healthy,
            "is_supported_crop": is_supported
        }

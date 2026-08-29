import asyncio
from graph.state import DiseaseState
from agents.disease.graph import decision_node, mapper_node
from services.disease_detection.detector import DiseaseDetector
from services.disease_detection.schemas import DiseaseDetectionResult, TopPrediction
from unittest.mock import AsyncMock

async def test_integration():
    print("Testing integration...")
    
    # Mock detector to simulate HF API response without hitting real API
    # Since we verified HF API manually in Phase 0, we just want to test graph flow
    
    class MockDetector(DiseaseDetector):
        async def predict(self, image_input):
            return DiseaseDetectionResult(
                crop="Apple",
                disease="Apple Scab",
                raw_label="Apple Scab",
                confidence=0.98,
                is_confident=True,
                is_supported_crop=True,
                is_healthy=False,
                top_predictions=[TopPrediction(label="Apple Scab", confidence=0.98)]
            )
            
    # Swap out real detector with mock
    import services.disease_detection.detector
    services.disease_detection.detector.predict = MockDetector().predict
    
    from agents.disease.graph import detector
    detector.predict = MockDetector().predict
    
    state = DiseaseState(image_path="dummy.jpg", question="What disease is this?", prediction=None)
    
    # 1. Run decision node
    print("1. Running decision_node")
    decision_result = await decision_node(state)
    print("Decision result:", decision_result)
    
    state.update(decision_result)
    
    # 2. Run mapper node
    print("2. Running mapper_node")
    mapper_result = mapper_node(state)
    print("Mapper result:", mapper_result)
    
    assert mapper_result["disease_id"] == "apple_scab", f"Expected apple_scab, got {mapper_result['disease_id']}"
    assert mapper_result["crop"] == "apple", f"Expected apple, got {mapper_result['crop']}"
    print("Integration test passed!")

if __name__ == "__main__":
    asyncio.run(test_integration())

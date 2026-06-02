import pytest
from app.anomaly.detector import AnomalyDetector

def test_anomaly_detector_warmup():
    detector = AnomalyDetector(contamination=0.05)
    # Sending less than 20 points should always return False (warmup phase)
    for i in range(10):
        is_anomaly = detector.add_data_point(50.0, 50.0, 0.1)
        assert not is_anomaly

def test_anomaly_detector_detects_spike():
    detector = AnomalyDetector(contamination=0.05)
    
    # Warmup with 20 completely normal points
    for i in range(20):
        detector.add_data_point(30.0, 40.0, 0.05)
        
    # Send a massive spike
    is_anomaly = detector.add_data_point(100.0, 99.0, 0.99)
    # It should detect it as an outlier
    assert is_anomaly

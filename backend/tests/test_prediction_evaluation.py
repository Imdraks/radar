from datetime import datetime, timedelta
from types import SimpleNamespace
from app.intelligence.prediction_service import ArtistPredictionService


def test_evaluation_does_not_train_on_target(monkeypatch):
    service = ArtistPredictionService(None)
    rows = [SimpleNamespace(snapshot_date=datetime(2026,1,1)+timedelta(days=30*i), spotify_monthly_listeners=value) for i,value in enumerate([100,100,1000])]
    monkeypatch.setattr(service, '_get_snapshots', lambda *args, **kwargs: list(reversed(rows)))
    training_seen = []
    def predict(name, training):
        training_seen.append([r.spotify_monthly_listeners for r in training])
        return SimpleNamespace(is_valid=True, central=SimpleNamespace(growth_rate=0))
    monkeypatch.setattr(service, '_predict_from_snapshots', predict)
    result = service.evaluate_history('Artist', 1)
    assert result['sample_count'] == 1
    assert result['mae_listeners'] == 900
    assert training_seen == [[100,100]]
    assert result['calibrated_probability'] is False


def test_insufficient_history_has_no_invented_accuracy(monkeypatch):
    service = ArtistPredictionService(None)
    monkeypatch.setattr(service, '_get_snapshots', lambda *args, **kwargs: [])
    result = service.evaluate_history('Artist', 1)
    assert result['status'] == 'insufficient_history'
    assert result['mae_listeners'] is None

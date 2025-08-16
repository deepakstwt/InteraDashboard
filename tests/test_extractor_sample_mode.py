from datetime import datetime, timedelta


def test_sample_extraction_mode(monkeypatch, extractor):
    monkeypatch.setenv('USE_LIVE_VAHAN', '0')
    end = datetime.now().strftime('%Y-%m-%d')
    start = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
    data = extractor.extract_all_data(start, end)
    assert 'state_wise' in data and 'manufacturer_wise' in data and 'category_trends' in data
    assert len(data['state_wise']) > 0

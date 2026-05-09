from unittest.mock import MagicMock, patch

import numpy as np

from app.ml.backend_sklearn import predict_sklearn_tfidf


@patch("app.ml.backend_sklearn.joblib.load")
@patch("app.ml.backend_sklearn.hf_hub_download")
def test_predict_sklearn_tfidf_hf_dual(mock_dl: MagicMock, mock_jload: MagicMock):
    mock_dl.side_effect = ["/fake/clf.joblib", "/fake/vec.joblib"]

    vectorizer = MagicMock()
    clf = MagicMock()
    clf.predict.return_value = np.array(["positive"])
    clf.predict_proba.return_value = np.array([[0.15, 0.85]])

    mock_jload.side_effect = [clf, vectorizer]

    out = predict_sklearn_tfidf(
        "DineshKumar1329/Sentiment_Analysis", "Nice product!"
    )

    assert out["label"] == "positive"
    assert out["score"] == 0.85
    assert out["backend"] == "sklearn_tfidf_hf"
    assert out["hf_model_ref"] == "DineshKumar1329/Sentiment_Analysis"
    vectorizer.transform.assert_called_once_with(["nice product!"])
    assert mock_dl.call_count == 2


def test_local_joblib_path_still_requires_file(tmp_path):
    p = tmp_path / "missing.joblib"
    try:
        predict_sklearn_tfidf(str(p), "x")
    except FileNotFoundError as e:
        assert "нет файла" in str(e)
    else:
        raise AssertionError("expected FileNotFoundError")

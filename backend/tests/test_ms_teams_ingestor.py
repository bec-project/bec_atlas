from unittest import mock

import pytest
from bec_lib import messages

from bec_atlas.ingestor.ms_teams_ingestor import MSTeamsIngestor


@pytest.fixture
def teams_ingestor(backend):
    _, app = backend
    return MSTeamsIngestor(config=app.config["teams"])


def test_send_feedback_to_chat(teams_ingestor):
    msg = messages.FeedbackMessage(feedback="This is a test feedback message.", rating=4)

    with mock.patch.object(teams_ingestor, "session") as mock_session:
        mock_post = mock_session.post
        mock_post.return_value.status_code = 200
        teams_ingestor.send_feedback_to_chat(msg)
        assert mock_post.called
        args, kwargs = mock_post.call_args
        assert args[0] == teams_ingestor.feedback_webhook_url
        assert "json" in kwargs
        assert "content" in kwargs["json"]
        assert "This is a test feedback message." in kwargs["json"]["content"]

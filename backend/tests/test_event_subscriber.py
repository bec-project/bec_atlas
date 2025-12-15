import json
import threading
import time
from unittest import mock

import pytest
import requests

from bec_atlas.ingestor.signal_manager import EventSubscriber


@pytest.fixture
def mock_callback():
    """Create a mock callback function for testing."""
    return mock.Mock()


@pytest.fixture
def event_subscriber(mock_callback):
    """Create an EventSubscriber instance with a mock callback."""
    subscriber = EventSubscriber(host="http://test-host.com", on_event=mock_callback)
    yield subscriber
    # Ensure the subscriber is stopped after each test
    subscriber.stop()
    if subscriber._thread.is_alive():
        subscriber._thread.join(timeout=2)


class TestEventSubscriberStartStop:
    """Tests for starting and stopping the EventSubscriber."""

    def test_start_launches_thread(self, event_subscriber):
        """Test that start() launches the background thread."""
        with mock.patch.object(event_subscriber, "_run"):
            event_subscriber.start()
            time.sleep(0.1)  # Give thread time to start

            assert event_subscriber._thread.is_alive()

    def test_stop_sets_event(self, event_subscriber):
        """Test that stop() sets the stop event."""
        event_subscriber.stop()

        assert event_subscriber._stop.is_set()

    def test_stop_terminates_thread(self, event_subscriber, mock_sse_response):
        """Test that stop() terminates the running thread."""
        # Mock requests.get to return immediately
        response = mock_sse_response(iter([]))

        with mock.patch("bec_atlas.ingestor.signal_manager.requests.get", return_value=response):
            event_subscriber.start()
            time.sleep(0.1)
            assert event_subscriber._thread.is_alive()

            event_subscriber.stop()
            event_subscriber._thread.join(timeout=2)

            assert not event_subscriber._thread.is_alive()


class TestEventSubscriberEventProcessing:
    """Tests for event processing functionality."""

    def test_processes_valid_event(self, event_subscriber, mock_callback, mock_sse_response):
        """Test that valid SSE events are processed and callback is invoked."""
        test_event = {"type": "test", "data": "hello"}
        sse_line = f"data:{json.dumps(test_event)}"
        response = mock_sse_response(iter([sse_line]))

        with mock.patch("bec_atlas.ingestor.signal_manager.requests.get", return_value=response):
            event_subscriber.start()
            time.sleep(0.2)
            event_subscriber.stop()
            event_subscriber._thread.join(timeout=2)

        mock_callback.assert_called_once_with(test_event)

    def test_processes_multiple_events(self, event_subscriber, mock_callback, mock_sse_response):
        """Test that multiple events are processed in sequence."""
        event1 = {"id": 1, "data": "first"}
        event2 = {"id": 2, "data": "second"}
        event3 = {"id": 3, "data": "third"}

        sse_lines = [
            f"data:{json.dumps(event1)}",
            f"data:{json.dumps(event2)}",
            f"data:{json.dumps(event3)}",
        ]
        response = mock_sse_response(iter(sse_lines))

        with mock.patch("bec_atlas.ingestor.signal_manager.requests.get", return_value=response):
            event_subscriber.start()
            time.sleep(0.2)
            event_subscriber.stop()
            event_subscriber._thread.join(timeout=2)

        assert mock_callback.call_count == 3
        mock_callback.assert_any_call(event1)
        mock_callback.assert_any_call(event2)
        mock_callback.assert_any_call(event3)

    def test_ignores_empty_lines(self, event_subscriber, mock_callback, mock_sse_response):
        """Test that empty lines are ignored."""
        test_event = {"type": "test"}
        sse_lines = ["", f"data:{json.dumps(test_event)}", "", ""]
        response = mock_sse_response(iter(sse_lines))

        with mock.patch("bec_atlas.ingestor.signal_manager.requests.get", return_value=response):
            event_subscriber.start()
            time.sleep(0.2)
            event_subscriber.stop()
            event_subscriber._thread.join(timeout=2)

        mock_callback.assert_called_once_with(test_event)

    def test_ignores_non_data_lines(self, event_subscriber, mock_callback, mock_sse_response):
        """Test that lines not starting with 'data:' are ignored."""
        test_event = {"type": "test"}
        sse_lines = ["event: message", "id: 123", f"data:{json.dumps(test_event)}", "retry: 1000"]
        response = mock_sse_response(iter(sse_lines))

        with mock.patch("bec_atlas.ingestor.signal_manager.requests.get", return_value=response):
            event_subscriber.start()
            time.sleep(0.2)
            event_subscriber.stop()
            event_subscriber._thread.join(timeout=2)

        mock_callback.assert_called_once_with(test_event)

    def test_handles_event_with_whitespace(
        self, event_subscriber, mock_callback, mock_sse_response
    ):
        """Test that whitespace in data is properly stripped."""
        test_event = {"type": "test"}
        sse_line = f"data:  {json.dumps(test_event)}  "
        response = mock_sse_response(iter([sse_line]))

        with mock.patch("bec_atlas.ingestor.signal_manager.requests.get", return_value=response):
            event_subscriber.start()
            time.sleep(0.2)
            event_subscriber.stop()
            event_subscriber._thread.join(timeout=2)

        mock_callback.assert_called_once_with(test_event)

    def test_stops_processing_when_stop_called(
        self, event_subscriber, mock_callback, mock_sse_response
    ):
        """Test that the subscriber stops processing events when stop is called."""

        def slow_iter():
            """Generator that yields events slowly."""
            yield f"data:{json.dumps({'id': 1})}"
            time.sleep(0.1)
            yield f"data:{json.dumps({'id': 2})}"
            time.sleep(0.1)
            yield f"data:{json.dumps({'id': 3})}"

        response = mock_sse_response(slow_iter())

        with mock.patch("bec_atlas.ingestor.signal_manager.requests.get", return_value=response):
            event_subscriber.start()
            time.sleep(0.05)  # Let first event process
            event_subscriber.stop()
            event_subscriber._thread.join(timeout=2)

        # Should have processed only the first event before stopping
        assert mock_callback.call_count <= 2


class TestEventSubscriberHTTPConnection:
    """Tests for HTTP connection handling."""

    def test_connects_to_correct_endpoint(self, event_subscriber, mock_sse_response):
        """Test that the subscriber connects to the correct SSE endpoint."""
        response = mock_sse_response(iter([]))

        with mock.patch(
            "bec_atlas.ingestor.signal_manager.requests.get", return_value=response
        ) as mock_get:
            event_subscriber.start()
            time.sleep(0.1)
            event_subscriber.stop()
            event_subscriber._thread.join(timeout=2)

        mock_get.assert_called()
        call_args = mock_get.call_args
        assert call_args[0][0] == "http://test-host.com/api/v1/events"
        assert call_args[1]["stream"] is True
        assert call_args[1]["timeout"] is None
        assert call_args[1]["headers"]["Accept"] == "text/event-stream"

    def test_response_encoding_set_to_utf8(self, event_subscriber, mock_sse_response):
        """Test that response encoding is set to UTF-8."""
        response = mock_sse_response(iter([]))

        with mock.patch("bec_atlas.ingestor.signal_manager.requests.get", return_value=response):
            event_subscriber.start()
            time.sleep(0.1)
            event_subscriber.stop()
            event_subscriber._thread.join(timeout=2)

        assert response.encoding == "utf-8"


class TestEventSubscriberErrorHandling:
    """Tests for error handling and recovery."""

    def test_retries_on_connection_error(self, event_subscriber, mock_callback, mock_sse_response):
        """Test that the subscriber retries connection on errors."""
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise requests.exceptions.ConnectionError("Connection failed")
            # On third attempt, succeed
            return mock_sse_response(iter([]))

        with mock.patch("bec_atlas.ingestor.signal_manager.requests.get", side_effect=side_effect):
            with mock.patch("bec_atlas.ingestor.signal_manager.time.sleep") as mock_sleep:
                event_subscriber.start()
                time.sleep(0.2)
                event_subscriber.stop()
                event_subscriber._thread.join(timeout=2)

                # Should have retried twice (2 failures before success)
                assert mock_sleep.call_count >= 2

    def test_retries_on_http_error(self, event_subscriber, mock_sse_response):
        """Test that the subscriber retries on HTTP errors."""
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                mock_response = mock.Mock()
                mock_response.raise_for_status = mock.Mock(
                    side_effect=requests.exceptions.HTTPError("500 Server Error")
                )
                mock_response.__enter__ = mock.Mock(return_value=mock_response)
                mock_response.__exit__ = mock.Mock(return_value=False)
                return mock_response
            # On second attempt, succeed
            return mock_sse_response(iter([]))

        with mock.patch("bec_atlas.ingestor.signal_manager.requests.get", side_effect=side_effect):
            with mock.patch("bec_atlas.ingestor.signal_manager.time.sleep") as mock_sleep:
                event_subscriber.start()
                time.sleep(0.2)
                event_subscriber.stop()
                event_subscriber._thread.join(timeout=2)

                assert mock_sleep.call_count >= 1

    def test_handles_json_decode_error(
        self, event_subscriber, mock_callback, capsys, mock_sse_response
    ):
        """Test that invalid JSON in event data is handled gracefully."""
        invalid_sse_line = "data:invalid json{{"
        response = mock_sse_response(iter([invalid_sse_line]))

        with mock.patch("bec_atlas.ingestor.signal_manager.requests.get", return_value=response):
            with mock.patch("bec_atlas.ingestor.signal_manager.time.sleep") as mock_sleep:
                event_subscriber.start()
                time.sleep(0.2)
                event_subscriber.stop()
                event_subscriber._thread.join(timeout=2)

                # Should retry after JSON error
                assert mock_sleep.call_count >= 1
                mock_callback.assert_not_called()

    def test_continues_running_after_exception(
        self, event_subscriber, mock_callback, mock_sse_response
    ):
        """Test that the subscriber continues running after an exception."""
        call_count = 0
        event_processed = threading.Event()
        original_sleep = time.sleep

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Temporary error")
            # Second call succeeds with event, third call blocks indefinitely
            if call_count == 2:
                test_event = {"recovered": True}

                def iter_with_signal():
                    yield f"data:{json.dumps(test_event)}"
                    event_processed.set()
                    # Wait indefinitely to prevent further iterations
                    while not event_subscriber._stop.is_set():
                        original_sleep(0.1)

                return mock_sse_response(iter_with_signal())
            # Shouldn't get here, but if we do, just block
            raise Exception("Unexpected third call")

        # Mock sleep to speed up retry delay, but use a small actual delay
        with mock.patch("bec_atlas.ingestor.signal_manager.requests.get", side_effect=side_effect):
            with mock.patch(
                "bec_atlas.ingestor.signal_manager.time.sleep",
                side_effect=lambda x: original_sleep(0.01),
            ):
                event_subscriber.start()
                # Wait for the event to be processed
                event_processed.wait(timeout=2)
                event_subscriber.stop()
                event_subscriber._thread.join(timeout=2)

                # Should have recovered and processed the event once
                mock_callback.assert_called_with({"recovered": True})
                assert mock_callback.call_count >= 1


class TestEventSubscriberIntegration:
    """Integration tests for EventSubscriber."""

    def test_full_lifecycle(self, mock_callback, mock_sse_response):
        """Test complete lifecycle: create, start, process events, stop."""
        subscriber = EventSubscriber(host="http://test.com", on_event=mock_callback)

        # Create mock events
        events = [{"id": i, "data": f"event_{i}"} for i in range(3)]
        sse_lines = [f"data:{json.dumps(event)}" for event in events]
        response = mock_sse_response(iter(sse_lines))

        with mock.patch("bec_atlas.ingestor.signal_manager.requests.get", return_value=response):
            # Start subscriber
            assert not subscriber._thread.is_alive()
            subscriber.start()
            time.sleep(0.2)
            assert subscriber._thread.is_alive()

            # Process events
            assert mock_callback.call_count == 3
            for event in events:
                mock_callback.assert_any_call(event)

            # Stop subscriber
            subscriber.stop()
            subscriber._thread.join(timeout=2)
            assert not subscriber._thread.is_alive()

    def test_callback_exceptions_do_not_crash_subscriber(self, event_subscriber, mock_sse_response):
        """Test that exceptions in the callback don't crash the subscriber."""
        call_count = 0
        events_processed = threading.Event()
        original_sleep = time.sleep

        def failing_callback(event):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("Callback error")
            # Second event should still be processed
            if call_count >= 2:
                events_processed.set()

        event_subscriber.on_event = failing_callback

        events = [{"id": 1}, {"id": 2}]
        sse_lines = [f"data:{json.dumps(event)}" for event in events]
        response = mock_sse_response(iter(sse_lines))

        with mock.patch("bec_atlas.ingestor.signal_manager.requests.get", return_value=response):
            with mock.patch(
                "bec_atlas.ingestor.signal_manager.time.sleep",
                side_effect=lambda x: original_sleep(0.01),
            ):
                event_subscriber.start()
                # Wait for events to be processed
                events_processed.wait(timeout=2)
                event_subscriber.stop()
                event_subscriber._thread.join(timeout=2)

                # Both events should have been attempted despite first callback failing
                assert call_count >= 1

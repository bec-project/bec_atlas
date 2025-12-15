from bec_atlas.ingestor.signal_manager import SignalEventMessage


def test_signal_message_with_image_attachment():
    msg = {
        "envelope": {
            "source": "+41123456",
            "sourceNumber": "+41123456",
            "sourceUuid": "e8b2ead6-5ea7-46e9-a4a3-a66f93c1c402",
            "sourceName": "Test User",
            "sourceDevice": 1,
            "timestamp": 1769609483860,
            "serverReceivedTimestamp": 1769609485902,
            "serverDeliveredTimestamp": 1769609485903,
            "dataMessage": {
                "timestamp": 1769609483860,
                "message": None,
                "expiresInSeconds": 0,
                "isExpirationUpdate": False,
                "viewOnce": False,
                "attachments": [
                    {
                        "contentType": "image/jpeg",
                        "filename": "signal-2026-01-28-151123.jpeg",
                        "id": "zYUcWigEWOSjYRrQ4Ii1.jpeg",
                        "size": 160895,
                        "width": 1152,
                        "height": 2048,
                        "caption": None,
                        "uploadTimestamp": 1769609484247,
                    }
                ],
            },
        },
        "account": "+41123456",
    }
    signal_msg = SignalEventMessage(**msg)
    assert signal_msg.envelope.source == "+41123456"


def test_signal_message_with_quote():
    msg = {
        "envelope": {
            "source": "+411123456",
            "sourceNumber": "+411123456",
            "sourceUuid": "e8b2ead6-5ea7-46e9-a4a3-a66f93c1c402",
            "sourceName": "Test user",
            "sourceDevice": 1,
            "timestamp": 1769611441620,
            "serverReceivedTimestamp": 1769611443080,
            "serverDeliveredTimestamp": 1769611443082,
            "dataMessage": {
                "timestamp": 1769611441620,
                "message": "Quote",
                "expiresInSeconds": 0,
                "isExpirationUpdate": False,
                "viewOnce": False,
                "quote": {
                    "id": 1769610753495,
                    "author": "+411123456",
                    "authorNumber": "+411123456",
                    "authorUuid": "e8b2ead6-5ea7-46e9-a4a3-a66f93c1c402",
                    "text": "Forschungsstrasse\n5303 WÃ¼renlingen\nSwitzerland\n\nhttps://maps.google.com/maps?q=47.53780386372539%2C8.228827665817196",
                    "attachments": [
                        {
                            "contentType": "image/jpeg",
                            "filename": "signal-2026-01-28-153233.jpeg",
                            "thumbnail": {
                                "contentType": "image/jpeg",
                                "filename": "signal-2026-01-28-153233.jpeg",
                                "id": "yPm24k3c2qi6US1Vliyi.jpeg",
                                "size": 57440,
                                "width": 600,
                                "height": 600,
                                "caption": None,
                                "uploadTimestamp": 1769611441855,
                            },
                        }
                    ],
                },
            },
        },
        "account": "+411123456",
    }
    signal_msg = SignalEventMessage(**msg)
    assert signal_msg.envelope.source == "+411123456"


def test_signal_typing_message():
    msg = {
        "envelope": {
            "source": "+411123456",
            "sourceNumber": "+411123456",
            "sourceUuid": "e8b2ead6-5ea7-46e9-a4a3-a66f93c1c402",
            "sourceName": "Test user",
            "sourceDevice": 1,
            "timestamp": 1769601645905,
            "serverReceivedTimestamp": 1769601646032,
            "serverDeliveredTimestamp": 1769601646033,
            "typingMessage": {"action": "STARTED", "timestamp": 1769601645905},
        },
        "account": "+411123456",
    }
    signal_msg = SignalEventMessage(**msg)
    assert signal_msg.envelope.source == "+411123456"

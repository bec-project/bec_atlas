from __future__ import annotations

from datetime import datetime

import requests
from bec_lib import messages


class MSTeamsIngestor:
    def __init__(self, config: dict):
        """
        Initialize the MSTeamsIngestor with the given configuration.

        Args:
            config (dict): The configuration dictionary containing the Teams webhook URL.
        """
        self.session = requests.Session()
        self.feedback_webhook_url = config.get("feedback_webhook_url", "")

    def send_card(self, adaptive_card_content: dict, webhook_url: str) -> None:
        """
        Sends any Adaptive Card to Teams via webhook.

        Args:
            adaptive_card_content (dict): The content of the Adaptive Card to send.
            webhook_url (str): The Teams incoming webhook URL to send the card to.
        """

        payload = {
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": adaptive_card_content,
                }
            ]
        }

        response = self.session.post(webhook_url, json=payload, timeout=5)

        if response.status_code >= 400:
            raise RuntimeError(f"Teams webhook failed: {response.status_code} - {response.text}")

    def _build_header_section(
        self, feedback_type: str, color_header: str, color_divider: str
    ) -> str:
        """
        Build the header section of the feedback HTML.

        Args:
            feedback_type (str): The type of feedback.
            color_header (str): The color to use for the header text.
            color_divider (str): The color to use for the horizontal divider.

        Returns:
            str: The HTML string for the header section.
        """
        # Format feedback type: "general_feedback" -> "General Feedback"
        formatted_type = feedback_type.replace("_", " ").title()
        return f"""
<h2 style="color: {color_header}; margin-bottom: 5px;">BEC User Feedback: {formatted_type}</h2>
<hr style="border: none; border-top: 1px solid {color_divider}; margin-bottom: 15px;">
"""

    def _build_user_info_section(
        self, message: messages.FeedbackMessage, formatted_timestamp: str
    ) -> str:
        """
        Build the user info section of the feedback HTML.

        Args:
            message (messages.FeedbackMessage): The feedback message containing user information.
            formatted_timestamp (str): The formatted timestamp of the feedback.

        Returns:
            str: The HTML string for the user info section.
        """
        return f"""
<table style="border-collapse: collapse; width: 100%;">
    <tr>
    <td style="padding: 6px 0; width: 140px;"><strong>Beamline:</strong></td>
    <td>{message.realm_id}</td>
    </tr>
    <tr>
    <td style="padding: 6px 0;"><strong>Experiment:</strong></td>
    <td>{message.experiment_id}</td>
    </tr>
    <tr>
    <td style="padding: 6px 0;"><strong>User:</strong></td>
    <td>{message.username}</td>
    </tr>
    <tr>
    <td style="padding: 6px 0;"><strong>Timestamp:</strong></td>
    <td>{formatted_timestamp}</td>
    </tr>
</table>
"""

    def _build_environment_section(
        self, message: messages.FeedbackMessage, color_divider: str
    ) -> str:
        """
        Build the environment section of the feedback HTML.

        Args:
            message (messages.FeedbackMessage): The feedback message containing version information.
            color_divider (str): The color to use for the horizontal divider.

        Returns:
            str: The HTML string for the environment section.

        """
        versions_list = [
            f"<li><strong>BEC Version:</strong> {message.versions.bec_lib}</li>",
            f"<li><strong>Widgets Version:</strong> {message.versions.bec_widgets}</li>",
            f"<li><strong>Ophyd Devices Version:</strong> {message.versions.ophyd_devices}</li>",
        ]

        versions_html = "\n    ".join(versions_list)

        return f"""
<hr style="border: none; border-top: 1px solid {color_divider}; margin: 15px 0;">

<h3 style="margin-bottom: 5px;">Environment</h3>
<ul style="margin-top: 5px;">
    {versions_html}
</ul>
"""

    def _build_rating_section(
        self, rating: int, stars: str, color_star: str, color_text: str
    ) -> str:
        """
        Build the user rating section of the feedback HTML.

        Args:
            rating (int): The numeric rating provided by the user.
            stars (str): A string of star characters representing the rating visually.
            color_star (str): The color to use for the star characters.
            color_text (str): The color to use for the rating text.

        Returns:
            str: The HTML string for the rating section.
        """
        return f"""
<h3 style="margin-bottom: 5px;">User Rating</h3>
<p style="font-size: 20px; color: {color_star}; margin: 5px 0;">
    {stars}
    <span style="font-size: 14px; color: {color_text};">({rating} / 5)</span>
</p>
"""

    def _build_comments_section(self, feedback: str) -> str:
        """
        Build the comments section of the feedback HTML.

        Args:
            feedback (str): The user feedback comments.

        Returns:
            str: The HTML string for the comments section.
        """
        comment_text = feedback.strip()
        return f"""
<h3 style="margin-bottom: 5px;">Comments</h3>
<div style="
    padding: 10px;
    border-radius: 6px;
    white-space: pre-wrap;">
    {comment_text}
</div>
"""

    def send_feedback_to_chat(self, message: messages.FeedbackMessage) -> None:
        """
        Send a formatted feedback message to Teams chat using the incoming webhook.

        Args:
            message (messages.FeedbackMessage): The feedback message containing user feedback details.
        """

        # Color definitions - adjust these to change theme globally
        color_header = "#0078d4"  # Header text (Teams blue)
        color_divider_primary = "#ddd"  # Primary horizontal dividers
        color_divider_secondary = "#eee"  # Secondary horizontal dividers
        color_star_rating = "#f9a825"  # Star rating color (golden)
        color_rating_text = "#555"  # Rating number text

        # Generate star rating visual
        filled_stars = "★" * int(message.rating)
        empty_stars = "☆" * (5 - int(message.rating))
        stars = filled_stars + empty_stars

        # Format timestamp as readable datetime
        timestamp_dt = datetime.fromtimestamp(message.timestamp)
        formatted_timestamp = timestamp_dt.strftime("%Y-%m-%d %H:%M:%S")

        # Build HTML content from modular sections
        html_content = f"""
<div style="font-family: Arial, sans-serif; font-size: 14px;">
{self._build_header_section(message.feedback_type, color_header, color_divider_primary)}
{self._build_user_info_section(message, formatted_timestamp)}
{self._build_environment_section(message, color_divider_secondary)}
{self._build_rating_section(message.rating, stars, color_star_rating, color_rating_text)}
{self._build_comments_section(message.feedback)}
</div>
"""

        payload = {"content": html_content}

        response = self.session.post(self.feedback_webhook_url, json=payload, timeout=5)

        if response.status_code >= 400:
            raise RuntimeError(f"Teams webhook failed: {response.status_code} - {response.text}")


if __name__ == "__main__":  # pragma: no cover
    from bec_atlas.utils.env_loader import load_env

    env_config = load_env()
    teams_webhook = MSTeamsIngestor(env_config["teams"])
    feedback = messages.FeedbackMessage(
        realm_id="Test Beamline",
        experiment_id="Exp123",
        username="test_user",
        feedback_type="general_feedback",
        feedback="This is a test feedback message.",
        rating=4,
    )
    # teams_webhook.emit_feedback_card(feedback)
    teams_webhook.send_feedback_to_chat(feedback)

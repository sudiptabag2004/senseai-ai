from typing import Dict, List
import aiohttp
from api.settings import settings


async def send_slack_notification(message: Dict, webhook_url: str):
    async with aiohttp.ClientSession() as session:
        async with session.post(webhook_url, json=message) as response:
            if response.status >= 400:
                response_text = await response.text()
                print(
                    f"Failed to send Slack notification: {response.status} - {response_text}"
                )


async def send_slack_notification_for_new_user(user: Dict):
    """
    Send Slack notification when a new user is created.

    Args:
        user: Dictionary containing user information
    """
    # Check if Slack webhook URL is configured
    if not settings.slack_user_signup_webhook_url:
        return

    message = {"text": f"User created: {user['email']} UserId: {user['id']}"}

    # Send notification asynchronously
    await send_slack_notification(message, settings.slack_user_signup_webhook_url)


async def send_slack_notification_for_learner_added_to_cohort(
    user_invited: Dict,
    org_slug: str,
    org_id: int,
    cohort_name: str,
    cohort_id: int,
):
    # Check if Slack webhook URL is configured
    if not settings.slack_user_signup_webhook_url:
        return

    message = {
        "text": f"Learner added to cohort: {user_invited['email']} UserId: {user_invited['id']}\n"
        f"School: {org_slug} (SchoolId: {org_id})\n"
        f"Cohort: {cohort_name} (CohortId: {cohort_id})"
    }

    # Send notification asynchronously
    await send_slack_notification(message, settings.slack_user_signup_webhook_url)


async def send_slack_notification_for_member_added_to_org(
    user_added: Dict,
    org_slug: str,
    org_id: int,
):
    # Check if Slack webhook URL is configured
    if not settings.slack_user_signup_webhook_url:
        return

    message = {
        "text": f"User added as admin: {user_added['email']} UserId: {user_added['id']}\n"
        f"School: {org_slug} (SchoolId: {org_id})"
    }

    # Send notification asynchronously
    await send_slack_notification(message, settings.slack_user_signup_webhook_url)


async def send_slack_notification_for_new_org(
    org_slug: str,
    org_id: int,
    created_by: Dict,
):
    # Check if Slack webhook URL is configured
    if not settings.slack_user_signup_webhook_url:
        return

    message = {
        "text": f"New school created: {org_slug} (SchoolId: {org_id})\n"
        f"Created by: {created_by['email']} (UserId: {created_by['id']})"
    }

    # Send notification asynchronously
    await send_slack_notification(message, settings.slack_user_signup_webhook_url)


async def send_slack_notification_for_new_course(
    course_name: str,
    course_id: int,
    org_slug: str,
    org_id: int,
):
    # Check if Slack webhook URL is configured
    if not settings.slack_course_created_webhook_url:
        return

    message = {
        "text": f"New course created: {course_name} (CourseId: {course_id})\n"
        f"School: {org_slug} (SchoolId: {org_id})"
    }

    # Send notification asynchronously
    await send_slack_notification(message, settings.slack_course_created_webhook_url)


async def send_slack_notification_for_usage_stats(
    last_day_stats: List[Dict],
    current_month_stats: List[Dict],
    current_year_stats: List[Dict],
):
    """
    Send Slack notification with usage statistics for different time periods.

    Args:
        last_day_stats: Usage stats for the last day
        current_month_stats: Usage stats for the current month
        current_year_stats: Usage stats for the current year
    """
    # Check if Slack webhook URL is configured
    if not settings.slack_usage_stats_webhook_url:
        return

    def format_stats(stats: List[Dict], period: str) -> str:
        if not stats:
            return f"📊 *{period}*: No usage data"

        total_messages = sum(org["user_message_count"] for org in stats)
        top_orgs = stats[:5]  # Show top 5 organizations

        # Use different emojis for different time periods
        emoji_map = {
            "Last 24 Hours": "⚡",
            "Last 30 Days": "📈",
            "Last 12 Months": "📊",
        }
        emoji = emoji_map.get(period, "📊")
        formatted = f"{emoji} *{period}* (Total: {total_messages:,} messages):\n"
        formatted += "```\n"  # Start code block for table formatting
        formatted += f"{'Organization':<50} {'Messages':>10}\n"
        formatted += f"{'-' * 50} {'-' * 10}\n"

        for org in top_orgs:
            org_name = (
                org["org_name"][:28] + ".."
                if len(org["org_name"]) > 30
                else org["org_name"]
            )
            formatted += f"{org_name:<50} {org['user_message_count']:>10,}\n"

        if len(stats) > 5:
            remaining_count = len(stats) - 5
            remaining_messages = sum(org["user_message_count"] for org in stats[5:])
            formatted += (
                f"{f'+{remaining_count} more orgs':<50} {remaining_messages:>10,}\n"
            )

        formatted += "```\n"  # End code block
        return formatted

    # Format the message
    message_text = "🚀 *Usage Summary*\n\n"
    message_text += format_stats(last_day_stats, "Last 24 Hours") + "\n"
    message_text += format_stats(current_month_stats, "This Month") + "\n"
    message_text += format_stats(current_year_stats, "This Year")

    message = {"text": message_text}

    # Send notification asynchronously
    await send_slack_notification(message, settings.slack_usage_stats_webhook_url)

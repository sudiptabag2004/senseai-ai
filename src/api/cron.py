from api.db import get_usage_summary_by_organization
from api.slack import send_slack_notification_for_usage_stats


async def send_usage_summary_stats():
    """
    Get usage summary statistics for different time periods and send them via Slack webhook.

    This function retrieves usage statistics for the last day, last month, and last year,
    then sends a formatted summary to a Slack channel via webhook.
    """
    try:
        # Get usage statistics for different time periods
        last_day_stats = await get_usage_summary_by_organization("last_day")
        current_month_stats = await get_usage_summary_by_organization("current_month")
        current_year_stats = await get_usage_summary_by_organization("current_year")

        # Send the statistics via Slack webhook
        await send_slack_notification_for_usage_stats(
            last_day_stats, current_month_stats, current_year_stats
        )

    except Exception as e:
        print(f"Error in get_usage_summary_stats: {e}")
        raise

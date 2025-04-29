from typing import Dict
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

import requests
import os
from typing import List, Dict
from datetime import datetime


def get_user_by_id(user_id: int) -> Dict:
    """Get user details by ID"""
    response = requests.get(f"{os.getenv('BACKEND_URL')}/users/{user_id}")
    if response.status_code != 200:
        raise Exception("Failed to get user")
    return response.json()


def update_user(
    user_id: int,
    first_name: str,
    middle_name: str,
    last_name: str,
    default_dp_color: str,
) -> Dict:
    """Update user details"""
    response = requests.put(
        f"{os.getenv('BACKEND_URL')}/users/{user_id}",
        params={
            "first_name": first_name,
            "middle_name": middle_name,
            "last_name": last_name,
            "default_dp_color": default_dp_color,
        },
    )
    if response.status_code != 200:
        raise Exception("Failed to update user")
    return response.json()


def get_user_cohorts(user_id: int) -> List[Dict]:
    """Get all cohorts for a user"""
    response = requests.get(f"{os.getenv('BACKEND_URL')}/users/{user_id}/cohorts")
    if response.status_code != 200:
        raise Exception("Failed to get user cohorts")
    return response.json()


def get_user_streak(user_id: int, cohort_id: int) -> List[str]:
    """Get current streak for a user"""
    response = requests.get(
        f"{os.getenv('BACKEND_URL')}/users/{user_id}/streak",
        params={"cohort_id": cohort_id},
    )
    if response.status_code != 200:
        raise Exception("Failed to get user streak")

    streak_days = response.json()

    if not streak_days:
        return streak_days

    for index, day in enumerate(streak_days):
        streak_days[index] = datetime.strptime(day, "%Y-%m-%d").date()

    return streak_days


def get_user_activity_for_year(user_id: int, year: int) -> Dict:
    """Get user activity data for a specific year"""
    response = requests.get(
        f"{os.getenv('BACKEND_URL')}/users/{user_id}/activity/{year}"
    )
    if response.status_code != 200:
        raise Exception("Failed to get user activity for year")
    return response.json()


def get_user_active_in_last_n_days(user_id: int, n: int, cohort_id: int) -> List[str]:
    """Get dates when user was active in last n days"""
    response = requests.get(
        f"{os.getenv('BACKEND_URL')}/users/{user_id}/active_days",
        params={"days": n, "cohort_id": cohort_id},
    )
    if response.status_code != 200:
        raise Exception("Failed to get user active days")

    active_days = response.json()

    if not active_days:
        return active_days

    for index, day in enumerate(active_days):
        active_days[index] = datetime.strptime(day, "%Y-%m-%d")

    return active_days


def is_user_in_cohort(user_id: int, cohort_id: int) -> bool:
    """Check if user is in a cohort"""
    response = requests.get(
        f"{os.getenv('BACKEND_URL')}/users/{user_id}/cohort/{cohort_id}/present"
    )
    if response.status_code != 200:
        raise Exception("Failed to check if user is in cohort")

    return response.json()


def get_user_courses(user_id: int) -> List[Dict]:
    """
    Get all courses for a user, including:
    - Courses where user is a learner or mentor
    - All courses from organizations where user is admin or owner
    """
    response = requests.get(f"{os.getenv('BACKEND_URL')}/users/{user_id}/courses")
    if response.status_code != 200:
        raise Exception("Failed to get user courses")

    return response.json()

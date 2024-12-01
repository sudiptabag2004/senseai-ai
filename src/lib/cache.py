from typing import List, Union, Dict
from lib.db import get_cohorts_for_course, get_courses_for_cohort


def clear_course_cache_for_cohorts(cohorts: Union[List[int], List[Dict]]):
    for cohort in cohorts:
        if isinstance(cohort, dict):
            cohort_id = cohort["id"]
        else:
            cohort_id = cohort

        get_courses_for_cohort.clear(cohort_id)


def clear_cohort_cache_for_courses(courses: Union[List[int], List[Dict]]):
    for course in courses:
        if isinstance(course, dict):
            course_id = course["id"]
        else:
            course_id = course

        get_cohorts_for_course.clear(course_id)

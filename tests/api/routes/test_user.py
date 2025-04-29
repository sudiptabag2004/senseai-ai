import pytest
from fastapi import status


# Test for the get_user_by_id endpoint
@pytest.mark.asyncio
async def test_get_user_by_id_endpoints(client, mock_db):
    """
    Test all scenarios for the get_user_by_id endpoint
    """
    # Test scenario 1: User exists
    user_id = 1
    expected_user = {
        "id": user_id,
        "first_name": "Test",
        "last_name": "User",
        "email": "test@example.com",
    }
    mock_db["get_user"].return_value = expected_user

    response = client.get(f"/users/{user_id}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == expected_user
    mock_db["get_user"].assert_called_with(user_id)

    # Test scenario 2: User does not exist
    nonexistent_user_id = 999
    mock_db["get_user"].reset_mock()
    mock_db["get_user"].return_value = None

    response = client.get(f"/users/{nonexistent_user_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "User not found"}
    mock_db["get_user"].assert_called_with(nonexistent_user_id)


# Test for the update_user endpoint
@pytest.mark.asyncio
async def test_update_user_endpoint(client, mock_db):
    """
    Test all scenarios for the update_user endpoint
    """
    # Test scenario 1: Successful update
    user_id = 1
    updated_user = {
        "id": user_id,
        "first_name": "Updated",
        "middle_name": "Test",
        "last_name": "User",
        "default_dp_color": "blue",
    }
    mock_db["update_user"].return_value = updated_user

    response = client.put(
        f"/users/{user_id}?first_name=Updated&middle_name=Test&last_name=User&default_dp_color=blue"
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == updated_user
    mock_db["update_user"].assert_called_with(
        mock_db["cursor"], user_id, "Updated", "Test", "User", "blue"
    )

    # Test scenario 2: User not found during update
    nonexistent_user_id = 999
    mock_db["update_user"].reset_mock()
    mock_db["update_user"].return_value = None

    response = client.put(
        f"/users/{nonexistent_user_id}?first_name=Updated&middle_name=Test&last_name=User&default_dp_color=blue"
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "User not found"}
    mock_db["update_user"].assert_called_with(
        mock_db["cursor"], nonexistent_user_id, "Updated", "Test", "User", "blue"
    )


# Test for the get_user_cohorts endpoint
@pytest.mark.asyncio
async def test_get_user_cohorts_endpoint(client, mock_db):
    """
    Test all scenarios for the get_user_cohorts endpoint
    """
    # Test scenario 1: User has cohorts
    user_id = 1
    expected_cohorts = [{"id": 1, "name": "Cohort 1"}, {"id": 2, "name": "Cohort 2"}]
    mock_db["get_cohorts"].return_value = expected_cohorts

    response = client.get(f"/users/{user_id}/cohorts")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == expected_cohorts
    mock_db["get_cohorts"].assert_called_with(user_id)

    # Test scenario 2: User has no cohorts
    user_id_no_cohorts = 2
    mock_db["get_cohorts"].reset_mock()
    mock_db["get_cohorts"].return_value = []

    response = client.get(f"/users/{user_id_no_cohorts}/cohorts")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []
    mock_db["get_cohorts"].assert_called_with(user_id_no_cohorts)


# Test for the is_user_present_in_cohort endpoint
@pytest.mark.asyncio
async def test_is_user_in_cohort_endpoint(client, mock_db):
    """
    Test all scenarios for the is_user_present_in_cohort endpoint
    """
    # Test scenario 1: User is in cohort
    user_id = 1
    cohort_id = 1
    mock_db["is_user_in_cohort"].return_value = True

    response = client.get(f"/users/{user_id}/cohort/{cohort_id}/present")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() is True
    mock_db["is_user_in_cohort"].assert_called_with(user_id, cohort_id)

    # Test scenario 2: User is not in cohort
    user_id = 1
    cohort_id = 2
    mock_db["is_user_in_cohort"].reset_mock()
    mock_db["is_user_in_cohort"].return_value = False

    response = client.get(f"/users/{user_id}/cohort/{cohort_id}/present")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() is False
    mock_db["is_user_in_cohort"].assert_called_with(user_id, cohort_id)


# Test for the get_user_streak endpoint
@pytest.mark.asyncio
async def test_get_user_streak_endpoint(client, mock_db):
    """
    Test all scenarios for the get_user_streak endpoint
    """
    # Test scenario 1: User has streak and active days
    user_id = 1
    cohort_id = 1
    streak_days = ["2023-04-01", "2023-04-02", "2023-04-03"]
    active_days = ["2023-04-01", "2023-04-02", "2023-04-03"]

    mock_db["get_streak"].return_value = streak_days
    mock_db["get_active_days"].return_value = active_days

    response = client.get(f"/users/{user_id}/streak?cohort_id={cohort_id}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "streak_count": len(streak_days),
        "active_days": active_days,
    }
    mock_db["get_streak"].assert_called_with(user_id, cohort_id)
    mock_db["get_active_days"].assert_called_with(user_id, 3, cohort_id)

    # Test scenario 2: User has no streak
    mock_db["get_streak"].reset_mock()
    mock_db["get_active_days"].reset_mock()
    mock_db["get_streak"].return_value = []
    mock_db["get_active_days"].return_value = []

    response = client.get(f"/users/{user_id}/streak?cohort_id={cohort_id}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"streak_count": 0, "active_days": []}
    mock_db["get_streak"].assert_called_with(user_id, cohort_id)
    mock_db["get_active_days"].assert_called_with(user_id, 3, cohort_id)

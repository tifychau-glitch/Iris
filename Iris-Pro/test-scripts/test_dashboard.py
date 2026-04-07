#!/usr/bin/env python3
"""
IRIS Pro -- Test Dashboard Functionality
Tests project creation, status tracking, and activity logging.
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from test_setup import (
    print_header, print_section, print_success, print_error, print_info,
    reset_test_databases, create_test_project, get_projects_db, get_project
)


def test_dashboard():
    """Test dashboard and project management."""

    print_header("IRIS PRO - DASHBOARD TEST")

    # Initialize test database
    print_section("Initialize Dashboard DB")
    try:
        reset_test_databases()
        print_success("Dashboard test database ready")
    except Exception as e:
        print_error(f"Failed to initialize: {e}")
        return False

    # Test 1: Create projects
    print_section("Test 1: Create Projects")
    projects_data = [
        {
            "name": "Launch IRIS Pro",
            "description": "Get the accountability platform in front of users",
            "status": "in_progress"
        },
        {
            "name": "Iris-Core Integration",
            "description": "Seamless upgrade path from Iris-Core to Iris-Pro",
            "status": "not_started"
        },
        {
            "name": "Calendar System",
            "description": "Implement controlled calendar for time management",
            "status": "in_progress"
        }
    ]

    created_projects = []
    try:
        for proj in projects_data:
            project_id = create_test_project(
                name=proj["name"],
                description=proj["description"],
                status=proj["status"]
            )
            created_projects.append(project_id)
            print_success(f"Created: {proj['name']} (ID: {project_id}, Status: {proj['status']})")

    except Exception as e:
        print_error(f"Failed to create projects: {e}")
        return False

    # Test 2: Log activity
    print_section("Test 2: Activity Logging")
    try:
        conn = get_projects_db()
        now = datetime.now().isoformat()

        activities = [
            "Set up test environment",
            "Initialized dashbord databases",
            "Created test projects"
        ]

        for project_id in created_projects[:1]:  # Log to first project
            for activity in activities:
                conn.execute(
                    """INSERT INTO activity (project_id, message, created_at)
                       VALUES (?, ?, ?)""",
                    (project_id, activity, now)
                )
                print_info(f"Logged: {activity}")

        conn.commit()
        conn.close()
        print_success("Activity log entries created")

    except Exception as e:
        print_error(f"Failed to log activity: {e}")
        return False

    # Test 3: Create tasks within projects
    print_section("Test 3: Create Tasks")
    try:
        conn = get_projects_db()
        now = datetime.now().isoformat()

        tasks = [
            ("Research user feedback", True),
            ("Fix critical bugs", False),
            ("Implement new feature", False)
        ]

        for project_id in created_projects[:1]:
            for task_title, completed in tasks:
                conn.execute(
                    """INSERT INTO tasks (project_id, title, done, created_at, completed_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (project_id, task_title, 1 if completed else 0, now, now if completed else None)
                )
                status = "✓ Done" if completed else "○ Pending"
                print_info(f"Task: {task_title} [{status}]")

        conn.commit()
        conn.close()
        print_success(f"Created {len(tasks)} tasks")

    except Exception as e:
        print_error(f"Failed to create tasks: {e}")
        return False

    # Test 4: Verify project retrieval
    print_section("Test 4: Retrieve and Verify Projects")
    try:
        for project_id in created_projects:
            project = get_project(project_id)
            if project:
                print_success(f"Retrieved: {project['name']}")
                print_info(f"  Status: {project['status']}")
                print_info(f"  Created: {project['created_at'][:10]}")
            else:
                print_error(f"Project {project_id} not found")
                return False

    except Exception as e:
        print_error(f"Failed to retrieve projects: {e}")
        return False

    # Test 5: Test status transitions
    print_section("Test 5: Status Transitions")
    try:
        conn = get_projects_db()

        status_transitions = [
            ("idea", "not_started"),
            ("not_started", "in_progress"),
            ("in_progress", "done")
        ]

        test_project_id = created_projects[0]
        now = datetime.now().isoformat()

        for from_status, to_status in status_transitions:
            conn.execute(
                "UPDATE projects SET status = ?, updated_at = ? WHERE id = ?",
                (to_status, now, test_project_id)
            )
            print_success(f"Status transition: {from_status} → {to_status}")

        conn.commit()
        conn.close()

    except Exception as e:
        print_error(f"Failed to transition status: {e}")
        return False

    # Test 6: Final verification
    print_section("Test 6: Dashboard Statistics")
    try:
        conn = get_projects_db()

        # Count projects by status
        cursor = conn.execute("SELECT status, COUNT(*) as count FROM projects GROUP BY status")
        statuses = cursor.fetchall()

        print_info("Projects by status:")
        for row in statuses:
            print_info(f"  {row['status']}: {row['count']}")

        # Count tasks
        cursor = conn.execute("SELECT COUNT(*) as count FROM tasks")
        task_count = cursor.fetchone()['count']
        print_info(f"Total tasks: {task_count}")

        # Count activities
        cursor = conn.execute("SELECT COUNT(*) as count FROM activity")
        activity_count = cursor.fetchone()['count']
        print_info(f"Total activities: {activity_count}")

        conn.close()
        print_success("Dashboard statistics generated")

    except Exception as e:
        print_error(f"Failed to generate statistics: {e}")
        return False

    print_header("✓ DASHBOARD TEST PASSED")
    return True


if __name__ == "__main__":
    success = test_dashboard()
    sys.exit(0 if success else 1)

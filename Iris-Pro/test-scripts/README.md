# IRIS Pro - Test Scripts

Complete test infrastructure for the IRIS Pro accountability platform. Test individual pieces or run the full user journey.

## Quick Start

All commands run from the `Iris-Pro` directory:

```bash
cd /Users/tiffanychau/Downloads/IRIS/Iris-Pro
```

Then pick a test and copy-paste the command.

---

## Available Tests

### 1. Onboarding Test
Tests user account creation, business configuration, and initial setup.

**What it tests:**
- User account creation
- Business details capture
- Initial commitment setup
- Database verification

**Run it:**
```bash
python3 test-scripts/test_onboarding.py
```

**What to look for:**
- ✓ User account created
- ✓ Business details captured
- ✓ Initial commitments created
- ✓ All verified in database

**Typical output:**
```
============================================================
  IRIS PRO - ONBOARDING TEST
============================================================

--- Step 1: Initialize Test Environment ---
✓ Test databases initialized

--- Step 2: Create User Account ---
✓ User created: test-iris-user-001
• Email: tiffanychau@gmail.com
```

---

### 2. Dashboard Test
Tests project creation, status tracking, task management, and activity logging.

**What it tests:**
- Create projects with different statuses
- Log activities and progress
- Create and manage tasks
- Status transitions (idea → not_started → in_progress → done)
- Dashboard statistics

**Run it:**
```bash
python3 test-scripts/test_dashboard.py
```

**What to look for:**
- ✓ Projects created with correct statuses
- ✓ Tasks created for projects
- ✓ Activity logs recorded
- ✓ Status transitions work
- ✓ Statistics calculated

**Typical output:**
```
--- Test 1: Create Projects ---
✓ Created: Launch IRIS Pro (ID: 1, Status: in_progress)
✓ Created: Iris-Core Integration (ID: 2, Status: not_started)

--- Test 2: Activity Logging ---
• Logged: Set up test environment
• Logged: Initialized dashboard databases
```

---

### 3. Accountability Engine Test
Tests daily check-ins, commitment tracking, and accountability workflow.

**What it tests:**
- Create and manage commitments
- Log daily check-in messages
- Track commitment status (pending, in_progress, completed)
- Calculate accountability metrics
- Identify overdue commitments

**Run it:**
```bash
python3 test-scripts/test_accountability.py
```

**What to look for:**
- ✓ Commitments created with due dates
- ✓ Check-in messages logged
- ✓ Status updates work
- ✓ Metrics calculated correctly
- ✓ Overdue items identified

**Typical output:**
```
--- Test 1: Create Commitments ---
✓ Created: Complete Iris-Pro v1 launch (due in 7 days)
✓ Created: Integrate Iris-Core upgrade flow (due in 14 days)

--- Test 5: Accountability Metrics ---
• Commitments by status:
  pending: 3
  in_progress: 1
  completed: 1
```

---

### 4. Cron Jobs Test
Tests scheduled tasks, recurring automation, and cron expression validation.

**What it tests:**
- Schedule daily check-ins
- Schedule weekly reviews
- Schedule progress checks
- Validate cron expressions
- Test retry logic and error handling

**Run it:**
```bash
python3 test-scripts/test_cron_jobs.py
```

**What to look for:**
- ✓ Daily check-in scheduled at 9 AM
- ✓ Weekly review scheduled for Mondays
- ✓ All cron expressions valid
- ✓ Task execution simulated
- ✓ Retry logic configured

**Typical output:**
```
--- Test 1: Daily Check-In Schedule ---
✓ Daily check-in scheduled
  Frequency: Every day at 9:00 AM
  Action: IRIS sends daily accountability check-in

--- Test 5: Verify Scheduled Tasks ---
✓ Daily Check-In
  Schedule: 0 9 * * * (cron)
  Status: active
```

---

### 5. Upgrade Flow Test
Tests complete transition from Iris-Core to Iris-Pro experience.

**What it tests:**
- Mt. Everest goal migration from Core to Pro
- User account creation in Pro
- Feature activation (daily check-ins, calendar, etc.)
- Data continuity verification
- First Pro check-in experience

**Run it:**
```bash
python3 test-scripts/test_upgrade_flow.py
```

**What to look for:**
- ✓ Mt. Everest goal successfully migrated
- ✓ Pro account created
- ✓ All Pro features activated
- ✓ Data preserved from Core
- ✓ First check-in generated

**Typical output:**
```
--- Phase 1: Iris-Core Experience ---
• User completes Mt. Everest excavation:
  1. Defines 3-5 year goal
  2. Identifies why goal matters
  ...

--- Phase 3: Create IRIS Pro Account ---
✓ IRIS Pro account created for: tiffanychau@gmail.com
```

---

### 6. Full Journey Test
Runs all 5 tests in sequence to simulate complete user experience.

**What it tests:**
- Complete onboarding flow
- Full dashboard functionality
- End-to-end accountability
- Cron job scheduling
- Upgrade from Core to Pro

**Run it:**
```bash
python3 test-scripts/test_full_journey.py
```

**What to look for:**
- All 5 tests show ✓
- Summary shows "ALL TESTS PASSED"
- All features working together

**Typical output:**
```
--- Running: Onboarding ---
✓ Onboarding passed

--- Running: Dashboard ---
✓ Dashboard passed

--- Running: Accountability Engine ---
✓ Accountability Engine passed

--- Running: Cron Jobs ---
✓ Cron Jobs passed

--- Running: Upgrade Flow ---
✓ Upgrade Flow passed
```

---

## Test Databases

All tests use separate test databases, so they don't interfere with real data.

- **Test Projects DB:** `data/projects_test.db`
- **Test Accountability DB:** `data/iris_accountability_test.db`
- **Test Tasks DB:** `data/tasks_test.db`
- **Real Projects DB:** `data/projects.db`
- **Real Accountability DB:** `data/iris_accountability.db`
- **Real Tasks DB:** `data/tasks.db`

Tests automatically reset test databases each time they run.

---

## Cron Expression Reference

Used in the Cron Jobs test:

| Expression | Meaning |
|-----------|---------|
| `0 9 * * *` | Every day at 9:00 AM |
| `0 10 * * MON` | Every Monday at 10:00 AM |
| `0 */6 * * *` | Every 6 hours |
| `*/15 * * * *` | Every 15 minutes |

---

## Troubleshooting

**Error: "Test script not found"**
- Make sure you're in the `Iris-Pro` directory
- Check that test-scripts folder exists

**Error: "Database is locked"**
- Another test is running
- Wait a moment and try again
- Or delete the test database files manually

**Test fails with "Exception"**
- Check the full output (last 500 chars shown)
- Run the individual test to see more details

**Need to reset test data:**
```bash
rm -f data/*_test.db
python3 test-scripts/test_onboarding.py  # This will recreate them
```

---

## Quick Reference

| Test | Command | Tests |
|------|---------|-------|
| Onboarding | `python3 test-scripts/test_onboarding.py` | User setup, business config |
| Dashboard | `python3 test-scripts/test_dashboard.py` | Projects, tasks, activities |
| Accountability | `python3 test-scripts/test_accountability.py` | Commitments, check-ins |
| Cron Jobs | `python3 test-scripts/test_cron_jobs.py` | Scheduled tasks, automation |
| Upgrade Flow | `python3 test-scripts/test_upgrade_flow.py` | Core → Pro transition |
| Full Journey | `python3 test-scripts/test_full_journey.py` | Complete user experience |

---

## Workflow

**Recommended testing flow:**

1. **Make a change** to IRIS Pro code
2. **Run specific test** for the feature you changed
   - Onboarding change? → `test_onboarding.py`
   - Dashboard change? → `test_dashboard.py`
   - etc.
3. **If specific test passes**, run full journey:
   ```bash
   python3 test-scripts/test_full_journey.py
   ```
4. **If all tests pass**, you're good to deploy

---

## Integration with Iris-Core

When testing the upgrade flow, make sure:
- Iris-Core test scripts are in `../Iris-Core/test-scripts/`
- You've run `test_bot_conversation.py` to generate a Mt. Everest summary
- The upgrade flow test will import that summary data

---

## Next Steps

Once you're comfortable with individual tests:

1. **Create test clone** (separate Git branch for testing)
2. **Run full journey** before each deployment
3. **Document any failures** and fix issues
4. **Keep tests updated** when adding new features

See main `IRIS-Pro/README.md` for setup and deployment workflow.

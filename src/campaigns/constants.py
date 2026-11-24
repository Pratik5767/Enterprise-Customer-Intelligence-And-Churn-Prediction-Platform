"""
Vocabulary and defaults for retention campaigns. Change values here, not in the logic.
"""

CAMPAIGN_TYPES = [
    "phone_call", "email", "discount_offer", "contract_upgrade", "loyalty_reward", "service_review"
]

CAMPAIGN_TRANSITIONS = {                      # which status may follow which
    "draft": {"active", "cancelled"},
    "active": {"completed", "cancelled"},
    "completed": set(),
    "cancelled": set(),
}

# Activity statuses: pending -> attempted -> contacted | unreachable.  held_out = control group.
OUTREACH_STATUSES = {"pending", "attempted", "contacted"}        # states in which a rep may still log contact
OUTCOMES = ["accepted_offer", "interested", "callback_requested", "declined"]   # result of a conversation
FOLLOW_UP_OUTCOMES = {"interested", "callback_requested"}        # outcomes that need another touch

MAX_ATTEMPTS = 3                  # unsuccessful attempts before a customer is marked unreachable
RETRY_DAYS = 2                    # wait before trying again
FOLLOW_UP_AFTER_CONTACT_DAYS = 7
FOLLOW_UP_DAYS_BY_RANK = {1: 2, 2: 5, 3: 10, 4: 14}              # first-contact deadline by Module 4 priority rank

DEFAULT_HOLDOUT_SHARE = 0.20
DEFAULT_OUTCOME_WINDOW_DAYS = 90

# Evidence-quality thresholds (used for warnings)
MIN_CONTROL_SIZE = 100            # warn if the control group is smaller than this
MIN_OUTCOME_COVERAGE = 0.80       # warn if fewer than 80% of a group's outcomes are known
MAX_COVERAGE_GAP = 0.10           # warn if the two groups' coverage differs by more than 10 points
MAX_SMD = 0.10                    # warn if groups differ at enrolment by more than 0.1 standard deviations
STALE_SCORES_DAYS = 30            # warn if the risk scores are older than this


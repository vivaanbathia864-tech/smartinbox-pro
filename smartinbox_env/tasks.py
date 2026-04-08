# smartinbox_env/tasks.py

STRICT_SCORE_EPSILON = 0.001


TASKS = {
    1: {
        "name": "Basic Email Classification",
        "difficulty": "easy",
        "description": "Classify 5 emails as Spam (0), Normal (1), or Urgent (2)",
        "emails": [
            {
                "id": "e1",
                "subject": "WIN A FREE IPHONE NOW!!!",
                "body": "Congratulations! You have been selected to win a free iPhone. Click here now!",
                "sender": "promo@randomsite.xyz",
                "features": [0.95, 0.05, 0.1, 0.9, 0.05],
                "label": 0,  # Spam
                "label_name": "spam"
            },
            {
                "id": "e2",
                "subject": "Team meeting tomorrow at 10am",
                "body": "Hi, just a reminder we have our weekly sync tomorrow at 10am. Please be on time.",
                "sender": "manager@company.com",
                "features": [0.2, 0.8, 0.4, 0.1, 0.5],
                "label": 1,  # Normal
                "label_name": "normal"
            },
            {
                "id": "e3",
                "subject": "URGENT: Production server is DOWN",
                "body": "Our main production server went offline 5 minutes ago. Customers cannot access the app. Need immediate fix!",
                "sender": "devops@company.com",
                "features": [0.4, 0.9, 0.99, 0.2, 0.95],
                "label": 2,  # Urgent
                "label_name": "urgent"
            },
            {
                "id": "e4",
                "subject": "April Newsletter - Top Reads This Month",
                "body": "Check out our top articles this month. Industry news, tips, and more inside.",
                "sender": "newsletter@techdigest.com",
                "features": [0.15, 0.3, 0.1, 0.5, 0.1],
                "label": 1,  # Normal
                "label_name": "normal"
            },
            {
                "id": "e5",
                "subject": "PAYMENT FAILED - Immediate Action Required",
                "body": "Your subscription payment of $49.99 has failed. Please update your billing details within 24 hours to avoid service interruption.",
                "sender": "billing@saasapp.com",
                "features": [0.5, 0.85, 0.92, 0.4, 0.88],
                "label": 2,  # Urgent
                "label_name": "urgent"
            },
        ]
    },

    2: {
        "name": "Classification + Prioritization",
        "difficulty": "medium",
        "description": "Classify 10 emails AND return them sorted by priority (urgent first, spam last)",
        "emails": [
            {
                "id": "e1",
                "subject": "Database backup failed last night",
                "body": "Automated backup job failed at 2am. No backup exists for today. Investigate immediately.",
                "sender": "alerts@infra.com",
                "features": [0.45, 0.88, 0.96, 0.3, 0.91],
                "label": 2,
                "label_name": "urgent"
            },
            {
                "id": "e2",
                "subject": "You won a $1000 gift card!",
                "body": "Lucky winner! Claim your $1000 Amazon gift card by clicking the link below. Offer expires soon!",
                "sender": "giveaway@fakeprize.net",
                "features": [0.97, 0.02, 0.05, 0.95, 0.02],
                "label": 0,
                "label_name": "spam"
            },
            {
                "id": "e3",
                "subject": "Q1 report is ready for review",
                "body": "Hi team, the Q1 financial report has been uploaded to the shared drive. Please review by Friday.",
                "sender": "finance@company.com",
                "features": [0.1, 0.75, 0.35, 0.05, 0.4],
                "label": 1,
                "label_name": "normal"
            },
            {
                "id": "e4",
                "subject": "Security breach detected on your account",
                "body": "We detected an unauthorized login attempt from an unknown location. Please verify your identity immediately.",
                "sender": "security@company.com",
                "features": [0.3, 0.92, 0.98, 0.15, 0.97],
                "label": 2,
                "label_name": "urgent"
            },
            {
                "id": "e5",
                "subject": "Lunch menu for this week",
                "body": "Hey everyone, attached is the cafeteria lunch menu for this week. Enjoy!",
                "sender": "hr@company.com",
                "features": [0.05, 0.4, 0.05, 0.02, 0.05],
                "label": 1,
                "label_name": "normal"
            },
            {
                "id": "e6",
                "subject": "Cheap meds online no prescription needed",
                "body": "Order any medication without a prescription. Fast shipping worldwide. Best prices guaranteed.",
                "sender": "sales@pharmafraud.biz",
                "features": [0.99, 0.01, 0.02, 0.98, 0.01],
                "label": 0,
                "label_name": "spam"
            },
            {
                "id": "e7",
                "subject": "Client complaint - urgent response needed",
                "body": "Our biggest client called and is extremely upset about the delay. They are threatening to cancel. Please respond today.",
                "sender": "sales@company.com",
                "features": [0.35, 0.91, 0.95, 0.2, 0.93],
                "label": 2,
                "label_name": "urgent"
            },
            {
                "id": "e8",
                "subject": "Office holiday schedule",
                "body": "Please find attached the office holiday schedule for the upcoming months.",
                "sender": "hr@company.com",
                "features": [0.08, 0.5, 0.1, 0.03, 0.08],
                "label": 1,
                "label_name": "normal"
            },
            {
                "id": "e9",
                "subject": "Make $5000 a week from home!",
                "body": "Work from home and earn thousands weekly. No experience needed. Join thousands of happy earners!",
                "sender": "jobs@earnonline.fake",
                "features": [0.96, 0.03, 0.04, 0.97, 0.02],
                "label": 0,
                "label_name": "spam"
            },
            {
                "id": "e10",
                "subject": "Project deadline moved to tomorrow",
                "body": "Hi, just got word from the client. The deadline has been moved up to tomorrow morning. We need to finish tonight.",
                "sender": "pm@company.com",
                "features": [0.2, 0.87, 0.9, 0.1, 0.88],
                "label": 2,
                "label_name": "urgent"
            },
        ]
    },

    3: {
        "name": "Full Inbox Management",
        "difficulty": "hard",
        "description": "Classify 15 emails, prioritize them, AND draft a reply for urgent ones",
        "emails": [
            {
                "id": "e1",
                "subject": "CRITICAL: API rate limit exceeded - service degraded",
                "body": "Our API has exceeded its rate limit. 40% of user requests are failing. Revenue impact is $2000/hour.",
                "sender": "monitoring@company.com",
                "features": [0.3, 0.95, 0.99, 0.1, 0.99],
                "label": 2,
                "label_name": "urgent",
                "expected_reply_keywords": ["acknowledge", "investigating", "fix", "soon", "team", "resolve"]
            },
            {
                "id": "e2",
                "subject": "Cheap designer watches 90% off",
                "body": "Luxury watches for just $20! Limited time offer. Click now before stocks run out.",
                "sender": "deals@fakewatches.ru",
                "features": [0.98, 0.01, 0.01, 0.99, 0.01],
                "label": 0,
                "label_name": "spam",
                "expected_reply_keywords": []
            },
            {
                "id": "e3",
                "subject": "Welcome to the team - onboarding docs",
                "body": "Hi! Welcome aboard. Please find your onboarding documents attached. Let us know if you have questions.",
                "sender": "hr@company.com",
                "features": [0.05, 0.7, 0.2, 0.02, 0.25],
                "label": 1,
                "label_name": "normal",
                "expected_reply_keywords": []
            },
            {
                "id": "e4",
                "subject": "Legal notice: Copyright violation claim",
                "body": "Our legal team has identified a potential copyright violation on your platform. Please respond within 48 hours or we will escalate.",
                "sender": "legal@lawfirm.com",
                "features": [0.2, 0.93, 0.97, 0.08, 0.96],
                "label": 2,
                "label_name": "urgent",
                "expected_reply_keywords": ["acknowledge", "legal", "team", "respond", "review"]
            },
            {
                "id": "e5",
                "subject": "Monthly team newsletter",
                "body": "Here is the monthly team update with project highlights, upcoming events, and birthdays this month.",
                "sender": "comms@company.com",
                "features": [0.1, 0.45, 0.1, 0.05, 0.1],
                "label": 1,
                "label_name": "normal",
                "expected_reply_keywords": []
            },
            {
                "id": "e6",
                "subject": "You have been pre-approved for a $50,000 loan",
                "body": "No credit check needed! Get $50,000 deposited in your account today. Apply in 2 minutes.",
                "sender": "loans@scambank.net",
                "features": [0.99, 0.01, 0.01, 0.99, 0.01],
                "label": 0,
                "label_name": "spam",
                "expected_reply_keywords": []
            },
            {
                "id": "e7",
                "subject": "Key investor requesting urgent call",
                "body": "Our Series A investor wants to schedule an emergency call today. They have concerns about the recent metrics. Please arrange ASAP.",
                "sender": "cfo@company.com",
                "features": [0.25, 0.94, 0.97, 0.1, 0.95],
                "label": 2,
                "label_name": "urgent",
                "expected_reply_keywords": ["schedule", "call", "today", "available", "confirm"]
            },
            {
                "id": "e8",
                "subject": "Software update available",
                "body": "A new update is available for your development tools. Please update at your earliest convenience.",
                "sender": "updates@devtools.com",
                "features": [0.1, 0.55, 0.15, 0.05, 0.15],
                "label": 1,
                "label_name": "normal",
                "expected_reply_keywords": []
            },
            {
                "id": "e9",
                "subject": "Claim your lottery winnings today",
                "body": "You have won $250,000 in our online lottery. Claim within 24 hours by sending your bank details.",
                "sender": "winner@lotteryscam.com",
                "features": [0.97, 0.02, 0.02, 0.98, 0.01],
                "label": 0,
                "label_name": "spam",
                "expected_reply_keywords": []
            },
            {
                "id": "e10",
                "subject": "Employee performance review due Friday",
                "body": "Reminder that performance reviews for your team are due this Friday. Please submit on the HR portal.",
                "sender": "hr@company.com",
                "features": [0.1, 0.65, 0.3, 0.05, 0.35],
                "label": 1,
                "label_name": "normal",
                "expected_reply_keywords": []
            },
            {
                "id": "e11",
                "subject": "URGENT: Data center fire alarm triggered",
                "body": "Fire suppression system triggered in rack 4B. Physical inspection required immediately. All services may go offline.",
                "sender": "facilities@datacenter.com",
                "features": [0.2, 0.97, 0.99, 0.05, 0.99],
                "label": 2,
                "label_name": "urgent",
                "expected_reply_keywords": ["acknowledge", "dispatch", "team", "immediately", "checking"]
            },
            {
                "id": "e12",
                "subject": "Conference room booking confirmation",
                "body": "Your booking for Conference Room B on April 5th at 2pm has been confirmed.",
                "sender": "rooms@company.com",
                "features": [0.05, 0.4, 0.05, 0.02, 0.05],
                "label": 1,
                "label_name": "normal",
                "expected_reply_keywords": []
            },
            {
                "id": "e13",
                "subject": "Hot singles in your area",
                "body": "Find your perfect match today. Thousands of singles waiting to meet you. Sign up free!",
                "sender": "match@datingspam.xyz",
                "features": [0.96, 0.02, 0.02, 0.97, 0.01],
                "label": 0,
                "label_name": "spam",
                "expected_reply_keywords": []
            },
            {
                "id": "e14",
                "subject": "Customer data export request - compliance deadline today",
                "body": "Under GDPR, we must fulfill this customer data export request by end of day today or face regulatory fines.",
                "sender": "compliance@company.com",
                "features": [0.15, 0.94, 0.98, 0.08, 0.97],
                "label": 2,
                "label_name": "urgent",
                "expected_reply_keywords": ["processing", "compliance", "data", "today", "handle"]
            },
            {
                "id": "e15",
                "subject": "Feedback on last week's presentation",
                "body": "Great job on the presentation last week. The client was very impressed. Keep up the good work!",
                "sender": "director@company.com",
                "features": [0.05, 0.6, 0.1, 0.02, 0.1],
                "label": 1,
                "label_name": "normal",
                "expected_reply_keywords": []
            },
        ]
    }
}


def _strict_score(raw_score):
    """Clamp scores into the strict open interval (0, 1)."""
    bounded = min(max(float(raw_score), STRICT_SCORE_EPSILON), 1 - STRICT_SCORE_EPSILON)
    return round(bounded, 3)


def _normalize_submission(predictions, emails):
    """Return labels and an ordering for multi-part task evaluation."""
    if isinstance(predictions, dict):
        labels = list(predictions.get("labels", []))
        order = list(predictions.get("order", []))
    else:
        labels = list(predictions)
        order = []

    if not order:
        severity_rank = {2: 0, 1: 1, 0: 2}
        indexed_predictions = []
        for idx, email in enumerate(emails):
            label = labels[idx] if idx < len(labels) else 1
            indexed_predictions.append((severity_rank.get(label, 1), idx, email["id"]))
        order = [email_id for _, _, email_id in sorted(indexed_predictions)]

    return labels, order


def _classification_score(labels, emails):
    correct = sum(
        1 for i, email in enumerate(emails)
        if i < len(labels) and labels[i] == email["label"]
    )
    return _strict_score(correct / len(emails))


def _priority_order_score(ordered_ids, emails):
    urgent_ids = [e["id"] for e in emails if e["label"] == 2]
    normal_ids = [e["id"] for e in emails if e["label"] == 1]
    spam_ids = [e["id"] for e in emails if e["label"] == 0]

    if not ordered_ids:
        return STRICT_SCORE_EPSILON

    def _positions(ids):
        return [ordered_ids.index(email_id) for email_id in ids if email_id in ordered_ids]

    urgent_positions = _positions(urgent_ids)
    normal_positions = _positions(normal_ids)
    spam_positions = _positions(spam_ids)

    if not urgent_positions or not spam_positions:
        return STRICT_SCORE_EPSILON

    urgent_before_spam = max(urgent_positions) < min(spam_positions)
    normal_between = True
    if normal_positions:
        normal_between = (
            max(urgent_positions) < min(normal_positions) and
            max(normal_positions) < min(spam_positions)
        )

    if urgent_before_spam and normal_between:
        return _strict_score(1 - STRICT_SCORE_EPSILON)
    if urgent_before_spam:
        return _strict_score(0.5)
    return STRICT_SCORE_EPSILON


def grade_task(task_id, predictions, reply_drafts=None):
    """
    Grade agent predictions for a given task.
    Returns a score strictly inside the open interval (0, 1).
    """
    task = TASKS[task_id]
    emails = task["emails"]

    if task_id == 1:
        # Easy: just classification accuracy
        labels, _ = _normalize_submission(predictions, emails)
        return _strict_score(_classification_score(labels, emails))

    elif task_id == 2:
        # Medium: classification (60%) + prioritization order (40%)
        labels, ordered = _normalize_submission(predictions, emails)
        classification_score = _classification_score(labels, emails)
        order_score = _priority_order_score(ordered, emails)
        return _strict_score(0.6 * classification_score + 0.4 * order_score)

    elif task_id == 3:
        # Hard: classification (40%) + prioritization (30%) + reply quality (30%)
        labels, ordered = _normalize_submission(predictions, emails)
        classification_score = _classification_score(labels, emails)
        order_score = _priority_order_score(ordered, emails)

        reply_score = STRICT_SCORE_EPSILON
        if reply_drafts:
            urgent_emails = [e for e in emails if e["label"] == 2]
            scored_replies = 0
            for email in urgent_emails:
                draft = reply_drafts.get(email["id"], "")
                keywords = email.get("expected_reply_keywords", [])
                if keywords:
                    hits = sum(1 for kw in keywords if kw.lower() in draft.lower())
                    reply_score += hits / len(keywords)
                    scored_replies += 1
            if scored_replies > 0:
                reply_score = _strict_score(reply_score / scored_replies)

        return _strict_score(0.4 * classification_score + 0.3 * order_score + 0.3 * reply_score)

    return STRICT_SCORE_EPSILON

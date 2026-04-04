# Story 2.6: User Interview Guide for Pre-Flight Calibration

**Purpose**: Validate that Agent Managers actually need pre-flight voice calibration
**Target Audience**: Agent Managers who have completed the 10-Minute Launch onboarding
**Interview Format**: 30-minute structured interviews (remote or in-person)
**Goal**: Interview 5-10 users to make go/no-go decision on Story 2.6

**Decision Gate**:
- ✅ **PROCEED** if >30% express strong need for calibration
- ❌ **DEFER/RESCOPE** if <30% express need

---

## Interview Logistics

### Scheduling Template

```
Subject: Help us improve AI voice quality (30 min research study)

Hi [Name],

We're planning improvements to the AI voice configuration system and would love your input.

You've been selected because you've completed our onboarding and have real experience using the voice features.

We're looking for 30 minutes of your time to share your experience. Your feedback will directly shape our product roadmap.

[Link to schedule time]

Thanks,
[Product Team]
```

### Screening Questions (Before Interview)

1. Have you completed the 10-Minute Launch onboarding wizard?
2. Have you made at least 3 calls with your AI agent?
3. Are you available for a 30-minute interview this week?

**Only proceed if all 3 are YES.**

---

## Interview Script

### Introduction (2 minutes)

"Thanks for joining! I'm [Name] from the product team.

We're exploring a new feature called 'Pre-Flight Calibration' - a way to test and adjust your AI's voice before making live calls.

Before we invest in building this, we want to understand your real experiences and needs.

This interview is **not** a sales pitch. There are no wrong answers. We want your honest feedback, even if it's 'this feature sounds annoying.'

The interview will take about 25 minutes. I'll record my notes (with your permission).

Do you have any questions before we start?"

### Section 1: Current Experience (8 minutes)

**Goal**: Understand current pain points with voice configuration

**Q1.** Walk me through the last call you made with your AI agent.
- [Follow-up] How did you feel about the voice quality?
- [Follow-up] Did you make any adjustments before or during that call?

**Q2.** Have you ever made a call where the voice sounded wrong, too fast, too slow, or just "off"?
- [If YES] Tell me about that experience. What happened? What was the impact?
- [If NO] That's great! What do you think contributed to consistent voice quality?

**Q3.** How do you currently adjust voice settings, if at all?
- [Follow-up] Is it easy or difficult to find the right settings?
- [Follow-up] How many attempts does it typically take to get the voice "right"?

**Q4.** What's the **cost** of a bad voice configuration?
- [Prompt] Think about: Time wasted, caller experience, redials, frustration
- [Follow-up] How often does this happen? (Daily, weekly, monthly, rarely?)

### Section 2: Testing the Concept (10 minutes)

**Goal**: Validate proposed solution

**Concept Explanation**:
"Imagine a 'Pre-Flight Calibration' step. Before dialing, you could:
- Hear a 10-second test clip of your selected voice
- Adjust sliders for speech speed (0.5x - 2.0x) and stability (0.0 - 1.0)
- Re-play the test clip instantly to hear changes
- Save your configuration once it sounds right

This would add about 1-2 minutes to your pre-call routine."

**Q5.** Initially, how does this sound to you?
- [Prompt] Use a scale: Very Useful / Somewhat Useful / Not Sure / Not Useful / Would Annoy Me

**Q6.** **If positive**: What's the **most valuable** part of this concept?
- [Prompt] Test clip? Sliders? Instant feedback? Saving configs?

**Q6.** **If negative/skeptical**: What concerns do you have?
- [Prompt] Too much friction? Unnecessary? Wrong problem to solve?

**Q7.** Would you actually use this before **every** call, or only in certain scenarios?
- [Follow-up] What scenarios?
- [Follow-up] When would you SKIP it?

**Q8.** What if this was **optional** - how often would you use it?
- [Prompt] Every call? First call with a new agent? When voice sounds off? Never?

### Section 3: Alternative Approaches (5 minutes)

**Goal**: Explore if there's a better solution

**Q9.** What if instead of a calibration step, we:
- [Option A] Provided better default voice settings?
- [Option B] Auto-adjusted based on call performance?
- [Option C] Let you save multiple voice "presets" to choose from?

Which approach sounds MOST valuable, if any?

**Q10.** Is "voice quality before first call" even a problem for you?
- [If NO] What ARE the top 3 problems you face with our voice system?
- [If YES] Rank these: Voice quality / Reliability / Latency / Cost / Other

### Section 4: Closing Questions (5 minutes)

**Q11.** On a scale of 1-10, how much do you need this feature?
- 1 = Don't build it
- 5 = Nice to have
- 10 = Critical for my workflow

**Q12.** If we built this, what would make you **love** it?
- [Prompt] Think of one feature or detail that would delight you

**Q13.** If we built this, what would make you **hate** it?
- [Prompt] Think of one thing that would make this worse than useless

**Q14.** Is there anything else about voice configuration we should know?

**Q15.** Can we follow up with you if we have more questions?

---

## Data Collection Template

### Interview Summary Form

```yaml
interview_id: INTERVIEW-001
date: YYYY-MM-DD
interviewer: [Name]
participant_type: Agent Manager
onboarding_completed: true
calls_made: [Number]
interview_duration_minutes: 30

# Section 1: Current Experience
voice_quality_issues:
  - [Issue description]
  - [Impact description]
adjustment_behavior: [How they currently adjust voice settings]
pain_point_severity: [Low/Medium/High]
frequency_of_issues: [Daily/Weekly/Monthly/Rarely]

# Section 2: Concept Testing
initial_reaction: [Very Useful/Somewhat Useful/Not Sure/Not Useful/Would Annoy]
most_valuable_aspect: [If positive]
concerns: [If negative/skeptical]
usage_scenarios: [When they would use it]
skip_scenarios: [When they would skip it]

# Section 3: Alternatives
preferred_approach: [A/B/C/None]
top_voice_problems:
  1. [Problem 1]
  2. [Problem 2]
  3. [Problem 3]

# Section 4: Closing
need_score: [1-10]
love_feature: [What would make them love it]
hate_feature: [What would make them hate it]
follow_up_permission: [Yes/No]

# Overall Assessment
strong_need: [Yes/No]
would_use_regularly: [Yes/No]
recommends_building: [Yes/No]
key_quote: "[Memorable quote from interview]"
notes: |
  [Additional observations, context, non-verbal cues]
```

---

## Analysis Framework

### Quantitative Metrics

Track these metrics across all interviews:

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Total interviews | 5-10 | ____ | ____ |
| Strong need expressed (score 7-10) | >30% | ____% | ____ |
| Would use regularly | >30% | ____% | ____ |
| Recommends building | >30% | ____% | ____ |
| Initial reaction positive | >50% | ____% | ____ |

**Go/No-Go Decision**:
- ✅ **PROCEED** if all 4 metrics above target
- ⚠️ **CAUTION** if 2-3 metrics above target (add more interviews)
- ❌ **DEFER** if 0-1 metrics above target

### Qualitative Analysis

**Themes to look for**:
1. **Problem Validation**: Do users actually struggle with voice configuration?
2. **Solution Fit**: Does pre-flight calibration address the real problem?
3. **Adoption Friction**: Will users actually do this before every call?
4. **Alternatives**: Is there a better problem to solve?

**Red Flags** 🚩:
- "This sounds annoying" mentioned multiple times
- Users say they'd skip it or it's too much friction
- Voice quality isn't actually a problem
- There's a higher-priority voice issue we should solve instead

**Green Flags** ✅:
- Users get excited about the concept
- Specific stories of voice quality issues
- Clear use cases for when they'd use it
- Suggestions that improve the concept

---

## Deliverables

### After 5-10 Interviews, Produce:

1. **User Interview Summary** (`voice-calibration-user-interviews.md`)
   - Executive summary (1 page)
   - Quantitative findings (metrics table)
   - Qualitative themes (quotes, patterns)
   - Go/no-go recommendation

2. **Product Recommendations** (if proceeding)
   - Feature refinements based on feedback
   - Success metrics updated with user input
   - Implementation priority (if not "drop everything")

3. **Decision Document**
   - Clear recommendation: Build / Defer / Cancel
   - Rationale with data backing
   - Next steps if building
   - Alternative problems to solve if not building

---

## Interview Best Practices

### Do ✅
- Record interviews (with permission) for accurate quoting
- Ask "why?" to dig deeper into responses
- Welcome negative feedback - it saves us from building the wrong thing
- Share findings with product team after each interview
- Stop interviews if you're hearing the same thing repeatedly (saturation)

### Don't ❌
- Lead the witness ("Wouldn't this be amazing?")
- Defend the concept or explain how it works
- Interview people who haven't used the voice features
- Go over 30 minutes without asking permission
- Skip negative respondents - their feedback is most valuable

### During Analysis
- Cluster responses by themes, not by individual
- Look for patterns, not outliers
- Weight feedback by user experience (more calls = more weight)
- Be suspicious of "nice to have" - ask hard follow-ups

---

## Timeline

| Week | Activity | Output |
|------|----------|--------|
| 1 | Schedule interviews, pilot interview script | Refined script |
| 2 | Conduct 5-10 interviews | Interview notes |
| 3 | Analyze data, write summary | User interview summary |
| 3 | Go/no-go decision meeting | Decision document |

**Total**: 3 weeks from kickoff to decision

---

## Related Artifacts

- Story 2.6: `_bmad-output/implementation-artifacts/2-6-pre-flight-calibration-dashboard.md`
- Action Plan: `_bmad-output/implementation-artifacts/2-6-adversarial-review-action-plan.md`
- Competitive Analysis: `_bmad-output/research/voice-calibration-competitive-analysis.md` (to be created)

---

**Last Updated**: 2026-04-04
**Owner**: Product Manager (John)
**Status**: Ready for scheduling
**Next Review**: After 3 interviews conducted (early trend check)

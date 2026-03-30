export interface OnboardingOption {
  id: string;
  name: string;
  description: string;
}

export const BUSINESS_GOALS: OnboardingOption[] = [
  {
    id: "lead-generation",
    name: "Lead Generation",
    description: "Qualify and convert inbound leads into appointments",
  },
  {
    id: "cold-outreach",
    name: "Cold Outreach",
    description: "Proactively contact prospects with personalized pitches",
  },
  {
    id: "customer-support",
    name: "Customer Support",
    description: "Handle inbound support calls and resolve issues",
  },
  {
    id: "appointment-reminders",
    name: "Appointment Reminders",
    description:
      "Automated reminders and confirmations for upcoming appointments",
  },
];

export const VOICE_OPTIONS: OnboardingOption[] = [
  {
    id: "avery",
    name: "Avery",
    description: "Warm, professional tone ideal for customer-facing outreach",
  },
  {
    id: "jordan",
    name: "Jordan",
    description: "Confident, energetic great for sales and lead gen",
  },
  {
    id: "casey",
    name: "Casey",
    description: "Calm, reassuring suited for support and reminders",
  },
  {
    id: "morgan",
    name: "Morgan",
    description: "Authoritative, clear strong for B2B cold calling",
  },
];

export const INTEGRATION_OPTIONS: OnboardingOption[] = [
  {
    id: "gohighlevel",
    name: "GoHighLevel",
    description: "Sync contacts, deals, and pipeline data automatically",
  },
  {
    id: "hubspot",
    name: "HubSpot",
    description: "Push leads and activity data into your HubSpot CRM",
  },
  {
    id: "skip",
    name: "Skip for now",
    description: "You can always connect a CRM later in settings",
  },
];

export const SAFETY_LEVELS: OnboardingOption[] = [
  {
    id: "strict",
    name: "Strict (recommended)",
    description:
      "Full DNC/TCPA compliance checks, auto-escalation, and audit logging",
  },
  {
    id: "moderate",
    name: "Moderate",
    description: "Standard compliance checks with manual escalation controls",
  },
  {
    id: "relaxed",
    name: "Relaxed",
    description: "Minimal compliance checks for internal use only",
  },
];

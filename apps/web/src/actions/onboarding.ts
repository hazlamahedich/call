"use server";

import { auth } from "@clerk/nextjs/server";
import type {
  Agent,
  OnboardingPayload,
  OnboardingStatus,
  DbScript,
} from "@call/types";

import { API_URL } process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function getOnboardingStatus(): Promise<{
  data: OnboardingStatus | null;
  error: string | null;
}> {
  try {
    const { getToken } = await auth();
    const token = await getToken();

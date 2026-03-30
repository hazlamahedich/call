"use client";

import { useOrganization } from "@clerk/nextjs";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getOnboardingStatus } from "@/actions/onboarding";

export function OnboardingGuard({ children }: { children: React.ReactNode }) {
  const { organization } = useOrganization();
  const router = useRouter();
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    if (!organization) {
      setChecking(false);
      return;
    }
    getOnboardingStatus().then(({ data }) => {
      if (data && !data.completed) {
        router.push("/onboarding");
      } else {
        setChecking(false);
      }
    });
  }, [organization, router]);

  if (checking) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="animate-pulse space-y-4 w-full max-w-md px-4">
          <div className="h-8 bg-muted rounded w-1/3" />
          <div className="h-4 bg-muted rounded w-2/3" />
          <div className="h-32 bg-muted rounded" />
        </div>
      </div>
    );
  }

  return <>{children}</>;
}

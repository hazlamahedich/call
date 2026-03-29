"use client";

import { useState } from "react";
import { useOrganization } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { createOrganization } from "@/actions/organization";
import { OrgType, PlanType } from "@call/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { StatusMessage } from "@/components/ui/status-message";

export default function NewOrganizationPage() {
  const router = useRouter();
  const { organization } = useOrganization();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    name: "",
    type: "agency" as OrgType,
    plan: "pro" as PlanType,
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      const slug = formData.name.toLowerCase().replace(/\s+/g, "-");
      const result = await createOrganization({
        name: formData.name,
        slug,
        type: formData.type,
        plan: formData.plan,
      });

      if (result.error) {
        setError(result.error);
      } else {
        router.push("/dashboard");
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setIsLoading(false);
    }
  };

  const selectClassName =
    "w-full rounded-md border border-input bg-background px-md py-2 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <Card className="w-full max-w-md p-8">
        <h1 className="mb-6 text-2xl font-bold text-foreground">
          Create Organization
        </h1>

        {error && (
          <StatusMessage variant="error" className="mb-4">
            {error}
          </StatusMessage>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="org-name"
              className="mb-2 block text-sm text-muted-foreground"
            >
              Organization Name
            </label>
            <Input
              id="org-name"
              type="text"
              value={formData.name}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, name: e.target.value }))
              }
              required
            />
          </div>

          <div>
            <label
              htmlFor="org-type"
              className="mb-2 block text-sm text-muted-foreground"
            >
              Type
            </label>
            <select
              id="org-type"
              value={formData.type}
              onChange={(e) =>
                setFormData((prev) => ({
                  ...prev,
                  type: e.target.value as OrgType,
                }))
              }
              className={selectClassName}
            >
              <option value="agency">Agency</option>
            </select>
          </div>

          <div>
            <label
              htmlFor="org-plan"
              className="mb-2 block text-sm text-muted-foreground"
            >
              Plan
            </label>
            <select
              id="org-plan"
              value={formData.plan}
              onChange={(e) =>
                setFormData((prev) => ({
                  ...prev,
                  plan: e.target.value as PlanType,
                }))
              }
              className={selectClassName}
            >
              <option value="free">Free</option>
              <option value="pro">Pro</option>
              <option value="enterprise">Enterprise</option>
            </select>
          </div>

          <Button type="submit" disabled={isLoading} className="w-full">
            {isLoading ? "Creating..." : "Create Organization"}
          </Button>
        </form>
      </Card>
    </div>
  );
}

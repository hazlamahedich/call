"use client";

import { useState } from "react";
import { useOrganization } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { createOrganization } from "@/actions/organization";
import { OrgType, PlanType } from "@call/types";

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

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#09090B]">
      <div className="w-full max-w-md rounded-lg border border-[#27272A] bg-[#18181B] p-8">
        <h1 className="mb-6 text-2xl font-bold text-white">
          Create Organization
        </h1>

        {error && (
          <div className="mb-4 rounded bg-red-900/20 p-3 text-red-400">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-2 block text-sm text-zinc-400">
              Organization Name
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, name: e.target.value }))
              }
              className="w-full rounded border border-[#27272A] bg-[#09090B] px-3 py-2 text-white"
              required
            />
          </div>

          <div>
            <label className="mb-2 block text-sm text-zinc-400">Type</label>
            <select
              value={formData.type}
              onChange={(e) =>
                setFormData((prev) => ({
                  ...prev,
                  type: e.target.value as OrgType,
                }))
              }
              className="w-full rounded border border-[#27272A] bg-[#09090B] px-3 py-2 text-white"
            >
              <option value="agency">Agency</option>
            </select>
          </div>

          <div>
            <label className="mb-2 block text-sm text-zinc-400">Plan</label>
            <select
              value={formData.plan}
              onChange={(e) =>
                setFormData((prev) => ({
                  ...prev,
                  plan: e.target.value as PlanType,
                }))
              }
              className="w-full rounded border border-[#27272A] bg-[#09090B] px-3 py-2 text-white"
            >
              <option value="free">Free</option>
              <option value="pro">Pro</option>
              <option value="enterprise">Enterprise</option>
            </select>
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full rounded bg-[#10B981] px-4 py-2 font-medium text-white hover:bg-[#10B981]/90 disabled:opacity-50"
          >
            {isLoading ? "Creating..." : "Create Organization"}
          </button>
        </form>
      </div>
    </div>
  );
}

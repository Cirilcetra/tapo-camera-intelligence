"use client";

import { Suspense } from "react";
import { Spinner } from "@/components/ui/Spinner";
import DashboardContent from "./DashboardContent";

export default function DashboardPage() {
  return (
    <Suspense
      fallback={
        <div className="flex justify-center py-16">
          <Spinner size={28} />
        </div>
      }
    >
      <DashboardContent />
    </Suspense>
  );
}

"use client";

import { useCameras } from "@/hooks/useCameras";
import { CameraCard } from "@/components/camera/CameraCard";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { Spinner } from "@/components/ui/Spinner";
import { Camera, Plus } from "lucide-react";
import Link from "next/link";

export default function CamerasPage() {
  const { cameras, loading, error, deleteCamera } = useCameras();

  const handleDelete = async (id: number) => {
    if (confirm("Remove this camera?")) {
      await deleteCamera(id);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-zinc-100">Cameras</h2>
          <p className="mt-0.5 text-sm text-zinc-500">
            {cameras.length} camera{cameras.length !== 1 ? "s" : ""} configured
          </p>
        </div>
        <Link href="/cameras/add">
          <Button>
            <Plus className="h-4 w-4" />
            Add Camera
          </Button>
        </Link>
      </div>

      {loading && (
        <div className="flex justify-center py-16">
          <Spinner size={28} />
        </div>
      )}

      {error && (
        <p className="rounded-lg border border-red-800 bg-red-900/20 px-4 py-3 text-sm text-red-400">
          {error}
        </p>
      )}

      {!loading && cameras.length === 0 && (
        <EmptyState
          icon={Camera}
          title="No cameras added yet"
          description="Add your first Tapo or RTSP camera to get started"
          action={
            <Link href="/cameras/add">
              <Button>
                <Plus className="h-4 w-4" />
                Add Camera
              </Button>
            </Link>
          }
        />
      )}

      {!loading && cameras.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {cameras.map((cam) => (
            <CameraCard key={cam.id} camera={cam} onDelete={handleDelete} />
          ))}
        </div>
      )}
    </div>
  );
}

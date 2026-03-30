"use client";

import { useState, useRef, useCallback } from "react";
import { Upload } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

const MAX_FILE_SIZE = 2 * 1024 * 1024;
const MAGIC_BYTES: Record<string, number[]> = {
  "image/png": [0x89, 0x50, 0x4e, 0x47],
  "image/jpeg": [0xff, 0xd8, 0xff],
  "image/svg+xml": [],
};
const MAX_WIDTH = 120;
const MAX_HEIGHT = 40;

interface LogoUploadProps {
  currentLogo: string | null;
  onLogoChange: (dataUrl: string | null) => void;
  reducedMotion?: boolean;
}

function checkMagicBytes(buf: ArrayBuffer): string | null {
  const bytes = new Uint8Array(buf.slice(0, 8));
  if (
    bytes[0] === 0x89 &&
    bytes[1] === 0x50 &&
    bytes[2] === 0x4e &&
    bytes[3] === 0x47
  )
    return "image/png";
  if (bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff)
    return "image/jpeg";
  const text = new TextDecoder().decode(bytes);
  if (text.trimStart().startsWith("<")) return "image/svg+xml";
  return null;
}

function readFileAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = () => reject(new Error("Failed to read file"));
    reader.readAsDataURL(file);
  });
}

function resizeImage(file: File, dataUrl: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      let { width, height } = img;
      if (width > MAX_WIDTH) {
        height = (height * MAX_WIDTH) / width;
        width = MAX_WIDTH;
      }
      if (height > MAX_HEIGHT) {
        width = (width * MAX_HEIGHT) / height;
        height = MAX_HEIGHT;
      }
      const canvas = document.createElement("canvas");
      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext("2d");
      if (!ctx) return reject(new Error("Canvas not supported"));
      ctx.drawImage(img, 0, 0, width, height);
      URL.revokeObjectURL(img.src);
      resolve(canvas.toDataURL("image/png"));
    };
    img.onerror = () => {
      URL.revokeObjectURL(img.src);
      reject(new Error("Failed to load image"));
    };
    img.src = dataUrl;
  });
}

export function LogoUpload({
  currentLogo,
  onLogoChange,
  reducedMotion,
}: LogoUploadProps) {
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const processFile = useCallback(
    async (file: File) => {
      setError(null);
      if (file.size > MAX_FILE_SIZE) {
        setError("File exceeds 2MB limit");
        return;
      }
      const buf = await file.slice(0, 8).arrayBuffer();
      const mime = checkMagicBytes(buf);
      if (!mime) {
        setError("Invalid file type. Accept PNG, JPG, or SVG.");
        return;
      }
      try {
        const dataUrl = await readFileAsDataUrl(file);
        if (mime === "image/svg+xml") {
          onLogoChange(dataUrl);
        } else {
          const objectUrl = URL.createObjectURL(file);
          const resized = await resizeImage(file, objectUrl);
          onLogoChange(resized);
        }
      } catch {
        setError("Failed to process image");
      }
    },
    [onLogoChange],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) processFile(file);
    },
    [processFile],
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) processFile(file);
    },
    [processFile],
  );

  return (
    <Card variant="standard" className="p-0">
      <CardContent className="p-md">
        <div
          role="button"
          tabIndex={0}
          className={cn(
            "flex min-h-[80px] cursor-pointer flex-col items-center justify-center gap-xs rounded-md border-2 border-dashed border-border p-md transition-colors",
            dragOver && "border-neon-emerald bg-neon-emerald/5",
          )}
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") inputRef.current?.click();
          }}
        >
          {currentLogo ? (
            <img
              src={currentLogo}
              alt="Brand logo"
              className="max-h-[40px] max-w-[120px] object-contain"
            />
          ) : (
            <>
              <Upload className="size-6 text-muted-foreground" />
              <span className="text-xs text-muted-foreground">
                Drop logo or click to upload
              </span>
              <span className="text-[10px] text-muted-foreground/60">
                PNG, JPG, SVG — max 2MB
              </span>
            </>
          )}
        </div>
        {currentLogo && (
          <button
            type="button"
            className="mt-xs text-xs text-muted-foreground hover:text-foreground"
            onClick={(e) => {
              e.stopPropagation();
              onLogoChange(null);
            }}
          >
            Remove logo
          </button>
        )}
        {error && <p className="mt-xs text-xs text-destructive">{error}</p>}
        <input
          ref={inputRef}
          type="file"
          accept="image/png,image/jpeg,image/svg+xml"
          aria-label="Upload logo"
          className="hidden"
          onChange={handleChange}
        />
      </CardContent>
    </Card>
  );
}

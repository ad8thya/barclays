"use client";

export default function SkeletonBlock({ width = "100%", height = "16px" }) {
  return (
    <div
      style={{ width, height }}
      className="rounded skeleton"
    />
  );
}

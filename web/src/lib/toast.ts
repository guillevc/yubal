import { addToast } from "@heroui/react";

type ToastColor = "success" | "danger" | "warning" | "primary";

interface ToastOptions {
  title: string;
  description: string;
}

function showToast(color: ToastColor, options: ToastOptions): void {
  addToast({ ...options, color });
}

export function showSuccessToast(title: string, description: string): void {
  showToast("success", { title, description });
}

export function showErrorToast(title: string, description: string): void {
  showToast("danger", { title, description });
}

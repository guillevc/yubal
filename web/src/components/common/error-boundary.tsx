import { AlertTriangle } from "lucide-react";
import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error("ErrorBoundary caught an error:", error, errorInfo);
  }

  render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="bg-background text-foreground dark flex min-h-screen flex-col items-center justify-center gap-1">
          <AlertTriangle className="text-danger h-12 w-12" />
          <h1 className="text-lg font-semibold">Something went wrong</h1>
          <p className="text-foreground-500 max-w-md text-center text-sm">
            An unexpected error occurred. Please refresh the page.
          </p>
          {this.state.error && (
            <pre className="bg-content1 text-content1-foreground max-w-lg overflow-auto rounded-lg p-4 mt-4 font-mono text-xs">
              {this.state.error.message}
            </pre>
          )}
        </div>
      );
    }

    return this.props.children;
  }
}

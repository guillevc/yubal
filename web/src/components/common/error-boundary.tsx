import { Button } from "@heroui/react";
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

  handleRetry = (): void => {
    this.setState({ hasError: false, error: null });
  };

  render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="flex min-h-screen flex-col items-center justify-center gap-4 p-8">
          <AlertTriangle className="text-danger h-12 w-12" />
          <h1 className="text-foreground text-xl font-semibold">
            Something went wrong
          </h1>
          <p className="text-foreground-500 max-w-md text-center">
            An unexpected error occurred. Please try refreshing the page.
          </p>
          {this.state.error && (
            <pre className="bg-content2 text-foreground-600 max-w-lg overflow-auto rounded-lg p-4 text-xs">
              {this.state.error.message}
            </pre>
          )}
          <div className="flex gap-2">
            <Button color="primary" onPress={this.handleRetry}>
              Try again
            </Button>
            <Button variant="flat" onPress={() => window.location.reload()}>
              Refresh page
            </Button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

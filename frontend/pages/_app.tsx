import "@/styles/globals.css";
import type { AppProps } from "next/app";
import { ClerkProvider } from "@clerk/nextjs";
import { ToastContainer } from "@/components/Toast";
import ErrorBoundary from "@/components/ErrorBoundary";

const PUBLISHABLE_KEY = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;

export default function App({ Component, pageProps }: AppProps) {
  return (
    <ErrorBoundary>
      <ClerkProvider publishableKey={PUBLISHABLE_KEY} {...pageProps}>
        <Component {...pageProps} />
        <ToastContainer />
      </ClerkProvider>
    </ErrorBoundary>
  );
}

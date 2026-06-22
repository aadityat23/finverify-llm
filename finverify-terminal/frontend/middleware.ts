import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * Middleware — Conditional Clerk Auth
 * Only activates Clerk if NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY is set.
 * Without it, everything is public (anonymous mode works).
 */

const clerkKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;

export default async function middleware(req: NextRequest) {
  // If Clerk is not configured, pass through all requests
  if (!clerkKey) {
    return NextResponse.next();
  }

  // Dynamically import Clerk middleware only when configured
  try {
    const { clerkMiddleware, createRouteMatcher } = await import(
      "@clerk/nextjs/server"
    );

    const isProtectedRoute = createRouteMatcher([
      "/dashboard(.*)",
      "/history(.*)",
    ]);

    // Create and run Clerk middleware
    const clerkMw = clerkMiddleware((auth: any, request: any) => {
      if (isProtectedRoute(request)) {
        auth.protect();
      }
    });

    return clerkMw(req, {} as any);
  } catch {
    // If Clerk import fails, pass through
    return NextResponse.next();
  }
}

export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
    "/__clerk/:path*",
  ],
};

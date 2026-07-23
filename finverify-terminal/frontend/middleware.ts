import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * Middleware — Pass-through
 * Clerk auth has been stripped (Session 2.3).
 * All routes are public. Re-add Clerk middleware when auth is ready.
 */

export default function middleware(_req: NextRequest) {
  return NextResponse.next();
}

export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
  ],
};

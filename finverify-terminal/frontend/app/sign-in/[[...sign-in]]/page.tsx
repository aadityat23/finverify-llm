import { SignIn } from "@clerk/nextjs";

export default function SignInPage() {
  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <SignIn
        appearance={{
          elements: {
            rootBox: "mx-auto",
            card: "bg-[#0a0a0a] border border-t-border shadow-2xl",
          },
        }}
      />
    </div>
  );
}
